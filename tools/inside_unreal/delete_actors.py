"""delete_actors.py — runs INSIDE the Unreal Editor's Python.

The dangerous half of the checkpoint system (see `ue.py snapshot` /
`revert-additions`): removes actors that are NOT on a keep-list, i.e.
everything added since a checkpoint was taken.

Safety design:
  * dry_run defaults to True — it only REPORTS what it would delete.
    Actual deletion requires PARAMS["dry_run"] == False (the CLI only sends
    that when the user passed --yes).
  * Engine-infrastructure actors are never touched, keep-list or not.
  * Only whole actors are removed; assets and files are never deleted.
"""

import json
import traceback

import unreal

try:
    PARAMS = json.loads(UAA_PARAMS_JSON)  # noqa: F821 (injected by tools/ue.py)
except NameError:
    PARAMS = {}

# Never delete these even if they aren't in the checkpoint - the level itself
# needs them.
PROTECTED_CLASSES = {
    "WorldSettings", "Brush", "DefaultPhysicsVolume", "LevelBounds",
    "WorldDataLayers", "DataLayerManager", "WorldPartitionMiniMap",
    "AbstractNavData", "GameplayDebuggerPlayerManager",
}


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


def _destroy(actor):
    for destroyer in (
        lambda: unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(actor),
        lambda: unreal.EditorLevelLibrary.destroy_actor(actor),
    ):
        result = _safe(destroyer)
        if result:
            return True
    return False


def main():
    keep_keys = set(PARAMS.get("keep_keys") or [])
    dry_run = bool(PARAMS.get("dry_run", True))
    if not keep_keys:
        _emit({"fatal": "refusing to run without a keep-list (empty checkpoint?)"})
        return

    targets, protected = [], []
    for actor in _all_actors():
        label = _safe(lambda: str(actor.get_actor_label()), "")
        cls = _safe(lambda: str(actor.get_class().get_name()), "")
        key = label + "||" + cls
        if key in keep_keys:
            continue
        if cls in PROTECTED_CLASSES:
            protected.append({"label": label, "class": cls})
            continue
        targets.append({"label": label, "class": cls, "actor": actor})

    if dry_run:
        _emit({"dry_run": True,
               "would_delete": [{"label": t["label"], "class": t["class"]} for t in targets],
               "protected_skipped": protected})
        return

    deleted, failed = [], []
    for target in targets:
        entry = {"label": target["label"], "class": target["class"]}
        (deleted if _destroy(target["actor"]) else failed).append(entry)

    _emit({"dry_run": False, "deleted": deleted, "failed": failed,
           "protected_skipped": protected})


try:
    main()
except Exception:
    _emit({"fatal": traceback.format_exc()})
