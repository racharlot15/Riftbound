"""
Riftbound Menus Module
Main menu, pause menu, and character selection screens
"""

from ursina import Entity, Text, camera, color
try:
    from engine.audio import sound_manager
except Exception:
    sound_manager = None


class MainMenu(Entity):
    """
    Main game menu displayed at startup.
    Options: Start Game, Settings, Quit
    """

    def __init__(self):
        super().__init__(
            parent=camera.ui
        )
        
        self.visible = True
        self.selection = 0
        self.options = ['START', 'SETTINGS', 'QUIT']
        self.confirmed = False
        
        # Title
        self.title = Text(
            text='RIFTBOUND',
            origin=(0, 0),
            scale=3,
            y=0.3,
            color=color.white
        )
        
        # Subtitle
        self.subtitle = Text(
            text='A Fighting Game',
            origin=(0, 0),
            scale=1.2,
            y=0.15,
            color=color.gray
        )
        
        # Menu options
        self.menu_texts = []
        for i, option in enumerate(self.options):
            txt = Text(
                text=f'> {option} <' if i == 0 else f'  {option}  ',
                origin=(0, 0),
                scale=1.5,
                y= -0.05 - (i * 0.08),
                color=color.yellow if i == 0 else color.white
            )
            self.menu_texts.append(txt)
        
        # Instructions
        self.instructions = Text(
            text='UP/DOWN: Navigate | ENTER/A: Select',
            origin=(0, 0),
            scale=0.8,
            y=-0.35,
            color=color.light_gray
        )
        
        print("✓ Main menu created")

    def navigate(self, direction):
        """Move selection up or down"""
        old_selection = self.selection
        self.selection = (self.selection + direction) % len(self.options)
        
        # Update visual appearance
        self.menu_texts[old_selection].text = f"  {self.options[old_selection]}  "
        self.menu_texts[old_selection].color = color.white
        
        self.menu_texts[self.selection].text = f"> {self.options[self.selection]} <"
        self.menu_texts[self.selection].color = color.yellow
        
        # Play menu move sound
        try:
            if sound_manager:
                sound_manager.play('menu_move')
        except Exception:
            pass

    def confirm(self):
        """Confirm current selection"""
        self.confirmed = True
        # Play menu confirm sound
        try:
            if sound_manager:
                sound_manager.play('menu_confirm')
        except Exception:
            pass
        return self.options[self.selection]

    def get_selection(self):
        """Get currently selected option name"""
        return self.options[self.selection]

    def hide_menu(self):
        """Hide the main menu"""
        self.visible = False
        self.title.disable()
        self.subtitle.disable()
        self.instructions.disable()
        for txt in self.menu_texts:
            txt.disable()

    def show_menu(self):
        """Show the main menu"""
        self.visible = True
        self.title.enable()
        self.subtitle.enable()
        self.instructions.enable()
        for txt in self.menu_texts:
            txt.enable()


class CharacterSelectScreen(Entity):
    """
    Character selection screen.
    Allows players to choose their fighter.
    """

    def __init__(self, character_registry):
        """
        Create character select screen.
        
        Args:
            character_registry: Dict of available characters from characters module
        """
        super().__init__(
            parent=camera.ui
        )
        
        self.registry = character_registry
        self.characters = list(character_registry.keys())
        self.p1_selection = 0
        self.p2_selection = 1
        self.selecting_player = 1  # Which player is selecting
        self.confirmed = False
        
        # Title
        self.title = Text(
            text='SELECT YOUR FIGHTER',
            origin=(0, 0),
            scale=2,
            y=0.4,
            color=color.white
        )
        
        # Player labels
        self.p1_label = Text(
            text='PLAYER 1',
            origin=(0, 0),
            scale=1.2,
            y=0.25,
            x=-0.35,
            color=color.azure
        )
        
        self.p2_label = Text(
            text='PLAYER 2 / CPU',
            origin=(0, 0),
            scale=1.2,
            y=0.25,
            x=0.35,
            color=color.red
        )
        
        # Character preview boxes (simplified as text for now)
        self.p1_char_text = Text(
            text='',
            origin=(0, 0),
            scale=1.5,
            y=0.05,
            x=-0.35
        )
        
        self.p2_char_text = Text(
            text='',
            origin=(0, 0),
            scale=1.5,
            y=0.05,
            x=0.35
        )
        
        # Character description
        self.description = Text(
            text='',
            origin=(0, 0),
            scale=0.9,
            y=-0.15,
            color=color.light_gray
        )
        
        # Instructions
        self.instructions = Text(
            text='LEFT/RIGHT: Change | A: Confirm P1 | START: Begin',
            origin=(0, 0),
            scale=0.7,
            y=-0.35,
            color=color.gray
        )
        
        # Initial display update
        self._update_display()
        
        print(f"✓ Character select created with {len(self.characters)} fighters")

    def _update_display(self):
        """Update character preview displays"""
        p1_key = self.characters[self.p1_selection]
        p2_key = self.characters[self.p2_selection]
        
        p1_data = self.registry[p1_key]
        p2_data = self.registry[p2_key]
        
        self.p1_char_text.text = p1_data['name']
        self.p1_char_text.color = color.rgb(*p1_data['color'])
        
        self.p2_char_text.text = p2_data['name']
        self.p2_char_text.color = color.rgb(*p2_data['color'])
        
        # Show description for currently selecting player
        active_key = p1_key if self.selecting_player == 1 else p2_key
        active_data = self.registry[active_key]
        self.description.text = active_data['description']

    def navigate_p1(self, direction):
        """Change P1 character selection"""
        self.p1_selection = (self.p1_selection + direction) % len(self.characters)
        self.selecting_player = 1
        self._update_display()
        try:
            if sound_manager:
                sound_manager.play('menu_move')
        except Exception:
            pass

    def navigate_p2(self, direction):
        """Change P2 character selection"""
        self.p2_selection = (self.p2_selection + direction) % len(self.characters)
        self.selecting_player = 2
        self._update_display()
        try:
            if sound_manager:
                sound_manager.play('menu_move')
        except Exception:
            pass

    def confirm_selection(self, player=None):
        """Confirm selection for specified player (or current)"""
        if player:
            self.selecting_player = player
        
        # Play confirm sound
        try:
            if sound_manager:
                sound_manager.play('menu_confirm')
        except Exception:
            pass

        # Toggle between players or finalize
        if self.selecting_player == 1:
            self.selecting_player = 2
            self._update_display()
            return None  # Not finalized yet
        else:
            self.confirmed = True
            return {
                'p1': self.characters[self.p1_selection],
                'p2': self.characters[self.p2_selection]
            }

    def get_selections(self):
        """Get selected character keys"""
        return {
            'p1': self.characters[self.p1_selection],
            'p2': self.characters[self.p2_selection]
        }

    def hide_screen(self):
        """Hide character select"""
        self.title.disable()
        self.p1_label.disable()
        self.p2_label.disable()
        self.p1_char_text.disable()
        self.p2_char_text.disable()
        self.description.disable()
        self.instructions.disable()


class PauseMenu(Entity):
    """
    In-game pause menu.
    Options: Resume, Restart, Quit to Menu
    """

    def __init__(self):
        super().__init__(
            parent=camera.ui
        )
        
        self.visible = False
        self.paused = False
        self.selection = 0
        self.options = ['RESUME', 'RESTART', 'QUIT TO MENU']
        
        # Background overlay (darkens game)
        self.overlay = Entity(
            parent=camera.ui,
            model='quad',
            scale=(2, 1),
            color=color.rgba(0, 0, 0, 150),
            z=1
        )
        self.overlay.disable()
        
        # Pause text
        self.title = Text(
            text='PAUSED',
            origin=(0, 0),
            scale=2.5,
            y=0.15,
            color=color.white,
            z=2
        )
        self.title.disable()
        
        # Menu options
        self.menu_texts = []
        for i, option in enumerate(self.options):
            txt = Text(
                text=f'> {option} <' if i == 0 else f'  {option}  ',
                origin=(0, 0),
                scale=1.3,
                y=-0.05 - (i * 0.07),
                color=color.yellow if i == 0 else color.white,
                z=2
            )
            txt.disable()
            self.menu_texts.append(txt)
        
        print("✓ Pause menu created")

    def toggle_pause(self):
        """Toggle pause state on/off"""
        self.paused = not self.paused
        self.visible = self.paused
        
        if self.paused:
            self.overlay.enable()
            self.title.enable()
            for txt in self.menu_texts:
                txt.enable()
        else:
            self.overlay.disable()
            self.title.disable()
            for txt in self.menu_texts:
                txt.disable()
        
        return self.paused

    def navigate(self, direction):
        """Move through pause options (only when paused)"""
        if not self.paused:
            return
        
        old = self.selection
        self.selection = (self.selection + direction) % len(self.options)
        
        self.menu_texts[old].text = f"  {self.options[old]}  "
        self.menu_texts[old].color = color.white
        
        self.menu_texts[self.selection].text = f"> {self.options[self.selection]} <"
        self.menu_texts[self.selection].color = color.yellow
        
        try:
            if sound_manager:
                sound_manager.play('menu_move')
        except Exception:
            pass

    def confirm(self):
        """Get confirmed option"""
        if not self.paused:
            return None
        try:
            if sound_manager:
                sound_manager.play('menu_confirm')
        except Exception:
            pass
        return self.options[self.selection]


class DebugHUD(Entity):
    """
    Heads-up display showing debug information.
    Shows states, positions, and other useful data.
    """

    def __init__(self):
        super().__init__(
            parent=camera.ui
        )
        
        # Main debug text (top-left)
        self.debug_text = Text(
            text='',
            x=-0.85,
            y=0.35,
            scale=0.75,
            color=color.white
        )
        
        # Combo counter (center-top)
        self.combo_text = Text(
            text='',
            x=-0.1,
            y=0.25,
            scale=1.5,
            color=color.yellow
        )
        
        # FPS counter (top-right)
        self.fps_text = Text(
            text='',
            x=0.75,
            y=0.45,
            scale=0.6,
            color=color.green
        )
        
        print("✓ Debug HUD created")

    def update_debug(self, player_info, enemy_info):
        """Update debug display with fighter information"""
        self.debug_text.text = (
            f"STATE: {player_info['state']}\n"
            f"ATTACK: {player_info.get('attack', 'None')}\n"
            f"LAST ANIM: {player_info.get('last_animation', 'N/A')}\n"
            f"HEAVY CD: {player_info.get('heavy_cd', 0.0):.2f}s | LAUNCHER CD: {player_info.get('launcher_cd', 0.0):.2f}s\n"
            f"HP: {player_info['health']}/{player_info['max_health']}\n"
            f"ENEMY HP: {enemy_info['health']}/{enemy_info['max_health']}\n"
            f"POS: ({player_info['position'][0]}, {player_info['position'][1]})"
        )

    def update_combo(self, combo_count):
        """Update combo counter display"""
        if combo_count > 1:
            self.combo_text.text = f"{combo_count} HIT COMBO!"
        else:
            self.combo_text.text = ""

    def update_fps(self, fps):
        """Update FPS counter"""
        self.fps_text.text = f"{int(fps)} FPS"

    def toggle_visibility(self):
        """Toggle debug HUD visibility"""
        self.debug_text.visible = not self.debug_text.visible
        self.fps_text.visible = not self.fps_text.visible
