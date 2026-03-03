"""Analyze audio files and generate energy scores for index.json"""
import os
import json
import numpy as np
import soundfile as sf
from pathlib import Path

def calculate_energy_score(wav_path: str) -> float:
    """Calculate perceptual energy score combining RMS, spectral centroid, and dynamics"""
    try:
        x, sr = sf.read(wav_path)
        if x.ndim > 1:
            x = x.mean(axis=1)
        x = x.astype(np.float32)
        
        # 1. RMS energy (loudness)
        rms = np.sqrt(np.mean(x ** 2))
        rms_db = 20 * np.log10(rms + 1e-9)
        rms_norm = max(0, min(1, (rms_db + 60) / 60))
        
        # 2. Spectral centroid (brightness - higher = more energetic)
        # Using FFT to get frequency content
        fft = np.abs(np.fft.rfft(x))
        freqs = np.fft.rfftfreq(len(x), 1/sr)
        
        # Weighted average frequency (spectral centroid)
        centroid = np.sum(freqs * fft) / (np.sum(fft) + 1e-9)
        # Normalize: typical centroid range 500-5000 Hz
        centroid_norm = max(0, min(1, (centroid - 500) / 4500))
        
        # 3. Dynamic range / variance (more variation = more energetic)
        # Calculate RMS in chunks to measure dynamics
        chunk_size = int(sr * 0.1)  # 100ms chunks
        rms_chunks = []
        for i in range(0, len(x) - chunk_size, chunk_size):
            chunk = x[i:i+chunk_size]
            rms_chunks.append(np.sqrt(np.mean(chunk ** 2)))
        
        if rms_chunks:
            dynamics = np.std(rms_chunks) / (np.mean(rms_chunks) + 1e-9)
            dynamics_norm = min(1, dynamics * 2)  # Scale up
        else:
            dynamics_norm = 0.5
        
        # 4. Zero-crossing rate (texture - higher = more energetic/percussive)
        zero_crossings = np.sum(np.abs(np.diff(np.sign(x)))) / 2
        zcr = zero_crossings / len(x)
        zcr_norm = min(1, zcr * 10)  # Normalize
        
        # Combine metrics with weights
        # Spectral centroid and dynamics are more important for "energy" perception
        energy = (rms_norm * 0.15 + centroid_norm * 0.40 + 
                  dynamics_norm * 0.25 + zcr_norm * 0.20)
        
        return round(float(energy), 2)
    except Exception as e:
        print(f"Error processing {wav_path}: {e}")
        return 0.5

def categorize_track(filename: str) -> list:
    """Categorize track based on filename"""
    name = filename.lower()
    if 'calm' in name:
        return ['calm', 'ambient']
    elif 'energetic' in name:
        return ['energetic', 'upbeat']
    elif 'serious' in name:
        return ['serious', 'dramatic']
    elif 'educational' in name:
        return ['educational', 'informative']
    else:
        return ['general']

def main():
    tracks_dir = Path(__file__).parent / 'media' / 'music_library' / 'tracks'
    index_path = Path(__file__).parent / 'media' / 'music_library' / 'index.json'
    
    tracks = []
    
    # Get all audio files
    audio_files = sorted([f for f in os.listdir(tracks_dir) if f.endswith('.mp3')])
    
    print(f"Found {len(audio_files)} audio files\n")
    print("-" * 60)
    
    for filename in audio_files:
        file_path = tracks_dir / filename
        track_id = filename.replace('.mp3', '')
        
        # Calculate energy score
        energy = calculate_energy_score(str(file_path))
        tags = categorize_track(filename)
        
        track_entry = {
            "id": track_id,
            "tags": tags,
            "energy": energy,
            "path": f"tracks/{filename}"
        }
        tracks.append(track_entry)
        
        print(f"{track_id:20} | Energy: {energy:.2f} | Tags: {tags}")
    
    print("-" * 60)
    
    # Write to index.json
    index_data = {"tracks": tracks}
    
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2)
    
    print(f"\nUpdated {index_path} with {len(tracks)} tracks")

if __name__ == '__main__':
    main()
