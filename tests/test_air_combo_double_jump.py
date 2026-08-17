from Riftbound.engine.fighter import Fighter, JUMP_FORCE


def test_double_jump_allows_second_jump():
    f = Fighter("Jumper", position=(0,1,0), fighter_color=(0.2,0.4,0.6,1))
    # ensure starting grounded
    f.grounded = True
    f.jumps_used = 0

    # first jump
    f.try_jump()
    assert not f.grounded
    assert f.jumps_used == 1
    assert f.vertical_velocity >= JUMP_FORCE * 0.99

    # simulate a small frame so we are still airborne
    f.y += 0.1

    # second (double) jump
    f.try_jump()
    assert not f.grounded
    assert f.jumps_used == 2
    # second jump should provide at least a partial force
    assert f.vertical_velocity >= JUMP_FORCE * 0.8


def test_air_combo_limit():
    f = Fighter("Aerial", position=(0,2,0), fighter_color=(0.8,0.1,0.1,1))
    f.grounded = False
    f.state = "JUMP"
    f.air_attacks_used = 0
    f.max_air_attacks = 2

    # first aerial attack
    ok1 = f.start_attack('LIGHT')
    assert ok1 is True
    assert f.air_attacks_used == 1

    # simulate finishing attack: clear attack state
    f.set_state('JUMP')
    f.attack_name = None

    # second aerial attack
    ok2 = f.start_attack('MEDIUM')
    assert ok2 is True
    assert f.air_attacks_used == 2

    # simulate finishing attack again
    f.set_state('JUMP')
    f.attack_name = None

    # third aerial attack should be rejected/buffered
    ok3 = f.start_attack('HEAVY')
    assert ok3 is False
    assert f.buffered_attack == 'HEAVY'
