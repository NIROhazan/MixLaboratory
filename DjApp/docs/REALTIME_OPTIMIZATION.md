# Real-Time Performance Optimization Plan

## Current Issues

### 1. **BPM Changes are Slow** ❌
- Uses `TempoChangeWorker` (background thread)
- Creates temporary files
- Reloads audio after processing
- **Delay: 2-10 seconds**

### 2. **Solution: Instant Playback Rate** ✅
Use `QMediaPlayer.setPlaybackRate()` for:
- **Instant tempo changes** (0ms delay)
- **Real-time response** to BPM adjustments
- Optional background processing for high-quality key-lock

---

## Implementation Strategy

### Phase 1: Instant Tempo (Playback Rate)
```python
def set_deck_tempo_realtime(self, new_bpm):
    """Instant tempo change using playback rate"""
    if self.original_bpm == 0:
        return
    
    # Calculate playback rate
    rate = new_bpm / self.original_bpm
    
    # Apply instantly
    self.player.setPlaybackRate(rate)
    self.current_bpm = new_bpm
```

**Pros:**
- ✅ **0ms delay** - instant response
- ✅ No file processing needed
- ✅ Works while playing

**Cons:**
- ⚠️ Changes pitch (chipmunk effect)
- ⚠️ Not suitable for large BPM changes

### Phase 2: Hybrid Approach (BEST)
```python
def set_deck_tempo_hybrid(self, new_bpm):
    """
    1. Apply playback rate INSTANTLY for immediate feedback
    2. Process high-quality key-locked version in background
    3. Swap to high-quality when ready
    """
    # Step 1: Instant feedback
    rate = new_bpm / self.original_bpm
    self.player.setPlaybackRate(rate)
    
    # Step 2: Background processing (if change > 5 BPM)
    if abs(new_bpm - self.original_bpm) > 5:
        self.start_background_quality_processing(new_bpm)
```

---

## Other Real-Time Optimizations

### 1. **EQ Changes**
Current: Debounced with timer
Optimized: **Direct audio filter application**

### 2. **Volume Changes** ✅
Already real-time via `QAudioOutput.setVolume()`

### 3. **Crossfader** ✅
Already real-time

### 4. **Waveform Updates**
Current: Updates every frame
Optimized: **Update only visible region**

---

## Performance Targets

| Feature | Current | Target | Status |
|---------|---------|--------|--------|
| BPM Change | 2-10s | <100ms | 🔴 TODO |
| EQ Change | ~200ms | <50ms | 🟡 OK |
| Volume Change | <10ms | <10ms | ✅ DONE |
| Crossfade | <10ms | <10ms | ✅ DONE |
| Waveform | Variable | 60 FPS | 🟡 OK |

---

## Implementation Order

1. ✅ **Remove debug logging** (huge performance gain)
2. 🔴 **Implement instant playback rate tempo**
3. 🔴 **Add background high-quality processing**
4. 🟡 **Optimize waveform rendering**
5. 🟡 **Profile and optimize hotspots**

---

## Code Changes Needed

### `deck_widgets.py`
```python
# Replace set_deck_tempo with:
def set_deck_tempo_instant(self, new_bpm):
    """Apply tempo change instantly using playback rate"""
    pass

def set_deck_tempo_quality(self, new_bpm):
    """Process high-quality key-locked version in background"""
    pass
```

### Add User Setting
```json
{
  "realtime_mode": true,  // Use instant playback rate
  "quality_mode": false   // Use background processing (slower)
}
```

---

## Testing Plan

1. **Test instant BPM changes** while playing
2. **Test large BPM changes** (±20 BPM)
3. **Test during mixing** (both decks playing)
4. **Measure latency** with audio analysis

---

**Next Step: Implement instant playback rate tempo changes**

