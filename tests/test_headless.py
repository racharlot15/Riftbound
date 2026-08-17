from ursina import Ursina
import Riftbound.main as main


def test_headless_initialize_and_step():
    # Start Ursina in headless mode and run a few steps to catch runtime errors
    app = Ursina(window_type='none', development_mode=False, editor_ui_enabled=False)

    try:
        main.initialize_game()

        # Step the engine a few frames
        for _ in range(3):
            app.step()

        # Basic smoke check: player and enemy should exist
        assert main.player is not None
        assert main.enemy is not None

    finally:
        # Ensure cleanup and terminate Ursina instance
        try:
            main.cleanup()
        except Exception:
            pass
