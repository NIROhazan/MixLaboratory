"""
AI-Powered Auto-Mix Engine for MixLab DJ

This module provides intelligent playlist generation and track matching
using BPM compatibility and Camelot wheel harmonic mixing rules.
"""

import os
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TrackInfo:
    """
    Container for track metadata used in auto-mix analysis.
    """
    def __init__(self, file_path: str, bpm: float = 0, key: str = "", key_confidence: float = 0.0):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.bpm = bpm
        self.key = key
        self.key_confidence = key_confidence
        self.camelot = self._extract_camelot()
    
    def _extract_camelot(self) -> str:
        """Extract Camelot notation from key string (e.g., '8B' from 'C Major (8B)')."""
        if '(' in self.key and ')' in self.key:
            return self.key.split('(')[-1].strip(')')
        return ""
    
    def __repr__(self):
        return f"TrackInfo({self.filename}, BPM={self.bpm:.1f}, Key={self.key})"


class AutoMixEngine:
    """
    AI-powered engine for intelligent playlist generation and track matching.
    
    Uses harmonic mixing principles (Camelot wheel) and BPM compatibility
    to create smooth, professional DJ mixes.
    """
    
    # Camelot wheel compatibility rules for harmonic mixing
    CAMELOT_WHEEL = {
        '1A': ['1A', '2A', '12A', '1B'],    # Compatible keys
        '2A': ['2A', '3A', '1A', '2B'],
        '3A': ['3A', '4A', '2A', '3B'],
        '4A': ['4A', '5A', '3A', '4B'],
        '5A': ['5A', '6A', '4A', '5B'],
        '6A': ['6A', '7A', '5A', '6B'],
        '7A': ['7A', '8A', '6A', '7B'],
        '8A': ['8A', '9A', '7A', '8B'],
        '9A': ['9A', '10A', '8A', '9B'],
        '10A': ['10A', '11A', '9A', '10B'],
        '11A': ['11A', '12A', '10A', '11B'],
        '12A': ['12A', '1A', '11A', '12B'],
        '1B': ['1B', '2B', '12B', '1A'],
        '2B': ['2B', '3B', '1B', '2A'],
        '3B': ['3B', '4B', '2B', '3A'],
        '4B': ['4B', '5B', '3B', '4A'],
        '5B': ['5B', '6B', '4B', '5A'],
        '6B': ['6B', '7B', '5B', '6A'],
        '7B': ['7B', '8B', '6B', '7A'],
        '8B': ['8B', '9B', '7B', '8A'],
        '9B': ['9B', '10B', '8B', '9A'],
        '10B': ['10B', '11B', '9B', '10A'],
        '11B': ['11B', '12B', '10B', '11A'],
        '12B': ['12B', '1B', '11B', '12A'],
    }
    
    def __init__(self, audio_analyzer=None):
        """
        Initialize the AutoMix engine.
        
        Args:
            audio_analyzer: AudioAnalyzerBridge instance for track analysis.
        """
        self.audio_analyzer = audio_analyzer
        self.track_database: List[TrackInfo] = []
    
    def analyze_folder(self, folder_path: str, progress_callback=None) -> List[TrackInfo]:
        """
        Analyze all audio files in a folder for BPM and key.
        
        Args:
            folder_path (str): Path to folder containing audio files.
            progress_callback (callable): Optional callback for progress updates (file, current, total).
            
        Returns:
            List[TrackInfo]: List of analyzed tracks.
        """
        if not self.audio_analyzer:
            logger.error("No audio analyzer available for folder analysis")
            return []
        
        # Find all audio files
        audio_extensions = ('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma')
        audio_files = []
        
        try:
            for file in os.listdir(folder_path):
                if file.lower().endswith(audio_extensions):
                    audio_files.append(os.path.join(folder_path, file))
        except Exception as e:
            logger.error(f"Error reading folder {folder_path}: {e}")
            return []
        
        if not audio_files:
            logger.warning(f"No audio files found in {folder_path}")
            return []
        
        logger.info(f"Analyzing {len(audio_files)} tracks in {folder_path}")
        tracks = []
        
        for idx, file_path in enumerate(audio_files):
            try:
                # Progress callback
                if progress_callback:
                    progress_callback(os.path.basename(file_path), idx + 1, len(audio_files))
                
                # Analyze BPM
                bpm, _ = self.audio_analyzer.analyze_file(file_path)
                
                # Detect key
                key, confidence = self.audio_analyzer.detect_key(file_path)
                
                # Create track info
                track = TrackInfo(file_path, bpm, key, confidence)
                tracks.append(track)
                
                logger.info(f"Analyzed: {track.filename} - BPM={bpm:.1f}, Key={key}")
                
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
                continue
        
        self.track_database = tracks
        logger.info(f"Folder analysis complete: {len(tracks)} tracks ready")
        return tracks
    
    def calculate_compatibility_score(self, track1: TrackInfo, track2: TrackInfo) -> float:
        """
        Calculate compatibility score between two tracks (0.0 - 1.0).
        
        Higher score = better match for mixing.
        
        Scoring factors:
        - BPM compatibility (±6% is ideal, ±10% acceptable)
        - Camelot wheel harmonic compatibility
        - Key detection confidence
        
        Args:
            track1 (TrackInfo): First track.
            track2 (TrackInfo): Second track.
            
        Returns:
            float: Compatibility score (0.0 to 1.0).
        """
        score = 0.0
        
        # 1. BPM Compatibility (50% weight)
        if track1.bpm > 0 and track2.bpm > 0:
            bpm_diff_percent = abs(track1.bpm - track2.bpm) / track1.bpm * 100
            
            if bpm_diff_percent <= 6:
                # Perfect BPM match (within ±6%)
                bpm_score = 1.0
            elif bpm_diff_percent <= 10:
                # Acceptable match (within ±10%)
                bpm_score = 1.0 - (bpm_diff_percent - 6) / 4 * 0.3  # 0.7-1.0
            elif bpm_diff_percent <= 15:
                # Workable with adjustments
                bpm_score = 0.4 - (bpm_diff_percent - 10) / 5 * 0.4  # 0.0-0.4
            else:
                # Poor match
                bpm_score = 0.0
            
            score += bpm_score * 0.5
        else:
            # Missing BPM data - neutral score
            score += 0.25
        
        # 2. Harmonic Compatibility (40% weight) - Camelot wheel
        if track1.camelot and track2.camelot:
            if track1.camelot == track2.camelot:
                # Same key - perfect mix
                key_score = 1.0
            elif track2.camelot in self.CAMELOT_WHEEL.get(track1.camelot, []):
                # Harmonically compatible (adjacent, parallel, or energy boost)
                key_score = 0.9
            else:
                # Not harmonically compatible
                key_score = 0.2
            
            # Weight by key detection confidence
            avg_confidence = (track1.key_confidence + track2.key_confidence) / 2
            key_score *= avg_confidence
            
            score += key_score * 0.4
        else:
            # Missing key data - neutral score
            score += 0.20
        
        # 3. Energy/Genre matching bonus (10% weight)
        # For now, we use BPM as proxy for energy level
        if track1.bpm > 0 and track2.bpm > 0:
            # Prefer similar energy levels
            energy_diff = abs(track1.bpm - track2.bpm)
            if energy_diff <= 10:
                energy_score = 1.0
            elif energy_diff <= 20:
                energy_score = 0.5
            else:
                energy_score = 0.0
            
            score += energy_score * 0.1
        else:
            score += 0.05
        
        return min(1.0, score)  # Ensure score doesn't exceed 1.0
    
    def generate_playlist(self, start_track: Optional[TrackInfo] = None, 
                         length: int = 10, 
                         strategy: str = "optimal") -> List[TrackInfo]:
        """
        Generate an intelligently ordered playlist for smooth mixing.
        
        Args:
            start_track (TrackInfo, optional): Track to start with. If None, chooses best starting track.
            length (int): Number of tracks in playlist.
            strategy (str): Playlist generation strategy:
                - "optimal": Best harmonic and BPM matches (default)
                - "energy_up": Gradually increase BPM/energy
                - "energy_down": Gradually decrease BPM/energy
                - "key_journey": Focus on harmonic progression
        
        Returns:
            List[TrackInfo]: Ordered playlist.
        """
        if not self.track_database:
            logger.warning("No tracks in database for playlist generation")
            return []
        
        if length > len(self.track_database):
            length = len(self.track_database)
        
        # Choose starting track
        if start_track is None:
            # Start with a track with high confidence key detection and good BPM
            scored_tracks = []
            for track in self.track_database:
                # Prefer tracks with good metadata
                score = (track.key_confidence * 0.6) + (0.4 if 100 <= track.bpm <= 140 else 0.2)
                scored_tracks.append((score, track))
            
            scored_tracks.sort(reverse=True, key=lambda x: x[0])
            start_track = scored_tracks[0][1] if scored_tracks else self.track_database[0]
        
        playlist = [start_track]
        available_tracks = [t for t in self.track_database if t != start_track]
        
        # Build playlist track by track
        for _ in range(length - 1):
            if not available_tracks:
                break
            
            current_track = playlist[-1]
            best_next_track = None
            best_score = -1.0
            
            # Find best next track based on strategy
            for candidate in available_tracks:
                base_score = self.calculate_compatibility_score(current_track, candidate)
                
                # Apply strategy modifiers
                if strategy == "energy_up":
                    # Prefer tracks with slightly higher BPM
                    if candidate.bpm > current_track.bpm:
                        base_score *= 1.2
                    elif candidate.bpm < current_track.bpm - 5:
                        base_score *= 0.7
                
                elif strategy == "energy_down":
                    # Prefer tracks with slightly lower BPM
                    if candidate.bpm < current_track.bpm:
                        base_score *= 1.2
                    elif candidate.bpm > current_track.bpm + 5:
                        base_score *= 0.7
                
                elif strategy == "key_journey":
                    # Strong focus on harmonic compatibility
                    if candidate.camelot == current_track.camelot:
                        base_score *= 1.3
                    elif candidate.camelot in self.CAMELOT_WHEEL.get(current_track.camelot, []):
                        base_score *= 1.1
                
                # Track with best score wins
                if base_score > best_score:
                    best_score = base_score
                    best_next_track = candidate
            
            if best_next_track:
                playlist.append(best_next_track)
                available_tracks.remove(best_next_track)
            else:
                # No good match found, pick randomly from remaining
                if available_tracks:
                    playlist.append(available_tracks.pop(0))
        
        logger.info(f"Generated playlist with {len(playlist)} tracks using '{strategy}' strategy")
        return playlist
    
    def get_best_next_tracks(self, current_track: TrackInfo, count: int = 5) -> List[Tuple[TrackInfo, float]]:
        """
        Get the best matching tracks for the current track.
        
        Args:
            current_track (TrackInfo): Current playing track.
            count (int): Number of suggestions to return.
            
        Returns:
            List[Tuple[TrackInfo, float]]: List of (track, compatibility_score) pairs, sorted by score.
        """
        if not self.track_database:
            return []
        
        # Calculate scores for all tracks
        scored_tracks = []
        for track in self.track_database:
            if track == current_track:
                continue
            
            score = self.calculate_compatibility_score(current_track, track)
            scored_tracks.append((track, score))
        
        # Sort by score (descending)
        scored_tracks.sort(reverse=True, key=lambda x: x[1])
        
        # Return top N
        return scored_tracks[:count]
    
    def export_playlist_report(self, playlist: List[TrackInfo]) -> str:
        """
        Generate a detailed report of playlist compatibility.
        
        Args:
            playlist (List[TrackInfo]): Playlist to analyze.
            
        Returns:
            str: Formatted report text.
        """
        if not playlist:
            return "Empty playlist"
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("AUTO-MIX PLAYLIST REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        for idx, track in enumerate(playlist):
            report_lines.append(f"Track {idx + 1}: {track.filename}")
            report_lines.append(f"  BPM: {track.bpm:.1f}   Key: {track.key}")
            
            # Compatibility with next track
            if idx < len(playlist) - 1:
                next_track = playlist[idx + 1]
                compat_score = self.calculate_compatibility_score(track, next_track)
                report_lines.append(f"  → Compatibility with next track: {compat_score:.1%}")
            
            report_lines.append("")
        
        # Overall playlist stats
        avg_bpm = np.mean([t.bpm for t in playlist if t.bpm > 0])
        avg_confidence = np.mean([t.key_confidence for t in playlist if t.key_confidence > 0])
        
        report_lines.append("-" * 80)
        report_lines.append(f"Average BPM: {avg_bpm:.1f}")
        report_lines.append(f"Average Key Confidence: {avg_confidence:.1%}")
        report_lines.append(f"Total Tracks: {len(playlist)}")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)

