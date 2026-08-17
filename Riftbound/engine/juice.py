"""
Game-feel "juice" utilities: hitstop, camera shake, hit flash helpers.
These are fully guarded so missing dependencies are safe no-ops.
"""

import random
from ursina import color

# Hitstop timer (global freeze)
_hitstop_timer = 0.0

# Camera shake state
_shake_timer = 0.0
_shake_strength = 0.0
_shake_base_position = None

# Optional registered hit flash entity (set from main.initialize_game)
_hit_flash_entity = None


def register_hit_flash(entity):
    global _hit_flash_entity
    _hit_flash_entity = entity


def trigger_hitstop(duration=0.06):
    """Start or extend the hitstop freeze-frame timer."""
    global _hitstop_timer
    _hitstop_timer = max(_hitstop_timer, duration)


def update_hitstop(dt):
    """Update hitstop; return True if the game should be frozen this frame."""
    global _hitstop_timer
    if _hitstop_timer > 0:
        _hitstop_timer -= dt
        return True
    return False


def trigger_shake(strength=0.15, duration=0.15):
    global _shake_timer, _shake_strength, _shake_base_position
    _shake_timer = max(_shake_timer, duration)
    _shake_strength = max(_shake_strength, strength)
    # base position is captured on first trigger; update_shake will fill it
    if _shake_base_position is None:
        # lazily set on first update if camera available
        _shake_base_position = None


def update_shake(dt):
    """Call every frame to update camera shake. Safe no-op if camera missing."""
    global _shake_timer, _shake_strength, _shake_base_position
    try:
        from ursina import camera
    except Exception:
        return

    if _shake_timer > 0:
        if _shake_base_position is None:
            # store base pos once
            _shake_base_position = camera.position
        _shake_timer -= dt
        offset = (
            random.uniform(-_shake_strength, _shake_strength),
            random.uniform(-_shake_strength, _shake_strength),
            0
        )
        try:
            camera.position = _shake_base_position + offset
        except Exception:
            # If camera vector ops fail, just no-op
            pass
    else:
        if _shake_base_position is not None:
            try:
                camera.position = _shake_base_position
            except Exception:
                pass
            _shake_base_position = None
            _shake_strength = 0.0


def flash(strength=0.4, duration=0.12, color_rgb=(255, 255, 255)):
    """Trigger a full-screen flash using the registered hit_flash entity.
    Safe no-op if not registered.
    """
    global _hit_flash_entity
    if not _hit_flash_entity:
        return
    try:
        from ursina import color as ursina_color
        # animate alpha up then down
        r, g, b = color_rgb
        try:
            _hit_flash_entity.color = ursina_color.rgba(r, g, b, 0)
            _hit_flash_entity.animate_color(ursina_color.rgba(r, g, b, int(255 * strength)), duration=duration/2, curve='out_expo')
            _hit_flash_entity.animate_color(ursina_color.rgba(r, g, b, 0), duration=duration/2, delay=duration/2, curve='linear')
        except Exception:
            pass
    except Exception:
        pass
