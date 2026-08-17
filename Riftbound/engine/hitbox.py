"""
Riftbound Hitbox Module
Handles attack hitbox visualization and collision detection
"""

from ursina import Entity, color


class AttackHitbox(Entity):
    """
    Visual representation of attack hit area.
    Only visible during active frames of attacks.
    """

    def __init__(self, model=None, texture=None):

        # allow swapping visual model/texture if provided and exists
        try:
            import os
            has_model = model is not None and os.path.exists(model)
            has_texture = texture is not None and os.path.exists(texture)
        except Exception:
            has_model = False
            has_texture = False

        model_arg = model if has_model else "cube"
        kwargs = dict(model=model_arg, color=color.rgba(255, 80, 80, 80), visible=False)
        if has_texture:
            kwargs['texture'] = texture

        super().__init__(**kwargs)

        self.owner = None
        self.attack_name = None

    def show_hitbox(self):
        """Make hitbox visible for collision checking"""
        self.show()

    def hide_hitbox(self):
        """Hide hitbox when not active"""
        self.hide()

    def set_position(self, x, y, z):
        """Update hitbox position"""
        self.position = (x, y, z)

    def set_size(self, width, height, depth):
        """Update hitbox dimensions"""
        self.scale = (width, height, depth)

    def check_collision(self, target, range_val, height_val):
        """
        Check if this hitbox collides with a target fighter.
        
        Args:
            target: Fighter entity to check against
            range_val: Horizontal reach of attack
            height_val: Vertical reach of attack
        
        Returns:
            bool: True if collision detected
        """
        # Use axis-aligned rectangle overlap instead of comparing distances.
        # The previous calculation added generous fixed padding to both axes,
        # allowing an attack to connect behind the attacker or above its
        # visible box.  The hitbox dimensions are set from the attack data
        # immediately before this method is called.
        hitbox_width = float(getattr(self, 'scale_x', 0) or range_val)
        hitbox_height = float(getattr(self, 'scale_y', 0) or height_val)
        target_width = float(getattr(target, 'scale_x', 1.2) or 1.2)
        target_height = float(getattr(target, 'scale_y', 2.0) or 2.0)

        hitbox_left = self.x - hitbox_width / 2
        hitbox_right = self.x + hitbox_width / 2
        hitbox_bottom = self.y - hitbox_height / 2
        hitbox_top = self.y + hitbox_height / 2

        target_left = target.x - target_width / 2
        target_right = target.x + target_width / 2
        target_bottom = target.y - target_height / 2
        target_top = target.y + target_height / 2

        overlaps_x = hitbox_left <= target_right and hitbox_right >= target_left
        overlaps_y = hitbox_bottom <= target_top and hitbox_top >= target_bottom
        return overlaps_x and overlaps_y
