# Troubleshooting

First move, always: type `/doctor` in Claude Code (or run
`python tools/ue.py doctor` yourself) — it tells you *which* connection is
broken. Then find that symptom below. And remember: you can paste any error
straight into the chat and let the agent debug with you.

---

## "python is not recognized" (Windows)

Python isn't on your PATH. Re-run the installer from python.org, choose
**Modify**, and tick **"Add Python to environment variables"** — or reinstall
and tick **"Add Python to PATH"** on the first screen. Close and reopen your
terminal afterwards. (Try `py tools/ue.py doctor` too — the `py` launcher is
sometimes installed even when `python` isn't.)

## Doctor says: "No running Unreal Editor answered"

The Blueprint/screenshot channel can't find the editor. In order of likelihood:

1. **The editor isn't open**, or is open on a different project than you think.
2. **Remote Execution isn't ticked** — Edit → Project Settings → search
   "Python" → **Remote Execution**. This is *per project*.
3. **You didn't restart the editor** after ticking it. It only reads that
   setting on startup.
4. **Firewall** — the first time, Windows asks about UnrealEditor; if someone
   clicked Cancel, allow it manually: Windows Security → Firewall → Allow an
   app → UnrealEditor (private networks is enough).
5. **Non-default Python settings** — if you (or a studio setup) changed the
   Python plugin's multicast settings, mirror them at the top of
   `tools/uaa_remote.py` (defaults: group `239.0.0.1:6766`, bind `127.0.0.1`).

## Doctor says: "found the editor, but it never opened the command connection"

Something else is squatting on the reply channel (TCP port 6776) — usually a
*second* remote-exec client (another terminal, an IDE plugin). Close other
tools that talk to Unreal's Python and retry.

## "Unreal MCP server not detected"

The agent's *building* channel is down (reading Blueprints can still work —
they're separate):

1. In the editor console (backtick `` ` ``): `ModelContextProtocol.StartServer 8123`
2. Still nothing? Check **Edit → Plugins**: **Unreal MCP** must be Enabled and
   the editor restarted since.
3. `"port already in use"` → another program owns 8123. Pick another number
   (e.g. `ModelContextProtocol.StartServer 8200`) and change the port in this
   repo's `.mcp.json` to match.
4. Remember it's **per project** — a fresh project needs the plugin enabled
   again, and only one editor can own a port at a time.

## Agent connects but "can barely do anything" in Unreal

You're missing the **AllToolsets** plugin — without it the MCP server exposes
only a minimal toolset. Edit → Plugins → enable **AllToolsets** → restart →
restart the MCP server.

## Screenshots never appear

The viewport must actually be visible on screen — don't minimize the editor.
Click once inside the viewport and retry. Immersive/PIE modes can also
redirect captures; stop playing (Esc) first.

## Blueprint report has a "could NOT see" section

Not a bug — your engine version hides some Blueprint internals from Python.
The report tells you exactly what's missing. Components, variables and
functions almost always come through; node-graph detail varies by version.

## The editor hangs on startup after enabling Remote Execution (macOS)

Known Unreal quirk on some macOS versions. Close the editor, open
`<YourProject>/Config/DefaultEngine.ini`, and remove or set to False:
```ini
[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution=False
```
You lose Blueprint reading/screenshots but keep MCP building. (Re-test on
newer engine versions — it's fixed in some.)

## It was working yesterday and not today

90% of the time: the editor was restarted and the MCP server didn't auto-start.
Run `ModelContextProtocol.StartServer 8123` again, or turn on auto-start
(Editor Preferences → Model Context Protocol). Then `/doctor` to confirm.
