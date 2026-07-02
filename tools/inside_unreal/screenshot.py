"""screenshot.py — runs INSIDE the Unreal Editor's Python.

Asks the editor to take a high-resolution screenshot of the current
viewport. The file appears in the project's Saved/Screenshots folder a
moment later; tools/ue.py waits for it and copies it into exports/.

Run from outside:   python tools/ue.py screenshot
Run in the editor:  py "C:/path/to/unreal-artist-agent/tools/inside_unreal/screenshot.py"
"""

import json
import os
import time
import traceback

import unreal

try:
    PARAMS = json.loads(UAA_PARAMS_JSON)  # noqa: F821 (injected by tools/ue.py)
except NameError:
    PARAMS = {}


def _emit(payload):
    print("UAA_RESULT_BEGIN")
    print(json.dumps(payload))
    print("UAA_RESULT_END")


def main():
    width = int(PARAMS.get("width") or 1280)
    height = int(PARAMS.get("height") or 720)
    filename = PARAMS.get("filename") or ("uaa_shot_%s.png" % time.strftime("%Y%m%d_%H%M%S"))

    unreal.AutomationLibrary.take_high_res_screenshot(width, height, filename)

    shot_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.screen_shot_dir())
    _emit({
        "requested": filename,
        "width": width,
        "height": height,
        "expected_path": os.path.join(shot_dir, filename),
        "note": "The editor writes the file over the next few frames; poll for it.",
    })


try:
    main()
except Exception:
    _emit({"fatal": traceback.format_exc()})
