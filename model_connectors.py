"""
model_connectors.py — the bridge between the agent loop and a real AI model.

WHERE YOUR API KEY GOES
-----------------------
Nowhere in this file. The key is read from an "environment variable", which is
a setting stored on your own computer, outside the code. This matters because
code gets shared, copied into papers, and pushed to GitHub. Keys should not
travel with it.

To set it, open a terminal and run ONE of these before running the experiment:

    Mac / Linux:
        export ANTHROPIC_API_KEY="sk-ant-your-key-here"

    Windows PowerShell:
        $env:ANTHROPIC_API_KEY="sk-ant-your-key-here"

That setting lasts until you close the terminal. To make it permanent, put the
same line in your shell profile file — ask me when you get there and I will
walk you through it for your specific machine.

NEVER paste your key into a chat, a document, or this file.
"""

import os


# ---------------------------------------------------------------------------
# Anthropic (Claude)
# ---------------------------------------------------------------------------

def make_anthropic_model(model="claude-sonnet-4-6", max_tokens=4000):
    """Returns a function the agent loop can call.

    The loop does not know or care that this talks to a real API — it has the
    same shape as the fake scripted model used in testing.
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run:  pip install anthropic")

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. See the instructions at the top of this file."
        )

    client = anthropic.Anthropic(api_key=key)

    def call(system, messages, tools):
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools,
        )
        # Convert the SDK's response object into the plain dictionary shape
        # the agent loop expects.
        content = []
        for block in resp.content:
            if block.type == "text":
                content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        return {"content": content, "stop_reason": resp.stop_reason}

    call.model_id = model
    return call


# ---------------------------------------------------------------------------
# Azure OpenAI  (if you use your employer's deployment)
# ---------------------------------------------------------------------------

def make_azure_model(deployment=None, max_tokens=4000):
    """Azure needs THREE settings, not one:

        AZURE_OPENAI_API_KEY    - the key
        AZURE_OPENAI_ENDPOINT   - e.g. https://your-resource.openai.azure.com/openai/v1/
        AZURE_OPENAI_DEPLOYMENT - the name your IT team gave the model deployment

    Note the deployment name is NOT the model name. That difference is the most
    common source of confusion with Azure.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Run:  pip install openai")

    key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    deployment = deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT")

    missing = [n for n, v in [("AZURE_OPENAI_API_KEY", key),
                              ("AZURE_OPENAI_ENDPOINT", endpoint),
                              ("AZURE_OPENAI_DEPLOYMENT", deployment)] if not v]
    if missing:
        raise RuntimeError(f"Not set: {', '.join(missing)}")

    client = OpenAI(api_key=key, base_url=endpoint)

    def to_openai_tools(tools):
        """Anthropic and OpenAI describe tools differently. This translates."""
        return [{"type": "function",
                 "function": {"name": t["name"],
                              "description": t["description"],
                              "parameters": t["input_schema"]}}
                for t in tools]

    def call(system, messages, tools):
        # Translate the conversation into OpenAI's format.
        oai_messages = [{"role": "system", "content": system}]
        for m in messages:
            if isinstance(m.get("content"), str):
                oai_messages.append({"role": m["role"], "content": m["content"]})
            else:
                # Tool results and assistant tool calls need restructuring.
                for block in m["content"]:
                    if block.get("type") == "tool_result":
                        oai_messages.append({"role": "tool",
                                             "tool_call_id": block["tool_use_id"],
                                             "content": block["content"]})
                    elif block.get("type") == "text":
                        oai_messages.append({"role": m["role"], "content": block["text"]})
                    elif block.get("type") == "tool_use":
                        oai_messages.append({
                            "role": "assistant",
                            "tool_calls": [{"id": block["id"], "type": "function",
                                            "function": {"name": block["name"],
                                                         "arguments": str(block["input"])}}],
                        })

        resp = client.chat.completions.create(
            model=deployment,
            max_tokens=max_tokens,
            messages=oai_messages,
            tools=to_openai_tools(tools),
        )
        choice = resp.choices[0]
        content = []
        if choice.message.content:
            content.append({"type": "text", "text": choice.message.content})
        for tc in (choice.message.tool_calls or []):
            import json as _json
            content.append({"type": "tool_use", "id": tc.id, "name": tc.function.name,
                            "input": _json.loads(tc.function.arguments)})
        stop = "end_turn" if choice.finish_reason == "stop" else "tool_use"
        return {"content": content, "stop_reason": stop}

    call.model_id = f"azure:{deployment}"
    return call
