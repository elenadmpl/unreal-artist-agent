"""make_building.py — generate a blockout skyscraper in Blender, export FBX.

A tiny, original parametric building generator: stacked tiers with setbacks,
ledge slabs between tiers, and a roof block. Meant as silhouette/blockout
meshes for procedural cities (see docs/07-BIG-WORLDS.md), and as a friendly
first "generated asset" to open and tweak.

Run headless (no Blender window):

    blender --background --python tools/blender/make_building.py -- --floors 14 --out tower.fbx
    blender --background --python tools/blender/make_building.py -- --floors 6 --width 30 --depth 20 --seed 7 --out low_wide.fbx

Units are meters. Status: experimental — written for Blender 3.x/4.x FBX
defaults; if your Blender version misbehaves, please open an issue.
"""

import argparse
import random
import sys

import bpy


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Blockout building generator")
    parser.add_argument("--floors", type=int, default=12, help="total floors (default 12)")
    parser.add_argument("--floor-height", type=float, default=3.2, dest="floor_height",
                        help="meters per floor (default 3.2)")
    parser.add_argument("--width", type=float, default=22.0, help="footprint width in meters")
    parser.add_argument("--depth", type=float, default=18.0, help="footprint depth in meters")
    parser.add_argument("--tiers", type=int, default=0,
                        help="how many setback tiers (0 = pick from floor count)")
    parser.add_argument("--seed", type=int, default=0, help="random seed for variation")
    parser.add_argument("--out", default="building.fbx", help="output FBX path")
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def add_box(name, center, size):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    box = bpy.context.active_object
    box.name = name
    box.scale = (size[0], size[1], size[2])
    return box


def build(args):
    rng = random.Random(args.seed)
    tiers = args.tiers or (1 if args.floors <= 6 else rng.choice((2, 2, 3)))
    floors_left = args.floors
    width, depth = args.width, args.depth
    z = 0.0
    parts = []

    for tier in range(tiers):
        remaining_tiers = tiers - tier
        floors = floors_left if remaining_tiers == 1 else max(
            2, round(floors_left * rng.uniform(0.45, 0.6)))
        floors_left -= floors
        height = floors * args.floor_height

        parts.append(add_box("tier_%d" % tier,
                             (0.0, 0.0, z + height / 2.0),
                             (width, depth, height)))
        z += height

        # A thin ledge slab caps every tier — reads as architecture from afar.
        parts.append(add_box("ledge_%d" % tier,
                             (0.0, 0.0, z + 0.2),
                             (width + rng.uniform(0.6, 1.4),
                              depth + rng.uniform(0.6, 1.4), 0.4)))
        z += 0.4

        # Set back for the next tier.
        width *= rng.uniform(0.62, 0.8)
        depth *= rng.uniform(0.62, 0.8)

    # Roof block (mechanical penthouse), off-center for a less perfect look.
    parts.append(add_box("roof",
                         (rng.uniform(-1.0, 1.0) * width * 0.15,
                          rng.uniform(-1.0, 1.0) * depth * 0.15,
                          z + 1.5),
                         (width * 0.4, depth * 0.4, 3.0)))

    # Join everything into one mesh named after the output file.
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    building = bpy.context.active_object
    building.name = "Building_seed%d" % args.seed
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return building


def export(args):
    bpy.ops.export_scene.fbx(
        filepath=args.out,
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",
        bake_space_transform=True,
    )


def main():
    args = parse_args()
    clear_scene()
    building = build(args)
    building.select_set(True)
    export(args)
    dims = building.dimensions
    print("[make_building] wrote %s  (%.1fm x %.1fm x %.1fm, %d floors, seed %d)"
          % (args.out, dims.x, dims.y, dims.z, args.floors, args.seed))


if __name__ == "__main__":
    main()
