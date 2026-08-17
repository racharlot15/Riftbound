import importlib


def test_engine_and_characters_importable():
    # Ensure core modules import without executing the game loop
    mods = [
        'Riftbound.engine.fighter',
        'Riftbound.engine.controller',
        'Riftbound.engine.combat',
        'Riftbound.characters.agile_hero',
        'Riftbound.characters.grappler',
        'Riftbound.characters.zoner',
        'Riftbound.ui.menus',
        'Riftbound.ui.health_bar',
    ]

    for m in mods:
        importlib.import_module(m)


def test_constants_present():
    from Riftbound.engine.fighter import MOVE_SPEED, JUMP_FORCE
    assert MOVE_SPEED > 0
    assert JUMP_FORCE > 0
