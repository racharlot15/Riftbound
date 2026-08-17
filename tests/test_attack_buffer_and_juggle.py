import time
from Riftbound.engine.fighter import Fighter
from Riftbound.engine import combat


def test_attack_buffering_and_buffer_execution():
    a = Fighter("Attacker", position=(0,1,0), fighter_color=(1,0,0,1))
    b = Fighter("Target", position=(2,1,0), fighter_color=(0,1,0,1))

    # Start a light attack and immediately request a medium — with Magic Series enabled should chain immediately
    assert a.start_attack('LIGHT') is True
    result = a.start_attack('MEDIUM')
    # chaining should return True and no buffered attack should be set
    assert result is True
    assert a.buffered_attack is None

    # Step frames until buffered attack begins
    started = False
    for _ in range(30):
        phase = a.update_attack(b, dt=0.05)
        if a.attack_name == 'MEDIUM':
            started = True
            break
    assert started, "Buffered attack did not start after previous attack finished"


def test_launcher_applies_juggle():
    attacker = Fighter("Launcher", position=(0,1,0), fighter_color=(1,1,0,1))
    target = Fighter("Dummy", position=(1,1,0), fighter_color=(0.5,0.5,0.5,1))

    launcher_data = combat.ATTACKS['LAUNCHER']

    # Simulate a direct hit from a launcher attack
    target.grounded = True
    target.vertical_velocity = 0
    target.take_hit(launcher_data, attacker)

    # LAUNCHER should put target airborne and give vertical_velocity boost
    assert not target.grounded
    from Riftbound.engine.fighter import JUMP_FORCE
    assert target.vertical_velocity >= JUMP_FORCE * 0.85
