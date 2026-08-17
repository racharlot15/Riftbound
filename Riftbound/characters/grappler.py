"""
Grappler Character Class
Slow, powerful fighter with grabs and armor through attacks.

Stats:
- Speed: Low
- Damage: Very High
- Health: High
- Special: Command Grab, Super Armor on heavy attacks
"""

from engine.fighter import Fighter, MOVE_SPEED, JUMP_FORCE


class Grappler(Fighter):
    """
    Power-based grappler character.
    Slow movement but devastating damage output.
    Has access to command grabs that bypass blocks.
    """

    # Character-specific stat modifiers
    SPEED_MULTIPLIER = 0.75      # 25% slower movement
    JUMP_MULTIPLIER = 0.85       # 15% lower jumps
    DAMAGE_MULTIPLIER = 1.35     # 35% more damage
    HEALTH_MODIFIER = 130        # +30 HP
    
    # Grab system
    GRAB_RANGE = 2.0             # Range of command grab
    GRAB_DAMAGE = 18             # Base grab damage
    GRAB_STUN = 0.45             # Stun duration after grab
    
    # Armor system
    ARMOR_ATTACKS = ['HEAVY']    # Which attacks have super armor
    ARMOR_HITS = 1               # How many hits can be absorbed

    def __init__(self, position, color=None):
        
        if color is None:
            color = (1.0, 0.4, 0.2)  # Default orange
        
        super().__init__(
            name="GRAPPLER",
            position=position,
            fighter_color=color
        )

        # Attempt to load actor
        try:
            from engine.assets import CHARACTER_ASSETS
            from direct.actor.Actor import Actor
            assets = CHARACTER_ASSETS.get('grappler') or {}
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
        
        # Armor state
        self.armor_active = False
        self.armor_hits_remaining = 0
        
        # Grab state
        self.is_grabbing = False
        self.grab_target = None
        self.grab_timer = 0
        
        print(f"✓ {self.fighter_name} ready - Powerhouse!")

    def start_attack(self, attack_name):
        """Override to add armor to heavy attacks"""
        result = super().start_attack(attack_name)
        
        if result and attack_name in self.ARMOR_ATTACKS:
            self.armor_active = True
            self.armor_hits_remaining = self.ARMOR_HITS
            print(f"  🛡️ {self.fighter_name} activates SUPER ARMOR!")
        
        return result

    def take_hit(self, data, attacker):
        """Override to check armor before taking hitstun"""
        # Check if we can absorb this hit with armor
        if self.armor_active and self.armor_hits_remaining > 0:
            self.armor_hits_remaining -= 1
            reduced_damage = int(data['damage'] * 0.3)  # Only 30% damage through armor
            self.health -= reduced_damage
            
            print(f"  🛡️ {self.fighter_name} armor absorbs hit! (-{reduced_damage} HP)")
            
            if self.armor_hits_remaining <= 0:
                self.armor_active = False
                print(f"  💔 {self.fighter_name} armor broken!")
            
            if self.health_bar:
                self.health_bar.update_health(self.health)
            
            if self.health <= 0:
                self.set_state("KO")
                print(f"  ☠️ {self.fighter_name} KNOCKED OUT!")
            return
        
        # No armor - take hit normally
        super().take_hit(data, attacker)
        
        # Deactivate armor when hit
        self.armor_active = False

    def execute_grab(self, target):
        """
        Attempt a command grab on target.
        Grabs bypass block but have limited range.
        """
        distance = abs(self.x - target.x)
        
        if distance <= self.GRAB_RANGE:
            # Successful grab!
            self.is_grabbing = True
            self.grab_target = target
            self.grab_timer = self.GRAB_STUN
            self.state = "ATTACK"
            
            # Apply grab damage
            actual_damage = int(self.GRAB_DAMAGE * self.DAMAGE_MULTIPLIER)
            target.health -= actual_damage
            target.health = max(0, target.health)
            
            # Put target into extended hitstun
            target.state = "HITSTUN"
            target.hitstun_timer = self.GRAB_STUN
            
            # Knockback toward grappler (for follow-up)
            if self.x < target.x:
                target.knockback_velocity = -2
            else:
                target.knockback_velocity = 2
            
            if target.health_bar:
                target.health_bar.update_health(target.health)
            
            print(f"  🤏 {self.fighter_name} GRABS {target.fighter_name}! (-{actual_damage} HP)")
            
            return True
        else:
            print(f"  ❌ {self.fighter_name} grab missed (too far)")
            return False

    def update_grab(self):
        """Process grab animation/timer"""
        import time as ursina_time
        
        if self.grab_timer > 0:
            self.grab_timer -= ursina_time.dt
            
            if self.grab_timer <= 0:
                self.is_grabbing = False
                self.grab_target = None
                if self.grounded:
                    self.set_state("IDLE")
                else:
                    self.set_state("JUMP")

    def update_attack(self, opponent):
        """Override to process grab state"""
        if self.is_grabbing:
            self.update_grab()
            return 'grab'
        
        return super().update_attack(opponent)

    def move_horizontal(self, direction):
        """Override for slower movement speed"""
        modified_direction = direction * self.SPEED_MULTIPLIER
        super().move_horizontal(modified_direction)

    def get_info(self):
        """Include character-specific info"""
        info = super().get_info()
        info['archetype'] = 'Grappler'
        info['armor_active'] = self.armor_active
        info['armor_hits'] = self.armor_hits_remaining
        return info
