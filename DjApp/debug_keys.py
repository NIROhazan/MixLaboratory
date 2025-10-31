"""
Quick debug script to check key cache
"""
import os
import json
from pathlib import Path

cache_dir = Path("cache/keys")
print(f"Checking cache directory: {cache_dir}")
print(f"Directory exists: {cache_dir.exists()}")

if cache_dir.exists():
    key_files = list(cache_dir.glob("*.json"))
    print(f"\nFound {len(key_files)} key cache files:")
    
    for key_file in key_files:
        with open(key_file, 'r') as f:
            data = json.load(f)
        print(f"\n{key_file.name}:")
        print(f"  Key: {data.get('key')}")
        print(f"  Confidence: {data.get('confidence')}")
        print(f"  Cached at: {data.get('cached_at')}")

# Check cache metadata
metadata_file = Path("cache/cache_metadata.json")
if metadata_file.exists():
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    print(f"\n\nCache metadata has {len(metadata)} entries")
    for file_path, info in list(metadata.items())[:3]:
        print(f"\nFile: {file_path}")
        print(f"  Metadata: {info}")

