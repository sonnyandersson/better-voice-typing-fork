import sounddevice as sd

apis = sd.query_hostapis()
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        api = apis[d["hostapi"]]["name"]
        print(f"{i:>3}  {d['name']:<45} in={d['max_input_channels']} sr={d['default_samplerate']} api={api}")
