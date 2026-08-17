"""
Riftbound Controller Module
Handles HID input from custom controller with D-PAD smoothing
"""

import hid


# ============================================================
# CONTROLLER CONFIGURATION
# ============================================================

VID = 0x146B
PID = 0x0603

# D-PAD SMOOTHING - makes dpad movement as fluid as analog stick
DPAD_SMOOTH_SPEED = 15  # Higher = faster response (snappier), lower = more fluid/gradual


# ============================================================
# CONTROLLER STATE
# ============================================================

controller = None
initialized = False

left_x = 128
left_y = 255
dpad = 0
buttons = 0
l2 = 0
r2 = 128

previous_buttons = 0
previous_dpad = 0

dpad_horizontal_smoothed = 0.0
dpad_vertical_smoothed = 0.0


# ============================================================
# CONTROLLER INITIALIZATION
# ============================================================

def init_controller():
    """Initialize HID controller connection"""
    global controller, initialized
    
    try:
        controller = hid.device()
        controller.open(VID, PID)
        controller.set_nonblocking(True)
        initialized = True
        print("✓ Controller connected")
        return True
    except Exception as e:
        print(f"✗ Controller connection failed: {e}")
        initialized = False
        return False


def close_controller():
    """Close HID controller connection"""
    global initialized
    
    if controller and initialized:
        try:
            controller.close()
            print("✓ Controller disconnected")
        except:
            pass
        initialized = False


# ============================================================
# INPUT READING
# ============================================================

def read_controller():
    """Read latest input data from controller"""
    
    global left_x, left_y, dpad, buttons, l2, r2
    
    if not initialized or not controller:
        return

    latest = None

    # Read multiple times to get latest state
    for _ in range(10):
        data = controller.read(64)
        if data:
            latest = data

    if latest is None:
        return

    # Parse input data
    if len(latest) > 2:
        left_x = latest[1]
        left_y = latest[2]

    if len(latest) > 11:
        dpad = latest[11]

    if len(latest) > 10:
        buttons = latest[10]

    if len(latest) > 9:
        l2 = latest[8]
        r2 = latest[9]


# ============================================================
# BUTTON DETECTION FUNCTIONS
# ============================================================

def held(mask):
    """Check if button is currently held down"""
    return (buttons & mask) != 0


def just_pressed(mask):
    """Check if button was just pressed this frame"""
    return (
        (buttons & mask) != 0
        and
        (previous_buttons & mask) == 0
    )


# Attack button detection
def light_pressed():
    return just_pressed(4)


def medium_pressed():
    return just_pressed(8)


def heavy_pressed():
    return just_pressed(2)


def launcher_pressed():
    return just_pressed(1)


def dash_pressed():
    return just_pressed(16)


def special_pressed():
    return just_pressed(32)


# Trigger/shoulder button detection
def block_pressed():
    return l2 > 200


def super_pressed():
    return r2 < 50


# Jump input detection
def jump_just_pressed():
    """Detect if jump was just pressed this frame (D-pad up)"""
    return dpad == 4 and previous_dpad != 4


def jump_held():
    """Detect if jump button is currently held down"""
    return dpad == 4


# ============================================================
# MOVEMENT INPUT WITH SMOOTHING
# ============================================================

DEADZONE = 0.12


def get_horizontal():
    """
    Get horizontal movement input with smooth D-PAD interpolation.
    Returns value between -1.0 and 1.0 like an analog stick.
    """
    
    global dpad_horizontal_smoothed

    # Get analog stick input
    analog = (left_x - 128) / 127

    if abs(analog) < DEADZONE:
        analog = 0

    # Get raw dpad input target
    dpad_target = 0.0

    if dpad == 28:      # Left
        dpad_target = -1.0
    elif dpad == 12:    # Right
        dpad_target = 1.0

    # Smoothly interpolate dpad value towards target (like analog stick)
    import time as ursina_time
    
    if dpad_target != 0:
        # D-pad is pressed - smoothly ramp up to full value
        diff = dpad_target - dpad_horizontal_smoothed
        smoothing_factor = min(1.0, DPAD_SMOOTH_SPEED * ursina_time.dt)
        dpad_horizontal_smoothed += diff * smoothing_factor
        
        # Clamp to prevent overshoot
        dpad_horizontal_smoothed = max(-1.0, min(1.0, dpad_horizontal_smoothed))
        
        return dpad_horizontal_smoothed
    else:
        # No dpad input - smoothly decay to zero (natural stop feel)
        if abs(dpad_horizontal_smoothed) > 0.01:
            decay_factor = 1.0 - min(1.0, DPAD_SMOOTH_SPEED * ursina_time.dt)
            dpad_horizontal_smoothed *= decay_factor
            
            # Snap to zero once very small to avoid drift
            if abs(dpad_horizontal_smoothed) < 0.01:
                dpad_horizontal_smoothed = 0.0
                
            return dpad_horizontal_smoothed
        else:
            dpad_horizontal_smoothed = 0.0

    return max(-1, min(1, analog))


# ============================================================
# STATE MANAGEMENT
# ============================================================

def store_input_state():
    """Store current input state for next-frame comparison"""
    global previous_buttons, previous_dpad
    previous_buttons = buttons
    previous_dpad = dpad


def reset_inputs():
    """Reset all input states"""
    global left_x, left_y, dpad, buttons, l2, r2
    global previous_buttons, previous_dpad
    global dpad_horizontal_smoothed, dpad_vertical_smoothed
    
    left_x = 128
    left_y = 255
    dpad = 0
    buttons = 0
    l2 = 0
    r2 = 128
    previous_buttons = 0
    previous_dpad = 0
    dpad_horizontal_smoothed = 0.0
    dpad_vertical_smoothed = 0.0
