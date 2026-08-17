# RIFTBOUND
## A 2D Fighting Game with Modular Architecture

```
Riftbound/
│
├── main.py                    # 🎮 Game entry point
│
├── engine/                    # ⚙️ Core game systems
│   ├── __init__.py           # Engine package init
│   ├── controller.py         # HID input & D-PAD smoothing
│   ├── fighter.py            # Base Fighter class (physics, combat, movement)
│   ├── combat.py             # Attack data & damage calculations
│   ├── hitbox.py             # Attack hitbox system
│   └── camera.py             # Camera setup & facing logic
│
├── characters/                # 👥 Playable fighter archetypes
│   ├── __init__.py           # Character registry
│   ├── agile_hero.py         # Fast rushdown character (double jump, dash)
│   ├── grappler.py           # Slow powerhouse (armor, command grabs)
│   ├── zoner.py              # Projectile keepaway character
│   └── aerial_fighter.py     # Air specialist (multi-jump, air dash)
│
├── assets/                    # 🎨 Game resources (placeholders)
│   ├── models/               # 3D models (.obj, .fbx)
│   ├── animations/           # Animation data (.anim)
│   ├── sounds/               # Audio files (.wav, .ogg)
│   └── textures/             # Images (.png, .jpg)
│
└── ui/                       # 🖥️ User interface
    ├── __init__.py           # UI package init
    ├── health_bar.py         # Health display system
    └── menus.py              # Main menu, char select, pause, debug HUD
```

---

## 🚀 Quick Start

### Requirements
- Python 3.8+
- Ursina Engine (`pip install ursina`)
- hid module for controller support (`pip install hid-api`)
- Custom HID controller (VID: 0x146B, PID: 0x0603)

### Running the Game

```bash
cd Riftbound/
python main.py
```

### Keyboard Fallback (no controller needed)
| Key | Action |
|-----|--------|
| A/D | Move left/right |
| Space | Jump (tap=short, hold=high) |
| Q | Light Attack |
| W | Medium Attack |
| E | Heavy Attack |

---

## 🎯 Features Implemented

### Core Systems ✅
- **Smooth D-PAD Movement**: Interpolated input matches analog stick feel
- **Variable Height Jumps**: Tap for short hops, hold for full height
- **Coyote Time**: 80ms forgiveness window after leaving edges
- **Jump Buffering**: Press before landing - still jumps!
- **Air Control**: Move while airborne (slightly slower)
- **Arena Boundaries**: Can't walk off stage

### Combat System ✅
- **Attack Phases**: Startup → Active → Recovery
- **Hit Detection**: Range + height based collision
- **Block Mechanic**: L2 to block (reduces 80% damage)
- **Knockback Physics**: Directional pushback on hit
- **Combo Counter**: Tracks consecutive hits

### Character Archetypes ✅
1. **Agile Hero** (+30% speed, double jump, dash)
2. **Grappler** (+30 HP, super armor, command grabs)
3. **Zoner** (projectiles, anti-air tools)
4. **Aerial Fighter** (triple jump, air dash, fast fall)

---

## 📁 Module Details

### `engine/controller.py`
- HID device communication
- D-PAD smoothing algorithm
- Button state tracking (held vs just_pressed)
- Input buffering system

### `engine/fighter.py`
- Base Fighter entity class
- State machine (IDLE/WALK/JUMP/ATTACK/BLOCK/HITSTUN/KO)
- Gravity and jump physics
- Movement and arena clamping
- Combo timer management

### `characters/*.py`
Each character extends Fighter with unique abilities:
- Modified stats (speed, damage, health)
- Special mechanics (jumps, armor, projectiles)
- Character-specific attacks

### `ui/menus.py`
- MainMenu: Start/settings/quit options
- CharacterSelectScreen: Fighter selection
- PauseMenu: In-game pause screen
- DebugHUD: Real-time game state display

---

## 🔧 Configuration

Edit constants in respective modules:

```python
# engine/fighter.py - Physics
GRAVITY = 22
JUMP_FORCE = 11
MOVE_SPEED = 7

# engine/controller.py - Input
DPAD_SMOOTH_SPEED = 15  # Higher=snappier, Lower=more fluid
DEADZONE = 0.12

# engine/combat.py - Balance
ATTACKS['LIGHT']['damage'] = 5
BLOCK_DAMAGE_REDUCTION = 0.8
```

---

## 🎮 Adding New Characters

1. Create file in `characters/`:
```python
from ..engine.fighter import Fighter

class YourCharacter(Fighter):
    SPEED_MULTIPLIER = 1.0
    DAMAGE_MULTIPLIER = 1.0
    HEALTH_MODIFIER = 100
    
    def __init__(self, position, color=None):
        super().__init__("YOUR CHAR", position, color or (1,1,1))
        # Add custom abilities...
```

2. Register in `characters/__init__.py`:
```python
CHARACTER_REGISTRY['your_char'] = {
    'class': YourCharacter,
    'name': 'Your Character',
    'description': 'Description here',
    'color': (r, g, b)
}
```

3. Use in `main.py`:
```python
from characters.your_character import YourCharacter
player = YourCharacter((-5, 1, 0))
```

---

## 📝 Development Notes

- All coordinates relative to arena center (0,0,0)
- Ground level at Y=1
- Positive X = right, Negative X = left
- Time values in seconds (use `time.dt` for frame-independent)
- Colors use Ursina's `color.rgb(r,g,b)` format

---

## 🐛 Debugging

Debug HUD shows (top-left of screen):
- Current state
- Active attack name
- Health values
- Position coordinates
- FPS counter

Toggle visibility by calling `debug_hud.toggle_visibility()`

---

**Version**: 0.1.0 (Modular Architecture)  
**Engine**: Ursina (Python)  
**Controller**: Custom HID (VID:146B PID:0603)

---

*Built with ❤️ for fighting game enthusiasts*
