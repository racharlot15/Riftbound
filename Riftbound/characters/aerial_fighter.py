"""
Aerial Fighter Character Class
Airborne-focused fighter with extended air mobility and aerial combos.

Stats:
- Speed: Medium-High (in air)
- Damage: Medium-High
- Health: Medium-Low
- Special: Multi-jump, Air combos, Fast fall
"""

from engine.fighter import Fighter, MOVE_SPEED, AIR_MOVE_SPEED, GRAVITY, MAX_FALL_SPEED


class AerialFighter(Fighter):
    """
    Air-centric combat specialist.
    Dominates with superior aerial movement and juggling abilities.
    """

    # Character-specific stat modifiers
    SPEED_MULTIPLIER = 1.0       # Normal ground speed
    AIR_SPEED_MULTIPLIER = 1.25   # 25% faster air movement
    JUMP_MULTIPLIER = 1.2         # 20% higher jumps
    DAMAGE_MULTIPLIER = 1.1       # 10% more damage
    HEALTH_MODIFIER = 95          # -5 HP
    
    # Aerial abilities
    MAX_JUMPS = 3                  # Can jump up to 3 times (ground + 2 air)
    FAST_FALL_MULTIPLIER = 1.8     # Gravity increase when fast falling
    AIR_DASH_DISTANCE = 4
    AIR_DASH_COOLDOWN = 0.7
    
    # Juggle system
    JUGGLE_GRAVITY_REDUCTION = 0.6  # Reduced gravity when being juggled
    LAUNCHER_HEIGHT_BONUS = 1.3      # Launchers send higher

    def __init__(self, position, color=None):
        
        if color is None:
            color = (0.2, 1.0, 0.5)  # Default green
        
        super().__init__(
            name="AERIAL FIGHTER",
            position=position,
            fighter_color=color
        )

        # Attempt to load actor
        try:
            from engine.assets import CHARACTER_ASSETS
            from direct.actor.Actor import Actor
            assets = CHARACTER_ASSETS.get('aerial_fighter') or {}
            if assets.get('model'):
                try:
                    self.actor = Actor(assets['model'])
                    try:
                        self.actor.reparentTo(self)
                    except Exception:
                        pass
                    self.animation_clips = assets.get('animations', {})
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
            self.actor = None
            self.animation_clips = {}

        # Apply character stats
        self.max_health = self.HEALTH_MODIFIER
        self.health = self.max_health
        
        # Multi-jump tracking
        self.jumps_remaining = self.MAX_JUMPS
        self.total_jumps_used = 0
        
        # Air dash
        self.air_dash_timer = 0
        self.is_air_dashing = False
        self.air_dash_direction = 0
        
        # Fast fall state
        self.is_fast_falling = False
        
        # Juggle state (when hitting airborne opponents)
        self.juggle_combo_count = 0
        
        print(f"✓ {self.fighter_name} ready - Sky dominator!")

    def try_jump(self):
        """Override for multi-jump capability"""
        # Always allow ground jump or coyote time jump
        if self.grounded or self.coyote_timer > 0:
            if self._execute_jump():
                self.jumps_remaining = self.MAX_JUMPS - 1  # Used ground jump
                return True
        
        # Check for extra jumps while airborne
        if not self.grounded and self.jumps_remaining > 0:
            if self.state not in ("HITSTUN", "KO", "BLOCK"):
                self._execute_air_jump()
                self.jumps_remaining -= 1
                self.total_jumps_used += 1
                print(f"  ✨ {self.fighter_name} air jump! ({self.jumps_remaining} remaining)")
                return True
        
        # Buffer if nothing else works
        if self.state != "KO":
            self.jump_buffer_timer = self.JUMP_BUFFER_TIME
        return False

    def _execute_air_jump(self):
        """Perform an additional jump while airborne"""
        from engine.fighter import JUMP_FORCE
        
        # Reset vertical velocity for consistent height
        self.vertical_velocity = JUMP_FORCE * self.JUMP_MULTIPLIER
        self.grounded = False
        self.can_variable_jump = True
        self.jump_held_this_jump = True
        self.is_fast_falling = False  # Cancel fast fall on new jump

    def start_fast_fall(self):
        """Begin fast falling to descend quickly"""
        if not self.grounded and self.vertical_velocity < 0:  # Must already be falling
            self.is_fast_falling = True
            print(f"  ⬇️ {self.fighter_name} fast falls!")

    def start_air_dash(self, direction):
        """Begin an air dash (can only be used airborne)"""
        if not self.grounded and self.air_dash_timer <= 0 and direction != 0:
            self.is_air_dashing = True
            self.air_dash_direction = direction
            self.air_dash_timer = self.AIR_DASH_DURATION if hasattr(self, 'AIR_DASH_DURATION') else 0.15
            print(f"  🌪️ {self.fighter_name} air dashes!")
            return True
        return False

    def update_gravity(self):
        """Override gravity for aerial-specific physics"""
        import time as ursina_time
        from engine.controller import jump_held
        
        # Reset jumps when grounded
        if self.grounded:
            self.jumps_remaining = self.MAX_JUMPS
            self.total_jumps_used = 0
            self.is_fast_falling = False
            self.is_air_dashing = False
        
        # Update coyote timer
        if self.grounded:
            self.coyote_timer = self.COYOTE_TIME
        else:
            self.coyote_timer = max(0, self.coyote_timer - ursina_time.dt)

        # Process buffered jump
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer = max(0, self.jump_buffer_timer - ursina_time.dt)

        if self.grounded:
            self.can_variable_jump = False
            self.jump_held_this_jump = False
            return

        # Handle air dash
        if self.is_air_dashing:
            self._process_air_dash(ursina_time)
            return

        # Apply base gravity
        gravity_multiplier = 1.0
        
        # Variable jump height
        should_cut_jump = (
            self.vertical_velocity < 0 or 
            (self.can_variable_jump and not jump_held() and self.vertical_velocity > 0)
        )
        
        if should_cut_jump:
            gravity_multiplier *= self.VARIABLE_GRAVITY_MULTIPLIER
        
        # Fast fall extra gravity
        if self.is_fast_falling:
            gravity_multiplier *= self.FAST_FALL_MULTIPLIER
        
        # Apply final gravity
        self.vertical_velocity -= GRAVITY * gravity_multiplier * ursina_time.dt
        
        # Clamp velocity
        self.vertical_velocity = max(self.vertical_velocity, -MAX_FALL_SPEED)

        # Apply movement
        self.y += self.vertical_velocity * ursina_time.dt

        # Ground collision
        if self.y <= 1:
            self.y = 1
            self.vertical_velocity = 0
            self.grounded = True
            self.is_fast_falling = False
            
            if self.state == "JUMP":
                self.set_state("IDLE")

    def _process_air_dash(self, time_module):
        """Process air dash movement"""
        dash_duration = 0.15  # Default
        dash_speed = self.AIR_DASH_DISTANCE / dash_duration
        
        self.x += self.air_dash_direction * dash_speed * time_module.dt
        
        # Still apply some gravity during air dash (reduced)
        self.vertical_velocity -= GRAVITY * 0.3 * time_module.dt
        self.y += self.vertical_velocity * time_module.dt
        
        # Ground check
        if self.y <= 1:
            self.y = 1
            self.vertical_velocity = 0
            self.grounded = True
            self.is_air_dashing = False
        
        # Air dash timer would need to be tracked separately
        # For now, end dash when vertical input changes or after very short time
        # This would need proper integration with controller input

    def move_horizontal(self, direction):
        """Override for enhanced air movement"""
        if not self.grounded:
            # Use enhanced air speed
            speed = AIR_MOVE_SPEED * self.AIR_SPEED_MULTIPLIER
            import time as ursina_time
            self.x += direction * speed * ursina_time.dt
            
            if self.state == "JUMP":
                pass  # Stay in jump state
        else:
            # Normal ground movement
            super().move_horizontal(direction)

    def launch_opponent(self, opponent, base_data):
        """
        Enhanced launcher that sends opponents higher for juggles.
        Used by this character's launcher attacks.
        """
        # Call normal take_hit first
        opponent.take_hit(base_data, self)
        
        # If opponent is now airborne, boost them higher
        if not opponent.grounded:
            opponent.vertical_velocity *= self.LAUNCHER_HEIGHT_BONUS
            self.juggle_combo_count += 1
            print(f"  🔺 {self.fighter_name} launches {opponent.fighter_name} into the air!")

    def get_info(self):
        """Include character-specific info"""
        info = super().get_info()
        info['archetype'] = 'Aerial Fighter'
        info['jumps_remaining'] = self.jumps_remaining
        info['is_fast_falling'] = self.is_fast_falling
        info['juggle_count'] = self.juggle_combo_count
        return info
