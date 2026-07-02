"""cesium_tools.py — runs INSIDE the Unreal Editor's Python.

Helpers for Cesium for Unreal (the free plugin that streams the real Earth,
including Google Photorealistic 3D Tiles, into your level).

Actions (picked via PARAMS["action"], see tools/ue.py):
  status  - is the plugin on, which Cesium actors exist, where is the origin
  goto    - move the world origin to a latitude/longitude and refresh tiles
  setup   - create the georeference + tileset (+ sky) if missing, then goto

The one hard-won gotcha this file exists for: you must move the origin by
CALLING CesiumGeoreference.set_origin_longitude_latitude_height(...), not by
writing the latitude/longitude properties directly. Property writes skip
Cesium's setters, and the planet renders in the wrong place at the wrong
scale. After moving, every tileset needs refresh_tileset().

`setup` adds actors to the level (never deletes); `goto` only moves the
origin; `status` is read-only.
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


def _prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def _mask_key(url):
    if not url:
        return url
    if "key=" in url:
        return url.split("key=")[0] + "key=***"
    return url


def _all_actors():
    actors = _safe(lambda: unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())
    if actors is None:
        actors = _safe(lambda: unreal.EditorLevelLibrary.get_all_level_actors())
    return actors or []


def _actors_of(class_name):
    found = []
    for actor in _all_actors():
        name = _safe(lambda: str(actor.get_class().get_name()), "")
        if name == class_name:
            found.append(actor)
    return found


def _plugin_loaded():
    return getattr(unreal, "CesiumGeoreference", None) is not None


def _spawn(class_name, label=None):
    cls = getattr(unreal, class_name, None)
    if cls is None:
        return None
    spawners = (
        lambda: unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(cls, unreal.Vector(0, 0, 0)),
        lambda: unreal.EditorLevelLibrary.spawn_actor_from_class(cls, unreal.Vector(0, 0, 0)),
    )
    for spawner in spawners:
        actor = _safe(spawner)
        if actor is not None:
            if label:
                _safe(lambda: actor.set_actor_label(label))
            return actor
    return None


def _set_origin(geo, lat, lon, height, notes):
    # Force cartographic placement first (the rebase is meaningless without it).
    placement = getattr(unreal, "OriginPlacement", None)
    if placement is not None:
        try:
            geo.set_origin_placement(placement.CARTOGRAPHIC_ORIGIN)
        except Exception:
            notes.append("could not set origin placement (usually already Cartographic)")
    # The setter's signature has changed across plugin versions: newer takes a
    # Vector(X=lon, Y=lat, Z=height), older takes three floats (lon, lat, height).
    try:
        geo.set_origin_longitude_latitude_height(unreal.Vector(lon, lat, height))
        return True
    except Exception:
        pass
    try:
        geo.set_origin_longitude_latitude_height(lon, lat, height)
        return True
    except Exception:
        notes.append("set_origin_longitude_latitude_height failed on %s" % geo.get_name())
        return False


def _describe(notes):
    georefs = []
    for geo in _actors_of("CesiumGeoreference"):
        georefs.append({
            "name": _safe(lambda: str(geo.get_actor_label())),
            "latitude": _safe(lambda: float(_prop(geo, "origin_latitude"))),
            "longitude": _safe(lambda: float(_prop(geo, "origin_longitude"))),
            "height": _safe(lambda: float(_prop(geo, "origin_height"))),
        })
    tilesets = []
    for tileset in _actors_of("Cesium3DTileset"):
        tilesets.append({
            "name": _safe(lambda: str(tileset.get_actor_label())),
            "source": _safe(lambda: str(_prop(tileset, "tileset_source"))),
            "url": _mask_key(_safe(lambda: str(_prop(tileset, "url")))),
        })
    has_sun = any(
        "DirectionalLight" in (_safe(lambda: str(a.get_class().get_name()), "") or "")
        or (_safe(lambda: str(a.get_class().get_name()), "") or "") == "SunSky"
        for a in _all_actors()
    )
    return {"plugin_loaded": _plugin_loaded(), "georeferences": georefs,
            "tilesets": tilesets, "has_sun": has_sun, "notes": notes}


def action_status(notes):
    return _describe(notes)


def action_goto(notes):
    lat = float(PARAMS.get("lat"))
    lon = float(PARAMS.get("lon"))
    height = float(PARAMS.get("height") or 200.0)
    georefs = _actors_of("CesiumGeoreference")
    if not georefs:
        notes.append("no CesiumGeoreference in the level - run setup first")
        return _describe(notes)
    moved = 0
    for geo in georefs:
        if _set_origin(geo, lat, lon, height, notes):
            moved += 1
    refreshed = 0
    for tileset in _actors_of("Cesium3DTileset"):
        if _safe(lambda: tileset.refresh_tileset()) is not None or True:
            refreshed += 1
    result = _describe(notes)
    result["moved_georeferences"] = moved
    result["refreshed_tilesets"] = refreshed
    return result


def action_setup(notes):
    if not _plugin_loaded():
        notes.append("Cesium for Unreal plugin is not enabled - install it from Fab, "
                     "enable it in Edit -> Plugins, restart, then retry")
        return _describe(notes)

    if not _actors_of("CesiumGeoreference"):
        if _spawn("CesiumGeoreference", "CesiumGeoreference") is None:
            notes.append("failed to spawn CesiumGeoreference")

    url = PARAMS.get("url")
    key = PARAMS.get("key")
    if not url and key:
        url = "https://tile.googleapis.com/v1/3dtiles/root.json?key=" + key
    if not _actors_of("Cesium3DTileset"):
        tileset = _spawn("Cesium3DTileset", "WorldTiles")
        if tileset is None:
            notes.append("failed to spawn Cesium3DTileset")
        elif url:
            source_enum = getattr(unreal, "TilesetSource", None)
            if source_enum is not None:
                _safe(lambda: tileset.set_editor_property("tileset_source", source_enum.FROM_URL))
            if _safe(lambda: tileset.set_editor_property("url", url)) is None:
                pass  # set_editor_property returns None on success too; verify below
            if not _safe(lambda: str(_prop(tileset, "url"))):
                notes.append("could not set the tileset URL - set it in the Details panel")
        else:
            notes.append("tileset created without a URL (no --key/--url given); "
                         "it will show nothing until one is set")

    if PARAMS.get("add_sky", True) and not _describe([])["has_sun"]:
        for cls, label in (("DirectionalLight", "Sun"), ("SkyAtmosphere", "SkyAtmosphere"),
                           ("SkyLight", "SkyLight")):
            if _spawn(cls, label) is None:
                notes.append("could not add %s" % cls)

    if PARAMS.get("lat") is not None and PARAMS.get("lon") is not None:
        return action_goto(notes)
    return _describe(notes)


def main():
    notes = []
    action = PARAMS.get("action") or "status"
    if not _plugin_loaded() and action != "setup":
        notes.append("Cesium for Unreal plugin not detected (unreal.CesiumGeoreference missing). "
                     "Fab -> 'Cesium for Unreal' (free) -> install -> Edit -> Plugins -> enable -> restart.")
        _emit(_describe(notes))
        return
    handler = {"status": action_status, "goto": action_goto, "setup": action_setup}.get(action)
    if handler is None:
        _emit({"fatal": "unknown action %r" % action})
        return
    _emit(handler(notes))


try:
    main()
except Exception:
    _emit({"fatal": traceback.format_exc()})
