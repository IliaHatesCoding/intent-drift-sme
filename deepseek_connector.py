"""
deepseek_connector.py — connects to DeepSeek's API.

DeepSeek uses an OpenAI-compatible interface, so this is close to the HKUST
connector but pointed at a different address with a different auth header.

SETUP
  1. Create an account at platform.deepseek.com
  2. Add credit (small amounts go a long way — it is substantially cheaper
     per token than the Western providers)
  3. Create an API key
  4. Add ONE line to your keys.env file:

         DEEPSEEK_API_KEY=your-key-here

  5. Test:   python3 deepseek_connector.py

MODELS
  deepseek-chat      general model, supports tool use — use this one
  deepseek-reasoner  reasoning model; tool support differs, avoid for now
"""

import os
import json
import urllib.request

from keys import load_keys

load_keys()

BASE_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


def _to_openai_tools(tools):
    return [{"type": "function",
             "function": {"name": t["name"],
                          "description": t["description"],
                          "parameters": t["input_schema"]}}
            for t in tools]


def _to_openai_messages(system, messages):
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


def _post(payload, key, timeout=180):
    req = urllib.request.Request(
        BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def make_deepseek_model(model=DEFAULT_MODEL, max_tokens=4000):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set.\n"
            "Add this line to keys.env:\n"
            "    DEEPSEEK_API_KEY=your-key-here")

    def call(system, messages, tools):
        payload = {
            "model": model,
            "messages": _to_openai_messages(system, messages),
            "tools": _to_openai_tools(tools),
            "max_tokens": max_tokens,
        }
        data = _post(payload, key)
        choice = data["choices"][0]
        msg = choice["message"]

        content = []
        if msg.get("content"):
            content.append({"type": "text", "text": msg["content"]})
        for tc in (msg.get("tool_calls") or []):
            try:
                args = json.loads(tc["function"]["arguments"])
            except (json.JSONDecodeError, TypeError):
                args = {}
            content.append({"type": "tool_use", "id": tc["id"],
                            "name": tc["function"]["name"], "input": args})

        stop = "end_turn" if choice.get("finish_reason") == "stop" else "tool_use"
        return {"content": content, "stop_reason": stop}

    call.model_id = f"deepseek:{model}"
    return call


def test_connection(model=DEFAULT_MODEL):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("FAIL: DEEPSEEK_API_KEY not set. Add it to keys.env — see the top of this file.")
        return False

    print(f"Endpoint: {BASE_URL}")
    print(f"Model:    {model}\n")
    try:
        data = _post({"model": model,
                      "messages": [{"role": "user",
                                    "content": "Reply with the single word: working"}],
                      "max_tokens": 10}, key, timeout=60)
        print("SUCCESS — model replied:", repr(data["choices"][0]["message"]["content"]))
        return True
    except Exception as exc:
        detail = ""
        if hasattr(exc, "read"):
            try:
                detail = exc.read().decode("utf-8")[:300]
            except Exception:
                pass
        print(f"FAILED: {exc} {detail}".strip())
        print("\nLikely causes:")
        print("  1. Key not yet active — new keys can take a minute")
        print("  2. No credit on the account")
        print("  3. Model name wrong — try 'deepseek-chat'")
        return False


if __name__ == "__main__":
    import sys
    test_connection(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL)
