"""Analyze SFX files and generate scores for index.json"""
import os
import json
import numpy as np
import soundfile as sf
from pathlib import Path


def calculate_sfx_scores(wav_path: str) -> dict:
    """Calculate various scores for SFX files"""
    try:
        x, sr = sf.read(wav_path)
        if x.ndim > 1:
            x = x.mean(axis=1)
        x = x.astype(np.float32)
        
        duration = len(x) / sr
        
        # 1. Intensity (RMS energy)
        rms = np.sqrt(np.mean(x ** 2))
        rms_db = 20 * np.log10(rms + 1e-9)
        intensity = max(0, min(1, (rms_db + 60) / 60))
        
        # 2. Spectral centroid (brightness)
        fft = np.abs(np.fft.rfft(x))
        freqs = np.fft.rfftfreq(len(x), 1/sr)
        centroid = np.sum(freqs * fft) / (np.sum(fft) + 1e-9)
        brightness = max(0, min(1, (centroid - 500) / 4500))
        
        # 3. Attack time (how quickly it reaches peak)
        envelope = np.abs(x)
        # Smooth envelope
        window_size = int(sr * 0.01)  # 10ms window
        if window_size > 0:
            envelope = np.convolve(envelope, np.ones(window_size)/window_size, mode='same')
        
        peak_idx = np.argmax(envelope)
        attack_time = peak_idx / sr
        # Normalize: quick attack (< 0.05s) = 1.0, slow attack (> 0.5s) = 0.0
        attack_score = max(0, min(1, 1 - (attack_time / 0.5)))
        
        # 4. Impact score (combination of quick attack + high intensity)
        impact = (attack_score * 0.6 + intensity * 0.4)
        
        # 5. Overall energy score
        energy = (intensity * 0.25 + brightness * 0.35 + attack_score * 0.25 + impact * 0.15)
        
        return {
            "intensity": round(float(intensity), 2),
            "brightness": round(float(brightness), 2),
            "attack": round(float(attack_score), 2),
            "impact": round(float(impact), 2),
            "energy": round(float(energy), 2),
            "duration": round(float(duration), 2)
        }
    except Exception as e:
        print(f"Error processing {wav_path}: {e}")
        return {
            "intensity": 0.5,
            "brightness": 0.5,
            "attack": 0.5,
            "impact": 0.5,
            "energy": 0.5,
            "duration": 0.0
        }


def categorize_sfx(filename: str) -> list:
    """Categorize SFX based on filename keywords"""
    name = filename.lower()
    tags = []
    
    # Primary category
    if 'whoosh' in name:
        tags.append('whoosh')
    if 'transition' in name:
        tags.append('transition')
    if 'swoosh' in name:
        tags.append('swoosh')
    if 'swipe' in name:
        tags.append('swipe')
    if 'hit' in name or 'impact' in name:
        tags.append('impact')
    if 'click' in name:
        tags.append('click')
    if 'beep' in name or 'boop' in name:
        tags.append('ui')
    if 'notification' in name or 'alert' in name:
        tags.append('notification')
    if 'ambient' in name or 'atmosphere' in name:
        tags.append('ambient')
    
    # Style/mood modifiers
    if 'cinematic' in name:
        tags.append('cinematic')
    if 'sci-fi' in name or 'scifi' in name:
        tags.append('sci-fi')
    if 'simple' in name or 'light' in name:
        tags.append('subtle')
    if 'heavy' in name or 'intense' in name:
        tags.append('intense')
    if 'motion' in name:
        tags.append('motion')
    
    # Default if no tags found
    if not tags:
        tags.append('general')
    
    return tags


def generate_id(filename: str) -> str:
    """Generate a clean ID from filename"""
    # Remove extension
    name = filename.replace('.mp3', '').replace('.wav', '')
    # Remove numbers at the end (like -433005)
    parts = name.split('-')
    # Filter out pure numeric parts at the end
    while parts and parts[-1].isdigit():
        parts.pop()
    # Join back and limit length
    clean_id = '-'.join(parts)
    # Shorten very long IDs
    if len(clean_id) > 50:
        clean_id = clean_id[:50]
    return clean_id


def main():
    sfx_dir = Path(__file__).parent / 'media' / 'sfx_library' / 'sfx'
    index_path = Path(__file__).parent / 'media' / 'sfx_library' / 'index.json'
    
    sfx_entries = []
    
    # Get all audio files
    audio_files = sorted([f for f in os.listdir(sfx_dir) if f.endswith(('.mp3', '.wav'))])
    
    print(f"Found {len(audio_files)} SFX files\n")
    print("=" * 80)
    
    for filename in audio_files:
        file_path = sfx_dir / filename
        sfx_id = generate_id(filename)
        
        # Calculate scores
        scores = calculate_sfx_scores(str(file_path))
        tags = categorize_sfx(filename)
        
        sfx_entry = {
            "id": sfx_id,
            "tags": tags,
            "energy": scores["energy"],
            "intensity": scores["intensity"],
            "brightness": scores["brightness"],
            "attack": scores["attack"],
            "impact": scores["impact"],
            "duration": scores["duration"],
            "path": f"sfx/{filename}"
        }
        sfx_entries.append(sfx_entry)
        
        print(f"File: {filename}")
        print(f"  ID: {sfx_id}")
        print(f"  Tags: {tags}")
        print(f"  Energy: {scores['energy']:.2f} | Intensity: {scores['intensity']:.2f} | "
              f"Brightness: {scores['brightness']:.2f}")
        print(f"  Attack: {scores['attack']:.2f} | Impact: {scores['impact']:.2f} | "
              f"Duration: {scores['duration']:.2f}s")
        print("-" * 80)
    
    # Write to index.json
    index_data = {"sfx": sfx_entries}
    
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2)
    
    print(f"\nUpdated {index_path} with {len(sfx_entries)} SFX entries")


if __name__ == '__main__':
    main()
