#!/usr/bin/env python3
"""ue.py — the one command for talking to your Unreal Editor.

    python tools/ue.py doctor                      check everything is wired up
    python tools/ue.py list-blueprints             list every Blueprint in the project
    python tools/ue.py read-blueprint BP_Door      export + report one Blueprint (name or /Game path)
    python tools/ue.py read-blueprint --all        export every Blueprint (up to --limit)
    python tools/ue.py read-material M_Rock        export + report a material's artist knobs
    python tools/ue.py scene-report                snapshot of every actor in the open level
    python tools/ue.py screenshot                  capture the viewport into exports/screenshots
    python tools/ue.py sweep                       QA pass: top-down + eye-level + player-eye shots
    python tools/ue.py camera frame --angle top    move the viewport camera (set/frame/get)
    python tools/ue.py snapshot                    checkpoint the scene (before building)
    python tools/ue.py diff-scene                  what changed since the checkpoint?
    python tools/ue.py revert-additions [--yes]    undo everything added since the checkpoint
    python tools/ue.py cesium status               real-world tiles: what's set up? (Cesium plugin)
    python tools/ue.py cesium goto --lat X --lon Y move the world origin to a real place
    python tools/ue.py exec "import unreal; ..."   run one line of Python inside the editor
    python tools/ue.py run my_script.py            run a Python file inside the editor
    python tools/ue.py peek Some.uasset            look inside a .uasset WITHOUT opening Unreal

Requires: the Unreal Editor running with Remote Execution enabled
(Edit -> Project Settings -> Plugins -> Python -> "Remote Execution").
`peek` and `doctor` also work when the editor is closed.
"""

import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uaa_remote  # noqa: E402
import bp_report  # noqa: E402
import scene_diff  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(REPO_ROOT, "exports")
INSIDE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inside_unreal")

try:  # emoji-free, but make unicode in asset names survive Windows consoles
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _script(name):
    with open(os.path.join(INSIDE, name), "r", encoding="utf-8") as handle:
        return handle.read()


def _run_inside(script_name, params, timeout=300.0, discover_timeout=5.0):
    """Run one of our inside_unreal scripts in the live editor."""
    with uaa_remote.UnrealConnection() as ue:
        info = ue.discover(timeout=discover_timeout)
        result = ue.run(uaa_remote.inject_params(_script(script_name), params), timeout=timeout)
    payload = uaa_remote.extract_result(result)
    errors = uaa_remote.output_errors(result)
    if payload is None:
        print("[!] The script ran but returned no result. Editor said:")
        print(uaa_remote.output_text(result)[-2000:] or "(nothing)")
        sys.exit(3)
    if payload.get("fatal"):
        print("[!] The script crashed inside Unreal:")
        print(payload["fatal"])
        sys.exit(3)
    for line in errors:
        if line.strip():
            print("[editor error] %s" % line)
    return info, payload


def _not_found(exc):
    print("[X] Could not reach Unreal.")
    print(str(exc))
    sys.exit(2)


# ---------------------------------------------------------------------- #
# commands
# ---------------------------------------------------------------------- #

def cmd_doctor(args):
    ok = True
    print("unreal-artist-agent doctor")
    print("-" * 40)

    version = sys.version_info
    if version >= (3, 8):
        print("[OK] Python %d.%d.%d" % version[:3])
    else:
        ok = False
        print("[X]  Python %d.%d is too old - install 3.8+ from python.org" % version[:2])

    # Channel 1: remote execution (used for Blueprint reading, scene reports, screenshots)
    try:
        with uaa_remote.UnrealConnection() as ue:
            info = ue.discover(timeout=args.timeout)
            print("[OK] Found Unreal Editor: engine %s" % info.get("engine_version", "?"))
            print("     Project: %s  (%s)" % (info.get("project_name", "?"), info.get("project_root", "?")))
            result = ue.run("print('uaa-ok')", timeout=30.0)
            if "uaa-ok" in uaa_remote.output_text(result):
                print("[OK] Remote Python execution works")
            else:
                ok = False
                print("[X]  Connected, but running Python inside the editor failed")
    except uaa_remote.UnrealNotFoundError as exc:
        ok = False
        print("[X]  Remote execution: not reachable")
        for line in str(exc).splitlines():
            print("     " + line)

    # Channel 2: the Unreal MCP server (used by the agent to build things)
    import urllib.request
    import urllib.error
    mcp_found = None
    for port in (args.mcp_port, 8123, 8000):
        if port is None:
            continue
        url = "http://127.0.0.1:%d/mcp" % port
        try:
            urllib.request.urlopen(url, timeout=2)
            mcp_found = port
            break
        except urllib.error.HTTPError:
            mcp_found = port  # server answered (even with an HTTP error) = running
            break
        except Exception:
            continue
    if mcp_found:
        print("[OK] Unreal MCP server answering on port %d" % mcp_found)
    else:
        print("[--] Unreal MCP server not detected (ports 8123/8000).")
        print("     In the editor console (backtick key), run:  ModelContextProtocol.StartServer 8123")

    print("-" * 40)
    print("All good - ask your agent to build something!" if ok and mcp_found else
          "Some checks failed - see docs/04-TROUBLESHOOTING.md")
    sys.exit(0 if ok else 1)


def cmd_exec(args):
    try:
        with uaa_remote.UnrealConnection() as ue:
            ue.discover(timeout=args.timeout)
            result = ue.run(args.code, timeout=300.0)
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)
    print(uaa_remote.output_text(result), end="")
    if result.get("result") and result["result"] != "None":
        print(result["result"])
    sys.exit(0 if result.get("success") else 3)


def cmd_run(args):
    with open(args.file, "r", encoding="utf-8") as handle:
        source = handle.read()
    args.code = source
    cmd_exec(args)


def cmd_list_blueprints(args):
    try:
        _info, payload = _run_inside("blueprint_reader.py",
                                     {"list_only": True, "root": args.root},
                                     timeout=args.timeout_long, discover_timeout=args.timeout)
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)
    blueprints = payload.get("blueprints") or []
    if not blueprints:
        print("No Blueprints found under %s" % args.root)
        return
    print("%d Blueprint(s) under %s:" % (len(blueprints), args.root))
    for bp in blueprints:
        print("  %-24s %s" % (bp.get("asset_class", ""), bp.get("path", "")))


def cmd_read_blueprint(args):
    if not args.target and not args.all:
        print("Tell me which Blueprint: ue.py read-blueprint BP_Door   (or --all)")
        sys.exit(1)
    out_dir = os.path.join(EXPORTS, "blueprints")
    params = {
        "root": args.root,
        "out_dir": out_dir,
        "limit": args.limit,
    }
    if args.target:
        params["target"] = args.target
    try:
        _info, payload = _run_inside("blueprint_reader.py", params, timeout=args.timeout_long, discover_timeout=args.timeout)
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)

    reports = payload.get("reports") or []
    if not reports:
        print(payload.get("message") or "No Blueprint matched.")
        print("Tip: run `python tools/ue.py list-blueprints` to see what exists.")
        sys.exit(1)
    print("Exported %d Blueprint(s) (project has %d):"
          % (payload.get("count_exported", len(reports)), payload.get("count_found", 0)))
    for item in reports:
        md_path = bp_report.write_report(item["json"])
        rel = os.path.relpath(md_path, REPO_ROOT)
        note = "  (%d section(s) hidden by this UE version)" % item["sections_failed"] if item.get("sections_failed") else ""
        print("  %s -> %s%s" % (item.get("path"), rel, note))
    if payload.get("truncated"):
        print("Note: more matched than the limit (%d). Raise it with --limit." % args.limit)


def cmd_scene_report(args):
    out_dir = os.path.join(EXPORTS, "scenes")
    try:
        _info, payload = _run_inside("scene_report.py", {"out_dir": out_dir},
                                     timeout=args.timeout_long, discover_timeout=args.timeout)
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)
    print("Level: %s   Actors: %s" % (payload.get("level"), payload.get("actor_count")))
    for cls, count in payload.get("top_classes") or []:
        print("  %5d  %s" % (count, cls))
    print("Full snapshot: %s" % os.path.relpath(payload["json"], REPO_ROOT))


def _take_screenshot(args, filename=None):
    """Trigger a viewport capture, wait for the file, copy into exports/. Returns the path."""
    filename = filename or ("uaa_shot_%s.png" % time.strftime("%Y%m%d_%H%M%S"))
    _info, payload = _run_inside(
        "screenshot.py",
        {"width": args.width, "height": args.height, "filename": filename},
        timeout=60.0, discover_timeout=args.timeout)

    expected = payload.get("expected_path")
    deadline = time.time() + 30.0
    last_size = -1
    while time.time() < deadline:
        if os.path.isfile(expected):
            size = os.path.getsize(expected)
            if size > 0 and size == last_size:
                break
            last_size = size
        time.sleep(0.5)
    else:
        print("[!] Screenshot never appeared at: %s" % expected)
        print("    Click once inside the Unreal viewport (it must be visible) and try again.")
        sys.exit(3)

    out_dir = os.path.join(EXPORTS, "screenshots")
    os.makedirs(out_dir, exist_ok=True)
    final = os.path.join(out_dir, os.path.basename(expected))
    shutil.copy2(expected, final)
    return final


def cmd_screenshot(args):
    final = _take_screenshot(args)
    print("Screenshot: %s" % os.path.relpath(final, REPO_ROOT))


def cmd_camera(args):
    params = {"mode": args.mode}
    if args.mode == "set":
        params.update({"location": [args.x, args.y, args.z],
                       "pitch": args.pitch, "yaw": args.yaw})
    elif args.mode == "frame":
        params["angle"] = args.angle
    try:
        _info, payload = _run_inside("camera.py", params,
                                     timeout=60.0, discover_timeout=args.timeout)
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)
    if payload.get("error"):
        print("[!] %s" % payload["error"])
        sys.exit(1)
    cam = payload.get("camera")
    if cam:
        print("Camera at %s  pitch=%s yaw=%s" % (cam.get("location"), cam.get("pitch"), cam.get("yaw")))


def cmd_sweep(args):
    """The 3-angle QA pass: top-down, eye-level, player-eye."""
    results = []
    for angle in ("top", "eye", "player"):
        try:
            _info, cam_payload = _run_inside("camera.py", {"mode": "frame", "angle": angle},
                                             timeout=60.0, discover_timeout=args.timeout)
        except uaa_remote.UnrealNotFoundError as exc:
            _not_found(exc)
        if not cam_payload.get("moved"):
            print("[!] Could not frame the %s angle: %s" % (angle, cam_payload.get("error", "unknown")))
            continue
        time.sleep(args.settle)  # let streaming/exposure settle before capturing
        shot = _take_screenshot(args, filename="sweep_%s_%s.png" % (angle, time.strftime("%H%M%S")))
        sidecar = os.path.splitext(shot)[0] + ".json"
        with open(sidecar, "w", encoding="utf-8") as handle:
            json.dump({"angle": angle, "camera": cam_payload.get("camera"),
                       "scene_bounds": cam_payload.get("bounds")}, handle, indent=2)
        results.append((angle, shot))
        print("  %-7s %s" % (angle, os.path.relpath(shot, REPO_ROOT)))
    if not results:
        sys.exit(3)
    print("Sweep done - %d angle(s). Each .png has a .json sidecar with the camera pose." % len(results))


CHECKPOINT_DIR = os.path.join(EXPORTS, "checkpoints")


def _checkpoint_path(name):
    return os.path.join(CHECKPOINT_DIR, "%s.json" % name)


def _fresh_scene(args, out_dir, filename):
    _info, payload = _run_inside("scene_report.py",
                                 {"out_dir": out_dir, "filename": filename},
                                 timeout=args.timeout_long, discover_timeout=args.timeout)
    return payload


def cmd_snapshot(args):
    try:
        payload = _fresh_scene(args, CHECKPOINT_DIR, "%s.json" % args.name)
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)
    print("Checkpoint '%s' saved: level %s, %s actor(s)."
          % (args.name, payload.get("level"), payload.get("actor_count")))
    print("Compare later with `diff-scene`, or undo additions with `revert-additions`.")


def cmd_diff_scene(args):
    checkpoint = _checkpoint_path(args.name)
    if not os.path.isfile(checkpoint):
        print("No checkpoint named '%s'. Take one first:  python tools/ue.py snapshot" % args.name)
        sys.exit(1)
    try:
        payload = _fresh_scene(args, os.path.join(EXPORTS, "scenes"),
                               "diff_current_%s.json" % time.strftime("%H%M%S"))
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)
    result = scene_diff.diff(scene_diff.load_snapshot(checkpoint),
                             scene_diff.load_snapshot(payload["json"]))
    print(scene_diff.format_diff(result))


def cmd_revert_additions(args):
    checkpoint = _checkpoint_path(args.name)
    if not os.path.isfile(checkpoint):
        print("No checkpoint named '%s'. Nothing to revert to." % args.name)
        sys.exit(1)
    keys = scene_diff.keep_keys(scene_diff.load_snapshot(checkpoint))
    params = {"keep_keys": keys, "dry_run": not args.yes}
    try:
        _info, payload = _run_inside("delete_actors.py", params,
                                     timeout=args.timeout_long, discover_timeout=args.timeout)
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)

    if payload.get("dry_run"):
        targets = payload.get("would_delete") or []
        if not targets:
            print("Nothing was added since checkpoint '%s' - the scene is already clean." % args.name)
            return
        print("Would delete %d actor(s) added since checkpoint '%s':" % (len(targets), args.name))
        for target in targets:
            print("  - %-30s %s" % (target.get("label"), target.get("class")))
        print("This was a preview. To actually delete them, add:  --yes")
    else:
        deleted = payload.get("deleted") or []
        failed = payload.get("failed") or []
        print("Deleted %d actor(s)." % len(deleted))
        for entry in failed:
            print("  [!] could not delete %s (%s)" % (entry.get("label"), entry.get("class")))


def cmd_read_material(args):
    if not args.target and not getattr(args, "all", False):
        print("Which material? ue.py read-material M_Rock   (or --all)")
        sys.exit(1)
    out_dir = os.path.join(EXPORTS, "materials")
    params = {"root": args.root, "out_dir": out_dir, "limit": args.limit}
    if args.target:
        params["target"] = args.target
    try:
        _info, payload = _run_inside("material_reader.py", params,
                                     timeout=args.timeout_long, discover_timeout=args.timeout)
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)
    reports = payload.get("reports") or []
    if not reports:
        print(payload.get("message") or "No material matched.")
        sys.exit(1)
    print("Exported %d material(s) (project has %d):"
          % (payload.get("count_exported", len(reports)), payload.get("count_found", 0)))
    for item in reports:
        md_path = bp_report.write_material_report(item["json"])
        print("  %s -> %s" % (item.get("path"), os.path.relpath(md_path, REPO_ROOT)))


def cmd_cesium(args):
    params = {"action": args.action}
    if args.action in ("goto", "setup"):
        if args.action == "goto" and (args.lat is None or args.lon is None):
            print("Where to? ue.py cesium goto --lat 37.9838 --lon 23.7275   (that's Athens)")
            sys.exit(1)
        params.update({"lat": args.lat, "lon": args.lon, "height": args.height})
    if args.action == "setup":
        params.update({"key": args.key, "url": args.url, "add_sky": not args.no_sky})
    try:
        _info, payload = _run_inside("cesium_tools.py", params, timeout=args.timeout_long, discover_timeout=args.timeout)
    except uaa_remote.UnrealNotFoundError as exc:
        _not_found(exc)

    if not payload.get("plugin_loaded"):
        print("[X] Cesium for Unreal plugin is not enabled in this project.")
    else:
        print("[OK] Cesium plugin loaded")
    for geo in payload.get("georeferences") or []:
        print("  Georeference %-20s lat=%s lon=%s height=%sm"
              % (geo.get("name"), geo.get("latitude"), geo.get("longitude"), geo.get("height")))
    for tileset in payload.get("tilesets") or []:
        print("  Tileset      %-20s %s" % (tileset.get("name"), tileset.get("url") or tileset.get("source")))
    if payload.get("moved_georeferences") is not None:
        print("Moved %d georeference(s), refreshed %d tileset(s)."
              % (payload["moved_georeferences"], payload.get("refreshed_tilesets", 0)))
        print("Give the tiles a few seconds to stream in, then take a screenshot.")
    if not payload.get("has_sun"):
        print("  (No sun/directional light in the level - the world may look black.)")
    for note in payload.get("notes") or []:
        print("[note] %s" % note)


def cmd_peek(args):
    import uasset_peek
    uasset_peek.print_summary(args.file)


# ---------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(prog="ue.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="seconds to wait when looking for the editor (default 5)")
    parser.add_argument("--timeout-long", type=float, default=600.0, dest="timeout_long",
                        help="seconds to allow for big jobs like exporting many Blueprints")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("doctor", help="check Python, the editor connection, and the MCP server")
    p.add_argument("--mcp-port", type=int, default=None)
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("exec", help="run one line of Python inside the editor")
    p.add_argument("code")
    p.set_defaults(func=cmd_exec)

    p = sub.add_parser("run", help="run a Python file inside the editor")
    p.add_argument("file")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("list-blueprints", help="list every Blueprint in the project")
    p.add_argument("--root", default="/Game")
    p.set_defaults(func=cmd_list_blueprints)

    p = sub.add_parser("read-blueprint", help="export Blueprint(s) to JSON + a plain-English report")
    p.add_argument("target", nargs="?", help="a name fragment (BP_Door) or full /Game path")
    p.add_argument("--all", action="store_true", help="export everything under --root")
    p.add_argument("--root", default="/Game")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_read_blueprint)

    p = sub.add_parser("scene-report", help="snapshot every actor in the open level")
    p.set_defaults(func=cmd_scene_report)

    p = sub.add_parser("screenshot", help="capture the viewport into exports/screenshots")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.set_defaults(func=cmd_screenshot)

    p = sub.add_parser("camera", help="move the viewport camera (set / frame / get)")
    p.add_argument("mode", choices=["set", "frame", "get"])
    p.add_argument("--x", type=float, default=0.0)
    p.add_argument("--y", type=float, default=0.0)
    p.add_argument("--z", type=float, default=300.0)
    p.add_argument("--pitch", type=float, default=0.0)
    p.add_argument("--yaw", type=float, default=0.0)
    p.add_argument("--angle", choices=["top", "eye", "player"], default="eye",
                   help="for frame mode: which auto-framed view")
    p.set_defaults(func=cmd_camera)

    p = sub.add_parser("sweep", help="QA pass: screenshot the scene from top / eye / player angles")
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--settle", type=float, default=1.0,
                   help="seconds to wait after moving the camera before capturing")
    p.set_defaults(func=cmd_sweep)

    p = sub.add_parser("snapshot", help="save a checkpoint of the current scene (for diff/revert)")
    p.add_argument("name", nargs="?", default="last")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("diff-scene", help="what changed since a checkpoint?")
    p.add_argument("name", nargs="?", default="last")
    p.set_defaults(func=cmd_diff_scene)

    p = sub.add_parser("revert-additions",
                       help="delete actors added since a checkpoint (previews by default; --yes to delete)")
    p.add_argument("name", nargs="?", default="last")
    p.add_argument("--yes", action="store_true",
                   help="actually delete (without this it only shows what would go)")
    p.set_defaults(func=cmd_revert_additions)

    p = sub.add_parser("read-material", help="export material(s) to JSON + a plain-English report")
    p.add_argument("target", nargs="?", help="a name fragment (M_Rock) or full /Game path")
    p.add_argument("--all", action="store_true", help="export everything under --root")
    p.add_argument("--root", default="/Game")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_read_material)

    p = sub.add_parser("cesium", help="real-world 3D tiles: status / goto / setup (needs the Cesium plugin)")
    p.add_argument("action", choices=["status", "goto", "setup"])
    p.add_argument("--lat", type=float, help="latitude in degrees, e.g. 37.9838")
    p.add_argument("--lon", type=float, help="longitude in degrees, e.g. 23.7275")
    p.add_argument("--height", type=float, default=200.0, help="camera-origin height in meters (default 200)")
    p.add_argument("--key", help="Google Maps Platform API key (setup only)")
    p.add_argument("--url", help="full tileset URL, if not using --key (setup only)")
    p.add_argument("--no-sky", action="store_true", help="setup: don't add sun/sky actors")
    p.set_defaults(func=cmd_cesium)

    p = sub.add_parser("peek", help="inspect a .uasset file without opening Unreal")
    p.add_argument("file")
    p.set_defaults(func=cmd_peek)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
