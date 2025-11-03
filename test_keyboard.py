import keyboard
import time

print("Press the < key (next to left Shift on Swedish keyboard)")
print("Press ESC to exit")
print("Listening for key presses...\n")

def on_key_event(event):
    if event.event_type == 'down':
        print(f"Key: {event.name}")
        print(f"  Scan code: {event.scan_code}")
        print(f"  VK code: {event.vk if hasattr(event, 'vk') else 'N/A'}")
        print()

        if event.name == 'esc':
            print("Exiting...")
            exit()

keyboard.hook(on_key_event)
keyboard.wait()
