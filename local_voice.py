import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import keyboard
import os
import sys
from faster_whisper import WhisperModel
# CHANGED: Using pynput to fix the Linux keyboard.write crash bug
from pynput.keyboard import Controller

# Initialize the tiny, ultra-fast local speech model
print("Loading local speech engine onto your system...")
model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
pynput_keyboard = Controller()

FS = 44100  
recording = []
is_recording = False

def callback(indata, frames, time, status):
    if is_recording:
        recording.append(indata.copy())

print("\n=== Local Jarvis Voice Active ===")
print("Press and HOLD the [F4] key on your keyboard to talk.")
print("Release [F4] when you are finished speaking.")

while True:
    keyboard.wait('f4')
    is_recording = True
    recording = []
    print("\n🎤 Listening...", end="", flush=True)
    
    with sd.InputStream(samplerate=FS, channels=1, callback=callback):
        while keyboard.is_pressed('f4'):
            sd.sleep(100)
            
    is_recording = False
    print(" Processing...", end="", flush=True)
    
    if recording:
        audio_data = np.concatenate(recording, axis=0)
        wav.write('/tmp/jarvis_speech.wav', FS, audio_data)
        
        # Transcribe audio entirely offline
        segments, info = model.transcribe('/tmp/jarvis_speech.wav', beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()
        
        if text:
            print(f"\n✨ Recognized: {text}")
            # CHANGED: Typing via pynput instead of keyboard.write to fix StopIteration
            pynput_keyboard.type(text)
        else:
            print("\n❌ Could not understand audio.")
