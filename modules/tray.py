import os
import threading
from typing import Any, Dict

import pyperclip
import pystray
from PIL import Image, ImageDraw

from modules.audio_manager import get_input_devices, get_default_device_id, set_input_device, create_device_identifier
from modules import transcribe

def create_tray_icon(icon_path: str) -> Image.Image:
    """Create tray icon from file path"""
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(current_dir, icon_path)
    return Image.open(icon_path)

def create_copy_menu(app):
    """Creates dynamic menu of recent transcriptions"""
    def make_copy_handler(text):
        return lambda icon, item: pyperclip.copy(text)

    return [
        pystray.MenuItem(
            app.history.get_preview(text),
            make_copy_handler(text)
        )
        for text in app.history.get_recent()
    ]

def create_microphone_menu(app):
    """Creates dynamic menu of available microphones"""
    devices = sorted(get_input_devices(), key=lambda d: d['name'].lower())
    current_identifier = app.settings.get('selected_microphone')
    favorite_identifiers = app.settings.get('favorite_microphones')
    default_device_id = get_default_device_id()

    def make_mic_handler(device: Dict[str, any]):
        def handler(icon, item):
            identifier = create_device_identifier(device)._asdict()
            app.settings.set('selected_microphone', identifier)
            set_input_device(device['id'])
            # Log the device change
            app.logger.info(f"Microphone changed to: {device['name']} (ID: {device['id']}, Channels: {device['max_input_channels']}, Sample Rate: {device['default_samplerate']} Hz)")
            # Refresh menu to update checkmark
            app.update_icon_menu()
        return handler

    def make_favorite_handler(device: Dict[str, any]):
        def handler(icon, item):
            identifier = create_device_identifier(device)._asdict()
            favorites = app.settings.get('favorite_microphones')

            if identifier in favorites:
                favorites.remove(identifier)
            else:
                favorites.append(identifier)

            app.settings.set('favorite_microphones', favorites)
            app.update_icon_menu()
        return handler

    # Create menu items
    select_items = []
    favorite_items = []

    for device in devices:
        identifier = create_device_identifier(device)._asdict()
        is_favorite = identifier in favorite_identifiers
        is_selected = identifier == current_identifier
        is_default = device['id'] == default_device_id

        star_prefix = "💫 " if is_favorite else "    "
        default_prefix = "🎙️ " if is_default else "    "
        combined_prefix = default_prefix if is_default else star_prefix

        select_items.append(
            pystray.MenuItem(
                f"{combined_prefix}{device['name']}",
                make_mic_handler(device),
                checked=lambda item, dev=device: create_device_identifier(dev)._asdict() == current_identifier
            )
        )

        favorite_items.append(
            pystray.MenuItem(
                f"{default_prefix}{device['name']}",
                make_favorite_handler(device),
                checked=lambda item, dev=device: create_device_identifier(dev)._asdict() in favorite_identifiers
            )
        )

    menu_items = [
        pystray.MenuItem(
            'Select Device',
            pystray.Menu(*select_items)
        ),
        pystray.MenuItem(
            'Manage Favorites',
            pystray.Menu(*favorite_items)
        ),
        pystray.MenuItem('Refresh Devices', lambda icon, item: app.refresh_microphones())
    ]

    return menu_items

def create_stt_provider_menu(app):
    """Creates menu for STT provider and model selection"""
    current_provider = transcribe.get_current_provider()
    available_providers = transcribe.get_available_providers()

    def make_provider_handler(provider_name: str):
        def handler(icon, item):
            try:
                transcribe.set_stt_provider(provider_name)
                app.update_icon_menu()
            except Exception as e:
                print(f"Error changing STT provider: {e}")
        return handler

    def make_model_handler(model: str):
        def handler(icon, item):
            app.settings.set('openai_stt_model', model)
            app.update_icon_menu()
        return handler

    # Create provider selection items
    provider_items = []
    for provider in available_providers:
        provider_items.append(
            pystray.MenuItem(
                provider['display_name'],
                make_provider_handler(provider['name']),
                checked=lambda item, p=provider: p['name'] == current_provider
            )
        )

    # Create model selection items (only for OpenAI currently)
    model_items = []
    if current_provider == 'openai':
        current_model = app.settings.get('openai_stt_model')
        openai_provider = next((p for p in available_providers if p['name'] == 'openai'), None)
        if openai_provider:
            for model in openai_provider['models']:
                display_name = {
                    'gpt-4o-transcribe': 'GPT-4o (Best)',
                    'gpt-4o-mini-transcribe': 'GPT-4o Mini',
                    'whisper-1': 'Whisper (Legacy)',
                }.get(model, model)

                model_items.append(
                    pystray.MenuItem(
                        display_name,
                        make_model_handler(model),
                        checked=lambda item, m=model: m == current_model
                    )
                )

    menu_items = []

    # Add provider selection
    menu_items.append(
        pystray.MenuItem(
            'Provider',
            pystray.Menu(*provider_items) if provider_items else pystray.Menu(
                pystray.MenuItem('No providers available', None, enabled=False)
            )
        )
    )

    # Add model selection (only shown for OpenAI)
    if model_items:
        menu_items.append(
            pystray.MenuItem(
                'OpenAI Model',
                pystray.Menu(*model_items)
            )
        )

    return menu_items

def setup_tray_icon(app):
    # Create a single icon instance
    icon = pystray.Icon(
        'Voice Typing',
        icon=create_tray_icon('assets/microphone-blue.png')
    )

    def update_icon(emoji_prefix: str, tooltip_text: str) -> None:
        """Update both the tray icon and tooltip"""
        try:
            # Update icon image from current status config
            icon.icon = create_tray_icon(app.status_manager.current_config.tray_icon_file)
            # Update tooltip with status message
            icon.title = f"{emoji_prefix} {tooltip_text}"
        except Exception as e:
            print(f"Error updating tray icon: {e}")

    # Store the update function in the app
    app.update_tray_tooltip = update_icon

    def copy_latest_transcription(icon, item) -> None:
        """
        Copies the most recent transcription to clipboard if available.
        """
        recent_texts = app.history.get_recent()
        if recent_texts:
            pyperclip.copy(recent_texts[0])

    def change_ui_position(new_pos: str):
        """Update settings and move indicator to new corner."""
        app.settings.set('ui_indicator_position', new_pos)
        app.ui_feedback.set_position(new_pos)
        # Refresh menu to update checkmarks
        if hasattr(app, 'update_icon_menu') and app.update_icon_menu:
            app.update_icon_menu()

    def change_ui_size(new_size: str):
        """Update settings and resize indicator."""
        app.settings.set('ui_indicator_size', new_size)
        app.ui_feedback.set_size(new_size)
        # Refresh menu to update checkmarks
        if hasattr(app, 'update_icon_menu') and app.update_icon_menu:
            app.update_icon_menu()

    def on_exit(icon, item):
        """Log exit and close the application."""
        app.logger.info("Application exiting.")
        icon.stop()
        # Ensure clean exit of the application
        os._exit(0)

    def get_menu():
        # Dynamic menu that updates when called
        copy_menu = create_copy_menu(app)
        microphone_menu = create_microphone_menu(app)
        stt_menu = create_stt_provider_menu(app)  # Add STT provider menu

        return pystray.Menu(
            # ↓ This is now the default item, triggered on left-click.
            pystray.MenuItem(
                'Copy Last Transcription',
                copy_latest_transcription,
                default=True
            ),
            pystray.MenuItem(
                '🔄 Retry Last Transcription',
                lambda icon, item: app.retry_transcription(),
                enabled=lambda item: app.last_recording is not None
            ),
            pystray.MenuItem(
                'Recent Transcriptions',
                pystray.Menu(*copy_menu) if copy_menu else pystray.Menu(
                    pystray.MenuItem('No transcriptions yet', None, enabled=False)
                ),
                enabled=bool(copy_menu)
            ),
            pystray.MenuItem(
                'Microphone',
                pystray.Menu(*microphone_menu)
            ),
            pystray.MenuItem(
                'Settings',
                pystray.Menu(
                    pystray.MenuItem(
                        'Continuous Capture',
                        lambda icon, item: None,
                        checked=lambda item: app.settings.get('continuous_capture')
                    ),
                    pystray.MenuItem(
                        'Clean Transcription',
                        lambda icon, item: app.toggle_clean_transcription(),
                        checked=lambda item: app.settings.get('clean_transcription')
                    ),
                    pystray.MenuItem(
                        'Lowercase Short Transcriptions',
                        lambda icon, item: app.toggle_lowercase_short(),
                        checked=lambda item: app.settings.get('lowercase_short_transcriptions')
                    ),
                    pystray.MenuItem(
                        'Silent-Start Timeout',
                        lambda icon, item: app.toggle_silence_detection(),
                        checked=lambda item: app.settings.get('silent_start_timeout') is not None
                    ),
                    pystray.MenuItem(
                        'Change Cursor on Recording',
                        lambda icon, item: app.toggle_cursor_change(),
                        checked=lambda item: app.settings.get('change_cursor_on_recording')
                    ),
                    pystray.MenuItem(
                        'Smart Capture',
                        lambda icon, item: None,
                        enabled=False
                    ),
                    pystray.MenuItem(
                        'Recording Indicator',
                        pystray.Menu(
                            # Size options
                            pystray.MenuItem(
                                'Normal Size',
                                lambda icon, item: change_ui_size('normal'),
                                checked=lambda item: app.settings.get('ui_indicator_size') == 'normal'
                            ),
                            pystray.MenuItem(
                                'Mini Size',
                                lambda icon, item: change_ui_size('mini'),
                                checked=lambda item: app.settings.get('ui_indicator_size') == 'mini'
                            ),
                            pystray.Menu.SEPARATOR,
                            # Position options
                            pystray.MenuItem(
                                'Top Left',
                                lambda icon, item: change_ui_position('top-left'),
                                checked=lambda item: app.settings.get('ui_indicator_position') == 'top-left'
                            ),
                            pystray.MenuItem(
                                'Top Center',
                                lambda icon, item: change_ui_position('top-center'),
                                checked=lambda item: app.settings.get('ui_indicator_position') == 'top-center'
                            ),
                            pystray.MenuItem(
                                'Top Right',
                                lambda icon, item: change_ui_position('top-right'),
                                checked=lambda item: app.settings.get('ui_indicator_position') == 'top-right'
                            ),
                            pystray.MenuItem(
                                'Bottom Left',
                                lambda icon, item: change_ui_position('bottom-left'),
                                checked=lambda item: app.settings.get('ui_indicator_position') == 'bottom-left'
                            ),
                            pystray.MenuItem(
                                'Bottom Center',
                                lambda icon, item: change_ui_position('bottom-center'),
                                checked=lambda item: app.settings.get('ui_indicator_position') == 'bottom-center'
                            ),
                            pystray.MenuItem(
                                'Bottom Right',
                                lambda icon, item: change_ui_position('bottom-right'),
                                checked=lambda item: app.settings.get('ui_indicator_position') == 'bottom-right'
                            ),
                        )
                    ),
                    pystray.MenuItem(  # Add STT submenu
                        'Speech-to-Text',
                        pystray.Menu(*stt_menu)
                    )
                )
            ),
            pystray.MenuItem('Restart', lambda icon, item: app.restart_app()),
            pystray.MenuItem('Exit', on_exit)
        )

    # Initial menu setup
    icon.menu = get_menu()
    # Store the update function in the app to call it from elsewhere
    app.update_icon_menu = lambda: setattr(icon, 'menu', get_menu()) # Updates the tray icon's menu

    # Start the icon's event loop in its own thread
    threading.Thread(target=icon.run).start()