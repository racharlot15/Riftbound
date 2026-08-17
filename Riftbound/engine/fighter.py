"""
Riftbound Fighter Module
Core Fighter class with movement, combat, and physics systems
"""

from ursina import Entity, Text
from .hitbox import AttackHitbox
from .combat import ATTACKS, COMBO_DECAY_TIME


# ============================================================
# PHYSICS CONSTANTS
# ============================================================

GRAVITY = 22
JUMP_FORCE = 11
VARIABLE_GRAVITY_MULTIPLIER = 1.4   # Extra gravity when falling/releasing jump early
MAX_FALL_SPEED = 20                  # Terminal velocity

# Jump timing windows (in seconds)
COYOTE_TIME = 0.08          # Can jump briefly after leaving ground
JUMP_BUFFER_TIME = 0.10     # Press jump before landing, still jumps

# Movement speeds
MOVE_SPEED = 7
AIR_MOVE_SPEED = 5          # Slightly slower movement in air


class Fighter(Entity):
    """
    Core fighter entity with complete fighting game mechanics.
    
    Handles:
    - Health and combat state
    - Movement (ground + air)
    - Jump physics with variable height
    - Attack execution and hit detection
    - Hitstun and knockback
    """

    def __init__(self, name, position, fighter_color, model_name=None, asset_key=None):
        """Fighter optional model_name is a base model filename (e.g. 'agile_hero.gltf').
        The existing primitive cube remains as the fallback visual and collision
        proxy. If model_name is provided, subclasses will attempt to load a
        Panda3D Actor and attach it as self.actor.
        """
        super().__init__(
            model="cube",
            scale=(1, 2, 1),
            position=position,
            color=fighter_color
        )

        self.fighter_name = name
        self.asset_key = asset_key

        # Actor for skeletal animation (Panda3D) — None until loaded by subclass
        self.actor = None
        # animation_clips mapping (populated by subclasses from CHARACTER_ASSETS)
        self.animation_clips = {}

        # Keep a fallback animator as a soft fallback (non-skeletal)
        self.animator = None

        # Last played animation clip or animator key (for debug overlay)
        self.last_animation = None

        # ----------------------------------------------------
        # HEALTH SYSTEM
        # ----------------------------------------------------

        self.max_health = 100
        self.health = 100

        # ----------------------------------------------------
        # COMBAT STATE MACHINE
        # ----------------------------------------------------

        self.state = "IDLE"           # Current state: IDLE, WALK, JUMP, ATTACK, BLOCK, HITSTUN, KO
        self.attack_name = None       # Current attack being performed
        self.attack_timer = 0         # Timer for current attack phase
        self.attack_hit = False       # Whether this attack has already hit
        # Attack buffering
        self.attack_buffer_timer = 0
        self.buffered_attack = None

        self.hitstun_timer = 0        # Remaining hitstun duration
        self.knockback_velocity = 0   # Current knockback movement speed

        # Combo tracking
        self.combo_count = 0
        self.combo_timer = 0
        self.combo_hit_index = 0  # 0-based index for combo scaling

        # ----------------------------------------------------
        # MOVEMENT & PHYSICS
        # ----------------------------------------------------

        self.vertical_velocity = 0
        self.grounded = True
        
        # Jump system variables
        self.coyote_timer = 0              # Time since leaving ground (for coyote time)
        self.jump_buffer_timer = 0         # Buffered jump input waiting to execute
        self.can_variable_jump = False     # Can we cut jump short by releasing button?
        self.jump_held_this_jump = False   # Track if jump was held this jump cycle

        # Double jump support
        self.max_jumps = 2                 # Allow one extra mid-air jump
        self.jumps_used = 0                # Number of jumps used since leaving ground

        # Air combo support
        self.max_air_attacks = 2           # Number of attacks allowed while airborne
        self.air_attacks_used = 0          # Counter for attacks used in current aerial sequence

        # Helper to ensure attack "active" phase punch-scale only triggers once
        self._attack_active_started = False

        # Cooldowns for heavy and launcher (seconds)
        self.heavy_cooldown_timer = 0.0
        self.launcher_cooldown_timer = 0.0

        # ----------------------------------------------------
        # HITBOX
        # ----------------------------------------------------

        self.hitbox = AttackHitbox()
        self.hitbox.owner = self

        # ----------------------------------------------------
        # VISUAL ELEMENTS
        # ----------------------------------------------------

        # Name tag above fighter
        Text(
            text=name,
            parent=self,
            y=1.5,
            origin=(0, 0),
            scale=2
        )

    def punch_scale(self, squash=(1.3, 0.7, 1.3), duration=0.08):
        """Play a quick squash-and-stretch scale tween for impact/attack visuals.
        Fully guarded so missing tween support won't raise errors.
        """
        try:
            # scale down/up sequence
            self.animate_scale(squash, duration=duration/2, curve='out_expo')
            self.animate_scale((1, 2, 1), duration=duration/2, delay=duration/2, curve='out_expo')
        except Exception:
            pass

        # Health bar (position set by game setup)
        self.health_bar = None

    # ========================================================
    # STATE MANAGEMENT
    # ========================================================

    def set_state(self, new_state):
        """Transition to a new state"""
        if self.state != new_state:
            
            old_state = self.state
            self.state = new_state
            
            # Clear attack data when leaving combat states
            if new_state not in ("ATTACK", "HITSTUN", "JUMP"):
                self.attack_name = None
            
            print(f"[{self.fighter_name}] {old_state} → {new_state}")

            # Prefer Panda3D Actor if attached: loop clip for state
            try:
                if getattr(self, 'actor', None) and getattr(self, 'animation_clips', None):
                    clip = self.animation_clips.get(new_state)
                    if clip:
                        try:
                            # actor.loop may raise if clip missing; swallow errors
                            self.actor.loop(clip)
                            try:
                                self.last_animation = clip
                            except Exception:
                                pass
                        except Exception:
                            pass
                # Fallback to animator (legacy non-skeletal system)
                elif getattr(self, 'animator', None):
                    try:
                        self.animator.play(new_state)
                        try:
                        self.last_animation = new_state
                        except Exception:
                        pass
                    except Exception:
                        pass
            except Exception:
                pass

    def can_act(self):
        """Check if fighter can perform actions (not stunned/KO'd)"""
        return self.state not in ("HITSTUN", "KO")

    def is_airborne(self):
        """Check if fighter is currently in the air"""
        return not self.grounded

    # ========================================================
    # ATTACK SYSTEM
    # ========================================================

    def start_attack(self, attack_name):
        """
        Begin an attack if conditions are met.
        
        Args:
            attack_name: Key from ATTACKS dictionary (LIGHT, MEDIUM, HEAVY, LAUNCHER)
        """
        # Prevent starting HEAVY/LAUNCHER if their cooldowns are active (buffer instead)
        try:
            from .combat import HEAVY_COOLDOWN, LAUNCHER_COOLDOWN, ATTACK_BUFFER_TIME
            if attack_name == 'HEAVY' and getattr(self, 'heavy_cooldown_timer', 0) > 0:
                # Buffer heavy
                self.attack_buffer_timer = ATTACK_BUFFER_TIME
                self.buffered_attack = attack_name
                return False
            if attack_name == 'LAUNCHER' and getattr(self, 'launcher_cooldown_timer', 0) > 0:
                # Buffer launcher
                self.attack_buffer_timer = ATTACK_BUFFER_TIME
                self.buffered_attack = attack_name
                return False
        except Exception:
            pass

        # Check if we can attack
        if self.state == "ATTACK":
            # Magic Series chaining: allow cancel into strictly higher strength attack
            from .combat import can_chain, ATTACKS, HEAVY_COOLDOWN, LAUNCHER_COOLDOWN
            try:
                # Immediate chaining allowed (responsive MvC-style)
                if can_chain(self.attack_name, attack_name):
                    # Enforce cooldowns for HEAVY/LAUNCHER on chain as well
                    if attack_name == 'HEAVY' and getattr(self, 'heavy_cooldown_timer', 0) > 0:
                        raise RuntimeError('heavy cooldown')
                    if attack_name == 'LAUNCHER' and getattr(self, 'launcher_cooldown_timer', 0) > 0:
                        raise RuntimeError('launcher cooldown')
                    self.attack_name = attack_name
                    # Skip or shorten startup on chained follow-ups for snappy feel
                    try:
                        startup = ATTACKS.get(attack_name, {}).get('startup', 0)
                        # Jump straight to end of startup so active hitbox comes out immediately
                        self.attack_timer = startup
                    except Exception:
                        self.attack_timer = 0
                    self.attack_hit = False
                    print(f"  ➜ {self.fighter_name} chains into: {attack_name}")
                    if getattr(self, 'actor', None) and getattr(self, 'animation_clips', None):
                        try:
                            clip = self.animation_clips.get(f"ATTACK_{attack_name}")
                            if clip:
                                try:
                                    self.actor.play(clip)
                                except Exception:
                                    pass
                                try:
                                    self.last_animation = clip
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    elif getattr(self, 'animator', None):
                        try:
                            mapping = {
                                'LIGHT': 'ATTACK_LIGHT',
                                'MEDIUM': 'ATTACK_MEDIUM',
                                'HEAVY': 'ATTACK_HEAVY',
                                'LAUNCHER': 'ATTACK_LAUNCHER'
                            }
                            mapped = mapping.get(attack_name)
                            if mapped:
                                try:
                                    self.animator.play(mapped)
                                except Exception:
                                    pass
                                try:
                                    self.last_animation = mapped
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    # Temporarily shorten active/recovery for chained follow-ups for snappy feel
                    try:
                        from .combat import ATTACKS as ATTACK_DB, HEAVY_COOLDOWN, LAUNCHER_COOLDOWN
                        orig = ATTACK_DB.get(attack_name, {})
                        factor = 0.5  # temporary speedup factor for chained hits
                        self._chained_attack_override = {
                            'attack': attack_name,
                            'active': orig.get('active', 0) * factor,
                            'recovery': orig.get('recovery', 0) * factor
                        }
                        # apply cooldown when chaining into powerful moves
                        if attack_name == 'HEAVY':
                            self.heavy_cooldown_timer = HEAVY_COOLDOWN
                        if attack_name == 'LAUNCHER':
                            self.launcher_cooldown_timer = LAUNCHER_COOLDOWN
                    except Exception:
                        self._chained_attack_override = None
                    return True
            except Exception:
                pass

            # Not a legal chain — fall back to buffering behavior
            from .combat import ATTACK_BUFFER_TIME, ATTACKS as ATTACK_DB
            cur = ATTACK_DB.get(self.attack_name)
            remaining = 0
            if cur is not None:
                try:
                    from .combat import STARTUP_MULTIPLIER, ACTIVE_MULTIPLIER, RECOVERY_MULTIPLIER
                    total = cur['startup'] * STARTUP_MULTIPLIER + cur['active'] * ACTIVE_MULTIPLIER + cur['recovery'] * RECOVERY_MULTIPLIER
                except Exception:
                    total = cur['startup'] + cur['active'] + cur['recovery']
                remaining = max(0, total - self.attack_timer)
            # keep buffer alive at least until this attack finishes
            self.attack_buffer_timer = max(ATTACK_BUFFER_TIME, remaining)
            self.buffered_attack = attack_name
            return False

        if self.state == "HITSTUN":
            # Buffer during hitstun
            from .combat import ATTACK_BUFFER_TIME
            self.attack_buffer_timer = ATTACK_BUFFER_TIME
            self.buffered_attack = attack_name
            return False
        
        # Air attack limit: allow attacks in air but cap how many
        if not self.grounded:
            if self.air_attacks_used >= self.max_air_attacks:
                from .combat import ATTACK_BUFFER_TIME
                self.attack_buffer_timer = ATTACK_BUFFER_TIME
                self.buffered_attack = attack_name
                return False
            else:
                # Consume one aerial attack slot when starting in air
                self.air_attacks_used += 1

        # Initialize attack
        self.attack_name = attack_name
        self.attack_timer = 0
        self.attack_hit = False
        self.state = "ATTACK"

        # apply cooldowns for heavy/launcher when started fresh
        try:
            from .combat import HEAVY_COOLDOWN, LAUNCHER_COOLDOWN
            if attack_name == 'HEAVY':
                self.heavy_cooldown_timer = HEAVY_COOLDOWN
            if attack_name == 'LAUNCHER':
                self.launcher_cooldown_timer = LAUNCHER_COOLDOWN
        except Exception:
            pass

        print(f"  ⚔️ {self.fighter_name} attacks: {attack_name}")
        # Prefer skeletal Actor playback when available
        try:
            if getattr(self, 'actor', None) and getattr(self, 'animation_clips', None):
                clip = self.animation_clips.get(f"ATTACK_{attack_name}")
                if clip:
                    try:
                        self.actor.play(clip)
                    except Exception:
                        pass
            elif getattr(self, 'animator', None):
                try:
                    mapping = {
                        'LIGHT': 'ATTACK_LIGHT',
                        'MEDIUM': 'ATTACK_MEDIUM',
                        'HEAVY': 'ATTACK_HEAVY',
                        'LAUNCHER': 'ATTACK_LAUNCHER'
                    }
                    mapped = mapping.get(attack_name)
                    if mapped:
                        self.animator.play(mapped)
                except Exception:
                    pass
        except Exception:
            pass
        return True

    def update_attack(self, opponent, dt=None):
        """
        Process current attack through its phases.
        
        Phases: STARTUP → ACTIVE → RECOVERY → COMPLETE
        """
        import time as ursina_time

        # If there is no current attack, try to start a buffered one if available
        if not self.attack_name:
            if self.buffered_attack and self.attack_buffer_timer > 0:
                next_attack = self.buffered_attack
                self.buffered_attack = None
                self.attack_buffer_timer = 0
                self.attack_name = next_attack
                self.attack_timer = 0
                self.attack_hit = False
                self.state = "ATTACK"
                print(f"  ▶️ {self.fighter_name} begins buffered attack: {next_attack}")
            else:
                return 'idle'

        data = ATTACKS[self.attack_name]
        # determine dt (allow injection for tests)
        if dt is None:
            real_dt = ursina_time.dt
        else:
            real_dt = dt

        # decrement attack buffer timer if active
        if self.attack_buffer_timer > 0:
            self.attack_buffer_timer = max(0, self.attack_buffer_timer - real_dt)
            if self.attack_buffer_timer == 0:
                self.buffered_attack = None

        self.attack_timer += real_dt

        # Base timings
        startup = data.get("startup", 0)
        active = data.get("active", 0)
        recovery = data.get("recovery", 0)

        # Apply global multipliers for MvC-like rapid feel
        try:
            from .combat import STARTUP_MULTIPLIER, ACTIVE_MULTIPLIER, RECOVERY_MULTIPLIER
            startup = startup * STARTUP_MULTIPLIER
            active = active * ACTIVE_MULTIPLIER
            recovery = recovery * RECOVERY_MULTIPLIER
        except Exception:
            pass

        # Apply temporary override for chained attacks (makes chained follow-ups faster)
        if getattr(self, '_chained_attack_override', None) and self._chained_attack_override.get('attack') == self.attack_name:
            try:
                active = self._chained_attack_override.get('active', active)
                recovery = self._chained_attack_override.get('recovery', recovery)
            except Exception:
                pass

        # Lenient chaining: if player buffered a legal chain input, allow it to trigger mid-attack
        # so players don't need frame-perfect timing to continue the Magic Series.
        try:
            from .combat import can_chain, ATTACKS as ATTACK_DB, HEAVY_COOLDOWN, LAUNCHER_COOLDOWN
            if self.buffered_attack and self.attack_buffer_timer > 0 and can_chain(self.attack_name, self.buffered_attack):
                next_attack = self.buffered_attack
                # enforce cooldowns: if on cooldown, keep buffering instead of dropping
                if next_attack == 'HEAVY' and getattr(self, 'heavy_cooldown_timer', 0) > 0:
                    # leave buffer in place
                    pass
                elif next_attack == 'LAUNCHER' and getattr(self, 'launcher_cooldown_timer', 0) > 0:
                    pass
                else:
                    # consume buffer and perform chain just like start_attack did
                    self.buffered_attack = None
                    self.attack_name = next_attack
                    # set timer to startup so active comes immediately (matches chain behavior)
                    try:
                        startup = ATTACK_DB.get(next_attack, {}).get('startup', 0)
                        self.attack_timer = startup
                    except Exception:
                        self.attack_timer = 0
                    self.attack_hit = False
                    print(f"  ➜ {self.fighter_name} lenient-chain into: {next_attack}")
                    # play actor/animator if available
                    try:
                        if getattr(self, 'actor', None) and getattr(self, 'animation_clips', None):
                            clip = self.animation_clips.get(f"ATTACK_{next_attack}")
                            if clip:
                                try:
                                    self.actor.play(clip)
                                except Exception:
                                    pass
                                try:
                                    self.last_animation = clip
                                except Exception:
                                    pass
                        elif getattr(self, 'animator', None):
                            mapping = {'LIGHT': 'ATTACK_LIGHT', 'MEDIUM': 'ATTACK_MEDIUM', 'HEAVY': 'ATTACK_HEAVY', 'LAUNCHER': 'ATTACK_LAUNCHER'}
                            mapped = mapping.get(next_attack)
                            if mapped:
                                try:
                                    self.animator.play(mapped)
                                except Exception:
                                    pass
                                try:
                                    self.last_animation = mapped
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    # chained override for shorter active/recovery
                    try:
                        orig = ATTACK_DB.get(next_attack, {})
                        factor = 0.5
                        self._chained_attack_override = {'attack': next_attack, 'active': orig.get('active', 0) * factor, 'recovery': orig.get('recovery', 0) * factor}
                        if next_attack == 'HEAVY':
                            self.heavy_cooldown_timer = HEAVY_COOLDOWN
                        if next_attack == 'LAUNCHER':
                            self.launcher_cooldown_timer = LAUNCHER_COOLDOWN
                    except Exception:
                        self._chained_attack_override = None
        except Exception:
            pass

        active_end = startup + active
        recovery_end = active_end + recovery

        # STARTUP PHASE: Preparing attack, no hitbox yet
        if self.attack_timer < startup:
            self.hitbox.hide_hitbox()
            # reset per-attack active-start flag
            self._attack_active_started = False
            return 'startup'

        # ACTIVE PHASE: Hitbox is out, can deal damage
        if self.attack_timer < active_end:
            # Trigger attacker punch-scale only on the first active frame
            if not self._attack_active_started:
                self._attack_active_started = True
                try:
                    self.punch_scale()
                except Exception:
                    pass

            self._update_attack_hitbox(data)
            self.hitbox.show_hitbox()
            
            if not self.attack_hit:
                self._check_attack_hit(opponent, data)
            
            return 'active'

        # RECOVERY PHASE: Attack ending, vulnerable window
        self.hitbox.hide_hitbox()

        if self.attack_timer >= recovery_end:
            # clear any chained override for this attack
            try:
                if getattr(self, '_chained_attack_override', None) and self._chained_attack_override.get('attack') == self.attack_name:
                    self._chained_attack_override = None
            except Exception:
                pass

            # Attack complete - return to appropriate state
            if self.grounded:
                self.set_state("IDLE")
            else:
                self.set_state("JUMP")

            # Play whiff sound if this attack never hit
            if not self.attack_hit:
                try:
                    from .audio import sound_manager
                    sound_manager.play('attack_whiff', character=getattr(self, 'asset_key', None))
                except Exception:
                    pass

            # If we have a buffered attack pending, start it immediately
            if self.buffered_attack and self.attack_buffer_timer > 0:
                next_attack = self.buffered_attack
                self.buffered_attack = None
                self.attack_buffer_timer = 0
                # Start the buffered attack
                self.attack_name = next_attack
                self.attack_timer = 0
                self.attack_hit = False
                self.state = "ATTACK"
                print(f"  ▶️ {self.fighter_name} begins buffered attack: {next_attack}")
                # Animator: play mapped attack clip
                if getattr(self, 'animator', None):
                    try:
                        mapping = {
                            'LIGHT': 'ATTACK_LIGHT',
                            'MEDIUM': 'ATTACK_MEDIUM',
                            'HEAVY': 'ATTACK_HEAVY',
                            'LAUNCHER': 'ATTACK_LAUNCHER'
                        }
                        mapped = mapping.get(next_attack)
                        if mapped:
                            try:
                                self.animator.play(mapped)
                            except Exception:
                                pass
                            try:
                                self.last_animation = mapped
                            except Exception:
                                pass
                    except Exception:
                        pass
                return 'startup'

            self.attack_name = None
            return 'complete'
            
        return 'recovery'

    def _update_attack_hitbox(self, data):
        """Position and size the attack hitbox based on attack data"""
        direction = 1 if self.rotation_y == 0 else -1
        
        self.hitbox.set_position(
            self.x + direction * data["range"] / 2,
            self.y,
            self.z - 1
        )
        
        self.hitbox.set_size(
            data["range"],
            data["height"],
            2
        )

    def _check_attack_hit(self, opponent, data):
        """Check if current attack hits the opponent"""
        if self.hitbox.check_collision(opponent, data["range"], data["height"]):
            opponent.take_hit(data, self)
            self.attack_hit = True

    # ========================================================
    # DAMAGE & HIT REACTIONS
    # ========================================================

    def take_hit(self, data, attacker):
        """
        Process taking damage from an attack.
        
        Args:
            data: Attack data dictionary
            attacker: Fighter who landed the attack
        """
        # BLOCK CHECK
        # Compute scaled damage based on attacker's combo index
        try:
            from .combat import get_combo_scaling
            attacker_index = getattr(attacker, 'combo_hit_index', 0) if attacker is not None else 0
            scaling = get_combo_scaling(attacker_index)
            scaled_damage = max(1, int(data.get('damage', 0) * scaling))
        except Exception:
            scaled_damage = data.get('damage', 0)

        if self.state == "BLOCK":
            from .combat import calculate_block_damage
            damage = calculate_block_damage(scaled_damage)
            self.health -= damage
            # Play block impact audio
            try:
                from .audio import sound_manager
                sound_manager.play('block_impact', character=getattr(self, 'asset_key', None))
            except Exception:
                pass
            print(f"  🛡️ {self.fighter_name} blocked! ({damage} damage)")
            # spawn small grey damage popup for blocked hits
            try:
                from ui.damage_popup import spawn_damage_popup
                from ursina import color as ursina_color
                spawn_damage_popup(damage, self.x, self.y, col=ursina_color.gray, scale=2)
            except Exception:
                pass
            return

        # APPLY DAMAGE (scaled)
        self.health -= scaled_damage
        self.health = max(0, self.health)

        # Cosmetic effects: hitstop, camera shake, screen flash, damage popup, squash/stretch
        try:
            # Hitstop duration by attack strength mapping
            from engine import juice
            duration = data.get('hitstun', 0.05)
            try:
                atk_key = getattr(attacker, 'attack_name', None)
                mapping = {'LIGHT': 0.04, 'MEDIUM': 0.06, 'HEAVY': 0.09, 'LAUNCHER': 0.10}
                if atk_key:
                    duration = mapping.get(atk_key, duration)
            except Exception:
                duration = data.get('hitstun', 0.05)
            try:
                juice.trigger_hitstop(duration)
            except Exception:
                pass
        except Exception:
            pass

        try:
            # Camera shake scaled by attack strength
            from engine.camera import trigger_shake
            try:
                atk_key = getattr(attacker, 'attack_name', None)
                strength_map = {'LIGHT': 0.05, 'MEDIUM': 0.12, 'HEAVY': 0.25, 'LAUNCHER': 0.25}
                strength = strength_map.get(atk_key, min(0.05 + data.get('damage', 0) * 0.01, 0.25))
                trigger_shake(strength=strength, duration=0.12)
            except Exception:
                trigger_shake(strength=0.08, duration=0.12)

            # Screen flash for heavy/launcher
            try:
                from engine import juice as _juice
                if getattr(attacker, 'attack_name', None) in ('HEAVY', 'LAUNCHER'):
                    try:
                        _juice.flash(strength=0.6, duration=0.12)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

        # Small defender punch_scale (compress on hit)
        try:
            self.punch_scale(squash=(0.7, 1.3, 0.7))
        except Exception:
            pass

        # Floating damage popup
        try:
            from ui.damage_popup import spawn_damage_popup
            from ursina import color as ursina_color
            spawn_color = ursina_color.white
            spawn_scale = 3
            # show scaled damage
            try:
                spawn_damage_popup(scaled_damage, self.x, self.y, col=spawn_color, scale=spawn_scale)
            except Exception:
                spawn_damage_popup(data.get('damage', 0), self.x, self.y, col=spawn_color, scale=spawn_scale)
        except Exception:
            pass

        # ENTER HITSTUN
        # Launcher attacks should launch opponent into the air for juggle follow-ups
        self.set_state("HITSTUN")
        self.hitstun_timer = data["hitstun"]

        # APPLY KNOCKBACK
        from .combat import calculate_knockback_direction
        self.knockback_velocity = calculate_knockback_direction(
            attacker.x, 
            self.x, 
            data["knockback"]
        )

        # If this attack is a launcher, apply vertical launch to enable juggle
        if data.get('juggle'):
            self.grounded = False
            # give vertical boost for juggle
            self.vertical_velocity = max(self.vertical_velocity, JUMP_FORCE * 0.85)
            # slightly extend hitstun to allow follow-up
            self.hitstun_timer = max(self.hitstun_timer, data.get('hitstun', 0) + 0.15)
            print(f"  🔼 {self.fighter_name} launched into juggle!")

        # Play hit audio
        try:
            from .audio import sound_manager
            sound_manager.play('hit_impact', character=getattr(self, 'asset_key', None))
        except Exception:
            pass

        # UPDATE COMBO COUNTER
        attacker.combo_count += 1
        attacker.combo_timer = COMBO_DECAY_TIME
        # advance per-hit combo index for scaling
        try:
            attacker.combo_hit_index = getattr(attacker, 'combo_hit_index', 0) + 1
        except Exception:
            pass

        print(f"  💥 {attacker.fighter_name} hits {self.fighter_name}! (-{scaled_damage} HP)")
        if attacker.combo_count > 1:
            print(f"     🔥 {attacker.combo_count}-HIT COMBO!")

        # UPDATE HEALTH BAR
        if self.health_bar:
            self.health_bar.update_health(self.health)

        # CHECK FOR K.O.
        if self.health <= 0:
            # Play KO audio
            try:
                from .audio import sound_manager
                sound_manager.play('ko', character=getattr(self, 'asset_key', None))
            except Exception:
                pass
            # Spawn a big red KO popup
            try:
                from ui.damage_popup import spawn_damage_popup
                from ursina import color as ursina_color
                spawn_damage_popup('K.O.', self.x, self.y, col=ursina_color.red, scale=5)
            except Exception:
                pass
            self.set_state("KO")
            print(f"  ☠️ {self.fighter_name} KNOCKED OUT!")

    def update_hitstun(self):
        """Process hitstun state - knocked back, unable to act"""
        import time as ursina_time
        
        self.hitstun_timer -= ursina_time.dt
        
        # Apply knockback movement
        self.x += self.knockback_velocity * ursina_time.dt
        
        # Apply gravity during airborne hitstun
        if not self.grounded:
            self.vertical_velocity -= GRAVITY * ursina_time.dt
            self.y += self.vertical_velocity * ursina_time.dt
            
            # Ground check during hitstun
            if self.y <= 1:
                self.y = 1
                self.vertical_velocity = 0
                self.grounded = True

        # Decay knockback velocity
        self.knockback_velocity *= 0.90

        # End hitstun when timer expires
        if self.hitstun_timer <= 0:
            self.set_state("IDLE")

    # ========================================================
    # MOVEMENT SYSTEM
    # ========================================================

    def move_horizontal(self, direction):
        """
        Move fighter horizontally.
        
        Args:
            direction: Movement direction (-1 left, 1 right), can be fractional for smoothing
        """
        import time as ursina_time
        
        if direction == 0:
            return
        
        # Use appropriate speed based on grounded/airborne state
        speed = AIR_MOVE_SPEED if not self.grounded else MOVE_SPEED
        
        self.x += direction * speed * ursina_time.dt
        
        # Update visual state if grounded
        if self.grounded and self.state not in ("ATTACK", "BLOCK"):
            self.set_state("WALK")

    def stop_movement(self):
        """Stop horizontal movement and return to idle if grounded"""
        if self.grounded and self.state not in ("ATTACK", "BLOCK", "HITSTUN"):
            self.set_state("IDLE")

    # ========================================================
    # JUMP PHYSICS SYSTEM
    # ========================================================

    def try_jump(self):
        """
        Attempt to jump. Uses coyote time and input buffering for responsive feel.
        """
        # Only buffer jumps when incapacitated; allow jump input during ATTACK for cancels
        if self.state in ("HITSTUN", "KO", "BLOCK"):
            # Buffer the jump attempt for when we can act
            if self.state != "KO":
                self.jump_buffer_timer = JUMP_BUFFER_TIME
                print(f"  [BUFFER] {self.fighter_name} buffered jump")
            return
        
        if self.grounded or self.coyote_timer > 0:
            self._execute_jump()
        else:
            # If we have double-jump remaining, allow immediate mid-air jump
            if self.jumps_used < self.max_jumps:
                self._execute_jump()
                return

            # Otherwise buffer the input
            self.jump_buffer_timer = JUMP_BUFFER_TIME
            print(f"  [BUFFER] {self.fighter_name} buffered jump (airborne)")

    def _execute_jump(self):
        """Actually perform the jump"""
        # Allow jumping unless in incapacitated states
        if self.state in ("HITSTUN", "KO", "BLOCK"):
            return

        # Determine if we can jump: grounded/coyote or have remaining double-jumps
        can_jump = self.grounded or self.coyote_timer > 0 or self.jumps_used < self.max_jumps
        if not can_jump:
            return

        # Launch into air
        self.grounded = False
        self.coyote_timer = 0
        self.jump_buffer_timer = 0

        # Count this jump usage
        self.jumps_used = min(self.jumps_used + 1, self.max_jumps)

        # First jump uses full force, subsequent mid-air jumps slightly reduced for balance
        force = JUMP_FORCE if self.jumps_used == 1 else JUMP_FORCE * 0.9
        self.vertical_velocity = max(self.vertical_velocity, force)
        
        # Enable variable height jumping only for primary jump
        self.can_variable_jump = (self.jumps_used == 1)
        self.jump_held_this_jump = True
        
        # Play jump sound (safe no-op)
        try:
            from .audio import sound_manager
            sound_manager.play('jump', character=getattr(self, 'asset_key', None))
        except Exception:
            pass

        self.set_state("JUMP")
        print(f"  ⬆️ {self.fighter_name} jumps! (used {self.jumps_used}/{self.max_jumps})")

    def update_gravity(self):
        """
        Apply gravity and handle ground/air transitions.
        Includes variable jump height and coyote time logic.
        """
        import time as ursina_time
        from engine.controller import jump_held
        
        # Update coyote timer when grounded
        if self.grounded:
            self.coyote_timer = COYOTE_TIME
        else:
            # Decrease coyote timer when airborne
            self.coyote_timer = max(0, self.coyote_timer - ursina_time.dt)

        # Process buffered jump input
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer = max(0, self.jump_buffer_timer - ursina_time.dt)
            if self.grounded and self.jump_buffer_timer > 0:
                self._execute_jump()
                return

        # Cooldown timers decrement (run regardless of grounded state)
        try:
            self.heavy_cooldown_timer = max(0.0, self.heavy_cooldown_timer - ursina_time.dt)
            self.launcher_cooldown_timer = max(0.0, self.launcher_cooldown_timer - ursina_time.dt)
        except Exception:
            pass

        # No gravity processing if grounded
        if self.grounded:
            # Reset variable jump flags
            self.can_variable_jump = False
            self.jump_held_this_jump = False
            # If crouching, stay crouched without changing to idle here
            if getattr(self, 'is_crouching', False):
                return
            return

        # Apply base gravity
        self.vertical_velocity -= GRAVITY * ursina_time.dt
        
        # Variable jump height: extra gravity when:
        # 1. Falling (moving down) - always apply
        # 2. Rising but jump button released - allows short hops
        should_cut_jump = (
            self.vertical_velocity < 0 or 
            (self.can_variable_jump and not jump_held() and self.vertical_velocity > 0)
        )
        
        if should_cut_jump:
            extra_gravity = GRAVITY * (VARIABLE_GRAVITY_MULTIPLIER - 1)
            self.vertical_velocity -= extra_gravity * ursina_time.dt
        
        # Clamp to terminal velocity
        self.vertical_velocity = max(self.vertical_velocity, -MAX_FALL_SPEED)

        # Apply vertical movement
        self.y += self.vertical_velocity * ursina_time.dt

        # Ground collision
        if self.y <= 1:
            self.y = 1
            self.vertical_velocity = 0
            self.grounded = True

            # Reset double-jump and air-attack counters on landing
            self.jumps_used = 0
            self.air_attacks_used = 0

            # Play landing sound
            try:
                from .audio import sound_manager
                sound_manager.play('land', character=getattr(self, 'asset_key', None))
            except Exception:
                pass
            
            # Return to idle if we were just jumping/falling
            if self.state == "JUMP":
                self.set_state("IDLE")

    # ========================================================
    # COMBO SYSTEM
    # ========================================================

    def update_combo_timer(self):
        """Decay combo counter over time"""
        import time as ursina_time
        
        if self.combo_timer > 0:
            self.combo_timer -= ursina_time.dt
        else:
            self.combo_count = 0
            try:
                self.combo_hit_index = 0
            except Exception:
                pass

    # ========================================================
    # UTILITY METHODS
    # ========================================================

    def get_info(self):
        """Return dict of current fighter state for debugging/UI"""
        return {
            'name': self.fighter_name,
            'state': self.state,
            'health': self.health,
            'max_health': self.max_health,
            'position': (round(self.x, 2), round(self.y, 2)),
            'grounded': self.grounded,
            'attack': self.attack_name,
            'combo': self.combo_count,
            'combo_hit_index': getattr(self, 'combo_hit_index', 0),
            'last_animation': getattr(self, 'last_animation', None),
            'heavy_cd': getattr(self, 'heavy_cooldown_timer', 0.0),
            'launcher_cd': getattr(self, 'launcher_cooldown_timer', 0.0)
        }

    def clamp_to_arena(self, arena_width):
        """Keep fighter within arena boundaries and apply a small elastic bounce when hitting walls.

        Behavior:
        - Compute effective visible arena based on camera frustum so fighters cannot leave the screen.
        - If fighter moves beyond the effective arena, set position to boundary and apply a reduced inverted velocity to knockback_velocity.
        """
        import time as ursina_time
        import math
        try:
            from ursina import camera, window
        except Exception:
            camera = None
            window = None

        # Default numeric bounds from arena_width
        half = arena_width / 2

        # If camera is available and perspective, compute visible half-width at fighter z
        visible_half = None
        try:
            if camera is not None and not getattr(camera, 'orthographic', False):
                # distance from camera to fighter on Z axis
                cam_z = getattr(camera, 'position', (0, 0, -18))[2]
                distance = abs(cam_z - getattr(self, 'z', 0))
                # camera.fov is horizontal fov in degrees
                fov = getattr(camera, 'fov', 40)
                visible_half = math.tan(math.radians(fov) / 2) * distance
            elif camera is not None and getattr(camera, 'orthographic', False):
                # orthographic: use camera.orthographic film size if available
                # fall back to arena half if not
                try:
                    visible_half = getattr(camera, 'fov', None) or (half)
                except Exception:
                    visible_half = None
        except Exception:
            visible_half = None

        # Choose effective half width conservatively: min of arena and visible
        if visible_half is not None and visible_half > 0:
            effective_half = min(half, visible_half)
        else:
            effective_half = half

        # tighter margins so fighters do not visually touch the edge
        margin = 0.5
        min_x = -effective_half + margin
        max_x = effective_half - margin

        # If we have no previous position recorded, just clamp
        prev_x = getattr(self, 'prev_x', self.x)

        # approximate horizontal velocity (units/sec) using prev_x and time.dt
        dt = ursina_time.dt if getattr(ursina_time, 'dt', 0) > 1e-6 else 1e-6
        vx = (self.x - prev_x) / dt

        bounce_factor = 0.45

        # If outside left boundary
        if self.x < min_x:
            self.x = min_x
            # Apply bounce: invert and reduce speed
            self.knockback_velocity = -vx * bounce_factor

        # If outside right boundary
        if self.x > max_x:
            self.x = max_x
            self.knockback_velocity = -vx * bounce_factor

        # Ensure we don't slowly drift outside due to tiny epsilons
        self.x = max(min_x, min(max_x, self.x))

        # store prev_x for next frame (will be updated at frame start in main.update)
        self.prev_x = self.x
