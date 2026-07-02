"""Offline test suite — everything that can be verified without Unreal.

Run it with plain Python (no test framework needed):

    python tests/test_offline.py

CI runs this on every push (see .github/workflows/tests.yml).
"""

import json
import os
import struct
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))

import bp_report  # noqa: E402
import scene_diff  # noqa: E402
import uaa_remote  # noqa: E402
import uasset_peek  # noqa: E402

failures = []


def check(label, cond, extra=""):
    print(("[OK] " if cond else "[FAIL] ") + label + (("  " + str(extra)) if extra and not cond else ""))
    if not cond:
        failures.append(label)


TMP = tempfile.mkdtemp(prefix="uaa_tests_")


# ---------------------------------------------------------------------- #
# blueprint reports
# ---------------------------------------------------------------------- #

sample_bp = {
    "name": "BP_SlidingDoor",
    "path": "/Game/Blueprints/BP_SlidingDoor.BP_SlidingDoor",
    "parent_class": "Actor",
    "ancestry": ["BP_SlidingDoor_C", "Actor", "Object"],
    "description": "Sliding door that opens for the player.",
    "interfaces": ["BPI_Interactable"],
    "components": [
        {"name": "DoorFrame", "class": "StaticMeshComponent",
         "children": [{"name": "DoorPanel", "class": "StaticMeshComponent"}]},
        {"name": "TriggerZone", "class": "BoxComponent"},
    ],
    "variables": [
        {"name": "open_speed", "type": "float", "default": "1.5"},
        {"name": "locked", "type": "bool", "default": "False"},
    ],
    "functions": [{"name": "toggle_lock", "signature": "x.toggle_lock() -> None"}],
    "graphs": [{
        "kind": "event_graph", "name": "EventGraph",
        "nodes": [
            {"type": "K2Node_Event", "event": "ReceiveBeginPlay"},
            {"type": "K2Node_CallFunction", "calls": "Play", "calls_owner": "Timeline_SlideOpen"},
            {"type": "K2Node_VariableGet", "variable": "locked"},
            {"type": "K2Node_VariableSet", "variable": "is_open"},
            {"type": "K2Node_Event", "custom_event": "ForceOpen", "comment": "Called by the level puzzle"},
        ],
    }],
    "widgets": {"name": "Canvas", "class": "CanvasPanel",
                "children": [{"name": "Title", "class": "TextBlock", "text": "Hello"}]},
    "errors": ["graphs: macro_graphs exists but could not be iterated"],
}
bp_json = os.path.join(TMP, "BP_SlidingDoor.json")
with open(bp_json, "w", encoding="utf-8") as fh:
    json.dump(sample_bp, fh)
md = open(bp_report.write_report(bp_json), encoding="utf-8").read()
check("bp report: explains kind", "an object that can be placed in a level" in md)
check("bp report: translates BeginPlay", "When the game starts" in md)
check("bp report: component tree", "**DoorPanel** (StaticMeshComponent)" in md)
check("bp report: reads vs writes", "**Changes:** is_open" in md)
check("bp report: custom events", "ForceOpen" in md)
check("bp report: call owners", "Play (on Timeline_SlideOpen)" in md)
check("bp report: widget tree", '**Title** (TextBlock) - shows "Hello"' in md)
check("bp report: honest blind spots", "could NOT see" in md)

# ---------------------------------------------------------------------- #
# material reports
# ---------------------------------------------------------------------- #

sample_mat = {
    "name": "MI_Rock_Mossy", "path": "/Game/Materials/MI_Rock_Mossy",
    "asset_class": "MaterialInstanceConstant", "is_instance": True,
    "parent_chain": ["MI_Rock", "M_RockBase"],
    "parameters": {
        "scalar": [{"name": "Roughness", "value": 0.7}],
        "vector": [{"name": "MossTint", "value": [0.2, 0.5, 0.1, 1.0]}],
        "texture": [], "switch": [],
    },
    "errors": [],
}
mat_json = os.path.join(TMP, "MI_Rock_Mossy.json")
with open(mat_json, "w", encoding="utf-8") as fh:
    json.dump(sample_mat, fh)
mat_md = open(bp_report.write_material_report(mat_json), encoding="utf-8").read()
check("material report: instance explained", "Material Instance" in mat_md and "M_RockBase" in mat_md)
check("material report: sliders table", "Roughness" in mat_md and "0.7" in mat_md)
check("material report: colors table", "MossTint" in mat_md)

base_mat = {"name": "M_Glass", "path": "/Game/M_Glass", "asset_class": "Material",
            "is_instance": False, "blend_mode": "BlendMode.BLEND_TRANSLUCENT",
            "parameters": {"scalar": [], "vector": [], "texture": [], "switch": []}, "errors": []}
base_json = os.path.join(TMP, "M_Glass.json")
with open(base_json, "w", encoding="utf-8") as fh:
    json.dump(base_mat, fh)
base_md = open(bp_report.write_material_report(base_json), encoding="utf-8").read()
check("material report: blend mode gloss", "see-through" in base_md)
check("material report: no-knobs case", "no artist-facing knobs" in base_md)

# ---------------------------------------------------------------------- #
# scene diff (the checkpoint safety net)
# ---------------------------------------------------------------------- #

old_scene = {"actors": [
    {"label": "Floor", "class": "StaticMeshActor", "location": [0, 0, 0]},
    {"label": "Sun", "class": "DirectionalLight", "location": [0, 0, 500]},
    {"label": "Rock1", "class": "StaticMeshActor", "location": [100, 0, 0]},
]}
new_scene = {"actors": [
    {"label": "Floor", "class": "StaticMeshActor", "location": [0, 0, 0]},
    {"label": "Sun", "class": "DirectionalLight", "location": [0, 0, 800]},
    {"label": "Campfire", "class": "Actor", "location": [50, 50, 0]},
]}
result = scene_diff.diff(old_scene, new_scene)
check("diff: detects addition", [a["label"] for a in result["added"]] == ["Campfire"])
check("diff: detects removal", [a["label"] for a in result["removed"]] == ["Rock1"])
check("diff: detects movement", len(result["moved"]) == 1 and result["moved"][0]["label"] == "Sun"
      and abs(result["moved"][0]["distance"] - 300.0) < 0.1)
check("diff: same scene is quiet", scene_diff.format_diff(scene_diff.diff(old_scene, old_scene))
      .startswith("No changes"))
check("diff: keep keys", "Floor||StaticMeshActor" in scene_diff.keep_keys(old_scene))
check("diff: human readable", "+ Campfire" in scene_diff.format_diff(result))

# ---------------------------------------------------------------------- #
# remote-execution helpers
# ---------------------------------------------------------------------- #

src = uaa_remote.inject_params("print(PARAMS)", {"target": "BP_Door", "limit": 5})
check("remote: inject_params is valid python",
      src.startswith("UAA_PARAMS_JSON = ")
      and json.loads(eval(src.split(" = ", 1)[1].split("\n")[0])) == {"target": "BP_Door", "limit": 5})

fake = {"success": True, "result": "None", "output": [
    {"type": "Info", "output": "noise\n"},
    {"type": "Info", "output": "UAA_RESULT_BEGIN\n"},
    {"type": "Info", "output": json.dumps({"reports": [1]}) + "\n"},
    {"type": "Info", "output": "UAA_RESULT_END\n"},
    {"type": "Error", "output": "LogTemp: an error"},
]}
check("remote: extract_result", uaa_remote.extract_result(fake) == {"reports": [1]})
check("remote: output_errors", uaa_remote.output_errors(fake) == ["LogTemp: an error"])
msg = json.loads(uaa_remote.UnrealConnection()._make_message("ping").decode())
check("remote: message shape", msg["magic"] == "ue_py" and msg["version"] == 1 and msg["type"] == "ping")

# ---------------------------------------------------------------------- #
# .uasset peek
# ---------------------------------------------------------------------- #

def fstring(text):
    raw = text.encode("ascii") + b"\x00"
    return struct.pack("<i", len(raw)) + raw

names = ["/Script/Engine", "/Script/CoreUObject", "Blueprint", "BP_TestDoor_C",
         "/Game/Meshes/SM_Door", "OpenSpeed", "ReceiveBeginPlay", "None"]
name_blob = b"".join(fstring(n) + struct.pack("<HH", 0, 0) for n in names)
header = struct.pack("<I", 0x9E2A83C1) + struct.pack("<i", -8)
header += struct.pack("<i", 864) + struct.pack("<i", 522) + struct.pack("<i", 1012)
header += struct.pack("<i", 0) + struct.pack("<i", 0) + struct.pack("<i", 4096)
header += fstring("None") + struct.pack("<I", 0)
name_offset = len(header) + 8
header += struct.pack("<i", len(names)) + struct.pack("<i", name_offset)
package = header + name_blob + b"\x00" * 64

uasset = os.path.join(TMP, "BP_TestDoor.uasset")
with open(uasset, "wb") as fh:
    fh.write(package)
info = uasset_peek.summarize(uasset)
check("peek: structured name table", info["read_method"] == "name table", info["read_method"])
check("peek: engine modules", info["engine_modules"] == ["/Script/CoreUObject", "/Script/Engine"])
check("peek: blueprint detected", info["looks_like_blueprint"])

broken = package[:40] + b"\xff\xff\xff\xff" + package[44:]
uasset2 = os.path.join(TMP, "broken.uasset")
with open(uasset2, "wb") as fh:
    fh.write(broken)
info2 = uasset_peek.summarize(uasset2)
check("peek: graceful fallback on corruption",
      info2["read_method"].startswith("string scan") and "/Script/Engine" in info2["engine_modules"])

txt = os.path.join(TMP, "not_a_package.uasset")
with open(txt, "wb") as fh:
    fh.write(b"hello this is not unreal at all" * 4)
check("peek: non-package flagged", not uasset_peek.summarize(txt)["valid_unreal_package"])

# ---------------------------------------------------------------------- #

print()
print("FAILURES: %d" % len(failures))
sys.exit(1 if failures else 0)
