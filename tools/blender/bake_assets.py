"""Blender asset bake for Riftbound: Descent (web hack-and-slash).

Takes the CC0 KayKit packs (Kay Lousberg, kaylousberg.com) and produces
compact, game-ready GLBs:

  hero.glb      Knight, sword + round shield only, trimmed action set
  skel_*.glb    Skeleton enemies with weapon bone-parented to handslot.r
  kit.glb       Dungeon props + Blender-modelled rift gate / boon orb

Run:  python bake_assets.py <raw_dir> <out_dir>      (pip install bpy)
"""
import math
import os
import sys

import bpy
from mathutils import Matrix

RAW, OUT = (os.path.abspath(p) for p in sys.argv[-2:])
os.makedirs(OUT, exist_ok=True)

HERO_KEEP_MESH = {"1H_Sword", "Round_Shield", "Knight_Helmet", "Knight_Cape",
                  "Knight_ArmLeft", "Knight_ArmRight", "Knight_Body",
                  "Knight_Head", "Knight_LegLeft", "Knight_LegRight"}
HERO_ANIMS = {"Idle", "Running_A", "1H_Melee_Attack_Slice_Diagonal",
              "1H_Melee_Attack_Slice_Horizontal", "1H_Melee_Attack_Chop",
              "1H_Melee_Attack_Stab", "2H_Melee_Attack_Spin", "Dodge_Forward",
              "Hit_A", "Death_A", "Spellcast_Shoot", "Cheer"}
SKEL_ANIMS = {"Idle_Combat", "Running_A", "Walking_D_Skeletons",
              "1H_Melee_Attack_Chop", "1H_Melee_Attack_Jump_Chop",
              "2H_Melee_Attack_Spin", "1H_Ranged_Shoot", "Spellcast_Shoot",
              "Spellcast_Summon", "Hit_A", "Death_C_Skeletons",
              "Spawn_Ground_Skeletons", "Taunt"}
# enemy -> (right-hand weapon, left-hand item or None)
SKELETONS = {
    "Minion": ("Blade", None),
    "Warrior": ("Axe", "Shield_Large_A"),
    "Rogue": ("Crossbow", None),
    "Mage": ("Staff", None),
}
PROPS = ["floor_tile_large", "floor_tile_large_rocks", "floor_tile_small_broken_A",
         "floor_tile_small_decorated", "wall", "wall_corner", "wall_broken",
         "wall_cracked", "wall_arched", "pillar", "pillar_decorated", "column",
         "torch_mounted", "barrel_large", "barrel_small_stack", "crates_stacked",
         "banner_red", "banner_patternA_red", "rubble_large", "rubble_half",
         "coin_stack_large", "sword_shield_broken", "stairs"]
PROP_FILES = {"wall_doorway": "wall_doorway.glb", "chest_gold": "chest_gold.glb",
              "floor_tile_big_spikes": "floor_tile_big_spikes.glb"}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def export(name, animations):
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, name), export_format="GLB",
        export_animations=animations, export_animation_mode="ACTIONS",
        export_force_sampling=True, export_optimize_animation_size=True,
        export_frame_step=1, export_apply=False, export_yup=True,
        export_image_format="AUTO", export_texcoords=True, export_normals=True,
        export_extras=False)


def trim_actions(keep):
    for act in list(bpy.data.actions):
        if act.name not in keep:
            bpy.data.actions.remove(act)
    for arm in (o for o in bpy.data.objects if o.type == "ARMATURE"):
        if arm.animation_data:
            for tr in list(arm.animation_data.nla_tracks):
                if not tr.strips or tr.strips[0].action is None:
                    arm.animation_data.nla_tracks.remove(tr)
            arm.animation_data.action = None


def dedupe_materials():
    """KayKit props share one palette atlas; collapse duplicates on import."""
    canon = {}
    for mat in list(bpy.data.materials):
        key = mat.name.split(".")[0]
        if key in canon:
            mat.user_remap(canon[key])
            bpy.data.materials.remove(mat)
        else:
            canon[key] = mat
    for img in list(bpy.data.images):
        key = img.name.split(".")[0]
        base = bpy.data.images.get(key)
        if base and base is not img:
            img.user_remap(base)
            bpy.data.images.remove(img)


def hand_offset():
    """Sword transform relative to handslot.r in the Knight rig (same rig as
    the skeletons), so weapons sit exactly like KayKit authored them."""
    objs = import_glb(os.path.join(RAW, "Knight.glb"))
    arm = next(o for o in objs if o.type == "ARMATURE")
    sword = bpy.data.objects["1H_Sword"]
    bone_r = arm.matrix_world @ arm.data.bones["handslot.r"].matrix_local
    bone_l = arm.matrix_world @ arm.data.bones["handslot.l"].matrix_local
    shield = bpy.data.objects["Round_Shield"]
    rel = (bone_r.inverted() @ sword.matrix_world,
           bone_l.inverted() @ shield.matrix_world)
    reset()
    return rel


def bake_hero():
    objs = import_glb(os.path.join(RAW, "Knight.glb"))
    for o in objs:
        if o.type == "MESH" and o.name not in HERO_KEEP_MESH:
            bpy.data.objects.remove(o, do_unlink=True)
    trim_actions(HERO_ANIMS)
    export("hero.glb", True)
    reset()


def attach(arm, item, bone, rel):
    objs = import_glb(os.path.join(RAW, "wpn", f"Skeleton_{item}.gltf"))
    mesh = next(o for o in objs if o.type == "MESH")
    for o in objs:
        if o is not mesh:
            bpy.data.objects.remove(o, do_unlink=True)
    world = arm.matrix_world @ arm.data.bones[bone].matrix_local @ rel
    mesh.parent = arm
    mesh.parent_type = "BONE"
    mesh.parent_bone = bone
    mesh.matrix_world = world
    mesh.name = f"wpn_{item}"


def bake_skeleton(kind, right, left, rel):
    objs = import_glb(os.path.join(RAW, f"Skeleton_{kind}.glb"))
    arm = next(o for o in objs if o.type == "ARMATURE")
    bpy.context.view_layer.update()
    attach(arm, right, "handslot.r", rel[0])
    if left:
        attach(arm, left, "handslot.l", rel[1])
    trim_actions(SKEL_ANIMS)
    dedupe_materials()
    export(f"skel_{kind.lower()}.glb", True)
    reset()


def emissive(name, rgb, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
    bsdf.inputs["Emission Strength"].default_value = strength
    bsdf.inputs["Roughness"].default_value = 0.35
    return mat


def stone(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    return mat


def build_rift_gate():
    """Hand-built in Blender: a carved stone arch ring with a glowing rift."""
    rock = stone("gate_stone", (0.16, 0.12, 0.14))
    glow = emissive("rift_glow", (1.0, 0.25, 0.55), 4.0)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.55, minor_radius=0.28,
                                     major_segments=10, minor_segments=6,
                                     location=(0, 0, 1.75), rotation=(math.pi / 2, 0, 0))
    ring = bpy.context.object
    ring.data.materials.append(rock)
    bev = ring.modifiers.new("bevel", "BEVEL")
    bev.width, bev.segments = 0.04, 2
    # Runes: small emissive studs around the ring
    for i in range(10):
        a = i / 10 * math.tau + math.pi / 10
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.11,
                                              location=(math.cos(a) * 1.55, -0.26,
                                                        1.75 + math.sin(a) * 1.55))
        bpy.context.object.data.materials.append(glow)
    bpy.ops.mesh.primitive_circle_add(vertices=32, radius=1.3, fill_type="TRIFAN",
                                      location=(0, 0, 1.75), rotation=(math.pi / 2, 0, 0))
    disc = bpy.context.object
    disc.data.materials.append(emissive("rift_core", (0.55, 0.05, 0.35), 2.5))
    disc.name = "gate_core"
    for z, w in ((0.1, 1.1), (0.3, 0.9)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, z), scale=(w * 3.6, 1.2, 0.2))
        bpy.context.object.data.materials.append(rock)
    parts = [o for o in bpy.context.scene.objects if o.parent is None and o.name.startswith(("Torus", "Ico", "Cube"))]
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = ring
    bpy.ops.object.convert(target="MESH")
    bpy.ops.object.join()
    ring.name = "rift_gate"
    disc.parent = ring
    disc.matrix_parent_inverse = ring.matrix_world.inverted()
    for o in bpy.context.selected_objects:
        o.select_set(False)


def build_boon_orb():
    gold = emissive("boon_gold", (1.0, 0.7, 0.25), 3.0)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.38, location=(0, 0, 1.2))
    core = bpy.context.object
    core.data.materials.append(gold)
    core.name = "boon_orb"
    bpy.ops.mesh.primitive_torus_add(major_radius=0.6, minor_radius=0.04, major_segments=32,
                                     minor_segments=4, location=(0, 0, 1.2),
                                     rotation=(math.radians(70), 0, 0))
    halo = bpy.context.object
    halo.data.materials.append(gold)
    halo.name = "boon_halo"
    halo.parent = core
    halo.matrix_parent_inverse = core.matrix_world.inverted()
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.45, depth=0.5, location=(0, 0, 0.25))
    ped = bpy.context.object
    ped.data.materials.append(stone("pedestal", (0.2, 0.15, 0.15)))
    ped.modifiers.new("bevel", "BEVEL").width = 0.05
    ped.name = "boon_pedestal"
    bpy.ops.object.select_all(action="DESELECT")
    ped.select_set(True)
    bpy.context.view_layer.objects.active = ped
    bpy.ops.object.convert(target="MESH")
    core.parent = ped
    core.matrix_parent_inverse = ped.matrix_world.inverted()


def bake_kit():
    files = {p: f"{p}.gltf.glb" for p in PROPS} | PROP_FILES
    for key, fname in files.items():
        objs = import_glb(os.path.join(RAW, fname))
        roots = [o for o in objs if o.parent is None]
        if len(roots) > 1:
            empty = bpy.data.objects.new(key, None)
            bpy.context.scene.collection.objects.link(empty)
            for r in roots:
                r.parent = empty
        else:
            roots[0].name = key
        (bpy.data.objects[key]).location = (0, 0, 0)
    dedupe_materials()
    build_rift_gate()
    build_boon_orb()
    export("kit.glb", False)
    reset()


if __name__ == "__main__":
    reset()
    rel = hand_offset()
    bake_hero()
    for kind, (r, l) in SKELETONS.items():
        bake_skeleton(kind, r, l, rel)
    bake_kit()
    for f in sorted(os.listdir(OUT)):
        print(f"{f:20s} {os.path.getsize(os.path.join(OUT, f)) / 1024:8.1f} KB")
