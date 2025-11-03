import re
from typing import List, Dict, Optional, NamedTuple
import sounddevice as sd

class DeviceIdentifier(NamedTuple):
    """Unique identifier for an audio device that persists across sessions"""
    name: str
    channels: int
    default_samplerate: float

def create_device_identifier(device: Dict[str, any]) -> DeviceIdentifier:
    """Creates a persistent identifier for a device"""
    return DeviceIdentifier(
        name=device['name'],
        channels=device['max_input_channels'],  # Match the key used in device info
        default_samplerate=device['default_samplerate']
    )

def find_device_by_identifier(identifier: DeviceIdentifier) -> Optional[Dict[str, any]]:
    """
    Finds the best matching device for a saved identifier.
    Prioritizes WASAPI variants for reliability.
    """
    devices = get_input_devices()

    # First try exact match
    for device in devices:
        if create_device_identifier(device) == identifier:
            return device

    # Fall back to name match, preferring WASAPI variants
    normalized_target = _normalize_device_name(identifier.name)
    matching_devices = []
    
    for d in devices:
        normalized_name = _normalize_device_name(d['name'])
        # Match either exact name or normalized name
        if d['name'] == identifier.name or normalized_name == normalized_target:
            matching_devices.append(d)
    
    if not matching_devices:
        return None
    
    # Sort by: API priority (WASAPI first) > sample rate > channels
    def sort_key(d):
        return (
            _get_host_api_priority(d['hostapi']),
            d['default_samplerate'],
            d['max_input_channels']
        )
    
    return max(matching_devices, key=sort_key)

def get_device_by_id(device_id: int) -> Optional[Dict[str, any]]:
    """Gets device info by ID, returns None if device not found"""
    try:
        device = sd.query_devices(device_id)
        if device['max_input_channels'] > 0:
            return {
                'id': device_id,
                'name': device['name'],
                'max_input_channels': device['max_input_channels'],
                'hostapi': device['hostapi'],
                'default_samplerate': device['default_samplerate']
            }
        return None
    except:
        return None

def _normalize_device_name(name: str) -> str:
    """
    Normalize device names to catch variants with truncation or slight differences.

    MME API often truncates device names at 31 characters, so we normalize by:
    1. Finding the common prefix up to the last opening parenthesis
    2. Taking the first N words inside the parenthesis (ignoring potentially truncated words)

    Examples:
        "Microphone (Sennheiser USB head" -> "Microphone (Sennheiser USB"
        "Microphone (Sennheiser USB headset)" -> "Microphone (Sennheiser USB"
    """
    normalized = name.strip()

    # Find the last opening parenthesis
    if '(' in normalized:
        last_paren = normalized.rfind('(')
        prefix = normalized[:last_paren+1]  # Everything up to and including '('

        # Extract content inside parentheses
        suffix = normalized[last_paren+1:]

        # Remove closing paren if present
        if suffix.endswith(')'):
            suffix = suffix[:-1].strip()

        # Take only first 2 words to avoid truncation differences
        # "Sennheiser USB head" vs "Sennheiser USB headset" both become "Sennheiser USB"
        words = suffix.split()
        if len(words) > 2:
            suffix = ' '.join(words[:2])
        elif words:
            suffix = ' '.join(words)

        normalized = prefix + suffix

    # Also handle trailing incomplete parentheses
    if normalized.endswith(' (') or normalized.endswith('('):
        normalized = normalized.rstrip('(').strip()

    return normalized

def _get_host_api_priority(hostapi_index: int) -> int:
    """
    Return priority score for host API (higher is better).
    WASAPI is most reliable on modern Windows, followed by DirectSound, MME, then WDM-KS.
    """
    try:
        api_info = sd.query_hostapis(hostapi_index)
        api_name = api_info['name'].lower()
        
        if 'wasapi' in api_name:
            return 400
        elif 'directsound' in api_name:
            return 300
        elif 'mme' in api_name:
            return 200
        elif 'wdm-ks' in api_name or 'ks' in api_name:
            return 100
        else:
            return 50
    except:
        return 0

def _is_problematic_endpoint(name: str, hostapi_index: int) -> bool:
    """
    Filter out known problematic device endpoints that don't carry real audio.
    """
    name_lower = name.lower()
    
    # Virtual processing endpoints that often return silence
    if name_lower.startswith('input ('):
        return True
    
    # System virtual devices (stereo mix, loopback, etc.)
    if any(pattern in name_lower for pattern in [
        'stereo mix',
        'system virtual',
        'loopback',
        'what u hear',
        'wave out mix'
    ]):
        return True
    
    # WDM-KS raw channel endpoints (use the aggregate instead)
    # e.g., "Microphone 1 (Device)", "Microphone 2 (Device)", "Microphone 3 (Device)"
    if re.match(r'microphone \d+ \(', name_lower):
        return True
    
    return False

def get_input_devices() -> List[Dict[str, any]]:
    """
    Returns a list of available input (microphone) devices.

    Intelligently deduplicates by:
    1. Normalizing device names to catch truncation
    2. Prioritizing devices with more channels (3-channel > 1-channel)
       - 1-channel devices are often problematic/non-functional
    3. When channel count is equal, prefer: WASAPI > DirectSound > MME > WDM-KS
    4. Filtering out problematic virtual/processing endpoints
    5. Choosing variants with best sample rate when channels and API are equal
    """
    all_devices = sd.query_devices()
    seen_devices: Dict[str, Dict] = {}  # Track by normalized name
    
    # Collect all input devices with metadata
    candidates = []
    for i in range(len(all_devices)):
        device = all_devices[i]
        if device['max_input_channels'] > 0:
            name = device['name']
            normalized_name = _normalize_device_name(name)
            
            # Skip problematic endpoints
            if _is_problematic_endpoint(name, device['hostapi']):
                continue
            
            device_info = {
                'id': i,
                'name': name,
                'normalized_name': normalized_name,
                'max_input_channels': device['max_input_channels'],
                'hostapi': device['hostapi'],
                'default_samplerate': device['default_samplerate'],
                'api_priority': _get_host_api_priority(device['hostapi'])
            }
            candidates.append(device_info)
    
    # For each normalized name, pick the best variant
    for device_info in candidates:
        normalized_name = device_info['normalized_name']

        if normalized_name not in seen_devices:
            seen_devices[normalized_name] = device_info
        else:
            existing = seen_devices[normalized_name]

            # IMPORTANT: Prefer devices with more channels first
            # 1-channel devices are often problematic/non-functional
            # Priority: channel count > API priority > sample rate
            current_channels = device_info['max_input_channels']
            existing_channels = existing['max_input_channels']

            is_better = (
                # Prefer more channels (3-channel over 1-channel, etc.)
                current_channels > existing_channels or
                # If same channel count, prefer better API
                (current_channels == existing_channels and
                 device_info['api_priority'] > existing['api_priority']) or
                # If same channel and API, prefer higher sample rate
                (current_channels == existing_channels and
                 device_info['api_priority'] == existing['api_priority'] and
                 device_info['default_samplerate'] > existing['default_samplerate'])
            )

            if is_better:
                seen_devices[normalized_name] = device_info
    
    # Remove internal metadata and return
    result = []
    for device in seen_devices.values():
        result.append({
            'id': device['id'],
            'name': device['name'],
            'max_input_channels': device['max_input_channels'],
            'hostapi': device['hostapi'],
            'default_samplerate': device['default_samplerate']
        })
    
    return result

def get_default_device_id() -> int:
    """Returns the system default input device ID"""
    device = sd.query_devices(None, kind='input')
    return device['index']

def set_input_device(device_id: int) -> None:
    """Sets the active input device for recording"""
    sd.default.device[0] = device_id  # Sets input device only

def get_all_device_variants() -> Dict[str, List[Dict[str, any]]]:
    """Returns all variants of input devices grouped by device name"""
    device_groups: Dict[str, List[Dict]] = {}

    for i, device in enumerate(sd.query_devices()):
        if device['max_input_channels'] > 0:
            original_name = device['name']

            if original_name not in device_groups:
                device_groups[original_name] = []

            device_groups[original_name].append({
                'id': i,
                'name': original_name,
                'channels': device['max_input_channels'],
                'hostapi': device['hostapi'],
                'default_samplerate': device['default_samplerate']
            })

    return device_groups

def is_valid_device_id(device_id: int) -> bool:
    """Checks if a device ID exists in the current device list"""
    return any(device['id'] == device_id for device in get_input_devices())

if __name__ == '__main__':
    print("Available Input Devices (Grouped):")
    print("-----------------------")
    device_groups = get_all_device_variants()
    default_id = get_default_device_id()

    for base_name, variants in device_groups.items():
        print(f"\nDevice: {base_name}")
        for variant in variants:
            default_marker = " (Default)" if variant['id'] == default_id else ""
            print(f"  ID: {variant['id']}{default_marker}")
            print(f"  Channels: {variant['channels']}")
            print(f"  Host API: {variant['hostapi']}")
            print(f"  Sample Rate: {variant['default_samplerate']} Hz")
            print("  -----------------------")

    print(f"\nTotal unique devices: {len(device_groups)}")
    print(f"Total variants across all devices: {sum(len(variants) for variants in device_groups.values())}")
