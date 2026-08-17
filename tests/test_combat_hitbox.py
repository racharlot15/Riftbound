import pytest
from Riftbound.engine import combat
from Riftbound.engine.hitbox import AttackHitbox


def test_get_attack_phase_boundaries():
    # startup=0.1, active=0.2, recovery=0.3 => active_end=0.3, recovery_end=0.6
    startup, active, recovery = 0.1, 0.2, 0.3
    assert combat.get_attack_phase(0.05, startup, active, recovery) == 'startup'
    assert combat.get_attack_phase(0.15, startup, active, recovery) == 'active'
    assert combat.get_attack_phase(0.45, startup, active, recovery) == 'recovery'
    assert combat.get_attack_phase(1.0, startup, active, recovery) == 'complete'


def test_calculate_block_and_knockback():
    assert combat.calculate_block_damage(10) >= 1
    assert combat.calculate_knockback_direction(0, 5, 3) == 3
    assert combat.calculate_knockback_direction(5, 0, 3) == -3


def test_hitbox_collision():
    hb = AttackHitbox()
    class Dummy:
        def __init__(self, x, y):
            self.x = x
            self.y = y
    # Place hitbox at origin
    hb.set_position(0, 1, 0)
    # Target within range
    t = Dummy(1.0, 1.0)
    assert hb.check_collision(t, range_val=2.0, height_val=1.5)
    # Target out of range
    t2 = Dummy(5.0, 10.0)
    assert not hb.check_collision(t2, range_val=2.0, height_val=1.5)
