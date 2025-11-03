import numpy as np
import sounddevice as sd
import soundfile as sf
import time

# Simulate multi-channel recording and conversion
print("Testing 3-channel to mono conversion...")

# Set device to Sennheiser (ID 15, 3 channels)
sd.default.device[0] = 15

duration = 2
samplerate = 22050
channels = 3

print(f"Recording {duration}s from 3-channel device...")

# Record multi-channel
recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype=np.int16)
sd.wait()

print(f"Recording shape: {recording.shape}")
print(f"Max amplitude: {np.max(np.abs(recording))}")

# Convert to mono like the recorder does
if recording.ndim > 1 and recording.shape[1] > 1:
    mono_data = np.mean(recording, axis=1)
else:
    mono_data = recording.flatten() if recording.ndim > 1 else recording

print(f"Mono data shape: {mono_data.shape}")
print(f"Mono data dtype: {mono_data.dtype}")

# Write to file
filename = 'test_mono.wav'
with sf.SoundFile(filename, mode='w', samplerate=samplerate, channels=1, subtype='PCM_16', format='WAV') as f:
    f.write(mono_data)

print(f"Written to {filename}")

# Try to read it back
print("Reading back...")
try:
    data, rate = sf.read(filename)
    print(f"Read successfully! Shape: {data.shape}, Rate: {rate}")
except Exception as e:
    print(f"ERROR reading back: {e}")
