from ursina import Text, color, destroy


def spawn_damage_popup(damage, world_x, world_y, col=color.white, scale=3):
    """Spawn a simple floating damage number using Ursina Text.
    world_x, world_y are treated in-world coordinates and will be converted
    into a Text placed in world space by parenting to scene (default).
    """
    try:
        t = Text(text=str(damage), position=(world_x, world_y + 2, -1), scale=scale, color=col, origin=(0,0))
        # float up and fade
        t.animate_position((world_x, world_y + 3.5, -1), duration=0.55, curve='out_expo')
        try:
            t.animate_color(color.rgba(int(col.r*255), int(col.g*255), int(col.b*255), 0), duration=0.55)
        except Exception:
            # fallback fade with alpha in hexless form
            t.animate_color(color.rgba(255,255,255,0), duration=0.55)
        destroy(t, delay=0.6)
    except Exception:
        # If Text is unavailable for any reason, silently fail
        pass
