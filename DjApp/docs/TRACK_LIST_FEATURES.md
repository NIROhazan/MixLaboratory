# Track List - Key/Scale Display Feature

## Overview

The track list now displays **musical keys** alongside BPM for each track, providing essential information for harmonic mixing before you load tracks into decks.

---

## Visual Display

### Track List Layout

```
Track Name
🎵 130 BPM | 🎹 C Major ✓
[Load Deck 1] [Load Deck 2]
```

### Key Information Display

- **🎹 Key Icon**: Musical keyboard emoji indicates key information
- **Key Name**: Displays as "C Major", "D Minor", etc.
- **Confidence Indicator**:
  - **✓ (Green)**: High confidence (>70%) - Reliable key detection
  - **~ (Yellow)**: Medium confidence (50-70%) - Good detection
  - **? (Orange)**: Low confidence (<50%) - Uncertain detection

---

## How It Works

### 1. **Automatic Key Detection**

When you open the track list, the system automatically:
- **Analyzes BPM** (fast, ~1-2 seconds per track)
- **Detects Musical Key** (slower, ~5-10 seconds per track)
- **Caches Results** for instant future access

### 2. **Background Processing**

- All analysis runs in **background threads**
- **UI remains responsive** while analyzing
- **Progress updates** show real-time status
- **Cached tracks load instantly**

### 3. **Persistent Caching**

Key detection results are **permanently cached**:
- ✅ Analyzed once, used forever
- ✅ Instant loading on subsequent opens
- ✅ Survives app restarts
- ✅ Shared across all features (auto-mix, deck loading)

---

## Color-Coded Confidence

The key display uses **color coding** to show detection quality:

| Color | Confidence | Meaning | Action |
|-------|-----------|---------|---------|
| 🟢 **Green** | >70% | Highly reliable | Trust this key for mixing |
| 🟡 **Yellow** | 50-70% | Good estimate | Generally safe to use |
| 🟠 **Orange** | <50% | Uncertain | Double-check by ear |

---

## Harmonic Mixing Benefits

### Why Key Display Matters

**Harmonic mixing** ensures smooth, musical transitions between tracks:

1. **Compatible Keys** = Smooth transitions
2. **Incompatible Keys** = Clash and dissonance
3. **Camelot Wheel** guides key compatibility

### Quick Key Matching Tips

**Energy Up/Down:**
- Same key: Always compatible
- Adjacent keys on Camelot wheel: Perfect

**Key Changes:**
- ±1 semitone: Usually works
- ±7 semitones (perfect 5th): Always works
- ±5 semitones (perfect 4th): Usually works

---

## Camelot Wheel Integration

Keys are displayed with **Camelot notation** in the full key string:
- "C Major (8B)"
- "A Minor (8A)"

The Camelot wheel makes it easy to find compatible keys:
- **Same number, different letter** (8A ↔ 8B): Perfect mix
- **±1 number, same letter** (8A → 9A or 7A): Energy shift
- **±1 number, different letter** (8A → 9B): Bold move

---

## Performance Optimization

### Fast Loading

- **BPM Cache**: Instant display for analyzed tracks
- **Key Cache**: No re-analysis needed
- **Smart Loading**: Only analyzes new/changed files

### Memory Efficiency

- **Lazy Loading**: Keys analyzed only when needed
- **Disk Cache**: Minimal memory footprint
- **Shared Cache**: One analysis, many uses

---

## Technical Details

### Key Detection Algorithm

Uses **Krumhansl-Schmuckler key-finding algorithm**:
1. Analyze audio with **Chroma CQT** (Constant-Q Transform)
2. Calculate **pitch class distribution**
3. Correlate with **major/minor key profiles**
4. Return **best matching key** with confidence score

### Supported Keys

**Major Keys:**
- C, C♯, D, E♭, E, F, F♯, G, A♭, A, B♭, B

**Minor Keys:**
- All relative minors (A, B♭, B, C, C♯, D, E♭, E, F, F♯, G, G♯)

---

## User Experience

### On First Load

```
Track Name
Analyzing...
[Load Deck 1] [Load Deck 2]
```

### During Analysis

```
Track Name
🎵 130 BPM | Analyzing...
[Load Deck 1] [Load Deck 2]
```

### Fully Analyzed

```
Track Name
🎵 130 BPM | 🎹 C Major ✓
[Load Deck 1] [Load Deck 2]
```

---

## Integration with Other Features

### Deck Display

When you load a track into a deck:
- Key appears in **deck key display**
- Shows **full Camelot notation**
- Includes **transposition controls** (♭/♯)

### Auto-Mix System

The AI auto-mix uses key data to:
- **Score harmonic compatibility**
- **Generate optimal playlists**
- **Ensure smooth transitions**

### Manual Mixing

Use key information to:
- **Plan your set** before loading tracks
- **Find compatible tracks** quickly
- **Avoid key clashes** during live mixing

---

## Troubleshooting

### No Key Displayed

**Possible causes:**
- Analysis still in progress (wait a moment)
- Key detection failed (try reloading folder)
- Track has ambiguous/atonal key (rare)

### Low Confidence

**Tips for better results:**
- Harmonic tracks detect better than percussive
- Longer tracks give more reliable results
- Monophonic/sparse arrangements may struggle

### Wrong Key Detected

**What to do:**
- Use the **transpose controls** in deck view
- Report patterns (helps improve algorithm)
- Trust your ears over the display

---

## Future Enhancements

### Planned Features

- **Manual key override** (edit incorrect detections)
- **Key history tracking** (learn common keys in your library)
- **Bulk key analysis** (background indexing)
- **Key-based search/filter** (find all tracks in A Minor)

---

## Keyboard Shortcuts

*Coming soon:*
- `K` - Toggle key display on/off
- `Ctrl+K` - Bulk key analysis for folder
- `Shift+K` - Export key data to file

---

## API Reference

### Signals

```python
key_analyzed = pyqtSignal(str, str, float)
# Emits: (file_path, key, confidence)
```

### Methods

```python
def update_track_key(file, key, confidence):
    """Update key display for a track"""

def _update_track_metadata(file):
    """Refresh BPM and Key display"""
```

---

## See Also

- [Key Detection System](deck_widgets.py) - Core detection logic
- [Camelot Wheel](audio_analyzer_bridge.py) - Harmonic compatibility
- [Auto-Mix Engine](automix_engine.py) - AI playlist generation
- [Cache Manager](cache_manager.py) - Persistent storage

---

**Happy Harmonic Mixing! 🎹🎵**

