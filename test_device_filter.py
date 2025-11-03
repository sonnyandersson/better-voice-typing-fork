"""Test the improved device filtering logic"""
import sys
sys.path.insert(0, '.')

from modules.audio_manager import get_input_devices, _get_host_api_priority
import sounddevice as sd

print("=" * 80)
print("IMPROVED DEVICE LIST (what the app will show in tray)")
print("=" * 80)

devices = get_input_devices()
print(f"\nTotal devices after filtering: {len(devices)}\n")

for device in sorted(devices, key=lambda d: d['name'].lower()):
    api_info = sd.query_hostapis(device['hostapi'])
    api_name = api_info['name']
    priority = _get_host_api_priority(device['hostapi'])
    
    print(f"ID: {device['id']:>3}  Priority: {priority}  API: {api_name:>20}")
    print(f"     Name: {device['name']}")
    print(f"     Channels: {device['max_input_channels']}  Sample Rate: {device['default_samplerate']} Hz")
    print()

print("=" * 80)
print("FILTERED OUT:")
print("=" * 80)
print("✓ 'Input (...)' virtual processing endpoints")
print("✓ 'Microphone 1/2/3 (...)' WDM-KS raw channels")
print("✓ 'Stereo Mix', 'System Virtual Line', loopback devices")
print("✓ Duplicate variants (kept best: WASAPI > DirectSound > MME > WDM-KS)")
