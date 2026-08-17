# Lightweight asset manifest using name-based resolution
# Models are referenced by base filename (e.g. 'agile_hero.gltf') and
# animation clip names are the internal clip names baked into the model.

CHARACTER_ASSETS = {
    'agile_hero': {
        'model': 'agile_hero.gltf',
        'animations': {
            'IDLE': 'idle',
            'WALK': 'walk',
            'JUMP': 'jump',
            'ATTACK_LIGHT': 'attack_light',
            'ATTACK_MEDIUM': 'attack_medium',
            'ATTACK_HEAVY': 'attack_heavy',
            'ATTACK_LAUNCHER': 'attack_launcher',
            'BLOCK': 'block',
            'HITSTUN': 'hitstun',
            'KO': 'ko',
        },
        'sounds': {
            'jump': 'agile_hero_jump',
            'land': 'agile_hero_land',
            'hit': 'agile_hero_hit',
            'ko': 'agile_hero_ko',
        },
    },
    'grappler': {
        'model': 'grappler.gltf',
        'animations': {},
        'sounds': {},
    },
    'zoner': {
        'model': 'zoner.gltf',
        'animations': {},
        'sounds': {},
    },
    'aerial_fighter': {
        'model': 'aerial_fighter.gltf',
        'animations': {},
        'sounds': {},
    }
}

SHARED_SOUNDS = {
    'attack_whiff': 'whiff',
    'block_impact': 'block',
    'hit_impact': 'hit_impact',
    'menu_move': 'menu_move',
    'menu_confirm': 'menu_confirm',
}


def get_character_assets(key):
    """Return manifest entry (may be incomplete). No file-system checks
    are performed here — loading is attempted by the runtime and may fail
    safely.
    """
    return CHARACTER_ASSETS.get(key, {})
