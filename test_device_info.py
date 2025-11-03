import sounddevice as sd

print('Current default input device:')
device_id = sd.default.device[0]
print(f'Device ID: {device_id}')
if device_id is not None:
    device = sd.query_devices(device_id)
    print(f'Name: {device["name"]}')
    print(f'Channels: {device["max_input_channels"]}')
