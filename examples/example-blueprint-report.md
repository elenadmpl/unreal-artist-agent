# Blueprint report: BP_SlidingDoor

> **This is a sample** of what `python tools/ue.py read-blueprint` produces,
> so you can see the value before setting anything up. Yours will look like
> this, generated from your real Blueprints into `exports/blueprints/`.

**Where it lives:** `/Game/Blueprints/BP_SlidingDoor.BP_SlidingDoor`

**What it is:** an object that can be placed in a level.
It is built on top of `Actor`.

> Author's description: Sliding door that opens for the player.

## Parts (components)

- **DoorFrame** (StaticMeshComponent)
  - **DoorPanel** (StaticMeshComponent)
- **TriggerZone** (BoxComponent)
- **OpenSound** (AudioComponent)

## Settings (variables)

| Name | Type | Default |
|---|---|---|
| open_speed | float | 1.5 |
| slide_distance | float | 220.0 |
| stays_open | bool | False |
| locked | bool | False |
| open_curve | CurveFloat | Curve_EaseInOut |

## When does it do things? (events)

- **ReceiveBeginPlay** - When the game starts / this object appears
- **ReceiveActorBeginOverlap** - When something touches / enters this
- **ReceiveActorEndOverlap** - When something stops touching / leaves this

## What does it do? (function calls, in graph order)

- Cast To BP_PlayerCharacter
- Branch (on **locked**)
- Play (on Timeline_SlideOpen)
- SetRelativeLocation (on DoorPanel)
- Play (on OpenSound)
- Reverse (on Timeline_SlideOpen)

## Which settings does the logic touch?

- **Changes:** is_open
- **Reads:** locked, slide_distance, open_speed, stays_open

## Notes the author left in the graph

> Only opens for the player, not for physics junk rolling into the trigger.

## What this report could NOT see

(Your Unreal version keeps some internals hidden from Python - this is normal.)
- graphs: exact pin-to-pin wiring is not exported; order shown is graph order, not execution order

---

*What the agent tells an artist after reading this:*

> **BP_SlidingDoor is a door that opens itself.** It watches a invisible box
> around itself (TriggerZone). When the *player* walks in — it ignores rolling
> props on purpose, per the author's note — and the door isn't `locked`, it
> slides the panel `slide_distance` centimeters along a smooth ease-in-out
> curve at `open_speed`, with a sound. When you walk away it slides back,
> unless `stays_open` is on.
>
> **Knobs you can safely play with:** `open_speed` (feel: lazy vs snappy),
> `slide_distance` (how far it opens), `stays_open`, `locked` — all per-door,
> right in the Details panel. Want me to make the doors in your level open
> slower and stay open?
