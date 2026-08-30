"""
keys.py — loads your API keys from a file called keys.env.

WHY THIS EXISTS
Your keys should live in exactly one place, and that place should never be
shared, emailed, screenshotted, or uploaded anywhere. This reads them from a
file that sits next to the code but is kept out of it.

HOW TO USE
1. In the same folder as this file, create a plain text file named:  keys.env
2. Put your keys in it, one per line, like this (no quotes, no spaces around =):

       HKUST_API_KEY=paste-your-hkust-key-here
       ANTHROPIC_API_KEY=paste-your-anthropic-key-here
       DEEPSEEK_API_KEY=paste-your-deepseek-key-here

3. Save it. That's all — the code reads it automatically.

If you ever put this project on GitHub or send it to a co-author, delete or
exclude keys.env. Everything else is safe to share.
"""

import os

KEYS_FILE = "keys.env"


def load_keys(path=KEYS_FILE):
    """Reads keys.env and puts the values into the environment for this session."""
    here = os.path.dirname(os.path.abspath(__file__))
    full = path if os.path.isabs(path) else os.path.join(here, path)

    if not os.path.exists(full):
        return False

    loaded = []
    with open(full, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name, value = name.strip(), value.strip().strip('"').strip("'")
            if value:
                os.environ[name] = value
                loaded.append(name)

    if loaded:
        print(f"Loaded keys: {', '.join(loaded)}")
    return True


def check():
    """Tells you which keys are present, without ever printing their values."""
    load_keys()
    for name in ["HKUST_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
                 "AZURE_OPENAI_API_KEY"]:
        v = os.environ.get(name)
        if v:
            print(f"  {name}: set  (ends ...{v[-4:]})")
        else:
            print(f"  {name}: not set")


if __name__ == "__main__":
    check()
