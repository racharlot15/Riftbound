"""
Agile Hero Character Class
Fast, combo-focused fighter with quick attacks and high mobility.

Stats:
- Speed: High
- Damage: Low-Medium  
- Health: Medium
- Special: Double Jump, Quick Dash
"""

from engine.fighter import Fighter, MOVE_SPEED, AIR_MOVE_SPEED


class AgileHero(Fighter):
    """
    High-speed rushdown character.
    Excels at close-range pressure with fast attack strings.
    """

    # Character-specific stat modifiers
    SPEED_MULTIPLIER = 1.3       # 30% faster movement
    JUMP_MULTIPLIER = 1.1        # 10% higher jumps
    DAMAGE_MULTIPLIER = 0.9      # 10% less damage
    HEALTH_MODIFIER = 100        # Standard health
    
    # Unique abilities
    CAN_DOUBLE_JUMP = True
    DASH_COOLDOWN = 0.5          # Seconds between dashes
    DASH_DISTANCE = 3            # Units traveled during dash
    DASH_DURATION = 0.1          # How long dash takes

    def __init__(self, position, color=None):
        
        if color is None:
            color = (0.2, 0.6, 1.0)  # Default blue
        
        super().__init__(
            name="AGILE HERO",
            position=position,
            fighter_color=color
        )

        # Apply character stats
        self.max_health = self.HEALTH_MODIFIER
        self.health = self.max_health
        
        # Double jump tracking
        self.double_jump_available = False
        self.has_double_jumped = False
        
        # Dash mechanics
        self.dash_timer = 0
        self.is_dashing = False
        self.dash_direction = 0

        # Attempt to load a skeletal actor if assets are available
        try:
            from engine.assets import CHARACTER_ASSETS
            from direct.actor.Actor import Actor
            assets = CHARACTER_ASSETS.get('agile_hero') or {}
            if assets.get('model'):
                try:
                    self.actor = Actor(assets['model'])
                    # Attach Panda3D Actor to this Ursina entity's node
                    try:
                        self.actor.reparentTo(self)
                    except Exception:
                        # If reparentTo fails, still keep actor reference
                        pass
                    self.animation_clips = assets.get('animations', {})
                    # shrink placeholder cube visual so actor is visible
                    try:
                        self.scale = (0.01, 0.01, 0.01)
                    except Exception:
                        pass
                except Exception as e:
                    print(f" [assets] Could not load actor for {self.fighter_name}: {e}")
                    self.actor = None
                    self.animation_clips = {}
            else:
                self.actor = None
                self.animation_clips = {}
        except Exception:
            # Panda3D not available or other error — continue with placeholder
            self.actor = None
            self.animation_clips = {}

        print(f"✓ {self.fighter_name} ready - Speed demon!")

    def try_double_jump(self):
        """Attempt to use double jump ability"""
        if not self.CAN_DOUBLE_JUMP:
            return False
        if not self.has_double_jumped and self.double_jump_available:
            if not self.grounded:
                from engine.fighter import JUMP_FORCE
                self.vertical_velocity = JUMP_FORCE * self.JUMP_MULTIPLIER
                self.has_double_jumped = True
                self.can_variable_jump = True
                print(f"  ⬆️⬆️ {self.fighter_name} double jumps!")
                return True
        return False

    def start_dash(self, direction):
        """Begin a quick dash in given direction"""
        if self.dash_timer <= 0 and direction != 0:
            self.is_dashing = True
            self.dash_direction = direction
            self.dash_timer = self.DASH_DURATION
            print(f"  💨 {self.fighter_name} dashes!")
            return True
        return False

    def update_dash(self):
        """Process dash movement each frame"""
        import time as ursina_time
        
        if self.dash_timer > 0:
            self.dash_timer -= ursina_time.dt
            
            # Move at dash speed
            dash_speed = self.DASH_DISTANCE / self.DASH_DURATION
            self.x += self.dash_direction * dash_speed * ursina_time.dt
            
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.dash_direction = 0
                # Start cooldown
                self.dash_timer = -self.DASH_COOLDOWN

    def update_gravity(self):
        """Override gravity to handle double jump logic"""
        import time as ursina_time
        # Update double jump availability
        if self.grounded:
            self.double_jump_available = True
            self.has_double_jumped = False
        else:
            self.double_jump_available = False

        # Process dash cooldown
        if self.dash_timer < 0:
            self.dash_timer += ursina_time.dt  # Count down negative cooldown
            if self.dash_timer >= 0:
                self.dash_timer = 0

        # If dashing, handle that first
        if self.is_dashing:
            self.update_dash()
            # Still apply gravity during dash
            super().update_gravity()
            return

        # Normal gravity processing
        super().update_gravity()

    def move_horizontal(self, direction):
        """Override movement for speed bonus"""
        # Apply speed multiplier
        modified_direction = direction * self.SPEED_MULTIPLIER
        super().move_horizontal(modified_direction)

    def get_info(self):
        """Include character-specific info"""
        info = super().get_info()
        info['archetype'] = 'Agile Hero'
        info['double_jump_ready'] = not self.has_double_jumped
        info['dash_ready'] = self.dash_timer == 0
        return info
