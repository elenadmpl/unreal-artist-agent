# 🎨 Unreal Artist Agent

[![tests](https://github.com/elenadmpl/unreal-artist-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/elenadmpl/unreal-artist-agent/actions/workflows/tests.yml)

**An AI copilot for Unreal Engine, made for artists and beginners — no coding needed.**

You open your Unreal project, open this folder in [Claude Code](https://claude.com/claude-code),
and then you just… talk:

> *"Build me a small campfire clearing with warm evening light."*
> *"What does BP_Door actually do? Explain it like I've never coded."*
> *"Something in my level looks off — take a look and tell me what."*

The agent gets **hands** (it drives the Unreal editor through Epic's official
Unreal MCP plugin), **eyes** (it takes screenshots and reads them, and gets a
list of every actor with exact positions), and — the special feature of this
repo — **it can read Blueprints** and explain them to you in plain language,
so other people's projects and marketplace assets stop being black boxes.

The goal: something an artist can set up in 15 minutes without touching
code. MIT licensed — use it, fork it, remix it. 💛

---

## What you need

| Thing | Notes |
|---|---|
| **Unreal Engine 5.8+** | Free, via the [Epic Games Launcher](https://store.epicgames.com/download). 5.8 ships the Unreal MCP plugin this uses. |
| **Claude Code** | The AI agent. [Install guide](https://docs.claude.com/en/docs/claude-code/overview). |
| **Python 3.8+** | Free, from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add Python to PATH"** during install. |
| A computer that runs Unreal | Windows or macOS. 32 GB RAM recommended for real scenes. |

No Visual Studio. No compiling. No third-party plugins to download.

---

## Setup (about 15 minutes, one time)

### 1. Get this folder
```
git clone https://github.com/elenadimopoulou/unreal-artist-agent.git
cd unreal-artist-agent
```
(No git? Click the green **Code** button on GitHub → **Download ZIP** → unzip.)

### 2. Turn on three plugins in your Unreal project
Open your project in Unreal, then **Edit → Plugins**, search for and enable:

- ✅ **Unreal MCP** (the agent's hands)
- ✅ **AllToolsets** (gives the agent the full set of building tools)
- ✅ **Python Editor Script Plugin** (usually already on)

Restart the editor when it asks.

### 3. Turn on Remote Execution (for Blueprint reading)
**Edit → Project Settings** → search for **Python** → check **Remote Execution**.
Restart the editor once more. *(If Windows Firewall asks about UnrealEditor,
click Allow.)*

### 4. Start the connection
In the Unreal editor, press the **backtick key `` ` ``** (under Esc) to open the
console, and run:
```
ModelContextProtocol.StartServer 8123
```
> Do this each time you launch the editor — or make it automatic:
> **Edit → Editor Preferences → Model Context Protocol → Auto Start Server** (port 8123).

### 5. Say hello
Open a terminal in this folder, start Claude Code with `claude`, and type:
```
/doctor
```
The agent checks every connection and walks you through anything that's not
working. When the doctor is happy, you're done — forever. From now on it's
just: open project → open Claude Code → talk.

> 💡 The first few times, Claude Code will ask permission before running its
> tools (`python tools/ue.py ...`). They're all read-only. Pick **"Always
> allow"** and it won't ask again.

---

## Things to say to it

| You say | What happens |
|---|---|
| `/build a foggy forest path with god rays` | It builds, screenshots itself, checks its own work, and iterates. |
| `/read-blueprint BP_Door` | Plain-English explanation: what it is, when it fires, what you can tweak. |
| `/check-scene` | "Here's what's in your level, and here's what looks wrong." |
| `/real-world Athens at golden hour` | Streams the real Earth into your level (free Cesium plugin + a Google key). |
| `/undo` | Shows what the agent added since its last checkpoint, and removes it — only after you confirm. |
| `/what-is Nanite` | Friendly explanations of any Unreal jargon, with artist analogies. |
| *"Make the lighting golden hour"* | You don't need the slash commands — just talk. |

Every `/build` automatically saves a **checkpoint** first and ends with a
**3-angle QA sweep** (top-down, eye-level, player-eye), so the agent checks
its own work the way an art director would — and you always have an undo.

Bigger adventures — procedural cities that build themselves (PCG), making any
level playable with a walkable character, and generating your own blockout
buildings in Blender — live in [docs/07-BIG-WORLDS.md](docs/07-BIG-WORLDS.md).

More copy-paste ideas: [docs/03-PROMPTS-FOR-ARTISTS.md](docs/03-PROMPTS-FOR-ARTISTS.md)

---

## The Blueprint reader ⭐

Blueprints are Unreal's visual "code" — boxes and wires inside `.uasset`
files you can't open in a text editor. This repo teaches the agent to read them:

```
python tools/ue.py read-blueprint BP_SlidingDoor
```

exports the Blueprint's **parts, settings, events, and logic** to
`exports/blueprints/` as JSON (for the agent) and Markdown (for you), and the
agent explains it in artist language. There's even `ue.py peek` for looking
inside a `.uasset` when the editor is closed.
See a real example: [examples/example-blueprint-report.md](examples/example-blueprint-report.md)
· How it works + limits: [docs/02-READING-BLUEPRINTS.md](docs/02-READING-BLUEPRINTS.md)

---

## Docs

1. [Getting started (the long, gentle version)](docs/00-GETTING-STARTED.md)
2. [Your first scene, step by step](docs/01-YOUR-FIRST-SCENE.md)
3. [Reading Blueprints](docs/02-READING-BLUEPRINTS.md)
4. [Prompts for artists](docs/03-PROMPTS-FOR-ARTISTS.md)
5. [Troubleshooting (start here when stuck)](docs/04-TROUBLESHOOTING.md)
6. [How it all works, for the curious](docs/05-HOW-IT-WORKS.md)
7. [Real-world cities with Cesium](docs/06-REAL-WORLD-CITIES.md)
8. [Big worlds: procedural cities & playable characters](docs/07-BIG-WORLDS.md)

## Credits & license

- Built with Epic's Unreal MCP plugin and Unreal's Python remote execution.
- **[MIT license](LICENSE)** — free for everyone, forever. If you make
  something cool with it, sharing back is appreciated but never required.
