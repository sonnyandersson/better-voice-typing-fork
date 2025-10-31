# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Windows desktop voice typing application built with Python 3.10-3.12. It provides superior transcription accuracy compared to Windows built-in voice typing (Win+H) by leveraging OpenAI's GPT-4o-transcribe and Whisper models. The app uses Caps Lock or middle mouse button (scroll wheel click) as the recording toggle and allows navigation between windows while recording.

**Core Technologies:**
- Python tkinter (minimal UI + system tray)
- pynput (keyboard shortcuts, mouse listener)
- sounddevice/soundfile (audio recording)
- OpenAI API (speech-to-text, optional text cleaning)
- LiteLLM (multi-model routing for text cleaning)

## Development Setup

### Initial Setup
```bash
# Ensure Python 3.10-3.12 is installed
python --version

# Create virtual environment using uv
uv venv --python ">=3.10,<3.13"

# Activate environment
.venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Create .env file from example (if .env.example exists, otherwise create manually)
# Add OPENAI_API_KEY and optionally ANTHROPIC_API_KEY
```

### Running the App
```bash
# Standard run
.\.venv\Scripts\python.exe .\voice_typing.pyw

# Debug mode (shows console logs)
.\.venv\Scripts\python.exe .\voice_typing.pyw --debug
```

### Testing
```bash
# Test keyboard functionality
python tests\keyboard_test.py

# Verify installation
python tests\test_installation.py
```

## Architecture

### Core Application Flow (voice_typing.pyw)

The `VoiceTypingApp` class is the main orchestrator that:
1. Initializes settings, logging, UI, recorder, and tray icon
2. Sets up keyboard listener (Caps Lock toggle via pynput's win32_event_filter)
3. Manages recording → processing → transcription → insertion lifecycle
4. Handles status updates across UI and tray components

**Key State Management:**
- `StatusManager` (modules/status_manager.py) - Centralized app status (IDLE, RECORDING, PROCESSING, TRANSCRIBING, CLEANING, ERROR) with callbacks to update UI and tray
- `self.cancel_flag` - Threading event to cancel ongoing processing
- `self.last_recording` - Path to last audio file for retry functionality

**Threading Model:**
- Main thread: tkinter UI event loop
- Background threads: Audio recording (`recorder.py`), audio processing (`_process_audio_thread`)
- All UI updates happen on main thread via callbacks

### Multi-Provider STT System (Strategy Pattern)

The app uses Strategy + Factory patterns to support multiple speech-to-text providers:

**Entry Point:** `modules/transcribe.py`
- `transcribe_audio(filename, language)` - Main function called by app
- `_get_transcriber(provider_name)` - Factory that instantiates provider classes
- Reads `stt_provider` from settings to route to correct implementation

**Provider Implementations:** `services/` directory
- `openai_stt.py` - `OpenAITranscriber` class supporting Whisper and GPT-4o models
- `google_stt.py` - `GoogleTranscriber` class (placeholder implementation)
- Each implements: `transcribe(audio_data)` and `update_language(language)`

**Adding New Providers:**
1. Create `services/new_provider_stt.py` with a class implementing `transcribe()` and `update_language()`
2. Add provider case to `_get_transcriber()` factory in `modules/transcribe.py`
3. Add provider config to `Settings.default_settings` in `modules/settings.py`
4. Update tray menu in `modules/tray.py` if needed for provider selection

### Audio Recording (modules/recorder.py)

`AudioRecorder` class handles:
- Real-time audio capture via sounddevice (16-bit WAV, 22.05kHz, mono)
- Audio level calculation with smoothing (for UI feedback)
- Silent-start timeout detection (auto-cancels if no sound in first N seconds)
- Post-recording analysis (duration check, silence threshold validation)

**Key Settings:**
- `SILENCE_THRESHOLD` - RMS threshold for silence detection (default: 0.01 = -40dB)
- `MIN_DURATION` - Minimum valid recording length (1.0s)
- `silent_start_timeout` - Auto-cancel if silent at start (default: 4.0s, null to disable)

**File Size Limit:** ~2.6MB per 60s due to OpenAI's 25MB file upload limit (~10min max recording)

### Settings System (modules/settings.py)

`Settings` class manages configuration via `settings.json`:
- Loads defaults, merges with saved settings
- Runs migrations on load (`_migrate_device_settings`, `_migrate_silence_timeout`)
- All settings saved via `.set()` method

**Important Settings:**
- `stt_provider` - 'openai' or 'google'
- `openai_stt_model` - 'gpt-4o-transcribe' (recommended), 'gpt-4o-mini-transcribe', 'whisper-1'
- `clean_transcription` - Enable LLM post-processing (default: false)
- `llm_model` - LiteLLM model string for cleaning (e.g., "openai/gpt-4o-mini")
- `selected_microphone` - DeviceIdentifier dict (migrated from int IDs)
- `ui_indicator_position` - 'top-right', 'top-left', 'bottom-right', 'bottom-left', 'top-center', 'bottom-center'
- `ui_indicator_size` - 'normal', 'mini'
- `change_cursor_on_recording` - Change Windows cursor during recording (default: true, may not work in Electron apps)

### UI Components

**Recording Indicator (modules/ui.py):**
- `UIFeedback` class - Floating tkinter window with audio level bar
- Positioning system based on primary monitor geometry
- Click handling for cancel operations
- Warning/error display with auto-dismiss timers
- Retry functionality for failed transcriptions

**System Tray (modules/tray.py):**
- `setup_tray_icon()` - Creates pystray icon with dynamic menu
- Microphone selection with favorites (star icons)
- History submenu with recent transcriptions
- Settings toggles (clean transcription, silence detection)
- Restart functionality

### Known Quirks & Workarounds

**GPT-4o-transcribe Cutoff Issue:**
- OpenAI model occasionally truncates end of transcription
- Workaround in `services/openai_stt.py`: `_pad_audio_with_noise()` adds 1.5s of quiet brown noise to prevent cutoff
- Users can retry transcription from tray menu if issue occurs

**Microphone Device Persistence:**
- Device IDs can change between sessions (USB reconnects, etc.)
- Solution: `DeviceIdentifier` namedtuple (name, channels, sample_rate) with migration logic in `settings.py`
- `audio_manager.py` has `find_device_by_identifier()` to relocate devices

**Caps Lock State Management:**
- win32_event_filter intercepts Caps Lock before OS
- Ctrl+Caps Lock bypasses recording to allow normal Caps Lock toggle
- Uses `listener.suppress_event()` to prevent OS toggle when recording

**Mouse Cursor Changes (modules/cursor_manager.py):**
- Windows cursor changes to "AppStarting" (arrow with hourglass) during recording
- Uses Windows API (`SetSystemCursor`) for system-wide cursor changes
- Automatic restoration on recording stop, error, or app exit
- Known limitation: Does not work in Electron-based apps (VS Code, Discord, etc.) as they manage their own cursors
- Can be toggled on/off via Settings menu in tray icon

## Development Guidelines

**From .cursorrules:**
- Use type hints for all function parameters and return values
- Avoid blocking operations (time.sleep) - use async/event-driven patterns
- Preserve nearby comments (NOTE:, IMPORTANT:) when editing code
- Prefer functional programming over OOP where applicable

**Versioning & Releases:**
- When committing significant changes, update `version.txt` and `CHANGELOG.json`
- README.md has "## Changelog" section - update with emoji prefixes for visibility

**Error Handling:**
- All errors logged to `C:\Users\{Username}\Documents\VoiceTyping\logs`
- Log retention controlled by `log_retention_days` setting (default: 60)
- temp_audio.wav kept for debugging failed transcriptions

**API Timeouts:**
- OpenAI client configured with 60s total timeout, 10s connect timeout (services/openai_stt.py:78)
- LLM cleaning timeout configurable via `cleaning_timeout` setting (default: 10s)

## Common Patterns

### Adding a New Setting
1. Add to `Settings.default_settings` dict in `modules/settings.py`
2. Add migration if needed in `Settings._run_migrations()`
3. Access via `self.settings.get('setting_name')` in app
4. Update tray menu or UI if user-configurable

### Adding Status States
1. Add enum to `AppStatus` in `modules/status_manager.py`
2. Add status config to `STATUS_CONFIGS` dict with icon/tooltip
3. Use `self.status_manager.set_status(AppStatus.NEW_STATE, optional_message)`

### Adding Tray Menu Items
1. Edit `create_tray_menu()` in `modules/tray.py`
2. Dynamic menus: `create_copy_menu()` (history) or `create_microphone_menu()` (devices)
3. Use lambda handlers or `make_handler()` functions to capture state

## File Locations

**User Data:**
- Logs: `C:\Users\{Username}\Documents\VoiceTyping\logs\`
- Settings: `settings.json` in project root (created on first run)
- Config: `.env` file for API keys (not committed)

**Project Structure:**
```
modules/          # Core application modules
  ├── audio_manager.py    # Device selection and management
  ├── clean_text.py       # LLM post-processing
  ├── history.py          # Transcription history tracking
  ├── logger.py           # Logging setup with retention
  ├── recorder.py         # Audio recording engine
  ├── screen_utils.py     # DPI awareness, monitor geometry
  ├── settings.py         # Configuration management
  ├── status_manager.py   # App state coordination
  ├── transcribe.py       # STT routing (factory)
  ├── tray.py            # System tray integration
  └── ui.py              # Recording indicator UI

services/         # STT provider implementations
  ├── openai_stt.py      # OpenAI Whisper/GPT-4o
  └── google_stt.py      # Google Cloud (placeholder)

tests/            # Test utilities
docs/             # Architecture documentation
```

## Troubleshooting

**No transcription produced:**
- Check microphone audio level (might be below `silence_threshold`)
- View `temp_audio.wav` and logs in `Documents\VoiceTyping\logs\`
- Adjust `silence_threshold` in settings.json (lower = more sensitive)

**Transcription cutoff:**
- Known issue with gpt-4o-transcribe model
- Use "Retry Last Transcription" from tray menu
- Brown noise padding workaround is active by default

**Keyboard shortcut not responding:**
- Use "Restart" from tray menu
- Check if app is running (tray icon visible)
- Ensure Caps Lock isn't locked by holding Ctrl while toggling

## References

- OpenAI Audio API: https://platform.openai.com/docs/guides/audio
- LiteLLM Providers: https://docs.litellm.ai/docs/providers
- STT Architecture Details: `docs/stt-upgrade-spec.md`
- Troubleshooting Guide: `TROUBLESHOOTING.md`
