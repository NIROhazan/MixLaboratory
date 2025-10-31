"""
Test key detection manually
"""
import os
from audio_analyzer_bridge import AudioAnalyzerBridge

# Find an audio file
test_dir = input("Enter path to audio directory: ")
files = [f for f in os.listdir(test_dir) if f.endswith(('.mp3', '.wav', '.flac'))]

if files:
    test_file = os.path.join(test_dir, files[0])
    print(f"\nTesting with: {test_file}")
    
    analyzer = AudioAnalyzerBridge()
    print("\nDetecting key...")
    
    try:
        key, confidence = analyzer.detect_key(test_file)
        print(f"\n✅ Result:")
        print(f"   Key: {key}")
        print(f"   Confidence: {confidence:.2%}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No audio files found!")

