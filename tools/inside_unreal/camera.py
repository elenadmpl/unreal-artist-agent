"""camera.py — runs INSIDE the Unreal Editor's Python.

Positions the editor viewport camera, so the agent can look at the scene
from meaningful angles before taking a screenshot.

Modes (PARAMS["mode"]):
  set    - exact pose: location [x,y,z], pitch, yaw
  frame  - auto-frame the whole scene from a named angle:
             top     straight down (layout / overlaps)
             eye     eye-level from outside (does it look good?)
             player  ~1.7m off the ground (how does it feel in game?)
  get    - just report the current camera pose (read-only)

Only moves the viewport camera — never touches any actor.
"""

import json
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


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _all_actors():
    actors = _safe(lambda: unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
    if actors is None:
        actors = _safe(lambda: unreal.EditorLevelLibrary.get_all_level_actors())
    return actors or []


def _set_camera(location, rotation):
    setters = (
        lambda: unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(location, rotation),
        lambda: unreal.EditorLevelLibrary.set_level_viewport_camera_info(location, rotation),
    )
    for setter in setters:
        try:
            setter()
            return True
        except Exception:
            continue
    return False


def _get_camera():
    getters = (
        lambda: unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_level_viewport_camera_info(),
        lambda: unreal.EditorLevelLibrary.get_level_viewport_camera_info(),
    )
    for getter in getters:
        info = _safe(getter)
        if info:
            location, rotation = info[0], info[1]
            return {
                "location": [round(location.x, 1), round(location.y, 1), round(location.z, 1)],
                "pitch": round(rotation.pitch, 1),
                "yaw": round(rotation.yaw, 1),
            }
    return None


def _scene_bounds():
    xs, ys, zs = [], [], []
    for actor in _all_actors():
        loc = _safe(lambda: actor.get_actor_location())
        if loc is None:
            continue
        xs.append(loc.x)
        ys.append(loc.y)
        zs.append(loc.z)
    if not xs:
        return None
    return {
        "min": [min(xs), min(ys), min(zs)],
        "max": [max(xs), max(ys), max(zs)],
        "center": [(min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0, (min(zs) + max(zs)) / 2.0],
    }


def _frame_pose(angle, bounds):
    cx, cy, cz = bounds["center"]
    min_z = bounds["min"][2]
    size_x = bounds["max"][0] - bounds["min"][0]
    size_y = bounds["max"][1] - bounds["min"][1]
    extent = max(size_x, size_y, 500.0)  # UE units = cm

    if angle == "top":
        location = unreal.Vector(cx, cy, bounds["max"][2] + extent * 1.0 + 1000.0)
        rotation = unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0)
    elif angle == "player":
        # Just inside the scene, at human eye height, looking forward.
        location = unreal.Vector(cx - extent * 0.4, cy, min_z + 170.0)
        rotation = unreal.Rotator(roll=0.0, pitch=0.0, yaw=0.0)
    else:  # "eye" — from outside, slightly above, looking at the middle
        distance = extent * 1.1 + 500.0
        location = unreal.Vector(cx - distance, cy, cz + extent * 0.25 + 200.0)
        rotation = unreal.Rotator(roll=0.0, pitch=-10.0, yaw=0.0)
    return location, rotation


def main():
    mode = PARAMS.get("mode") or "get"

    if mode == "get":
        _emit({"camera": _get_camera()})
        return

    if mode == "set":
        loc = PARAMS.get("location") or [0, 0, 300]
        location = unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2]))
        rotation = unreal.Rotator(roll=0.0,
                                  pitch=float(PARAMS.get("pitch") or 0.0),
                                  yaw=float(PARAMS.get("yaw") or 0.0))
        ok = _set_camera(location, rotation)
        _emit({"moved": ok, "camera": _get_camera()})
        return

    if mode == "frame":
        angle = PARAMS.get("angle") or "eye"
        bounds = _scene_bounds()
        if bounds is None:
            _emit({"moved": False, "error": "no actors with positions in the level"})
            return
        location, rotation = _frame_pose(angle, bounds)
        ok = _set_camera(location, rotation)
        _emit({"moved": ok, "angle": angle, "camera": _get_camera(), "bounds": bounds})
        return

    _emit({"fatal": "unknown mode %r" % mode})


try:
    main()
except Exception:
    _emit({"fatal": traceback.format_exc()})
