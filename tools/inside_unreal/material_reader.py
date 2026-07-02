"""material_reader.py — runs INSIDE the Unreal Editor's Python.

Exports Materials and Material Instances to JSON: what they are, which
parent they're based on, and every artist-facing parameter (the sliders,
colors and textures) with its current value. Read only.

Run from outside:   python tools/ue.py read-material <name>
Run in the editor:  py ".../tools/inside_unreal/material_reader.py"
"""

import json
import os
import re
import traceback

import unreal

try:
    PARAMS = json.loads(UAA_PARAMS_JSON)  # noqa: F821 (injected by tools/ue.py)
except NameError:
    PARAMS = {}

MATERIAL_CLASSES = ("Material", "MaterialInstanceConstant")


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
    if obj is None:
        return None
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def _asset_class_name(asset_data):
    for getter in (
        lambda: str(asset_data.asset_class_path.asset_name),
        lambda: str(asset_data.get_editor_property("asset_class")),
    ):
        value = _safe(getter)
        if value and value not in ("None", ""):
            return value
    return ""


def find_materials(root):
    found = []
    paths = _safe(lambda: unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)) or []
    for path in paths:
        data = _safe(lambda: unreal.EditorAssetLibrary.find_asset_data(path))
        if data is None:
            continue
        cls = _asset_class_name(data)
        if cls in MATERIAL_CLASSES:
            found.append({"path": str(path), "asset_class": cls})
    return found


def _vector_value(value):
    return _safe(lambda: [round(value.r, 3), round(value.g, 3), round(value.b, 3), round(value.a, 3)])


def _instance_overrides(material, errors):
    """Parameters this instance overrides compared to its parent."""
    out = {"scalar": [], "vector": [], "texture": [], "switch": []}
    specs = (
        ("scalar_parameter_values", "scalar", lambda v: _safe(lambda: round(float(v), 4))),
        ("vector_parameter_values", "vector", _vector_value),
        ("texture_parameter_values", "texture", lambda v: _safe(lambda: str(v.get_name()))),
    )
    for prop_name, bucket, converter in specs:
        values = _prop(material, prop_name)
        if values is None:
            continue
        try:
            for entry in values:
                info = _prop(entry, "parameter_info")
                name = _safe(lambda: str(_prop(info, "name")))
                value = converter(_prop(entry, "parameter_value"))
                if name:
                    out[bucket].append({"name": name, "value": value})
        except Exception:
            errors.append("parameters: %s exists but is not readable here" % prop_name)
    return out


def _base_material_params(material, errors):
    """All parameters a base Material exposes, with their defaults."""
    out = {"scalar": [], "vector": [], "texture": [], "switch": []}
    lib = getattr(unreal, "MaterialEditingLibrary", None)
    if lib is None:
        errors.append("parameters: MaterialEditingLibrary unavailable")
        return out
    specs = (
        ("get_scalar_parameter_names", "get_material_default_scalar_parameter_value",
         "scalar", lambda v: _safe(lambda: round(float(v), 4))),
        ("get_vector_parameter_names", "get_material_default_vector_parameter_value",
         "vector", _vector_value),
        ("get_texture_parameter_names", "get_material_default_texture_parameter_value",
         "texture", lambda v: _safe(lambda: str(v.get_name()))),
        ("get_static_switch_parameter_names", "get_material_default_static_switch_parameter_value",
         "switch", lambda v: bool(v)),
    )
    for names_fn, default_fn, bucket, converter in specs:
        names = _safe(lambda: getattr(lib, names_fn)(material))
        if names is None:
            continue
        for name in names:
            default = _safe(lambda: converter(getattr(lib, default_fn)(material, name)))
            out[bucket].append({"name": str(name), "value": default})
    return out


def read_one(path, asset_class):
    errors = []
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material is None:
        return {"path": path, "errors": ["could not load asset"]}
    report = {
        "name": _safe(lambda: str(material.get_name())),
        "path": path,
        "asset_class": asset_class,
        "is_instance": asset_class != "Material",
    }
    if report["is_instance"]:
        chain = []
        parent = _prop(material, "parent")
        hops = 0
        while parent is not None and hops < 10:
            chain.append(_safe(lambda: str(parent.get_name())))
            parent = _prop(parent, "parent")
            hops += 1
        report["parent_chain"] = chain
        report["parameters"] = _instance_overrides(material, errors)
    else:
        for prop_name in ("material_domain", "blend_mode", "shading_model", "two_sided"):
            value = _prop(material, prop_name)
            if value is not None:
                report[prop_name] = str(value)
        report["parameters"] = _base_material_params(material, errors)
    report["errors"] = errors
    return report


def _safe_filename(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name or "material")


def main():
    root = PARAMS.get("root") or "/Game"
    target = PARAMS.get("target")
    out_dir = PARAMS.get("out_dir")
    if not out_dir:
        saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
        out_dir = os.path.join(saved, "MaterialExports")
    limit = int(PARAMS.get("limit") or 25)

    materials = find_materials(root)
    if PARAMS.get("list_only"):
        _emit({"materials": materials, "root": root})
        return

    selected = materials
    if target:
        needle = target.lower()
        exact = [m for m in materials if m["path"].lower() == needle]
        selected = exact or [m for m in materials if needle in m["path"].lower()]
    if not selected:
        _emit({"reports": [], "count_found": len(materials), "root": root,
               "message": "No material matched %r under %s" % (target, root)})
        return

    os.makedirs(out_dir, exist_ok=True)
    reports = []
    for item in selected[:limit]:
        try:
            data = read_one(item["path"], item["asset_class"])
        except Exception:
            data = {"path": item["path"], "errors": [traceback.format_exc()]}
        file_path = os.path.join(out_dir, _safe_filename(data.get("name")) + ".json")
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        reports.append({"name": data.get("name"), "path": item["path"], "json": file_path,
                        "sections_failed": len(data.get("errors") or [])})
    _emit({"reports": reports, "count_found": len(materials),
           "count_exported": len(reports), "out_dir": out_dir,
           "truncated": len(selected) > limit})


try:
    main()
except Exception:
    _emit({"fatal": traceback.format_exc()})
