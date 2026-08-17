from Riftbound.engine.fighter import Fighter


def test_clamp_and_bounce():
    f = Fighter('Test', position=(0,1,0), fighter_color=(1,1,1,1))
    # simulate previous position far left to create a positive vx
    f.prev_x = -100
    # place beyond right boundary
    f.x = 100
    f.clamp_to_arena(arena_width=20)
    half = 20 / 2
    margin = 0.5
    max_x = half - margin
    assert f.x == max_x
    # knockback_velocity should be set (float)
    assert hasattr(f, 'knockback_velocity')
    assert isinstance(f.knockback_velocity, float)
