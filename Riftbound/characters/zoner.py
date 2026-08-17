"""
Zoner Character Class
Projectile-based keepaway fighter with strong zoning tools.

Stats:
- Speed: Medium-Low
- Damage: Medium (high from projectiles)
- Health: Low-Medium
- Special: Projectiles, Anti-air, Space control
"""

from ursina import Entity
from engine.fighter import Fighter, MOVE_SPEED


class Projectile(Entity):
    """
    Projectile entity fired by zoner characters.
    Travels across screen and can hit opponents.
    """

    def __init__(self, owner, direction, damage, speed, size=0.5, model=None, texture=None):
        
        # allow optional model/texture for projectile visuals
        try:
            import os
            has_model = model is not None and os.path.exists(model)
            has_texture = texture is not None and os.path.exists(texture)
        except Exception:
            has_model = False
            has_texture = False

        model_arg = model if has_model else "sphere"
        kwargs = dict(model=model_arg, scale=size, color=(0.6, 0.2, 1.0), position=(
                owner.x + direction * 1.5,
                owner.y + 1,
                owner.z
            ))
        if has_texture:
            kwargs['texture'] = texture

        super().__init__(**kwargs)
        
        self.owner = owner
        self.direction = direction
        self.damage = damage
        self.speed = speed
        self.active = True
        self.lifetime = 3.0  # Destroy after 3 seconds
        self.hit_opponents = []  # Track who we've already hit

    def update(self):
        """Move projectile and check lifetime"""
        import time as ursina_time
        
        if not self.active:
            return
        
        # Move projectile
        self.x += self.direction * self.speed * ursina_time.dt
        
        # Decrease lifetime
        self.lifetime -= ursina_time.dt
        
        if self.lifetime <= 0:
            self.destroy()
            self.active = False

    def check_hit(self, target):
        """Check if projectile hits a target"""
        if not self.active:
            return False
        if target in self.hit_opponents:
            return False
        
        distance = abs(self.x - target.x)
        
        if distance < 1.0:  # Hit detection range
            self.hit_opponents.append(target)
            return True
        
        return False

    def destroy(self):
        """Remove projectile from scene"""
        try:
            import ursina
            # Call ursina.destroy() safely; it will handle removal if present.
            ursina.destroy(self)
        except Exception:
            pass


class Zoner(Fighter):
    """
    Zone-control character.
    Uses projectiles and long-range pokes to keep opponents at distance.
    """

    # Character-specific stat modifiers
    SPEED_MULTIPLIER = 0.9       # 10% slower movement
    JUMP_MULTIPLIER = 0.95       # Slightly lower jumps
    DAMAGE_MULTIPLIER = 1.0      # Normal melee damage
    HEALTH_MODIFIER = 90         # -10 HP (glass cannon-ish)
    
    # Projectile stats
    PROJECTILE_DAMAGE = 8
    PROJECTILE_SPEED = 12
    PROJECTILE_COOLDOWN = 0.8    # Seconds between projectiles
    MAX_PROJECTILES = 1          # Max on screen at once
    
    # Anti-air properties
    ANTI_AIR_ACTIVE_FRAMES = 0.15
    ANTI_AIR_RANGE = 3.0
    ANTI_AIR_DAMAGE = 10

    def __init__(self, position, color=None):
        
        if color is None:
            color = (0.6, 0.2, 1.0)  # Default purple
        
        super().__init__(
            name="ZONER",
            position=position,
            fighter_color=color
        )

        # Attempt to load actor
        try:
            from engine.assets import CHARACTER_ASSETS
            from direct.actor.Actor import Actor
            assets = CHARACTER_ASSETS.get('zoner') or {}
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
        
        # Projectile management
        self.projectiles = []
        self.projectile_cooldown = 0
        
        # State tracking
        self.is_firing_projectile = False
        
        print(f"✓ {self.fighter_name} ready - Zone controller!")

    def fire_projectile(self, opponent):
        """
        Fire a projectile toward the opponent.
        Returns True if successfully fired.
        """
        import time as ursina_time
        
        # Check cooldown
        if self.projectile_cooldown > 0:
            return False
        
        # Check max projectiles
        active_count = sum(1 for p in self.projectiles if p.active)
        if active_count >= self.MAX_PROJECTILES:
            return False
        
        # Determine direction
        direction = 1 if opponent.x > self.x else -1
        
        # Create projectile
        proj = Projectile(
            owner=self,
            direction=direction,
            damage=self.PROJECTILE_DAMAGE,
            speed=self.PROJECTILE_SPEED
        )
        
        self.projectiles.append(proj)
        self.projectile_cooldown = self.PROJECTILE_COOLDOWN
        self.is_firing_projectile = True
        
        print(f"  🔮 {self.fighter_name} fires projectile!")
        return True

    def anti_air(self, opponent):
        """
        Perform an anti-air attack.
        Strong against jumping opponents.
        """
        # Check if opponent is above us and within range
        if opponent.y > self.y + 0.5:  # Opponent is airborne
            distance = abs(opponent.x - self.x)
            
            if distance <= self.ANTI_AIR_RANGE:
                # Hit confirmed!
                aa_data = {
                    'damage': self.ANTI_AIR_DAMAGE,
                    'knockback': 5,
                    'hitstun': 0.35
                }
                
                opponent.take_hit(aa_data, self)
                
                # Extra upward knockback for anti-air
                opponent.vertical_velocity = 8
                
                print(f"  ⬆️ {self.fighter_name} anti-airs {opponent.fighter_name}!")
                return True
        
        print(f"  ❌ {self.fighter_name} anti-air missed")
        return False

    def update_projectiles(self, opponent):
        """Update all active projectiles and check for hits"""
        import time as ursina_time
        
        # Update cooldown
        if self.projectile_cooldown > 0:
            self.projectile_cooldown -= ursina_time.dt
        
        # Update projectiles
        for proj in self.projectiles[:]:  # Copy list for safe iteration
            if proj.active:
                proj.update()
                
                # Check collision with opponent
                if proj.check_hit(opponent):
                    # Apply damage
                    proj_data = {
                        'damage': proj.damage,
                        'knockback': 3,
                        'hitstun': 0.25
                    }
                    
                    # Determine knockback direction
                    if proj.owner.x < opponent.x:
                        proj_data['knockback'] = abs(proj_data['knockback'])
                    else:
                        proj_data['knockback'] = -abs(proj_data['knockback'])
                    
                    opponent.take_hit(proj_data, self)
                    print(f"  💥 Projectile hits {opponent.fighter_name}!")
            
            elif proj in self.projectiles:
                self.projectiles.remove(proj)

    def move_horizontal(self, direction):
        """Override for slightly slower movement"""
        modified_direction = direction * self.SPEED_MULTIPLIER
        super().move_horizontal(modified_direction)

    def get_info(self):
        """Include character-specific info"""
        info = super().get_info()
        info['archetype'] = 'Zoner'
        info['active_projectiles'] = sum(1 for p in self.projectiles if p.active)
        info['projectile_ready'] = self.projectile_cooldown <= 0
        return info
