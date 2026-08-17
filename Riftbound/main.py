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
- Keyboard fallback: A/D=Move, Space=Jump, Q/W/E=Attacks, R=Launcher,
  F=Block, Shift=Dash, X=Character Special, S=Crouch

Author: Riftbound Dev Team
Version: 0.1.0 (Modular Architecture)
"""

import sys
import os

# Add project root to path for imports and set cwd to package folder so double-click runs resolve assets
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
try:
    os.chdir(script_dir)
except Exception:
    pass
# Ensure console supports UTF-8 so unicode symbols print correctly on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
# Helpful debug output for startup issues
try:
    print(f"Working directory: {os.getcwd()}")
except Exception:
    pass

from ursina import Ursina, window, camera, time, Entity, Text, AmbientLight, DirectionalLight, color, held_keys

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
    dash_pressed,
    special_pressed,
    crouch_held,
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

# Match state
match_active = True
result_text = None
initial_player_pos = None
initial_enemy_pos = None

# Lightweight deterministic CPU state. This keeps the prototype playable
# while a full behavior-tree AI remains out of scope.
enemy_ai_timer = 0.0
enemy_ai_attack_index = 0
enemy_ai_block_timer = 0.0


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
    
    # Remember initial positions for rematch resets
    global initial_player_pos, initial_enemy_pos, match_active
    try:
        initial_player_pos = (player.x, player.y, getattr(player, 'z', 0))
    except Exception:
        initial_player_pos = (-5, 1, 0)
    try:
        initial_enemy_pos = (enemy.x, enemy.y, getattr(enemy, 'z', 0))
    except Exception:
        initial_enemy_pos = (5, 1, 0)
    match_active = True

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
    print("  D-PAD DOWN: Crouch")
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
    print("  A/D: Move | Space: Jump | F: Block | S: Crouch")
    print("  Q: Light | W: Medium | E: Heavy | R: Launcher")
    print("  Shift: Dash | X: Character Special")
    print("-" * 40)


def _facing_direction(fighter, opponent):
    """Return the horizontal direction from fighter toward opponent."""
    return 1 if opponent.x >= fighter.x else -1


def _use_character_special(fighter, opponent, direction=0):
    """Run the archetype-specific move bound to the special input."""
    direction = direction or _facing_direction(fighter, opponent)
    if isinstance(fighter, Zoner):
        return fighter.fire_projectile(opponent)
    if isinstance(fighter, Grappler):
        return fighter.execute_grab(opponent)
    if isinstance(fighter, AgileHero):
        return fighter.start_dash(direction)
    if isinstance(fighter, AerialFighter) and not fighter.grounded:
        return fighter.start_air_dash(direction)
    return False


def _update_character_systems(fighter, opponent):
    """Advance mechanics that are independent from the base attack state."""
    if isinstance(fighter, Zoner):
        fighter.update_projectiles(opponent)


def _update_enemy_ai():
    """Simple CPU that approaches, blocks close attacks, and cycles normals."""
    global enemy_ai_timer, enemy_ai_attack_index, enemy_ai_block_timer

    if enemy.state in ("HITSTUN", "KO", "ATTACK"):
        return

    distance = abs(player.x - enemy.x)
    direction = _facing_direction(enemy, player)
    enemy_ai_timer = max(0.0, enemy_ai_timer - time.dt)
    enemy_ai_block_timer = max(0.0, enemy_ai_block_timer - time.dt)

    # A block is a short, occasional reaction rather than an instantaneous
    # answer to every player attack. This leaves ordinary hits meaningful.
    if enemy.state == "BLOCK" and enemy_ai_block_timer > 0:
        return
    if enemy.state == "BLOCK":
        enemy.set_state("IDLE")

    if player.state == "ATTACK" and distance <= 2.8 and enemy.grounded and enemy_ai_timer <= 0:
        enemy.set_state("BLOCK")
        enemy_ai_block_timer = 0.10
        enemy_ai_timer = 0.65
        return

    if distance > 1.8:
        enemy.move_horizontal(direction)
        return

    enemy.stop_movement()
    if enemy_ai_timer <= 0:
        attacks = ("LIGHT", "MEDIUM", "HEAVY")
        enemy.start_attack(attacks[enemy_ai_attack_index % len(attacks)])
        enemy_ai_attack_index += 1
        enemy_ai_timer = 0.45


# ============================================================
# MAIN GAME LOOP
# ============================================================

def update():
    """
    Main update function - called every frame by Ursina.
    Handles input processing, game logic, and state updates.
    """
    
    global paused, match_active, result_text

    # Feedback uses unscaled time so hitstop never makes shaking or the
    # freeze-frame timer feel delayed after a successful hit.
    frame_dt = max(time.dt_unscaled, 0.0)

    # Update camera shake (should run even during hitstop)
    try:
        update_shake(frame_dt)
    except Exception:
        pass

    # Update hitstop first so frames can be frozen; if frozen, return early
    try:
        if juice.update_hitstop(frame_dt):
            return
    except Exception:
        pass

    # Don't process game logic when paused
    if paused:
        return

    # If the match is over, skip game logic (input handler still receives keys for rematch)
    global match_active
    if not match_active:
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
    
    # Get movement input. Keyboard is held-key based so it is frame-rate
    # independent and behaves like the controller rather than moving in taps.
    horizontal = get_horizontal()
    keyboard_horizontal = int(bool(held_keys['d'])) - int(bool(held_keys['a']))
    if keyboard_horizontal:
        horizontal = keyboard_horizontal
    
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

    player_blocking = block_pressed() or bool(held_keys['f'])
    if player.state == "BLOCK" and not player_blocking:
        player.set_state("IDLE" if player.grounded else "JUMP")

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

        # --------------------------------------------------
        # CROUCH (controller down input or keyboard 's')
        # --------------------------------------------------
        controller_crouching = crouch_held()
        keyboard_crouching = bool(held_keys['s'])

        if (controller_crouching or keyboard_crouching) and player.grounded and player.state not in ("ATTACK", "BLOCK", "HITSTUN"):
            if not getattr(player, 'is_crouching', False):
                player.start_crouch()
        elif getattr(player, 'is_crouching', False):
            player.stop_crouch()

        # Check for block
        if player_blocking and player.grounded:
            player.set_state("BLOCK")

        else:
            if dash_pressed():
                _use_character_special(player, enemy, horizontal)

            elif special_pressed():
                _use_character_special(player, enemy, horizontal)

            # Check attack inputs (priority order)
            elif light_pressed():
                player.start_attack("LIGHT")

            elif medium_pressed():
                player.start_attack("MEDIUM")

            elif heavy_pressed():
                player.start_attack("HEAVY")

            elif launcher_pressed():
                player.start_attack("LAUNCHER")

            # Process movement
            else:
                
                if horizontal != 0 and not getattr(player, 'is_crouching', False):
                    player.move_horizontal(horizontal)
                elif not getattr(player, 'is_crouching', False):
                    player.stop_movement()

    # --------------------------------------------------------
    # PHYSICS UPDATE
    # --------------------------------------------------------

    # Apply gravity and handle ground/air transitions
    player.update_gravity()

    # Update combo timer
    player.update_combo_timer()

    _update_character_systems(player, enemy)

    # --------------------------------------------------------
    # ENEMY PROCESSING
    # --------------------------------------------------------

    _update_enemy_ai()

    if enemy.state == "HITSTUN":
        enemy.update_hitstun()

    elif enemy.state == "ATTACK":
        enemy.update_attack(player)

    elif enemy.state == "KO":
        pass

    # Enemy gravity
    enemy.update_gravity()
    enemy.update_combo_timer()
    _update_character_systems(enemy, player)

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
    # MATCH END CHECK
    # --------------------------------------------------------

    try:
        if match_active:
            if player is not None and player.state == 'KO':
                match_active = False
                try:
                    enemy.hitbox.hide_hitbox()
                except Exception:
                    pass
                winner = getattr(enemy, 'fighter_name', 'Enemy')
                try:
                    result_text = Text(f"{winner} wins! Press ENTER to rematch or ESC to return to menu", parent=camera.ui, position=(0, 0.1), origin=(0, 0), scale=1.2)
                except Exception:
                    result_text = None
            elif enemy is not None and enemy.state == 'KO':
                match_active = False
                try:
                    player.hitbox.hide_hitbox()
                except Exception:
                    pass
                winner = getattr(player, 'fighter_name', 'Player')
                try:
                    result_text = Text(f"{winner} wins! Press ENTER to rematch or ESC to return to menu", parent=camera.ui, position=(0, 0.1), origin=(0, 0), scale=1.2)
                except Exception:
                    result_text = None
    except Exception:
        pass

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
    
    global paused, match_active, result_text
    
    # Handle key releases (Ursina sends 'key up')
    if isinstance(key, str) and key.endswith(' up'):
        base = key[:-3]
        if base == 's' and hasattr(player, 'stop_crouch'):
            player.stop_crouch()
        return
    
    # Pause toggle
    if key == 'escape':
        # If match ended, treat ESC as return-to-menu (simple behavior: restart match and pause as menu)
        if not match_active:
            # destroy result text and return to menu state (for now, just rematch reset and pause)
            try:
                if result_text is not None:
                    result_text.enabled = False
            except Exception:
                pass
            # keep paused state but reset match_active so user can choose
            match_active = True
            # call reset to ensure UI consistent
            try:
                reset_match()
            except Exception:
                pass
            return
        paused = not paused
        print(f"Game {'PAUSED' if paused else 'RESUMED'}")
        return
    
    # Skip input if paused
    if paused:
        return
    
    # Jump
    if key == 'space':
        player.try_jump()
    
    # Rematch on Enter when match is over
    if key == 'enter' and not match_active:
        try:
            reset_match()
        except Exception:
            pass
        return

    # Crouch (press and hold 's')
    if key == 's':
        if hasattr(player, 'start_crouch'):
            player.start_crouch()
        return
    
    # Attacks
    if key == 'q':
        # disallow attacks while crouched for now
        if player.state != 'CROUCH' and not getattr(player, 'is_crouching', False):
            player.start_attack("LIGHT")
    
    if key == 'w':
        if player.state != 'CROUCH' and not getattr(player, 'is_crouching', False):
            player.start_attack("MEDIUM")
    
    if key == 'e':
        if player.state != 'CROUCH' and not getattr(player, 'is_crouching', False):
            player.start_attack("HEAVY")

    if key == 'r':
        if player.state != 'CROUCH' and not getattr(player, 'is_crouching', False):
            player.start_attack("LAUNCHER")

    if key == 'shift':
        _use_character_special(player, enemy)

    if key == 'x':
        _use_character_special(player, enemy)


# ============================================================
# MATCH / REMATCH HELPERS
# ============================================================

def reset_match():
    """Reset both fighters and UI for a new round/match."""
    global player, enemy, initial_player_pos, initial_enemy_pos, match_active, result_text
    try:
        # Reposition fighters to their initial spots
        if player is not None and initial_player_pos is not None:
            try:
                player.x, player.y, player.z = initial_player_pos
            except Exception:
                try:
                    player.position = initial_player_pos
                except Exception:
                    pass
        if enemy is not None and initial_enemy_pos is not None:
            try:
                enemy.x, enemy.y, enemy.z = initial_enemy_pos
            except Exception:
                try:
                    enemy.position = initial_enemy_pos
                except Exception:
                    pass
        # Reset fighter internal state
        try:
            if player is not None:
                player.reset_for_match()
        except Exception:
            pass
        try:
            if enemy is not None:
                enemy.reset_for_match()
        except Exception:
            pass
        # Clear result UI
        try:
            if result_text is not None:
                result_text.enabled = False
                result_text = None
        except Exception:
            pass
        # Reactivate match
        match_active = True
        print("↺ Match reset — ready to rematch")
    except Exception:
        pass


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