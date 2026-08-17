"""
Riftbound Characters Package
Contains all playable fighter archetypes
"""

from .agile_hero import AgileHero
from .grappler import Grappler
from .zoner import Zoner
from .aerial_fighter import AerialFighter

# Character registry for selection screens
CHARACTER_REGISTRY = {
    'agile_hero': {
        'class': AgileHero,
        'name': 'Agile Hero',
        'description': 'Fast attacks, high mobility, low damage',
        'color': (0.2, 0.6, 1.0)  # Blue
    },
    'grappler': {
        'class': Grappler,
        'name': 'Grappler',
        'description': 'Slow but powerful, command grabs',
        'color': (1.0, 0.4, 0.2)  # Orange
    },
    'zoner': {
        'class': Zoner,
        'name': 'Zoner',
        'description': 'Keep opponents away with projectiles',
        'color': (0.6, 0.2, 1.0)  # Purple
    },
    'aerial_fighter': {
        'class': AerialFighter,
        'name': 'Aerial Fighter',
        'description': 'Dominates the air with jump cancels',
        'color': (0.2, 1.0, 0.5)  # Green
    }
}

# Attach asset manifests (do not perform filesystem checks here)
try:
    from engine import assets as assets_mod
    for key in list(CHARACTER_REGISTRY.keys()):
        CHARACTER_REGISTRY[key]['assets'] = assets_mod.CHARACTER_ASSETS.get(key, {})
except Exception:
    for key in list(CHARACTER_REGISTRY.keys()):
        CHARACTER_REGISTRY[key]['assets'] = {}
