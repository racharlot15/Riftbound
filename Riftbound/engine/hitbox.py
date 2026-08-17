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
        distance_x = abs(self.x - target.x)
        distance_y = abs(self.y - target.y)

        # Check if within hitbox bounds (accounting for target body size)
        hit_threshold_x = range_val / 2 + 0.6   # Target body half-width
        hit_threshold_y = height_val / 2 + 1     # Target body half-height

        if distance_x <= hit_threshold_x and distance_y <= hit_threshold_y:
            return True
        
        return False
