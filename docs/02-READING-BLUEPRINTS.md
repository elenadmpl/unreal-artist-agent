# Reading Blueprints

The signature feature of this repo: the agent can open Unreal's "visual code"
and explain it to you like a patient colleague.

## What is a Blueprint, in one minute

When someone "programs" in Unreal without writing code, they connect boxes
with wires — *"when the player touches this → open the door → play a sound"*.
That box-and-wire logic is saved inside a **Blueprint**, which lives in a
`.uasset` file. Marketplace props, template characters, doors, pickups — they
all carry Blueprints. Normally, the only way to know what one does is to open
it in Unreal's graph editor and decipher the wires yourself.

The Blueprint reader does the deciphering for you.

## The three ways to read one

### 1. Ask the agent (recommended)
```
/read-blueprint BP_SlidingDoor
```
or just say *"what does the door blueprint do?"*. The agent exports it, reads
the export, and explains it in plain language.

### 2. Run the tool yourself
```
python tools/ue.py list-blueprints
python tools/ue.py read-blueprint BP_SlidingDoor
```
You get two files in `exports/blueprints/`:
- `BP_SlidingDoor.json` — every detail, for agents and tinkerers,
- `BP_SlidingDoor.md` — a readable report ([example](../examples/example-blueprint-report.md)).

Fuzzy names are fine — `door` finds `BP_SlidingDoor`. `--all` exports the
whole project (up to `--limit`, default 25).

### 3. From inside Unreal (no setup at all)
In the editor console (backtick), with the Python plugin on:
```
py "C:/path/to/unreal-artist-agent/tools/inside_unreal/blueprint_reader.py"
```
Exports every Blueprint to `<YourProject>/Saved/BlueprintExports/`.

### Bonus: when the editor is closed
```
python tools/ue.py peek "MyProject/Content/BP_Door.uasset"
```
Reads the raw file directly — you get the asset's ingredient list (which
classes, functions and other assets it references), which is often enough to
answer "what is this file?". No Unreal needed.

## What's in a report

- **What it is** — guessed from its parent class, in artist terms
  ("a piece of UI", "something a player can control").
- **Parts** — the components bolted together inside (meshes, lights, colliders).
- **Settings** — its variables, with defaults. These are the knobs the
  original author intended people to turn.
- **Events → actions** — *when* it reacts (game start, being touched, every
  frame) and *what* it calls in response, plus which settings the logic
  reads or changes.
- **The author's own graph comments**, when they left any.

## Honest limitations

- **The editor must be running** (with your project open) for full reports —
  the reader asks the live engine, because that's the only reliable way in.
- **Depth varies by engine version.** Epic doesn't promise Python access to
  Blueprint internals, so on some versions the node-graph section is partial
  (you always get components/variables/functions from the compiled class).
  Whatever couldn't be read is listed at the bottom of the report — the agent
  is instructed to be upfront about it.
- **Wires aren't exported one-by-one.** You get what happens and what it
  touches, not the exact pin-to-pin routing. For artists, that's the useful
  90%; for the last 10%, open the graph editor with the report beside you.
- **Reading is 100% safe.** The reader never modifies an asset — it only looks.
