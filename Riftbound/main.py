"""
RIFTBOUND
A 2D Fighting Game built with Ursina Engine

Main Entry Point

Controls:
- D-PAD/Analog: Movement (smoothed)
- D-PAD UP: Jump (variable height)
- □: Light Attack
- △: Medium Attack  
- ○: Heavy Attack
- ✕: Launcher
- L2: Block
- Keyboard fallback: A/D=Move, Space=Jump, Q/W/E=Attacks

Author: Riftbound Dev Team
Version: 0.1.0 (Modular Architecture)
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Ensure console supports UTF-8 so unicode symbols print correctly on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from ursina import Ursina, window, camera, time, Entity, Text, AmbientLight, DirectionalLight, color

# Import engine modules
from engine.controller import (
    init_controller,
    close_controller,
    read_controller,
    get_horizontal,
    jump_just_pressed,
    light_pressed,
    medium_pressed,
    heavy_pressed,
    launcher_pressed,
    block_pressed,
    store_input_state
)

from engine.fighter import Fighter, MOVE_SPEED
from engine.combat import ATTACKS
from engine.camera import setup_camera, update_camera_facing, update_shake
from engine import juice

# Import UI modules
from ui.health_bar import HealthBar
from ui.menus import DebugHUD

# Import character classes
from characters.agile_hero import AgileHero
from characters.grappler import Grappler
from characters.zoner import Zoner
from characters.aerial_fighter import AerialFighter


# ============================================================
# GAME CONFIGURATION
# ============================================================

GAME_TITLE = "Riftbound"
# Window defaults — set to fullscreen and borderless for a filled display
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FULLSCREEN = True
BORDERLESS = True

ARENA_WIDTH = 30


# ============================================================
# GLOBAL GAME STATE
# ============================================================

# Fighter instances (created in setup)
player = None
enemy = None

# UI elements
debug_hud = None

# Game state flags
game_running = True
paused = False


# ============================================================
# INITIALIZATION
# ============================================================

def initialize_game():
    """Set up all game systems and objects"""
    
    global player, enemy, debug_hud, hit_flash
    
    print("=" * 60)
    print(f"  {GAME_TITLE.upper()}")
    print("=" * 60)
    print()
    
    # Initialize window
    window.title = GAME_TITLE
    window.borderless = BORDERLESS
    window.fullscreen = FULLSCREEN
    
    # Initialize controller
    if not init_controller():
        print("⚠ Controller not found - using keyboard only")
    
    # Setup camera
    setup_camera()
    
    # Create fighters using different character classes for variety
    # Player uses Agile Hero (fast, combo-focused)
    player = AgileHero(
        position=(-5, 1, 0),
        color=color.azure
    )
    
    # Enemy uses Grappler (slow, powerful) - can be changed to other classes
    enemy = Grappler(
        position=(5, 1, 0),
        color=color.red
    )
    
    # Alternative options:
    # enemy = Zoner(position=(5, 1, 0), color=color.red)
    # enemy = AerialFighter(position=(5, 1, 0), color=color.red)
    
    # Assign health bars
    player.health_bar = HealthBar((-0.55, 0.42))
    enemy.health_bar = HealthBar((0.55, 0.42))
    
    # Create debug HUD
    debug_hud = DebugHUD()
    
    # Setup lighting
    AmbientLight(color=color.rgba(150, 150, 150, 0.5))
    DirectionalLight(y=10, rotation=(45, -45, 45))

    # Create arena visuals (ground and side boundaries)
    from ursina import Entity
    half = ARENA_WIDTH / 2
    # Ground
    Entity(model='plane', scale=(ARENA_WIDTH * 2, 1, 10), position=(0, 0.5, 0), color=color.gray)
    # Left and right walls as visual boundaries
    Entity(model='cube', scale=(0.2, 6, 1), position=(-half - 0.1, 3, 0), color=color.dark_gray)
    Entity(model='cube', scale=(0.2, 6, 1), position=(half + 0.1, 3, 0), color=color.dark_gray)
    
    # Create full-screen hit flash (starts invisible) and register with juice
    try:
        hit_flash = Entity(parent=camera.ui, model='quad', scale=(2, 1), color=color.rgba(255,255,255,0), z=-1)
        try:
            juice.register_hit_flash(hit_flash)
        except Exception:
            pass
    except Exception:
        # If UI or camera not available yet, continue silently
        hit_flash = None

    # Print control scheme
    _print_controls()
    
    print()
    print("✓ Game initialized successfully!")
    print()


def _print_controls():
    """Print control scheme to console"""
    print()
    print("CONTROLS:")
    print("-" * 40)
    print("MOVEMENT:")
    print("  Left Analog / D-PAD L,R: Move")
    print("  D-PAD UP: Jump (tap=short, hold=high)")
    print()
    print("ATTACKS:")
    print("  □ (Cross):   Light Attack")
    print("  △ (Triangle): Medium Attack")
    print("  ○ (Circle):  Heavy Attack")
    print("  ✕ (Square):  Launcher")
    print()
    print("DEFENSE:")
    print("  L2: Block")
    print()
    print("KEYBOARD FALLBACK:")
    print("  A/D: Move | Space: Jump")
    print("  Q: Light | W: Medium | E: Heavy")
    print("-" * 40)


# ============================================================
# MAIN GAME LOOP
# ============================================================

def update():
    """
    Main update function - called every frame by Ursina.
    Handles input processing, game logic, and state updates.
    """
    
    global paused

    # Update camera shake (should run even during hitstop)
    try:
        update_shake(time.dt)
    except Exception:
        pass

    # Update hitstop first so frames can be frozen; if frozen, return early
    try:
        if juice.update_hitstop(time.dt):
            return
    except Exception:
        pass

    # Don't process game logic when paused
    if paused:
        return

    # Record previous horizontal positions for collision/bounce calculation
    if player is not None:
        player.prev_x = getattr(player, 'x', 0)
    if enemy is not None:
        enemy.prev_x = getattr(enemy, 'x', 0)
    
    # --------------------------------------------------------
    # INPUT PROCESSING
    # --------------------------------------------------------
    
    # Read controller state
    read_controller()
    
    # Get movement input (smoothed)
    horizontal = get_horizontal()
    
    # Detect jump input
    jump_input = jump_just_pressed()

    # --------------------------------------------------------
    # PLAYER JUMP (always check for buffering)
    # --------------------------------------------------------
    
    if jump_input:
        player.try_jump()

    # --------------------------------------------------------
    # PLAYER STATE MACHINE
    # --------------------------------------------------------

    if player.state == "ATTACK":
        
        # Process attack animation/hit detection
        player.update_attack(enemy)
        
        # Allow limited movement during attacks
        if horizontal != 0:
            from engine.fighter import AIR_MOVE_SPEED
            speed = AIR_MOVE_SPEED if not player.grounded else MOVE_SPEED * 0.3
            player.x += horizontal * speed * time.dt

    elif player.state == "HITSTUN":
        
        # Process knockback/stun
        player.update_hitstun()

    elif player.state == "KO":
        
        # Defeated - no action
        pass

    else:
        
        # IDLE, WALK, JUMP states
        
        # Check for block
        if block_pressed() and player.grounded:
            player.state = "BLOCK"

        else:
            
            # Check attack inputs (priority order)
            if light_pressed():
                player.start_attack("LIGHT")

            elif medium_pressed():
                player.start_attack("MEDIUM")

            elif heavy_pressed():
                player.start_attack("HEAVY")

            elif launcher_pressed():
                player.start_attack("LAUNCHER")

            # Process movement
            else:
                
                if horizontal != 0:
                    player.move_horizontal(horizontal)
                else:
                    player.stop_movement()

    # --------------------------------------------------------
    # PHYSICS UPDATE
    # --------------------------------------------------------

    # Apply gravity and handle ground/air transitions
    player.update_gravity()

    # Update combo timer
    player.update_combo_timer()

    # --------------------------------------------------------
    # ENEMY PROCESSING (AI would go here)
    # --------------------------------------------------------

    if enemy.state == "HITSTUN":
        enemy.update_hitstun()

    elif enemy.state == "ATTACK":
        enemy.update_attack(player)

    elif enemy.state == "KO":
        pass

    # Enemy gravity
    enemy.update_gravity()

    # --------------------------------------------------------
    # FACING DIRECTION
    # --------------------------------------------------------

    update_camera_facing(player, enemy)

    # --------------------------------------------------------
    # ARENA BOUNDARIES
    # --------------------------------------------------------

    player.clamp_to_arena(ARENA_WIDTH)
    enemy.clamp_to_arena(ARENA_WIDTH)

    # --------------------------------------------------------
    # UI UPDATE
    # --------------------------------------------------------

    # Update debug HUD with fighter info
    if debug_hud:
        debug_hud.update_debug(
            player.get_info(),
            enemy.get_info()
        )
        debug_hud.update_combo(player.combo_count)
        debug_hud.update_fps(1.0 / max(time.dt_unscaled, 1e-6))

    # --------------------------------------------------------
    # STORE INPUT STATE FOR NEXT FRAME
    # --------------------------------------------------------

    store_input_state()


# ============================================================
# KEYBOARD INPUT HANDLER
# ============================================================

def input(key):
    """
    Handle keyboard input as fallback/alternative to controller.
    Called automatically by Ursina when keys are pressed.
    """
    
    global paused
    
    # Handle key releases (Ursina sends 'key up')
    if isinstance(key, str) and key.endswith(' up'):
        base = key[:-3]
        if base == 's' and hasattr(player, 'stop_crouch'):
            player.stop_crouch()
        return
    
    # Pause toggle
    if key == 'escape':
        paused = not paused
        print(f"Game {'PAUSED' if paused else 'RESUMED'}")
        return
    
    # Skip input if paused
    if paused:
        return
    
    # Movement
    if key == 'a':
        # allow movement unless crouching
        if player.state != 'CROUCH':
            player.x -= 0.5
            if player.grounded and player.state not in ("ATTACK", "BLOCK"):
                player.state = "WALK"
    
    if key == 'd':
        if player.state != 'CROUCH':
            player.x += 0.5
            if player.grounded and player.state not in ("ATTACK", "BLOCK"):
                player.state = "WALK"
    
    # Jump
    if key == 'space':
        player.try_jump()
    
    # Crouch (press and hold 's')
    if key == 's':
        if hasattr(player, 'start_crouch'):
            player.start_crouch()
        return
    
    # Attacks
    if key == 'q':
        # disallow attacks while crouched for now
        if player.state != 'CROUCH':
            player.start_attack("LIGHT")
    
    if key == 'w':
        if player.state != 'CROUCH':
            player.start_attack("MEDIUM")
    
    if key == 'e':
        if player.state != 'CROUCH':
            player.start_attack("HEAVY")


# ============================================================
# CLEANUP & SHUTDOWN
# ============================================================

def cleanup():
    """Clean up resources before exit"""
    print()
    print("=" * 60)
    print("Shutting down...")
    
    # Close controller connection
    close_controller()
    
    print("✓ Cleanup complete")
    print("=" * 60)


# ============================================================
# GAME ENTRY POINT
# ============================================================

if __name__ == '__main__':
    
    try:
        # Create Ursina app
        app = Ursina(
            title=GAME_TITLE,
            developer_mode=False,
            borderless=BORDERLESS,
            fullscreen=FULLSCREEN
        )
        
        # Initialize all game systems
        initialize_game()
        
        # Run main game loop
        print()
        print("▶ Starting game loop...")
        app.run()
        
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user")
    
    except Exception as e:
        print("\n" + "=" * 60)
        print("FATAL ERROR")
        print("=" * 60)
        print(f"\n{type(e).__name__}: {e}\n")
        
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()
    
    finally:
        # Always cleanup
        cleanup()
        
        print("\nThanks for playing Riftbound! 🎮")
        input("\nPress ENTER to exit...")
