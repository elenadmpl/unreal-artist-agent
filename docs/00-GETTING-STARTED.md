# Getting started — the gentle version

This is the long version of the README's setup, with every click spelled out
and nothing assumed. Total time: ~15 minutes plus Unreal download time.

## Step 0 — words you'll see (30 seconds)

- **Unreal Editor** — the big program where you make games/scenes.
- **Project** — one game/scene you're working on. Plugins are per-project.
- **Claude Code** — an AI agent that runs in a terminal window. You type to it
  in normal English; it does things on your computer for you.
- **MCP** — just a standard way for AI agents to plug into other programs.
  Unreal 5.8 has it built in. You never have to think about it again.
- **Blueprint** — Unreal's visual scripting: logic made of boxes and wires.

## Step 1 — install the three programs

1. **Unreal Engine 5.8+**: install the [Epic Games Launcher](https://store.epicgames.com/download),
   then inside it: Unreal Engine → Library → **＋** → install 5.8.
2. **Python**: [python.org/downloads](https://www.python.org/downloads/) → big yellow button.
   ⚠️ **Windows: on the first install screen, tick "Add Python to PATH".**
   That checkbox is the #1 cause of setup problems.
3. **Claude Code**: follow [the official install guide](https://docs.claude.com/en/docs/claude-code/overview).
   Afterwards, typing `claude` in a terminal should start it.

## Step 2 — get this folder

With git: `git clone https://github.com/elenadimopoulou/unreal-artist-agent.git`
Without git: green **Code** button on the GitHub page → **Download ZIP** → unzip
somewhere you'll find it (e.g. `Documents/unreal-artist-agent`).

## Step 3 — prepare your Unreal project (once per project)

Open your project (or make a new one — the **Games → Third Person** template is
great for playing around), then:

1. **Edit → Plugins**. Search and tick each of:
   - **Unreal MCP** ← lets the agent drive the editor
   - **AllToolsets** ← the full toolbox (without it the agent can barely build)
   - **Python Editor Script Plugin** ← usually already ticked
   Click **Restart Now** when the banner appears.
2. **Edit → Project Settings**, type "python" in the search box, and tick
   **Remote Execution**. Restart the editor again.
   *(This is what powers Blueprint reading, scene reports and screenshots.)*
3. If Windows Firewall pops up asking about UnrealEditor: **Allow**.

## Step 4 — start the server (each editor session)

Press the **backtick key `` ` ``** (top-left, under Esc) — a command bar appears
at the bottom of the editor. Type:

```
ModelContextProtocol.StartServer 8123
```

To never type it again: **Edit → Editor Preferences** → search "Model Context
Protocol" → tick **Auto Start Server**, set **Port** to `8123`.

> Why 8123 and not the default 8000? Port 8000 is popular — lots of other
> software squats on it. 8123 rarely collides. If you *do* change it, also
> change the number in this repo's `.mcp.json`.

## Step 5 — first contact

1. Open a terminal **in this repo's folder**
   (Windows: open the folder in Explorer, click the address bar, type `cmd`, Enter).
2. Type `claude` to start Claude Code. It will notice the `unreal` MCP server
   from `.mcp.json` — approve it.
3. Type **`/doctor`**. The agent runs its health check and fixes problems with
   you. Three green `[OK]`s = you're ready.
4. When the agent asks permission to run `python tools/ue.py ...` commands,
   choose **"Always allow"** — these are this repo's read-only tools for
   looking at your scene and Blueprints.

Now try your first scene: [01-YOUR-FIRST-SCENE.md](01-YOUR-FIRST-SCENE.md) 🎉

## Something didn't work?

That's normal the first time — it's plumbing, not you.
Go straight to [04-TROUBLESHOOTING.md](04-TROUBLESHOOTING.md), or just tell
the agent what you saw and let it debug with you.
