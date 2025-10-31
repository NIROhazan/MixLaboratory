"""
Debug script to see why keys aren't loading
"""
import os
import json
import hashlib
from pathlib import Path

# Your music directory - CHANGE THIS
music_dir = input("Enter your music folder path: ")

# List audio files
audio_files = [f for f in os.listdir(music_dir) if f.endswith(('.mp3', '.wav', '.flac'))]

print(f"\nFound {len(audio_files)} audio files\n")

# Check cache for each file
cache_dir = Path("cache/keys")

for audio_file in audio_files[:5]:  # Check first 5
    full_path = os.path.join(music_dir, audio_file)
    
    # Calculate cache key
    cache_key = hashlib.md5(full_path.encode('utf-8')).hexdigest()
    key_file = cache_dir / f"{cache_key}.json"
    
    print(f"File: {audio_file}")
    print(f"  Full path: {full_path}")
    print(f"  Cache key: {cache_key}")
    print(f"  Key file exists: {key_file.exists()}")
    
    if key_file.exists():
        with open(key_file, 'r') as f:
            data = json.load(f)
        print(f"  ✅ KEY: {data.get('key')} (confidence: {data.get('confidence'):.2f})")
    else:
        print(f"  ❌ NO KEY CACHED")
    print()

