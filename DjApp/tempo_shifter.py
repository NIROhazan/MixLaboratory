"""
Professional Tempo/Pitch Shifting with Key Lock (Pitch Preservation)

This module provides HIGH-QUALITY audio tempo changes that maintain pitch:

ALGORITHMS USED:
1. Rubber Band Library - Professional phase vocoder with transient detection
   - Used in: Ableton Live, Pro Tools, Audacity
   - Quality: Excellent (industry standard)
   - Key Lock: Perfect pitch preservation
   - Speed: Moderate

2. librosa Phase Vocoder - STFT-based time-stretching with phase locking
   - Quality: Good (research-grade)
   - Key Lock: Good pitch preservation
   - Speed: Fast

3. Native C++ FFT - Basic time-domain stretching (fallback)
   - Quality: Basic (some artifacts)
   - Key Lock: Partial
   - Speed: Very fast

WHAT IS KEY LOCK (PITCH PRESERVATION)?
- Tempo changes WITHOUT changing pitch
- Essential for DJ mixing (keep songs in same key)
- Uses phase vocoder algorithm (Short-Time Fourier Transform)
- Maintains harmonic structure while changing speed

PHASE VOCODER EXPLAINED:
1. Split audio into short time windows (frames)
2. Analyze frequency content with FFT
3. Adjust timing while maintaining phase relationships
4. Reconstruct audio with preserved pitch
5. Result: Tempo change without "chipmunk effect"
"""

import os
import numpy as np
import logging
import soundfile as sf

logger = logging.getLogger(__name__)

# Try importing pyrubberband (best quality)
try:
    import pyrubberband as pyrb
    PYRUBBERBAND_AVAILABLE = True
    logger.info("pyrubberband available - using professional Rubber Band Library")
except ImportError:
    PYRUBBERBAND_AVAILABLE = False
    logger.warning("pyrubberband not available. Install with: pip install pyrubberband")

# librosa is already required for key detection
try:
    import librosa
    LIBROSA_AVAILABLE = True
    logger.info("librosa available for time-stretching")
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not available")


class TempoShifter:
    """
    Professional audio tempo and pitch shifting with multiple engine support.
    """
    
    def __init__(self, native_bridge=None):
        """
        Initialize tempo shifter.
        
        Args:
            native_bridge: Optional AudioAnalyzerBridge for fallback C++ tempo changes.
        """
        self.native_bridge = native_bridge
        
        # Determine best available engine
        if PYRUBBERBAND_AVAILABLE:
            self.default_engine = "rubberband"
            logger.info("Default engine: Rubber Band (professional quality)")
        elif LIBROSA_AVAILABLE:
            self.default_engine = "librosa"
            logger.info("Default engine: librosa (good quality)")
        elif native_bridge and native_bridge.is_available():
            self.default_engine = "native"
            logger.info("Default engine: Native C++ (basic quality)")
        else:
            self.default_engine = None
            logger.error("No tempo change engines available!")
    
    def change_tempo(self, input_file: str, output_file: str, stretch_factor: float, 
                     engine: str = "auto", preserve_pitch: bool = True) -> bool:
        """
        Change audio tempo with time-stretching.
        
        Args:
            input_file (str): Input audio file path.
            output_file (str): Output audio file path.
            stretch_factor (float): Stretch factor (>1 slows down, <1 speeds up).
            engine (str): Engine to use - "rubberband", "librosa", "native", or "auto" (default best).
            preserve_pitch (bool): Whether to preserve pitch (True) or shift it with tempo (False).
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if engine == "auto":
            engine = self.default_engine
        
        if engine is None:
            logger.error("No tempo change engine available")
            return False
        
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Route to appropriate engine
            if engine == "rubberband":
                return self._change_tempo_rubberband(input_file, output_file, stretch_factor)
            elif engine == "librosa":
                return self._change_tempo_librosa(input_file, output_file, stretch_factor)
            elif engine == "native":
                return self._change_tempo_native(input_file, output_file, stretch_factor)
            else:
                logger.error(f"Unknown engine: {engine}")
                return False
        
        except Exception as e:
            logger.error(f"Tempo change failed: {e}", exc_info=True)
            return False
    
    def _change_tempo_rubberband(self, input_file: str, output_file: str, stretch_factor: float) -> bool:
        """
        Change tempo using Rubber Band Library (best quality).
        
        Uses industry-standard Rubber Band Library used in professional DAWs.
        """
        if not PYRUBBERBAND_AVAILABLE:
            logger.warning("Rubber Band not available, falling back")
            return self._change_tempo_librosa(input_file, output_file, stretch_factor)
        
        try:
            logger.info(f"Rubber Band: Processing {os.path.basename(input_file)}, factor={stretch_factor:.3f}")
            
            # Load audio
            y, sr = sf.read(input_file, dtype='float32')
            
            # Handle mono/stereo
            if y.ndim == 1:
                y = y.reshape(-1, 1)  # Make it 2D for pyrubberband
            
            # Apply time stretch (Rubber Band preserves pitch by default)
            y_stretched = pyrb.time_stretch(y, sr, stretch_factor)
            
            # Ensure output is 2D for soundfile
            if y_stretched.ndim == 1:
                y_stretched = y_stretched.reshape(-1, 1)
            
            # Save stretched audio
            sf.write(output_file, y_stretched, sr, subtype='PCM_16')
            
            logger.info(f"Rubber Band: Success! Output: {os.path.basename(output_file)}")
            return True
        
        except Exception as e:
            logger.error(f"Rubber Band error: {e}")
            return False
    
    def _change_tempo_librosa(self, input_file: str, output_file: str, stretch_factor: float) -> bool:
        """
        Change tempo using librosa phase vocoder with key lock (good quality, fast).
        
        Uses librosa's phase vocoder time-stretching which preserves pitch (key lock).
        This is a professional-grade algorithm that maintains audio quality.
        """
        if not LIBROSA_AVAILABLE:
            logger.warning("librosa not available, falling back to native")
            return self._change_tempo_native(input_file, output_file, stretch_factor)
        
        try:
            logger.info(f"🎵 librosa Phase Vocoder: {os.path.basename(input_file)}, factor={stretch_factor:.3f}")
            
            # Load audio with librosa (preserves original sample rate)
            y, sr = librosa.load(input_file, sr=None, mono=False)
            
            # Calculate rate (librosa uses inverse notation)
            # stretch_factor > 1 = slower (more stretched)
            # stretch_factor < 1 = faster (compressed)
            # librosa rate > 1 = faster, rate < 1 = slower
            # So: rate = 1 / stretch_factor
            rate = 1.0 / stretch_factor
            
            logger.info(f"   Sample rate: {sr} Hz, Rate: {rate:.3f}x, Channels: {y.ndim}")
            
            # Apply phase vocoder time stretch with key lock (pitch preservation)
            if y.ndim == 2:
                # Stereo processing - preserve spatial image
                logger.info("   Processing stereo (2 channels)")
                y_stretched = np.array([
                    librosa.effects.time_stretch(y[0], rate=rate),
                    librosa.effects.time_stretch(y[1], rate=rate)
                ])
                # Transpose to (samples, channels) for soundfile
                y_stretched = y_stretched.T
            else:
                # Mono processing
                logger.info("   Processing mono (1 channel)")
                y_stretched = librosa.effects.time_stretch(y, rate=rate)
            
            # Normalize to prevent clipping (optional, helps with quality)
            max_val = np.abs(y_stretched).max()
            if max_val > 0.95:  # Near clipping
                y_stretched = y_stretched * (0.95 / max_val)
                logger.info(f"   Normalized audio (peak was {max_val:.2f})")
            
            # Save with high quality settings
            sf.write(output_file, y_stretched, sr, subtype='PCM_16')
            
            output_duration = len(y_stretched) / sr
            logger.info(f"✅ librosa: Success! Duration: {output_duration:.2f}s")
            return True
        
        except Exception as e:
            logger.error(f"❌ librosa error: {e}")
            # Fall back to native if available
            if self.native_bridge:
                logger.info("Falling back to native C++ tempo change")
                return self._change_tempo_native(input_file, output_file, stretch_factor)
            return False
    
    def _change_tempo_native(self, input_file: str, output_file: str, stretch_factor: float) -> bool:
        """
        Change tempo using native C++ library (basic quality, fast).
        
        Fallback to original native implementation.
        """
        if not self.native_bridge or not self.native_bridge.is_available():
            logger.error("Native bridge not available")
            return False
        
        try:
            logger.info(f"Native: Processing {os.path.basename(input_file)}, factor={stretch_factor:.3f}")
            
            # Get audio length
            info = sf.info(input_file)
            length_seconds = info.duration
            
            # Call native library
            success = self.native_bridge.change_tempo(
                input_file, output_file, stretch_factor, length_seconds
            )
            
            if success:
                logger.info(f"Native: Success! Output: {os.path.basename(output_file)}")
            else:
                logger.error("Native tempo change reported failure")
            
            return success
        
        except Exception as e:
            logger.error(f"Native tempo change error: {e}")
            return False
    
    def pitch_shift(self, input_file: str, output_file: str, semitones: int, engine: str = "auto") -> bool:
        """
        Shift pitch without changing tempo.
        
        Args:
            input_file (str): Input audio file path.
            output_file (str): Output audio file path.
            semitones (int): Number of semitones to shift (positive = up, negative = down).
            engine (str): Engine to use - "rubberband", "librosa", or "auto".
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if engine == "auto":
            engine = self.default_engine if self.default_engine != "native" else "librosa"
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            if engine == "rubberband" and PYRUBBERBAND_AVAILABLE:
                return self._pitch_shift_rubberband(input_file, output_file, semitones)
            elif LIBROSA_AVAILABLE:
                return self._pitch_shift_librosa(input_file, output_file, semitones)
            else:
                logger.error("No pitch shift engine available")
                return False
        
        except Exception as e:
            logger.error(f"Pitch shift failed: {e}", exc_info=True)
            return False
    
    def _pitch_shift_rubberband(self, input_file: str, output_file: str, semitones: int) -> bool:
        """Pitch shift using Rubber Band."""
        try:
            logger.info(f"Rubber Band: Pitch shifting by {semitones:+d} semitones")
            
            y, sr = sf.read(input_file, dtype='float32')
            
            if y.ndim == 1:
                y = y.reshape(-1, 1)
            
            # Rubber Band pitch shift
            y_shifted = pyrb.pitch_shift(y, sr, semitones)
            
            if y_shifted.ndim == 1:
                y_shifted = y_shifted.reshape(-1, 1)
            
            sf.write(output_file, y_shifted, sr, subtype='PCM_16')
            logger.info("Rubber Band pitch shift: Success!")
            return True
        
        except Exception as e:
            logger.error(f"Rubber Band pitch shift error: {e}")
            return False
    
    def _pitch_shift_librosa(self, input_file: str, output_file: str, semitones: int) -> bool:
        """Pitch shift using librosa."""
        try:
            logger.info(f"librosa: Pitch shifting by {semitones:+d} semitones")
            
            y, sr = librosa.load(input_file, sr=None, mono=False)
            
            # Apply pitch shift
            if y.ndim == 2:
                y_shifted = np.array([
                    librosa.effects.pitch_shift(y[0], sr=sr, n_steps=semitones),
                    librosa.effects.pitch_shift(y[1], sr=sr, n_steps=semitones)
                ])
                y_shifted = y_shifted.T
            else:
                y_shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)
            
            sf.write(output_file, y_shifted, sr, subtype='PCM_16')
            logger.info("librosa pitch shift: Success!")
            return True
        
        except Exception as e:
            logger.error(f"librosa pitch shift error: {e}")
            return False
    
    def get_available_engines(self) -> list:
        """Get list of available engines."""
        engines = []
        if PYRUBBERBAND_AVAILABLE:
            engines.append("rubberband")
        if LIBROSA_AVAILABLE:
            engines.append("librosa")
        if self.native_bridge and self.native_bridge.is_available():
            engines.append("native")
        return engines
    
    def get_recommended_engine(self) -> str:
        """Get recommended engine based on quality vs speed."""
        return self.default_engine or "none"

