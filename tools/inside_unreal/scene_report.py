"""scene_report.py — runs INSIDE the Unreal Editor's Python.

Writes a JSON snapshot of the currently open level: every actor with its
label, class, position, rotation and scale. This is how the agent "reads"
your scene without screenshots. Read only — nothing is modified.

Run from outside:   python tools/ue.py scene-report
Run in the editor:  py "C:/path/to/unreal-artist-agent/tools/inside_unreal/scene_report.py"
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


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _get_actors():
    # UE 5.x way first, older fallback second.
    actors = _safe(lambda: unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
    if actors is None:
        actors = _safe(lambda: unreal.EditorLevelLibrary.get_all_level_actors())
    return actors or []


def _level_name():
    world = _safe(lambda: unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world())
    if world is None:
        world = _safe(lambda: unreal.EditorLevelLibrary.get_editor_world())
    return _safe(lambda: str(world.get_name())) if world is not None else None


def _vec(v, digits=1):
    return [round(v.x, digits), round(v.y, digits), round(v.z, digits)]


def _describe(actor):
    entry = {
        "label": _safe(lambda: str(actor.get_actor_label())),
        "class": _safe(lambda: str(actor.get_class().get_name())),
    }
    loc = _safe(lambda: actor.get_actor_location())
    if loc is not None:
        entry["location"] = _vec(loc)
    rot = _safe(lambda: actor.get_actor_rotation())
    if rot is not None:
        entry["rotation"] = [round(rot.roll, 1), round(rot.pitch, 1), round(rot.yaw, 1)]
    scale = _safe(lambda: actor.get_actor_scale3d())
    if scale is not None and (scale.x, scale.y, scale.z) != (1.0, 1.0, 1.0):
        entry["scale"] = _vec(scale, 2)
    return entry


def main():
    out_dir = PARAMS.get("out_dir")
    if not out_dir:
        saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
        out_dir = os.path.join(saved, "SceneReports")
    os.makedirs(out_dir, exist_ok=True)

    actors = _get_actors()
    described = [_describe(actor) for actor in actors]
    class_counts = {}
    for entry in described:
        cls = entry.get("class") or "Unknown"
        class_counts[cls] = class_counts.get(cls, 0) + 1

    snapshot = {
        "level": _level_name(),
        "actor_count": len(described),
        "class_counts": class_counts,
        "actors": described,
    }
    filename = PARAMS.get("filename") or ("scene_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
    file_path = os.path.join(out_dir, filename)
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2)

    top = sorted(class_counts.items(), key=lambda kv: -kv[1])[:15]
    _emit({"json": file_path, "level": snapshot["level"],
           "actor_count": snapshot["actor_count"], "top_classes": top})


try:
    main()
except Exception:
    _emit({"fatal": traceback.format_exc()})
