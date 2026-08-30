# Setup — running the experiment on your own machine

You need to run this on your computer rather than in our chat, because only
your machine can reach the HKUST endpoint.

Everything below assumes a Mac. Anything in a grey box is typed into Terminal.

---

## 1. Open Terminal

Press `Cmd + Space`, type `Terminal`, press Enter. A window with text appears.
This is where you type commands.

---

## 2. Check Python is installed

```
python3 --version
```

You should see something like `Python 3.11.x`. If you get "command not found",
install it from python.org and come back.

---

## 3. Put the project somewhere sensible

Download all the project files into one folder — for example a folder called
`intent-drift` inside your Documents.

Then point Terminal at that folder:

```
cd ~/Documents/intent-drift
```

(`cd` means "change directory". The `~` means your home folder.)

Check you're in the right place:

```
ls
```

You should see the file names listed: `sandbox.py`, `agent_loop.py`, and so on.

---

## 4. Create your keys file

In that same folder, create a plain text file called exactly `keys.env`.

Easiest way — run this, which creates it and opens it in TextEdit:

```
touch keys.env && open -e keys.env
```

Type your key into it like this, then save and close:

```
HKUST_API_KEY=your-hkust-subscription-key
```

No quotes. No spaces around the `=`.

Check it worked:

```
python3 keys.py
```

It will confirm which keys are set, showing only the last four characters —
never the whole value.

---

## 5. Test the connection before anything else

This sends one tiny message and costs a fraction of a cent. Replace `gpt-4o`
with whatever deployment name HKUST actually offers:

```
python3 hkust_connector.py gpt-4o
```

**If it prints `SUCCESS: working`** — you're connected, move to step 6.

**If it fails** — that's expected on the first try. The error message lists the
likely causes in order. Send me the exact error text and the deployment names
from the portal, and I'll correct the settings.

---

## 6. Run the smoke test

One run. One condition. Full detail printed. Then it stops.

```
python3 batch_runner.py
```

By default this still uses the fake scripted model. To switch to the real one,
open `batch_runner.py` in a text editor and find the block at the very bottom
marked `WHEN YOU HAVE YOUR KEY`. Follow the instructions in the comments there.

Read the output carefully before going further. This is the moment we find out
whether the scenario works.

---

## 7. Only then, the full matrix

Do not skip step 6. Thirty replicates of a broken scenario is thirty times the
cost of finding out it was broken.

---

## Safety notes

- `keys.env` is the only file containing secrets. Never share it, screenshot
  it, or upload it.
- If a key is ever exposed, regenerate it in the portal immediately. Old keys
  die the instant you regenerate.
- Everything else in this folder is safe to share with a co-author or publish
  alongside the paper.
