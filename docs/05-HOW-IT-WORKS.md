# How it all works (for the curious)

You don't need any of this to use the project. But if you're the kind of
artist who likes knowing what's under the hood — welcome.

## The big picture

```
 You (plain English)
   │
   ▼
 Claude Code  ←── CLAUDE.md tells it how to behave here
   │
   ├─► Channel 1: Unreal MCP  ──────────►  "hands"
   │    HTTP on 127.0.0.1:8123, Epic's       place actors, edit materials,
   │    built-in plugin (UE 5.8+).           move the camera, run PIE...
   │
   └─► Channel 2: python tools/ue.py  ──►  "eyes + reading glasses"
        Unreal's Python remote execution:    screenshots, actor snapshots,
        UDP discovery + a TCP channel,       Blueprint exports
        Epic ships it in the Python plugin.
```

Two channels because they fail independently: if MCP is down the agent can
still *see and read*, and tell you exactly what to fix. That's what `/doctor`
exploits.

## Channel 2, step by step

1. `tools/uaa_remote.py` shouts "ping" on a UDP multicast group
   (`239.0.0.1:6766`) that Unreal's Python plugin listens on.
2. The editor answers "pong" with its engine version and project.
3. Our client opens a local TCP port; the editor connects back to it.
4. We send Python source over that socket; the editor runs it on the game
   thread and streams back everything it printed.
5. Scripts in `tools/inside_unreal/` are written to run *inside* the editor
   this way: they read a `PARAMS` blob we prepend, do their read-only work,
   and print their result as JSON between `UAA_RESULT_BEGIN/END` marker lines
   so the client can fish it out of the editor's other log noise.

The protocol is Epic's own (the same one their `remote_execution.py` client
speaks); this repo's implementation is original and dependency-free.

## The Blueprint reader

A Blueprint is a `UBlueprint` asset: variable descriptions, a component tree
(the SimpleConstructionScript), and graphs of nodes. `blueprint_reader.py`
reads it from three angles, every section in its own try/except:

1. **The asset itself** — parent class, description, interfaces, component
   tree, variable descriptions.
2. **The compiled class** — it takes the generated class's *default object*
   and diffs its Python attributes against the parent class: what's left are
   the Blueprint's own variables (with live defaults) and functions. This
   angle works on any engine version, because it only uses supported
   reflection.
3. **The graphs** — `ubergraph_pages` / `function_graphs`, node by node:
   event nodes, function-call nodes (and what they call), variable get/set
   nodes, author comments. This is the version-dependent part; whatever the
   engine refuses to expose is recorded in the report's "could not see" list
   instead of crashing.

`tools/bp_report.py` then turns the JSON into the plain-English Markdown
report, including translating well-known events ("ReceiveTick" → "every
single frame — runs constantly!").

`tools/uasset_peek.py` is the editor-less fallback: it parses the `.uasset`
package header directly to recover the *name table* — every class, function,
variable and asset path the file references — with a string-scan fallback for
format drift between engine versions.

## Design rules (also encoded in CLAUDE.md)

- **One mutation at a time.** The editor has a single game thread; parallel
  writes corrupt the fun. Reads may overlap.
- **Verify visually.** Building without looking is how you get floating
  furniture. Screenshot → read → fix is mandatory, not optional.
- **Reading is sacred-safe.** Every tool in this repo that *reads*
  (blueprints, scenes, screenshots, peek) touches nothing. Anything that
  *writes* goes through the MCP channel where the agent's rules require
  confirmation for destructive acts.

## Extending it

Add a new in-editor capability in three steps:

1. Drop a script into `tools/inside_unreal/` following the existing pattern
   (`PARAMS` in, `_emit(payload)` out, read-only unless you really know why).
2. Add a subcommand in `tools/ue.py` that runs it via `_run_inside()`.
3. Teach the agent in `CLAUDE.md` (one line in the tool list), and optionally
   give artists a slash command in `.claude/commands/`.

PRs welcome — especially new in-editor readers (materials? animation
blueprints? niagara?) and better artist-language reports.
