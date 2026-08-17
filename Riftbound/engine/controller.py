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

# D-pad raw value for "down". Based on the observed pattern (up=4, right=12,
# left=28), down is most likely 20. If crouch doesn't trigger on your D-pad,
# print(dpad) during read_controller() while holding down to find the real value.
DPAD_DOWN_VALUE = 20

# NOTE: On this controller, byte indices 1 and 2 (originally mapped to
# left_x/left_y) do NOT carry real analog stick data — they were observed
# to be pinned at constant values (128 and 255) regardless of stick input,
# which caused jump to falsely trigger "up" 100% of the time. Analog
# vertical input (jump/crouch via stick) is disabled below until the real
# axis byte offset is identified. D-pad and keyboard input are unaffected
# and remain the primary controls.
ANALOG_VERTICAL_ENABLED = False


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
previous_analog_up = False

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


# ============================================================
# ANALOG STICK VERTICAL HELPER
# ============================================================

DEADZONE = 0.12
ANALOG_JUMP_THRESHOLD = 0.5    # how far up the stick must be pushed to count as "jump"
ANALOG_CROUCH_THRESHOLD = 0.5  # how far down the stick must be pushed to count as "crouch"

ANALOG_Y_UP_IS_LOW = False


def get_analog_vertical():
    """
    Get vertical stick input, normalized like get_horizontal().
    Returns -1.0 (down) to 1.0 (up).

    Currently disabled (see ANALOG_VERTICAL_ENABLED) because left_y was
    found to be pinned at a constant value on this controller, which made
    jump falsely trigger regardless of actual stick position.
    """
    if not ANALOG_VERTICAL_ENABLED:
        return 0.0

    if ANALOG_Y_UP_IS_LOW:
        raw = (128 - left_y) / 127
    else:
        raw = (left_y - 128) / 127

    if abs(raw) < DEADZONE:
        raw = 0

    return max(-1.0, min(1.0, raw))


# ============================================================
# JUMP INPUT DETECTION (D-PAD + ANALOG STICK)
# ============================================================

def analog_jump_pressed():
    """Edge-detect the analog stick crossing into 'up' this frame."""
    global previous_analog_up

    is_up = get_analog_vertical() > ANALOG_JUMP_THRESHOLD
    just_pressed_now = is_up and not previous_analog_up
    previous_analog_up = is_up
    return just_pressed_now


def jump_just_pressed():
    """Detect if jump was just pressed this frame (D-pad up, or analog
    stick up if enabled)"""
    analog_just = analog_jump_pressed()
    dpad_just = dpad == 4 and previous_dpad != 4
    return dpad_just or analog_just


def jump_held():
    """Detect if jump button is currently held down (D-pad, or analog
    stick if enabled)"""
    return dpad == 4 or get_analog_vertical() > ANALOG_JUMP_THRESHOLD


# ============================================================
# CROUCH INPUT DETECTION (D-PAD DOWN + ANALOG STICK DOWN)
# ============================================================

def crouch_held():
    """Detect if crouch input (down) is currently held"""
    return dpad == DPAD_DOWN_VALUE or get_analog_vertical() < -ANALOG_CROUCH_THRESHOLD


# ============================================================
# MOVEMENT INPUT WITH SMOOTHING
# ============================================================

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
    global previous_analog_up

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
    previous_analog_up = False