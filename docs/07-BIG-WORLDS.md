# Big worlds — procedural cities & making them playable

Two showstoppers: a city that builds itself, and levels you can actually
walk around in. Both are reachable from this harness — here is the honest
map of what the agent can drive and where you have to click.

## Part 1 — Procedural cities with PCG

**PCG** (Procedural Content Generation) is Unreal's built-in node system for
"rules instead of hand-placing": *scatter points on this surface → keep the
ones I want → put buildings on them*. Change a rule and a thousand buildings
update. Enable the **Procedural Content Generation Framework** plugin
(Edit → Plugins), restart, and the agent's `PCGToolset` (from the AllToolsets
plugin) can author actual PCG graphs for you over MCP.

The classic city recipe, in artist terms — each stage is something you can
watch appear in the viewport:

1. **Shape** — draw or describe the city's outline; it becomes a surface.
2. **Districts** — split it into colored neighborhoods (downtown, industrial…).
3. **Blocks** — a point grid per district; the gaps between cells become streets.
4. **Buildings** — a mesh spawner drops buildings on the points; height and
   style vary by district.
5. **Roads** — main avenues carved through with splines.
6. **Dress-up pass** — swap the blockout palette for real building meshes.

Ask for it in stages, not all at once:

> *"Enable PCG if needed, then make me a procedural city: start with just the
> shape and colored districts. Show me before you do the buildings."*

Two things worth knowing:

- **One step at a time is a hard rule.** Regenerating a PCG graph is one of
  those operations that must never run twice at once — the editor freezes.
  The agent knows this (it's in CLAUDE.md); if you drive PCG by hand, know
  it too.
- **Free building meshes:** Epic's **City Sample Buildings** pack (Fab, free
  with an Epic login — 2,000+ photoreal city meshes) is the classic
  dress-up-pass palette. Fab → add to library → **Add to Project** is a
  manual, multi-GB step only you can click; after that the agent can swap
  palettes freely. For fancier district shapes and road networks there's
  also the free, MIT-licensed **PCGEx** plugin.

## Part 2 — A character you can walk around with

Any level — your PCG city, a streamed real city, a hand-built diorama —
becomes "a game" with exactly four ingredients:

1. **A character** (a body with a camera and movement),
2. **a Game Mode** (the note that says "spawn *that* character"),
3. **a Player Start** (the spawn point),
4. **input bindings** (WASD/mouse — ship with the template character).

Unreal gives you all four for free via the **Third Person** content pack:

- **The one manual step:** in the editor, **Tools → Add Feature or Content
  Pack… → Blueprint tab → Third Person → Add to Project**. (Epic doesn't
  expose this dialog to automation — 30 seconds of clicking, once per
  project.)
- **Everything after is agent territory:** placing a Player Start where you
  want to spawn, setting the level's Game Mode override to
  `BP_ThirdPersonGameMode`, pressing Play. Just ask:

> *"I added the Third Person pack. Make this level playable — spawn me on the
> plaza facing the fountain."*

And when it works, meet your new best friend:

> */read-blueprint BP_ThirdPersonCharacter*

…is a great first Blueprint to have explained: you'll recognize everything
in it (camera arm, capsule, jump settings), because you've *used* it.

Walking on streamed Cesium tiles works too — the tiles have collision — just
expect spawn placement to need a nudge (the agent can trace for the ground).

## Part 3 — Bring your own buildings (Blender, optional)

If you have [Blender](https://www.blender.org) (free), this repo ships a
small starter generator for blockout towers you can use as a PCG palette:

```
blender --background --python tools/blender/make_building.py -- --floors 14 --out tower.fbx
blender --background --python tools/blender/make_building.py -- --floors 6 --width 30 --depth 20 --seed 7 --out low_wide.fbx
```

Then drop the FBX into Unreal (drag into the Content Browser, or ask the
agent to import it). It's deliberately simple — massing, setbacks, a roof
box — the point is silhouettes for cityscapes, and a file you can open and
tweak. Experimental: it hasn't been battle-tested across Blender versions,
so if it misbehaves, an issue (or PR!) is very welcome.
