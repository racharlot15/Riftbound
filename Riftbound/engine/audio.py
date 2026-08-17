from . import assets as assets_mod

class SoundManager:
    """Sound manager using ursina.Audio by base name. All plays are wrapped
    in try/except so missing assets won't crash the app.
    """
    def __init__(self):
        self._cache = {}

    def _resolve_name(self, sound_key, character_key=None):
        # Character-specific mapping
        if character_key:
            ch = assets_mod.CHARACTER_ASSETS.get(character_key, {})
            s = (ch.get('sounds') or {}).get(sound_key)
            if s:
                return s
        # Shared mapping
        s = assets_mod.SHARED_SOUNDS.get(sound_key)
        return s

    def play(self, sound_key, character=None):
        name = self._resolve_name(sound_key, character)
        if not name:
            # nothing mapped
            return
        try:
            from ursina import Audio
            # Audio resolves by name; autoplay=True starts playback
            Audio(name, autoplay=True)
        except Exception as e:
            # Warn once per missing asset to avoid spamming logs
            key = (name, character)
            if key not in self._cache:
                print(f"[audio] Warning: could not play sound '{name}': {e}")
                self._cache[key] = True


sound_manager = SoundManager()
