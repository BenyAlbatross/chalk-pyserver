import numpy as np
from PIL import Image
from scipy.io import wavfile
import os
import io

def divide_image_into_segments(image_path, num_segments=20):
    """
    Divide an image into segments and calculate average brightness for each.
    """
    # Load the image
    img = Image.open(image_path)
    
    # Convert to grayscale to get brightness values
    img_gray = img.convert('L')
    img_array = np.array(img_gray)
    
    height, width = img_array.shape
    
    # Divide horizontally into segments
    segment_height = height // num_segments
    brightness_values = []
    
    for i in range(num_segments):
        start_row = i * segment_height
        # Handle the last segment to include any remaining pixels
        if i == num_segments - 1:
            end_row = height
        else:
            end_row = (i + 1) * segment_height
        
        segment = img_array[start_row:end_row, :]
        avg_brightness = np.mean(segment)
        brightness_values.append(avg_brightness)
    
    return brightness_values

def create_bell_sound(frequency, duration, sample_rate=44100, decay=1.5):
    """
    Create a calming synth-bell sound with soft attack and gentle decay.
    """
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Use softer harmonics for a calming sound
    # Mostly sine waves with gentle overtones
    harmonics = [
        (1.0, 1.0),      # Fundamental (pure tone)
        (2.0, 0.3),      # Octave (gentle)
        (3.0, 0.15),     # Fifth (subtle)
        (4.0, 0.08),     # Second octave (very subtle)
    ]
    
    signal = np.zeros_like(t)
    for ratio, amplitude in harmonics:
        # Add slight detuning for warmth (chorus effect)
        detune = 1.0 + np.random.uniform(-0.002, 0.002)
        signal += amplitude * np.sin(2 * np.pi * frequency * ratio * detune * t)
    
    # Soft attack envelope (fade in)
    attack_time = 0.15
    attack_samples = int(attack_time * sample_rate)
    attack_env = np.ones_like(t)
    attack_env[:attack_samples] = np.linspace(0, 1, attack_samples)
    
    # Gentle exponential decay
    decay_env = np.exp(-decay * t)
    
    # Combine envelopes
    envelope = attack_env * decay_env
    signal = signal * envelope
    
    # Add subtle vibrato for warmth
    vibrato_rate = 4.5  # Hz
    vibrato_depth = 0.003
    vibrato = 1 + vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t)
    signal = signal * vibrato
    
    # Normalize
    if np.max(np.abs(signal)) > 0:
        signal = signal / np.max(np.abs(signal))
    
    # Soft limiting to prevent harsh sounds
    signal = signal * 0.8
    
    return signal

def brightness_to_note_frequency(normalized_index, scale_frequencies):
    """
    Map normalized index to a note frequency from the scale.
    """
    index = int(normalized_index)
    index = min(index, len(scale_frequencies) - 1)
    return scale_frequencies[index]

def generate_audio_from_brightness(brightness_values, output_file='output.wav'):
    """
    Generate audio file with bell sounds mapped to E pentatonic scale.
    """
    # E pentatonic scale (major) - multiple octaves for better range
    # E4, F#4, G#4, B4, C#5, E5, F#5, G#5
    e_pentatonic_frequencies = [
        164.81,  # E3
        185.00,  # F#3
        207.65,  # G#3
        246.94,  # B3
        277.18,  # C#4
        329.63,  # E4
        369.99,  # F#4
        415.30,  # G#4
        493.88,  # B4
        554.37,  # C#5
    ]
    
    sample_rate = 44100
    note_duration = 0.7  # Duration of each note in seconds (longer for calming effect)
    
    # Normalize brightness values to scale range
    min_brightness = min(brightness_values)
    max_brightness = max(brightness_values)
    max_note_index = len(e_pentatonic_frequencies) - 1
    
    print("Generating audio from brightness values...")
    print(f"Brightness values: {[f'{b:.1f}' for b in brightness_values]}")
    print(f"Min brightness: {min_brightness:.1f}, Max brightness: {max_brightness:.1f}")
    print(f"Scale range: 0 to {max_note_index} (indices)")
    
    # First, generate all note indices
    note_indices = []
    for i, brightness in enumerate(brightness_values):
        # Normalize to 0 to max_note_index range
        if max_brightness == min_brightness:
            normalized = 0
        else:
            normalized = (brightness - min_brightness) / (max_brightness - min_brightness) * max_note_index
        
        # Randomly round up or down (coin toss)
        if np.random.rand() < 0.5:
            note_index = int(np.floor(normalized))
        else:
            note_index = int(np.ceil(normalized))
        
        note_index = max(0, min(note_index, max_note_index))
        note_indices.append(note_index)
    
    # Randomize the order of notes
    np.random.shuffle(note_indices)
    
    # Create the full audio signal
    full_signal = np.array([])
    
    for i, note_index in enumerate(note_indices):
        # Occasionally randomly adjust by +/-1 note (30% chance)
        if np.random.rand() < 0.3:
            adjustment = np.random.choice([-1, 1])
            note_index = note_index + adjustment
            note_index = max(0, min(note_index, max_note_index))
        
        frequency = brightness_to_note_frequency(note_index, e_pentatonic_frequencies)
        print(f"Note {i+1}: Index={note_index}, Frequency={frequency:.2f} Hz")
        
        bell_sound = create_bell_sound(frequency, note_duration, sample_rate)
        full_signal = np.concatenate([full_signal, bell_sound])
    
    # Normalize the full signal
    full_signal = full_signal / np.max(np.abs(full_signal))
    
    # Convert to 16-bit PCM
    audio_data = np.int16(full_signal * 32767)
    
    # Write to WAV file
    wavfile.write(output_file, sample_rate, audio_data)
    print(f"\nAudio file saved as: {output_file}")

def main():
    image_path = "result_chalk_saturated.jpg"
    
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' not found!")
        return
    
    print(f"Processing image: {image_path}")
    
    # Step 1: Divide image and get brightness values
    brightness_values = divide_image_into_segments(image_path, num_segments=20)
    
    print(f"\nExtracted {len(brightness_values)} brightness values from image")
    
    # Step 2: Generate audio with bell sounds
    generate_audio_from_brightness(brightness_values, output_file='image_music.wav')
    
    print("\nDone! Play 'image_music.wav' to hear the result.")

def generate_doorbell_wav_from_image(image_bytes):
    """
    Generate WAV doorbell sound from image bytes.
    Returns WAV bytes ready to send to frontend.
    """
    # Load image from bytes
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convert to grayscale to get brightness values
    img_gray = img.convert('L')
    img_array = np.array(img_gray)
    
    height, width = img_array.shape
    num_segments = 20
    
    # Divide horizontally into segments
    segment_height = height // num_segments
    brightness_values = []
    
    for i in range(num_segments):
        start_row = i * segment_height
        if i == num_segments - 1:
            end_row = height
        else:
            end_row = (i + 1) * segment_height
        
        segment = img_array[start_row:end_row, :]
        avg_brightness = np.mean(segment)
        brightness_values.append(avg_brightness)
    
    # Generate audio to temporary WAV in memory
    sample_rate = 44100
    note_duration = 0.7
    
    e_pentatonic_frequencies = [
        164.81,  # E3
        185.00,  # F#3
        207.65,  # G#3
        246.94,  # B3
        277.18,  # C#4
        329.63,  # E4
        369.99,  # F#4
        415.30,  # G#4
        493.88,  # B4
        554.37,  # C#5
    ]
    
    min_brightness = min(brightness_values)
    max_brightness = max(brightness_values)
    max_note_index = len(e_pentatonic_frequencies) - 1
    
    note_indices = []
    for brightness in brightness_values:
        if max_brightness == min_brightness:
            normalized = 0
        else:
            normalized = (brightness - min_brightness) / (max_brightness - min_brightness) * max_note_index
        
        if np.random.rand() < 0.5:
            note_index = int(np.floor(normalized))
        else:
            note_index = int(np.ceil(normalized))
        
        note_index = max(0, min(note_index, max_note_index))
        note_indices.append(note_index)
    
    np.random.shuffle(note_indices)
    
    full_signal = np.array([])
    
    for note_index in note_indices:
        if np.random.rand() < 0.3:
            adjustment = np.random.choice([-1, 1])
            note_index = note_index + adjustment
            note_index = max(0, min(note_index, max_note_index))
        
        frequency = brightness_to_note_frequency(note_index, e_pentatonic_frequencies)
        bell_sound = create_bell_sound(frequency, note_duration, sample_rate)
        full_signal = np.concatenate([full_signal, bell_sound])
    
    full_signal = full_signal / np.max(np.abs(full_signal))
    audio_data = np.int16(full_signal * 32767)
    
    # Create WAV in memory
    wav_buffer = io.BytesIO()
    wavfile.write(wav_buffer, sample_rate, audio_data)
    wav_buffer.seek(0)
    
    return wav_buffer.read()

if __name__ == "__main__":
    main()
