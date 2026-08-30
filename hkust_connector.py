"""
hkust_connector.py — connects to HKUST's Azure OpenAI via their API gateway.

HKUST puts an "API Management" gateway in front of Azure OpenAI. That means
the address and the authentication header are slightly different from raw
Azure OpenAI:

  - the key goes in a header called  Ocp-Apim-Subscription-Key
    (raw Azure OpenAI uses  api-key  instead)
  - the base URL is HKUST's gateway, not a Microsoft address

Everything else works the same way.
"""

import os
import json
import urllib.request

from keys import load_keys

load_keys()   # reads keys.env into the environment, if that file exists


# Confirmed from the HKUST portal API definition page:
#   POST https://hkust.azure-api.net/openai/deployments/{deployment-id}/chat/completions?api-version=2024-10-21
DEFAULT_BASE = "https://hkust.azure-api.net"
DEFAULT_API_VERSION = "2024-10-21"


def _build_url(base, deployment, api_version):
    return (f"{base.rstrip('/')}/openai/deployments/{deployment}"
            f"/chat/completions?api-version={api_version}")


def make_hkust_model(deployment, api_version=DEFAULT_API_VERSION,
                     base_url=None, max_tokens=4000):
    """Returns a function the agent loop can call.

    deployment : the model deployment name, e.g. "gpt-4o".
                 This is NOT the model name — HKUST chooses these.
    """
    key = os.environ.get("HKUST_API_KEY")
    if not key:
        raise RuntimeError(
            "HKUST_API_KEY is not set.\n"
            "Create a file called keys.env next to this script containing:\n"
            '    HKUST_API_KEY=your-key-here'
        )

    base = (base_url or os.environ.get("HKUST_BASE_URL") or DEFAULT_BASE).rstrip("/")
    url = _build_url(base, deployment, api_version)

    def to_openai_tools(tools):
        """Translates our tool descriptions into OpenAI's format."""
        return [{"type": "function",
                 "function": {"name": t["name"],
                              "description": t["description"],
                              "parameters": t["input_schema"]}}
                for t in tools]

    def to_openai_messages(system, messages):
        """Translates the conversation into OpenAI's format."""
        out = [{"role": "system", "content": system}]
        for m in messages:
            if isinstance(m.get("content"), str):
                out.append({"role": m["role"], "content": m["content"]})
                continue
            tool_calls = []
            for block in m["content"]:
                t = block.get("type")
                if t == "text":
                    out.append({"role": m["role"], "content": block["text"]})
                elif t == "tool_use":
                    tool_calls.append({
                        "id": block["id"], "type": "function",
                        "function": {"name": block["name"],
                                     "arguments": json.dumps(block["input"])},
                    })
                elif t == "tool_result":
                    out.append({"role": "tool",
                                "tool_call_id": block["tool_use_id"],
                                "content": str(block["content"])})
            if tool_calls:
                out.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
        return out

    def call(system, messages, tools):
        payload = {
            "messages": to_openai_messages(system, messages),
            "tools": to_openai_tools(tools),
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": key,
                "api-key": key,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode("utf-8"))

        choice = data["choices"][0]
        msg = choice["message"]

        content = []
        if msg.get("content"):
            content.append({"type": "text", "text": msg["content"]})
        for tc in (msg.get("tool_calls") or []):
            content.append({
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["function"]["name"],
                "input": json.loads(tc["function"]["arguments"]),
            })

        stop = "end_turn" if choice.get("finish_reason") == "stop" else "tool_use"
        return {"content": content, "stop_reason": stop}

    call.model_id = f"hkust:{deployment}"
    return call


COMMON_DEPLOYMENTS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini",
    "gpt-4", "gpt-4-turbo", "gpt-35-turbo", "gpt-5", "gpt-5-mini",
]


def _try_one(deployment, api_version, base, key, verbose=True):
    url = _build_url(base, deployment, api_version)
    payload = {"messages": [{"role": "user", "content": "Reply with the single word: working"}],
               "max_tokens": 10}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Ocp-Apim-Subscription-Key": key,
                 "api-key": key},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        return True, data["choices"][0]["message"]["content"]
    except Exception as exc:
        detail = ""
        body = getattr(exc, "read", None)
        if body:
            try:
                detail = body().decode("utf-8")[:300]
            except Exception:
                pass
        return False, f"{exc} {detail}".strip()


def test_connection(deployment=None, api_version=DEFAULT_API_VERSION, base_url=None):
    """Checks the address, key, and deployment name.

    If no deployment is given, tries the common names one by one and reports
    which works. Each attempt costs a fraction of a cent.
    """
    key = os.environ.get("HKUST_API_KEY")
    if not key:
        print("FAIL: HKUST_API_KEY not set. Create keys.env — see SETUP.md.")
        return None

    base = (base_url or os.environ.get("HKUST_BASE_URL") or DEFAULT_BASE).rstrip("/")
    candidates = [deployment] if deployment else COMMON_DEPLOYMENTS

    print(f"Base URL: {base}")
    print(f"API version: {api_version}")
    print(f"Trying {len(candidates)} deployment name(s)...\n")

    for dep in candidates:
        ok, msg = _try_one(dep, api_version, base, key)
        if ok:
            print(f"  {dep:<16} SUCCESS — model replied: {msg!r}")
            print(f"\nUse this deployment name: {dep}")
            return dep
        short = msg.split("\n")[0][:150]
        print(f"  {dep:<16} failed — {short}")

    print("\nNone worked. Send me the error text above.")
    print("Common causes:")
    print("  - The deployment has a custom name (check Products page in the portal)")
    print("  - Your subscription is not approved for this API")
    print("  - A different api-version is required")
    return None


if __name__ == "__main__":
    import sys
    dep = sys.argv[1] if len(sys.argv) > 1 else None
    test_connection(dep)
