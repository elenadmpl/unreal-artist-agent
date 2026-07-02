"""bp_report.py — turn a Blueprint JSON export into a plain-English report.

Used by tools/ue.py after blueprint_reader.py has run inside the editor.
Can also be run by hand on any exported JSON file:

    python tools/bp_report.py exports/blueprints/BP_Door.json
"""

import json
import os
import sys

# What common parent classes mean, in artist language.
KIND_HINTS = [
    ("Character", "a playable or AI character (something that walks around)"),
    ("Pawn", "something a player or AI can possess and control"),
    ("GameModeBase", "the rules of the game (what happens on start, win, lose)"),
    ("GameMode", "the rules of the game (what happens on start, win, lose)"),
    ("PlayerController", "the bridge between the player's input and the game"),
    ("UserWidget", "a piece of UI - a menu, HUD element or on-screen panel"),
    ("AnimInstance", "an Animation Blueprint - it decides which animations play"),
    ("ActorComponent", "a reusable behaviour you can attach to other actors"),
    ("SceneComponent", "an attachable part with a position, used inside other actors"),
    ("LevelScriptActor", "a Level Blueprint - logic that belongs to one specific level"),
    ("Actor", "an object that can be placed in a level"),
]

# Event names that artists usually care about.
NOTABLE_EVENTS = {
    "ReceiveBeginPlay": "When the game starts / this object appears",
    "ReceiveTick": "Every single frame (runs constantly!)",
    "ReceiveActorBeginOverlap": "When something touches / enters this",
    "ReceiveActorEndOverlap": "When something stops touching / leaves this",
    "ReceiveHit": "When this physically collides with something",
    "ReceiveDestroyed": "When this object is removed from the world",
    "ReceiveAnyDamage": "When this takes damage",
}


def kind_of(report):
    ancestry = report.get("ancestry") or []
    parent = report.get("parent_class") or ""
    chain = ancestry + [parent]
    for marker, meaning in KIND_HINTS:
        for cls in chain:
            if cls and marker.lower() in cls.lower():
                return meaning
    return "a Blueprint (couldn't tell the exact kind from its parent class)"


def _component_lines(components, depth=0):
    lines = []
    for comp in components or []:
        label = comp.get("name") or "(unnamed)"
        cls = comp.get("class") or "?"
        lines.append("%s- **%s** (%s)" % ("  " * depth, label, cls))
        lines.extend(_component_lines(comp.get("children"), depth + 1))
    return lines


def _graph_summary(graphs):
    """Digest the node graphs: which events exist, what gets called/read/written."""
    events, calls, reads, writes, comments = [], [], [], [], []
    for graph in graphs or []:
        for node in graph.get("nodes") or []:
            ntype = node.get("type") or ""
            if node.get("custom_event"):
                events.append(("Custom event: " + node["custom_event"], None))
            elif node.get("event"):
                events.append((node["event"], NOTABLE_EVENTS.get(node["event"])))
            if node.get("calls"):
                target = node.get("calls_owner")
                calls.append(node["calls"] + ((" (on %s)" % target) if target else ""))
            if node.get("variable"):
                if "VariableSet" in ntype:
                    writes.append(node["variable"])
                else:
                    reads.append(node["variable"])
            if node.get("comment"):
                comments.append(node["comment"])
    dedupe = lambda seq: list(dict.fromkeys(seq))
    return dedupe(events), dedupe(calls), dedupe(reads), dedupe(writes), dedupe(comments)


def to_markdown(report):
    name = report.get("name") or "Unknown Blueprint"
    lines = ["# Blueprint report: %s" % name, ""]
    lines.append("**Where it lives:** `%s`" % (report.get("path") or "?"))
    lines.append("")
    lines.append("**What it is:** %s." % kind_of(report))
    parent = report.get("parent_class")
    if parent:
        lines.append("It is built on top of `%s`." % parent)
    desc = (report.get("description") or "").strip()
    if desc and desc != "None":
        lines.append("")
        lines.append("> Author's description: %s" % desc)
    lines.append("")

    interfaces = report.get("interfaces") or []
    if interfaces:
        lines.append("**Speaks these interfaces:** " + ", ".join("`%s`" % iface for iface in interfaces))
        lines.append("")

    components = report.get("components") or []
    if components:
        lines.append("## Parts (components)")
        lines.append("These are the building blocks glued together inside this Blueprint:")
        lines.append("")
        lines.extend(_component_lines(components))
        lines.append("")

    variables = report.get("variables") or []
    if variables:
        lines.append("## Settings (variables)")
        lines.append("Values that control how this Blueprint behaves. These are usually safe to look at and tweak:")
        lines.append("")
        lines.append("| Name | Type | Default |")
        lines.append("|---|---|---|")
        for var in variables[:60]:
            lines.append("| %s | %s | %s |" % (
                var.get("name", "?"),
                var.get("type", var.get("category", "")) or "",
                str(var.get("default", ""))[:60].replace("|", "\\|"),
            ))
        lines.append("")

    events, calls, reads, writes, comments = _graph_summary(report.get("graphs"))
    if events:
        lines.append("## When does it do things? (events)")
        for event, meaning in events[:40]:
            lines.append("- **%s**%s" % (event, (" - %s" % meaning) if meaning else ""))
        lines.append("")
    if calls:
        lines.append("## What does it do? (function calls, in graph order)")
        for call in calls[:80]:
            lines.append("- %s" % call)
        lines.append("")
    if reads or writes:
        lines.append("## Which settings does the logic touch?")
        if writes:
            lines.append("- **Changes:** " + ", ".join(writes[:30]))
        if reads:
            lines.append("- **Reads:** " + ", ".join(reads[:30]))
        lines.append("")
    if comments:
        lines.append("## Notes the author left in the graph")
        for comment in comments[:20]:
            lines.append("> %s" % comment)
        lines.append("")

    functions = report.get("functions") or []
    if functions:
        lines.append("## Its own functions")
        for fn in functions[:60]:
            sig = fn.get("signature") or fn.get("name")
            lines.append("- `%s`" % sig)
        lines.append("")

    errors = report.get("errors") or []
    if errors:
        lines.append("## What this report could NOT see")
        lines.append("(Your Unreal version keeps some internals hidden from Python - this is normal.)")
        for err in errors:
            lines.append("- %s" % err)
        lines.append("")

    return "\n".join(lines)


def write_report(json_path):
    with open(json_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)
    md_path = os.path.splitext(json_path)[0] + ".md"
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(to_markdown(report))
    return md_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/bp_report.py <exported-blueprint.json> [...]")
        sys.exit(1)
    for arg in sys.argv[1:]:
        print("Wrote", write_report(arg))
