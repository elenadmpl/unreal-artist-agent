"""blueprint_reader.py — runs INSIDE the Unreal Editor's Python.

Exports Blueprints to JSON files that humans and AI agents can read:
parent class, components, variables, functions, interfaces, and the node
graphs (events, function calls, variable reads/writes) as far as the
running engine version exposes them to Python.

Ways to run it:
  * From outside (recommended):  python tools/ue.py read-blueprint BP_Door
  * From the editor console:     py "C:/path/to/unreal-artist-agent/tools/inside_unreal/blueprint_reader.py"
    (exports EVERY Blueprint under /Game to <Project>/Saved/BlueprintExports)

Every section is wrapped in its own try/except: whatever this engine version
exposes gets exported, and anything it refuses is recorded under "errors"
instead of crashing the run. Nothing here modifies any asset — read only.
"""

import json
import os
import re
import traceback

import unreal

# Parameters injected by tools/ue.py; empty when run by hand in the editor.
try:
    PARAMS = json.loads(UAA_PARAMS_JSON)  # noqa: F821 (defined by the injector)
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
    if obj is None:
        return None
    try:
        return obj.get_editor_property(name)
    except Exception:
        return None


def _name_of(obj):
    if obj is None:
        return None
    return _safe(lambda: str(obj.get_name()), str(obj))


# ---------------------------------------------------------------------- #
# finding Blueprints
# ---------------------------------------------------------------------- #

def _asset_class_name(asset_data):
    for getter in (
        lambda: str(asset_data.asset_class_path.asset_name),  # UE 5.1+
        lambda: str(asset_data.get_editor_property("asset_class")),  # older
    ):
        value = _safe(getter)
        if value and value not in ("None", ""):
            return value
    return ""


def find_blueprints(root):
    """All Blueprint-like assets under `root` (default /Game)."""
    found = []
    paths = _safe(lambda: unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False)) or []
    for path in paths:
        data = _safe(lambda: unreal.EditorAssetLibrary.find_asset_data(path))
        if data is None:
            continue
        cls = _asset_class_name(data)
        if cls.endswith("Blueprint"):
            found.append({"path": str(path), "asset_class": cls})
    return found


# ---------------------------------------------------------------------- #
# reading one Blueprint
# ---------------------------------------------------------------------- #

def _generated_class(bp, path):
    candidates = (
        lambda: unreal.BlueprintEditorLibrary.generated_class(bp),
        lambda: bp.generated_class(),
        lambda: bp.get_editor_property("generated_class"),
        lambda: unreal.load_object(None, path.split(".")[0] + "." + bp.get_name() + "_C"),
    )
    for fn in candidates:
        cls = _safe(fn)
        if cls is not None:
            return cls
    return None


def _components(bp, errors):
    scs = _prop(bp, "simple_construction_script")
    if scs is None:
        return []
    roots = _prop(scs, "root_nodes")
    if roots is None:
        errors.append("components: SimpleConstructionScript found but root_nodes not readable on this engine version")
        return []

    def walk(node):
        entry = {"name": _safe(lambda: str(_prop(node, "internal_variable_name")))}
        comp_class = _prop(node, "component_class")
        if comp_class is None:
            template = _prop(node, "component_template")
            comp_class = _safe(lambda: template.get_class()) if template is not None else None
        entry["class"] = _name_of(comp_class)
        children = _prop(node, "child_nodes") or []
        kids = [walk(child) for child in children]
        if kids:
            entry["children"] = kids
        return entry

    return [walk(node) for node in roots]


def _variables(bp, gen_class, errors):
    """Best-effort variable list, from two independent angles."""
    out = []
    seen = set()

    # Angle 1: the Blueprint's own variable descriptions (richest, when exposed).
    new_vars = _prop(bp, "new_variables")
    if new_vars is not None:
        try:
            for var in new_vars:
                name = _safe(lambda: str(_prop(var, "var_name")))
                if not name:
                    continue
                entry = {"name": name, "source": "blueprint"}
                category = _safe(lambda: str(_prop(var, "category")))
                if category and category != "None":
                    entry["category"] = category
                default = _safe(lambda: str(_prop(var, "default_value")))
                if default:
                    entry["default"] = default
                out.append(entry)
                seen.add(name.lower())
        except Exception:
            errors.append("variables: new_variables exists but its entries are not readable here")

    # Angle 2: reflect over the compiled class's default object. Also brings
    # in defaults and Python-visible types.
    if gen_class is not None:
        try:
            cdo = unreal.get_default_object(gen_class)
            py_type = type(cdo)
            base = py_type.__mro__[1] if len(py_type.__mro__) > 1 else object
            own_names = sorted(set(dir(py_type)) - set(dir(base)))
            for name in own_names:
                if name.startswith("_"):
                    continue
                try:
                    value = getattr(cdo, name)
                except Exception:
                    continue
                if callable(value):
                    continue  # functions are collected separately
                snake = name.lower().replace("_", "")
                already = next((v for v in out if v["name"].lower().replace(" ", "").replace("_", "") == snake), None)
                if already is not None:
                    already.setdefault("type", type(value).__name__)
                    already.setdefault("default", repr(value)[:120])
                    continue
                if name.lower() in seen:
                    continue
                out.append({
                    "name": name,
                    "type": type(value).__name__,
                    "default": repr(value)[:120],
                    "source": "compiled_class",
                })
        except Exception:
            errors.append("variables: could not reflect over the compiled class default object")

    return out


def _functions(gen_class, errors):
    out = []
    if gen_class is None:
        return out
    try:
        cdo = unreal.get_default_object(gen_class)
        py_type = type(cdo)
        base = py_type.__mro__[1] if len(py_type.__mro__) > 1 else object
        for name in sorted(set(dir(py_type)) - set(dir(base))):
            if name.startswith("_"):
                continue
            try:
                value = getattr(cdo, name)
            except Exception:
                continue
            if not callable(value):
                continue
            doc = (getattr(value, "__doc__", "") or "").strip().splitlines()
            out.append({"name": name, "signature": doc[0] if doc else ""})
    except Exception:
        errors.append("functions: could not reflect over the compiled class")
    return out


def _interfaces(bp):
    out = []
    descriptions = _prop(bp, "implemented_interfaces") or []
    try:
        for desc in descriptions:
            iface = _prop(desc, "interface")
            name = _name_of(iface)
            if name:
                out.append(name)
    except Exception:
        pass
    return out


def _describe_node(node):
    entry = {"type": _safe(lambda: str(node.get_class().get_name()), "UnknownNode")}
    comment = _prop(node, "node_comment")
    if comment:
        entry["comment"] = str(comment)
    # Which function / variable / event / delegate does this node touch?
    for ref_prop, key in (
        ("function_reference", "calls"),
        ("variable_reference", "variable"),
        ("event_reference", "event"),
        ("delegate_reference", "delegate"),
    ):
        ref = _prop(node, ref_prop)
        if ref is not None:
            member = _safe(lambda: str(_prop(ref, "member_name")))
            if member and member != "None":
                entry[key] = member
            owner = _prop(ref, "member_parent")
            owner_name = _name_of(owner)
            if owner_name:
                entry[key + "_owner"] = owner_name
    custom = _prop(node, "custom_function_name")
    if custom and str(custom) != "None":
        entry["custom_event"] = str(custom)
    macro = _prop(node, "macro_graph")
    if macro is not None:
        entry["macro"] = _name_of(macro)
    x, y = _prop(node, "node_pos_x"), _prop(node, "node_pos_y")
    if x is not None and y is not None:
        entry["pos"] = [int(x), int(y)]
    return entry


def _graphs(bp, errors):
    out = []
    for prop_name, kind in (
        ("ubergraph_pages", "event_graph"),
        ("function_graphs", "function"),
        ("macro_graphs", "macro"),
    ):
        graphs = _prop(bp, prop_name)
        if graphs is None:
            continue
        try:
            for graph in graphs:
                entry = {"kind": kind, "name": _name_of(graph)}
                nodes = _prop(graph, "nodes")
                if nodes is not None:
                    entry["nodes"] = [_describe_node(node) for node in nodes]
                else:
                    entry["nodes_unavailable"] = True
                out.append(entry)
        except Exception:
            errors.append("graphs: %s exists but could not be iterated" % prop_name)
    if not out:
        errors.append(
            "graphs: this engine version does not expose Blueprint graphs to Python; "
            "exported class-level info only"
        )
    return out


def _widgets(bp, errors):
    """For Widget (UI) Blueprints: the tree of on-screen elements."""
    tree = _prop(bp, "widget_tree")
    if tree is None:
        return None
    root = _prop(tree, "root_widget")
    if root is None:
        errors.append("widgets: widget_tree present but root_widget not readable")
        return None
    budget = [200]  # cap so a pathological tree can't run away

    def walk(widget):
        if widget is None or budget[0] <= 0:
            return None
        budget[0] -= 1
        entry = {"name": _name_of(widget),
                 "class": _safe(lambda: str(widget.get_class().get_name()))}
        text = _prop(widget, "text")  # TextBlocks/buttons: show their label
        if text is not None:
            entry["text"] = _safe(lambda: str(text))
        kids = []
        count = _safe(lambda: widget.get_children_count())
        if count:
            for i in range(int(count)):
                child = walk(_safe(lambda: widget.get_child_at(i)))
                if child:
                    kids.append(child)
        else:
            content = _safe(lambda: widget.get_content())
            child = walk(content) if content is not None else None
            if child:
                kids.append(child)
        if kids:
            entry["children"] = kids
        return entry

    return walk(root)


def read_one(path):
    errors = []
    bp = unreal.EditorAssetLibrary.load_asset(path)
    if bp is None:
        return {"path": path, "errors": ["could not load asset"]}
    gen_class = _generated_class(bp, path)
    cdo_mro = []
    if gen_class is not None:
        try:
            cdo = unreal.get_default_object(gen_class)
            cdo_mro = [cls.__name__ for cls in type(cdo).__mro__[:8]]
        except Exception:
            pass
    report = {
        "name": _name_of(bp),
        "path": path,
        "asset_class": _safe(lambda: str(bp.get_class().get_name())),
        "parent_class": _name_of(_prop(bp, "parent_class")),
        "ancestry": cdo_mro,
        "description": _safe(lambda: str(_prop(bp, "blueprint_description"))) or "",
        "interfaces": _interfaces(bp),
        "components": _components(bp, errors),
        "variables": _variables(bp, gen_class, errors),
        "functions": _functions(gen_class, errors),
        "graphs": _graphs(bp, errors),
        "errors": errors,
    }
    widgets = _widgets(bp, errors)
    if widgets is not None:
        report["widgets"] = widgets
    return report


# ---------------------------------------------------------------------- #
# main
# ---------------------------------------------------------------------- #

def _default_out_dir():
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    return os.path.join(saved, "BlueprintExports")


def _safe_filename(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name or "blueprint")


def main():
    root = PARAMS.get("root") or "/Game"
    target = PARAMS.get("target")  # exact path, or a name fragment like "door"
    out_dir = PARAMS.get("out_dir") or _default_out_dir()
    limit = int(PARAMS.get("limit") or 25)

    blueprints = find_blueprints(root)

    if PARAMS.get("list_only"):
        _emit({"blueprints": blueprints, "root": root})
        return

    selected = blueprints
    if target:
        needle = target.lower()
        exact = [b for b in blueprints if b["path"].lower() == needle
                 or b["path"].split(".")[0].lower() == needle.split(".")[0]]
        selected = exact or [b for b in blueprints if needle in b["path"].lower()]

    if not selected:
        _emit({"reports": [], "count_found": len(blueprints), "root": root,
               "message": "No Blueprint matched %r under %s" % (target, root)})
        return

    os.makedirs(out_dir, exist_ok=True)
    reports = []
    for item in selected[:limit]:
        try:
            data = read_one(item["path"])
        except Exception:
            data = {"path": item["path"], "errors": [traceback.format_exc()]}
        filename = _safe_filename((data.get("name") or item["path"].split("/")[-1])) + ".json"
        file_path = os.path.join(out_dir, filename)
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        reports.append({"name": data.get("name"), "path": item["path"], "json": file_path,
                        "sections_failed": len(data.get("errors") or [])})

    _emit({"reports": reports, "count_found": len(blueprints),
           "count_exported": len(reports), "out_dir": out_dir, "root": root,
           "truncated": len(selected) > limit})


try:
    main()
except Exception:
    _emit({"fatal": traceback.format_exc()})
