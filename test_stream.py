import sounddevice as sd
import soundfile as sf
import sys

if len(sys.argv) < 2:
    print("Usage: python test_stream.py <device_id>")
    sys.exit(1)

dev_id = int(sys.argv[1])
info = sd.query_devices(dev_id)
sr = int(info["default_samplerate"])
fn = f"sd_test_{dev_id}.wav"

print(f"Opening device {dev_id}: {info['name']} ({sr} Hz)")

try:
    with sf.SoundFile(fn, mode="w", samplerate=sr, channels=1, subtype="PCM_16") as f:
        def cb(indata, frames, time, status):
            if status:
                print(f"Stream status: {status}")
            f.write(indata.copy())
        
        with sd.InputStream(device=dev_id, samplerate=sr, channels=1, callback=cb):
            print("Recording for 2 seconds... speak now!")
            sd.sleep(2000)
    
    print(f"✓ Successfully wrote {fn}")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
