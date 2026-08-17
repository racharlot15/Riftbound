import os

class AnimationController:
    """Lightweight animation controller that maps game states to animation
    file paths. It does not attempt to decode animation file formats — it
    simply tracks which clip would be played and silences missing files.
    """
    def __init__(self, fighter, manifest=None):
        self.fighter = fighter
        self.manifest = manifest or {}
        # current clip path (for debug / UI preview)
        self.current_clip = None

    def play(self, state_name):
        # state_name is an exact manifest key, e.g. 'IDLE', 'WALK', 'ATTACK_LIGHT'
        clip = (self.manifest or {}).get(state_name)
        if clip and os.path.exists(clip):
            # for now, just record which clip would be played
            self.current_clip = clip
            try:
                # Attempt to call into ursina animation loaders if available,
                # but swallow any exceptions for headless/test environments.
                from ursina import Animation, scene
                # load as a non-blocking hint (no-op if format unknown)
                Animation(clip, loop=False)
            except Exception:
                # Silent no-op if ursina animation isn't available or fails
                pass
        else:
            # Missing clip — do nothing (silent fallback)
            self.current_clip = None

    def has_clip(self, state_name):
        return bool((self.manifest or {}).get(state_name) and os.path.exists((self.manifest or {})[state_name]))
