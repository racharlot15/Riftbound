"""
Riftbound Health Bar Module
Visual health display for fighters
"""

from ursina import Entity, color, window, camera


class HealthBar(Entity):
    """
    Health bar displayed in the UI layer.
    Shows fighter's current health as a colored bar.
    """

    def __init__(self, position, max_width=0.35, bar_color=color.green):
        """
        Initialize health bar.
        
        Args:
            position: Tuple (x, y) position on screen
            max_width: Maximum width of the health bar
            bar_color: Color of the health bar
        """
        parent_entity = window.editor_ui if hasattr(window, 'editor_ui') and getattr(window, 'editor_ui') is not None else (camera.ui if hasattr(camera, 'ui') else None)
        super().__init__(
            parent=parent_entity,
            model="quad",
            color=bar_color,
            position=position,
            scale=(max_width, 0.035)
        )

        self.max_width = max_width
        self.base_color = bar_color

    def update_health(self, health, max_health=100):
        """
        Update health bar to reflect current health.
        
        Args:
            health: Current HP value
            max_health: Maximum HP for percentage calculation
        """
        ratio = max(0, min(1, health / max_health))
        self.scale_x = self.max_width * ratio
        
        # Change color based on health percentage
        if ratio > 0.6:
            self.color = self.base_color  # Green/normal
        elif ratio > 0.3:
            self.color = color.yellow     # Warning yellow
        else:
            self.color = color.red         # Critical red

    def reset(self):
        """Reset health bar to full"""
        self.scale_x = self.max_width
        self.color = self.base_color

    def set_position(self, position):
        """Move health bar to new screen position"""
        self.position = position


class DualHealthBar(Entity):
    """
    Combined health display showing both players' health.
    Includes names and potentially other info.
    """

    def __init__(self, player_name, enemy_name):
        """Create dual health bar layout"""
        super().__init__(
            parent=camera.ui
        )
        
        # Player 1 health (left side)
        self.player_bar = HealthBar(
            position=(-0.55, 0.42),
            max_width=0.35,
            bar_color=color.azure
        )
        
        # Player 2 health (right side)
        self.enemy_bar = HealthBar(
            position=(0.55, 0.42),
            max_width=0.35,
            bar_color=color.red
        )
        
        # Store references
        self.player_name = player_name
        self.enemy_name = enemy_name

    def update_bars(self, player_health, enemy_health, player_max=100, enemy_max=100):
        """Update both health bars"""
        self.player_bar.update_health(player_health, player_max)
        self.enemy_bar.update_health(enemy_health, enemy_max)

    def get_player_bar(self):
        """Get player's health bar object"""
        return self.player_bar

    def get_enemy_bar(self):
        """Get enemy's health bar object"""
        return self.enemy_bar
