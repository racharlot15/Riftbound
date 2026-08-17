"""
Riftbound Camera Module
Handles camera setup and positioning for fighting game view
"""

from ursina import camera
import random

# shake state kept at module level for compatibility with juice.update_shake
_shake_timer = 0.0
_shake_strength = 0.0
_shake_base_position = None


def trigger_shake(strength=0.15, duration=0.15):
    global _shake_timer, _shake_strength, _shake_base_position
    _shake_timer = max(_shake_timer, duration)
    _shake_strength = max(_shake_strength, strength)
    # The base position is captured on the next frame. Keeping it as plain
    # numbers avoids Vec3/tuple addition failures that previously silenced
    # the shake through the broad exception handler.


def update_shake(dt):
    global _shake_timer, _shake_strength, _shake_base_position
    if _shake_timer > 0:
        if _shake_base_position is None:
            _shake_base_position = (float(camera.x), float(camera.y), float(camera.z))
        _shake_timer = max(0.0, _shake_timer - max(0.0, dt))
        offset = (
            random.uniform(-_shake_strength, _shake_strength),
            random.uniform(-_shake_strength, _shake_strength),
            0
        )
        try:
            camera.position = (
                _shake_base_position[0] + offset[0],
                _shake_base_position[1] + offset[1],
                _shake_base_position[2],
            )
        except Exception:
            pass
    else:
        if _shake_base_position is not None:
            try:
                camera.position = _shake_base_position
            except Exception:
                pass
            _shake_base_position = None
            _shake_strength = 0.0


# ============================================================
# CAMERA CONFIGURATION
# ============================================================

DEFAULT_CAMERA_POSITION = (0, 7, -18)
DEFAULT_CAMERA_ROTATION = (15, 0, 0)


# ============================================================
# CAMERA SETUP
# ============================================================

def setup_camera():
    """Initialize camera position and rotation for fighting game view"""
    camera.position = DEFAULT_CAMERA_POSITION
    camera.rotation_x = DEFAULT_CAMERA_ROTATION[0]
    camera.rotation_y = DEFAULT_CAMERA_ROTATION[1]
    camera.rotation_z = DEFAULT_CAMERA_ROTATION[2]
    print("✓ Camera configured")


def update_camera_facing(fighter1, fighter2):
    """
    Update character facing directions so they look at each other.
    
    Args:
        fighter1: First fighter entity
        fighter2: Second fighter entity
    """
    # Fighter 1 faces opponent
    if fighter2.x > fighter1.x:
        fighter1.rotation_y = 0      # Face right
    else:
        fighter1.rotation_y = 180    # Face left

    # Fighter 2 faces opponent
    if fighter1.x > fighter2.x:
        fighter2.rotation_y = 180    # Face left
    else:
        fighter2.rotation_y = 0      # Face right


def get_camera_info():
    """Return current camera position and rotation info"""
    return {
        'position': camera.position,
        'rotation': (camera.rotation_x, camera.rotation_y, camera.rotation_z)
    }
