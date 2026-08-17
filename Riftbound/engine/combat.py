"""
Riftbound Combat System Module
Defines attack data, damage calculation, and combat mechanics
"""

# ============================================================
# ATTACK DATABASE
# ============================================================

ATTACKS = {
    "LIGHT": {
        "startup": 0.05,    # Faster startup for snappier feel
        "active": 0.08,     # Short active window but frequent
        "recovery": 0.12,   # Shorter recovery for rapid follow-ups
        "damage": 5,
        "knockback": 2.5,
        "hitstun": 0.18,
        "range": 2.0,
        "height": 1.5
    },

    "MEDIUM": {
        "startup": 0.10,
        "active": 0.10,
        "recovery": 0.18,
        "damage": 9,
        "knockback": 4,
        "hitstun": 0.22,
        "range": 2.3,
        "height": 1.5
    },

    "HEAVY": {
        "startup": 0.18,
        "active": 0.12,
        "recovery": 0.25,
        "damage": 14,
        "knockback": 6,
        "hitstun": 0.35,
        "range": 2.6,
        "height": 1.8
    },

    "LAUNCHER": {
        "startup": 0.15,
        "active": 0.12,
        "recovery": 0.20,
        "damage": 10,
        "knockback": 3,
        "hitstun": 0.28,
        "range": 2.2,
        "height": 2.5,
        "juggle": True
    }
}


# ============================================================
# COMBAT CONSTANTS
# ============================================================

BLOCK_DAMAGE_REDUCTION = 0.8   # Blocks reduce damage by 80%
MIN_BLOCK_DAMAGE = 1           # Minimum damage even when blocking
COMBO_DECAY_TIME = 1.0         # Seconds before combo counter resets (faster chains)

# Attack buffering / canceling
ATTACK_BUFFER_TIME = 0.25      # Seconds to buffer an attack input while busy (increased for lenient combo timing)
CANCEL_EARLY_WINDOW = 0.03     # Allow very short early cancels into next attack

# Global multipliers to shorten timings for faster MvC-style feel
# Set between 0.0 (no time) and 1.0 (original). Tunable.
STARTUP_MULTIPLIER = 0.5
ACTIVE_MULTIPLIER = 0.6
# Slightly slower than previous ultra-fast tuning: keep recovery at 0.33
RECOVERY_MULTIPLIER = 0.33

# ============================================================
# MAGIC SERIES / CHAINING
# ============================================================
CHAIN_ORDER = ["LIGHT", "MEDIUM", "HEAVY", "LAUNCHER"]

# Cooldowns (seconds) for powerful moves to prevent spamming
HEAVY_COOLDOWN = 0.6
LAUNCHER_COOLDOWN = 0.9

def can_chain(current_attack, next_attack):
    """Return True if next_attack is a legal Magic Series follow-up to
    current_attack (strictly higher in CHAIN_ORDER, no repeats/skips allowed).
    LAUNCHER cannot chain into anything further.
    """
    if current_attack not in CHAIN_ORDER or next_attack not in CHAIN_ORDER:
        return False
    current_index = CHAIN_ORDER.index(current_attack)
    next_index = CHAIN_ORDER.index(next_attack)
    return next_index == current_index + 1

# Damage scaling per hit index (0-based). Longer combos use MIN_SCALING.
COMBO_SCALING = [1.0, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
MIN_SCALING = 0.2

def get_combo_scaling(hit_index):
    """hit_index is 0-based (0 = first hit of the combo). Returns a scaling float."""
    if hit_index < 0:
        hit_index = 0
    if hit_index < len(COMBO_SCALING):
        return COMBO_SCALING[hit_index]
    return MIN_SCALING


# ============================================================
# COMBAT HELPER FUNCTIONS
# ============================================================

def get_attack_data(attack_name):
    """Retrieve attack data by name"""
    return ATTACKS.get(attack_name)


def calculate_block_damage(raw_damage):
    """Calculate reduced damage when blocking"""
    return max(MIN_BLOCK_DAMAGE, int(raw_damage * BLOCK_DAMAGE_REDUCTION))


def calculate_knockback_direction(attacker_x, target_x, knockback_value):
    """
    Determine knockback direction based on positions.
    
    Returns:
        float: Positive or negative knockback velocity
    """
    if attacker_x < target_x:
        return knockback_value   # Knock target right
    else:
        return -knockback_value  # Knock target left


def get_attack_phase(timer, startup, active, recovery):
    """
    Determine which phase of an attack we're in.
    
    Returns:
        str: 'startup', 'active', 'recovery', or 'complete'
    """
    active_end = startup + active
    recovery_end = active_end + recovery
    
    if timer < startup:
        return 'startup'
    elif timer < active_end:
        return 'active'
    elif timer < recovery_end:
        return 'recovery'
    else:
        return 'complete'
