"""
Riftbound Controller Input Module
Handles custom HID controller inputs (gamepads) with D-PAD smoothing,
deadzones, and keyboard fallbacks.
"""

# Safe HID import fallback
try:
    import hid
    HAS_HID = True
except ImportError:
    hid = None
    HAS_HID = False
    print("[controller] Warning: 'hidapi' module not found. Controller support disabled, falling back to keyboard controls.")

from ursina import held_keys

# ============================================================
# CONTROLLER CONFIGURATION
# ============================================================

# Target device identifiers (update if using specific hardware)
VENDOR_ID = 0x0000
PRODUCT_ID = 0x0000

# D-PAD & Analog Deadzones
DEADZONE = 0.15
SMOOTHING_FACTOR = 0.8  # D-PAD input smoothing (0.0 = instant, 1.0 = heavy smooth)

# Controller state tracking
game_controller = None
raw_horizontal = 0.0
smoothed_horizontal = 0.0

# Button states
button_states = {
    'jump': False,
    'light': False,
    'medium': False,
    'heavy': False,
    'launcher': False,
    'block': False,
    'crouch': False,
    'dash': False,
    'special': False
}

prev_button_states = button_states.copy()


# ============================================================
# INITIALIZATION & CLEANUP
# ============================================================

def init_controller():
    """
    Initialize connection to the HID controller device.
    Returns True if successful, False if no controller found or module missing.
    """
    global game_controller

    if not HAS_HID or hid is None:
        print("ℹ No HID library loaded. Using keyboard fallback.")
        return False

    try:
        # Attempt to open controller device
        game_controller = hid.device()
        
        # If specific Vendor/Product ID set, try opening by ID
        if VENDOR_ID != 0x0000 and PRODUCT_ID != 0x0000:
            game_controller.open(VENDOR_ID, PRODUCT_ID)
        else:
            # Look for any available HID device
            devices = hid.enumerate()
            if devices:
                game_controller.open_path(devices[0]['path'])
            else:
                print("ℹ No HID controllers found. Using keyboard fallback.")
                return False

        game_controller.set_nonblocking(True)
        print("✓ Controller connected successfully")
        return True

    except Exception as e:
        print(f"⚠ Controller initialization failed: {e}")
        print("  Using keyboard fallback controls.")
        game_controller = None
        return False


def close_controller():
    """Safely close controller connection"""
    global game_controller
    if HAS_HID and game_controller:
        try:
            game_controller.close()
            print("✓ Controller disconnected")
        except Exception:
            pass
        game_controller = None


# ============================================================
# INPUT READING & SMOOTHING
# ============================================================

def read_controller():
    """
    Read latest input report from controller and update button/axis states.
    Falls back gracefully to keyboard inputs if no controller is present.
    """
    global raw_horizontal, smoothed_horizontal, button_states, prev_button_states

    # Save previous state for 'just pressed' checks
    prev_button_states = button_states.copy()

    # If controller is active and module exists, try reading HID data
    if HAS_HID and game_controller:
        try:
            data = game_controller.read(64)
            if data:
                # Example HID parsing logic (adjust offsets if using specific hardware)
                # Parse horizontal axis / D-Pad from byte array
                raw_x = data[0] - 128 if len(data) > 0 else 0
                norm_x = raw_x / 128.0
                
                # Apply deadzone
                if abs(norm_x) < DEADZONE:
                    raw_horizontal = 0.0
                else:
                    raw_horizontal = norm_x

                # Parse buttons from data bytes
                if len(data) > 1:
                    btn_byte = data[1]
                    button_states['light'] = bool(btn_byte & 0x01)
                    button_states['medium'] = bool(btn_byte & 0x02)
                    button_states['heavy'] = bool(btn_byte & 0x04)
                    button_states['launcher'] = bool(btn_byte & 0x08)
                    button_states['jump'] = bool(btn_byte & 0x10)
                    button_states['block'] = bool(btn_byte & 0x20)
                    button_states['crouch'] = bool(btn_byte & 0x40)
                    button_states['dash'] = bool(btn_byte & 0x80)

        except Exception:
            # If reading fails, clear controller handle and switch to keyboard
            close_controller()

    # Keyboard fallback logic if no HID controller input received
    kb_horizontal = 0.0
    if held_keys['d'] or held_keys['right arrow']:
        kb_horizontal += 1.0
    if held_keys['a'] or held_keys['left arrow']:
        kb_horizontal -= 1.0

    # Combine or override with keyboard inputs
    if not game_controller:
        raw_horizontal = kb_horizontal
        button_states['jump'] = bool(held_keys['space'] or held_keys['w'] or held_keys['up arrow'])
        button_states['light'] = bool(held_keys['q'] or held_keys['j'])
        button_states['medium'] = bool(held_keys['w'] or held_keys['k'])
        button_states['heavy'] = bool(held_keys['e'] or held_keys['l'])
        button_states['launcher'] = bool(held_keys['r'] or held_keys['i'])
        button_states['block'] = bool(held_keys['f'] or held_keys['u'])
        button_states['crouch'] = bool(held_keys['s'] or held_keys['down arrow'])
        button_states['dash'] = bool(held_keys['left shift'] or held_keys['right shift'])
        button_states['special'] = bool(held_keys['x'] or held_keys['o'])

    # Apply exponential smoothing to horizontal axis for fluid movement
    smoothed_horizontal = (smoothed_horizontal * SMOOTHING_FACTOR) + (raw_horizontal * (1.0 - SMOOTHING_FACTOR))


# ============================================================
# GETTER HELPER FUNCTIONS
# ============================================================

def get_horizontal():
    """Get smoothed horizontal axis (-1.0 to 1.0)"""
    return smoothed_horizontal


def is_pressed(action):
    """Check if action button is currently held down"""
    return button_states.get(action, False)


def just_pressed(action):
    """Check if action button was pressed this frame"""
    return button_states.get(action, False) and not prev_button_states.get(action, False)


# Convenient alias getters
def jump_just_pressed():
    return just_pressed('jump')

def light_pressed():
    return just_pressed('light')

def medium_pressed():
    return just_pressed('medium')

def heavy_pressed():
    return just_pressed('heavy')

def launcher_pressed():
    return just_pressed('launcher')

def block_held():
    return is_pressed('block')

def crouch_held():
    return is_pressed('crouch')

def dash_just_pressed():
    return just_pressed('dash')

def special_just_pressed():
    return just_pressed('special')
