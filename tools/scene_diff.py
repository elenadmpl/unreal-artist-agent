"""scene_diff.py — compare two scene snapshots (from `ue.py snapshot` /
`ue.py scene-report`) and say what was added, removed, or moved.

This is the brain behind the checkpoint safety net: it runs entirely on
your machine on the exported JSON files, so it's fast and can't touch the
editor.
"""

import json
import math

MOVE_TOLERANCE = 1.0  # UE units (cm) — below this, "same place"


def load_snapshot(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _key(actor):
    return (actor.get("label") or "?") + "||" + (actor.get("class") or "?")


def _distance(a, b):
    if not a or not b:
        return 0.0
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def diff(old_snapshot, new_snapshot):
    """Returns {'added': [...], 'removed': [...], 'moved': [...]}.

    Actors are matched by (label, class) — Unreal keeps labels unique within
    a level, so this is reliable in practice.
    """
    old = {_key(a): a for a in old_snapshot.get("actors") or []}
    new = {_key(a): a for a in new_snapshot.get("actors") or []}

    added = [new[k] for k in new if k not in old]
    removed = [old[k] for k in old if k not in new]
    moved = []
    for k in new:
        if k not in old:
            continue
        dist = _distance(old[k].get("location"), new[k].get("location"))
        if dist > MOVE_TOLERANCE:
            moved.append({
                "label": new[k].get("label"),
                "class": new[k].get("class"),
                "from": old[k].get("location"),
                "to": new[k].get("location"),
                "distance": round(dist, 1),
            })
    order = lambda item: (item.get("class") or "", item.get("label") or "")
    return {"added": sorted(added, key=order),
            "removed": sorted(removed, key=order),
            "moved": sorted(moved, key=order)}


def keep_keys(snapshot):
    """The keep-list `delete_actors.py` needs to revert to this snapshot."""
    return sorted({_key(a) for a in snapshot.get("actors") or []})


def format_diff(result):
    lines = []
    added, removed, moved = result["added"], result["removed"], result["moved"]
    if not (added or removed or moved):
        return "No changes - the scene matches the checkpoint."
    if added:
        lines.append("Added since the checkpoint (%d):" % len(added))
        for actor in added:
            lines.append("  + %-30s %s" % (actor.get("label"), actor.get("class")))
    if removed:
        lines.append("Removed since the checkpoint (%d):" % len(removed))
        for actor in removed:
            lines.append("  - %-30s %s" % (actor.get("label"), actor.get("class")))
    if moved:
        lines.append("Moved (%d):" % len(moved))
        for actor in moved:
            lines.append("  ~ %-30s %s  (%.0f cm)" % (actor.get("label"), actor.get("class"), actor["distance"]))
    return "\n".join(lines)
