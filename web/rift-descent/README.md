# Riftbound: Descent

An isometric hack-and-slash roguelike in the browser (three.js). You fight down through eight crypt chambers, take a boon after each cleared room, and fight Varkas, the Bone Warden, at the bottom.

## Run locally
```
python3 -m http.server 8000 --directory web/rift-descent
# open http://localhost:8000/
```

## Controls
WASD to move, mouse to aim. Left click or J is a three-hit combo; strike right after a dash to lunge. Right click or K is Whirl (area attack). Space or Shift dashes, and you cannot be hit mid-dash. Q fires Rift Bolt, Esc pauses, M mutes. Touch screens get a virtual stick and buttons.

## Asset pipeline (Blender)
The source models are the CC0 KayKit packs by Kay Lousberg: Adventurers, Skeletons and Dungeon Remastered.
1. `pip install bpy` (Blender 5.x as a Python module)
2. Download the KayKit GLBs into a raw folder (see the list in `tools/blender/bake_assets.py`)
3. `python tools/blender/bake_assets.py <raw> web/rift-descent/assets` keeps only the knight's sword and shield, trims each rig to the animations the game uses, bone-parents the skeleton weapons to `handslot.r`/`handslot.l`, merges the dungeon props into one kit, and models the rift gate and boon shrine.
4. `python tools/blender/pack_assets.py web/rift-descent/assets` writes the gzip+base64 `.glb.txt` files that the game loads.
