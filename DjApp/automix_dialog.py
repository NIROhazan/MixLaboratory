"""
Auto-Mix Dialog for MixLab DJ

Provides a UI for AI-powered playlist generation and automatic mixing.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QProgressBar, QListWidget, QListWidgetItem, QComboBox,
    QSpinBox, QCheckBox, QGroupBox, QFileDialog, QMessageBox,
    QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from automix_engine import AutoMixEngine, TrackInfo


class FolderAnalysisWorker(QThread):
    """
    Background worker for analyzing tracks in a folder.
    """
    progress_update = pyqtSignal(str, int, int)  # filename, current, total
    analysis_complete = pyqtSignal(list)  # List of TrackInfo
    error_occurred = pyqtSignal(str)
    
    def __init__(self, automix_engine, folder_path):
        super().__init__()
        self.automix_engine = automix_engine
        self.folder_path = folder_path
        self.running = True
    
    def run(self):
        """Run folder analysis in background thread."""
        try:
            tracks = self.automix_engine.analyze_folder(
                self.folder_path,
                progress_callback=self._progress_callback
            )
            
            if self.running:
                self.analysis_complete.emit(tracks)
        
        except Exception as e:
            if self.running:
                self.error_occurred.emit(str(e))
    
    def _progress_callback(self, filename, current, total):
        """Forward progress updates to UI thread."""
        if self.running:
            self.progress_update.emit(filename, current, total)
    
    def stop(self):
        """Stop the analysis thread."""
        self.running = False


class AutoMixDialog(QDialog):
    """
    Dialog for configuring and running AI-powered auto-mix.
    """
    playlist_ready = pyqtSignal(list)  # Emits playlist when ready
    
    def __init__(self, audio_analyzer, parent=None):
        super().__init__(parent)
        self.audio_analyzer = audio_analyzer
        self.automix_engine = AutoMixEngine(audio_analyzer)
        self.current_playlist = []
        self.analysis_worker = None
        
        self.setWindowTitle("AI-Powered Auto-Mix")
        self.setMinimumSize(800, 700)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("🎵 AI-Powered Auto-Mix Playlist Generator")
        title_label.setProperty("class", "neonText")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #F3CF2C;")
        layout.addWidget(title_label)
        
        # Step 1: Folder Selection
        folder_group = QGroupBox("Step 1: Select Music Folder")
        folder_layout = QVBoxLayout(folder_group)
        
        folder_select_layout = QHBoxLayout()
        self.folder_path_label = QLabel("No folder selected")
        self.folder_path_label.setWordWrap(True)
        folder_select_btn = QPushButton("Browse...")
        folder_select_btn.clicked.connect(self.select_folder)
        
        folder_select_layout.addWidget(self.folder_path_label, 1)
        folder_select_layout.addWidget(folder_select_btn)
        folder_layout.addLayout(folder_select_layout)
        
        # Analysis progress
        self.analysis_progress_label = QLabel("Ready to analyze")
        self.analysis_progress_bar = QProgressBar()
        self.analysis_progress_bar.setValue(0)
        
        analyze_btn = QPushButton("Analyze Tracks")
        analyze_btn.clicked.connect(self.start_analysis)
        
        folder_layout.addWidget(self.analysis_progress_label)
        folder_layout.addWidget(self.analysis_progress_bar)
        folder_layout.addWidget(analyze_btn)
        
        layout.addWidget(folder_group)
        
        # Step 2: Playlist Configuration
        config_group = QGroupBox("Step 2: Configure Playlist")
        config_layout = QVBoxLayout(config_group)
        
        # Strategy selection
        strategy_layout = QHBoxLayout()
        strategy_label = QLabel("Mix Strategy:")
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "Optimal (Best Matches)",
            "Energy Up (Build Up)",
            "Energy Down (Wind Down)",
            "Key Journey (Harmonic Flow)"
        ])
        strategy_layout.addWidget(strategy_label)
        strategy_layout.addWidget(self.strategy_combo, 1)
        config_layout.addLayout(strategy_layout)
        
        # Playlist length
        length_layout = QHBoxLayout()
        length_label = QLabel("Number of Tracks:")
        self.length_spin = QSpinBox()
        self.length_spin.setMinimum(2)
        self.length_spin.setMaximum(100)
        self.length_spin.setValue(10)
        length_layout.addWidget(length_label)
        length_layout.addWidget(self.length_spin, 1)
        config_layout.addLayout(length_layout)
        
        # Crossfade time
        crossfade_layout = QHBoxLayout()
        crossfade_label = QLabel("Crossfade Duration (seconds):")
        self.crossfade_spin = QSpinBox()
        self.crossfade_spin.setMinimum(5)
        self.crossfade_spin.setMaximum(60)
        self.crossfade_spin.setValue(15)
        crossfade_layout.addWidget(crossfade_label)
        crossfade_layout.addWidget(self.crossfade_spin, 1)
        config_layout.addLayout(crossfade_layout)
        
        # Generate button
        generate_btn = QPushButton("Generate Playlist")
        generate_btn.clicked.connect(self.generate_playlist)
        config_layout.addWidget(generate_btn)
        
        layout.addWidget(config_group)
        
        # Step 3: Playlist View
        playlist_group = QGroupBox("Step 3: Review Generated Playlist")
        playlist_layout = QVBoxLayout(playlist_group)
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.setMinimumHeight(200)
        playlist_layout.addWidget(self.playlist_widget)
        
        # Playlist report
        report_btn = QPushButton("View Compatibility Report")
        report_btn.clicked.connect(self.show_compatibility_report)
        playlist_layout.addWidget(report_btn)
        
        layout.addWidget(playlist_group)
        
        # Bottom controls
        bottom_layout = QHBoxLayout()
        
        self.auto_play_checkbox = QCheckBox("Auto-play playlist")
        self.auto_play_checkbox.setChecked(True)
        bottom_layout.addWidget(self.auto_play_checkbox)
        
        bottom_layout.addStretch()
        
        load_playlist_btn = QPushButton("Load Playlist")
        load_playlist_btn.clicked.connect(self.load_playlist)
        load_playlist_btn.setStyleSheet("background: #F3CF2C; color: black; font-weight: bold; padding: 8px;")
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        
        bottom_layout.addWidget(load_playlist_btn)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    def select_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Music Folder",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.folder_path_label.setText(folder)
            self.analysis_progress_label.setText("Folder selected. Click 'Analyze Tracks' to begin.")
    
    def start_analysis(self):
        """Start analyzing tracks in the selected folder."""
        folder_path = self.folder_path_label.text()
        
        if folder_path == "No folder selected":
            QMessageBox.warning(self, "No Folder", "Please select a music folder first.")
            return
        
        if not os.path.isdir(folder_path):
            QMessageBox.warning(self, "Invalid Folder", "The selected folder does not exist.")
            return
        
        # Disable UI during analysis
        self.analysis_progress_bar.setValue(0)
        self.analysis_progress_label.setText("Starting analysis...")
        
        # Start analysis in background thread
        self.analysis_worker = FolderAnalysisWorker(self.automix_engine, folder_path)
        self.analysis_worker.progress_update.connect(self.update_analysis_progress)
        self.analysis_worker.analysis_complete.connect(self.analysis_finished)
        self.analysis_worker.error_occurred.connect(self.analysis_error)
        self.analysis_worker.start()
    
    def update_analysis_progress(self, filename, current, total):
        """Update progress bar during analysis."""
        progress = int((current / total) * 100)
        self.analysis_progress_bar.setValue(progress)
        self.analysis_progress_label.setText(f"Analyzing: {filename} ({current}/{total})")
    
    def analysis_finished(self, tracks):
        """Handle completed folder analysis."""
        self.analysis_progress_bar.setValue(100)
        self.analysis_progress_label.setText(
            f"Analysis complete! {len(tracks)} tracks ready for playlist generation."
        )
        
        if len(tracks) == 0:
            QMessageBox.warning(
                self,
                "No Tracks Found",
                "No audio tracks were found or analyzed in the selected folder."
            )
    
    def analysis_error(self, error_msg):
        """Handle analysis errors."""
        self.analysis_progress_label.setText("Analysis failed!")
        QMessageBox.critical(
            self,
            "Analysis Error",
            f"Failed to analyze folder:\n{error_msg}"
        )
    
    def generate_playlist(self):
        """Generate playlist based on configuration."""
        if not self.automix_engine.track_database:
            QMessageBox.warning(
                self,
                "No Tracks",
                "Please analyze a folder first before generating a playlist."
            )
            return
        
        # Get strategy
        strategy_map = {
            0: "optimal",
            1: "energy_up",
            2: "energy_down",
            3: "key_journey"
        }
        strategy = strategy_map[self.strategy_combo.currentIndex()]
        
        # Get length
        length = self.length_spin.value()
        
        # Generate playlist
        try:
            self.current_playlist = self.automix_engine.generate_playlist(
                start_track=None,
                length=length,
                strategy=strategy
            )
            
            # Update playlist widget
            self.playlist_widget.clear()
            for idx, track in enumerate(self.current_playlist):
                # Calculate compatibility with next track
                compat_text = ""
                if idx < len(self.current_playlist) - 1:
                    next_track = self.current_playlist[idx + 1]
                    compat_score = self.automix_engine.calculate_compatibility_score(track, next_track)
                    
                    # Color code compatibility
                    if compat_score >= 0.8:
                        color = "#00ff00"  # Green
                        compat_emoji = "✓✓"
                    elif compat_score >= 0.6:
                        color = "#ffff00"  # Yellow
                        compat_emoji = "✓"
                    else:
                        color = "#ff6600"  # Orange
                        compat_emoji = "⚠"
                    
                    compat_text = f" {compat_emoji} ({compat_score:.0%})"
                
                # Create list item
                item_text = f"{idx + 1}. {track.filename}\n   BPM: {track.bpm:.1f}  |  Key: {track.key}{compat_text}"
                item = QListWidgetItem(item_text)
                
                # Set font
                font = item.font()
                font.setPointSize(9)
                item.setFont(font)
                
                self.playlist_widget.addItem(item)
            
            QMessageBox.information(
                self,
                "Playlist Generated",
                f"Successfully generated a {len(self.current_playlist)}-track playlist using '{strategy}' strategy!"
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Generation Error",
                f"Failed to generate playlist:\n{str(e)}"
            )
    
    def show_compatibility_report(self):
        """Show detailed compatibility report."""
        if not self.current_playlist:
            QMessageBox.information(
                self,
                "No Playlist",
                "Generate a playlist first to view the compatibility report."
            )
            return
        
        # Generate report
        report = self.automix_engine.export_playlist_report(self.current_playlist)
        
        # Show in dialog
        report_dialog = QDialog(self)
        report_dialog.setWindowTitle("Playlist Compatibility Report")
        report_dialog.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(report_dialog)
        
        report_text = QTextEdit()
        report_text.setReadOnly(True)
        report_text.setPlainText(report)
        report_text.setStyleSheet("font-family: monospace; font-size: 10pt;")
        
        layout.addWidget(report_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(report_dialog.close)
        layout.addWidget(close_btn)
        
        report_dialog.exec()
    
    def load_playlist(self):
        """Load the generated playlist into the main app."""
        if not self.current_playlist:
            QMessageBox.warning(
                self,
                "No Playlist",
                "Please generate a playlist first."
            )
            return
        
        # Emit playlist with settings
        self.playlist_ready.emit(self.current_playlist)
        self.accept()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Stop analysis worker if running
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.analysis_worker.stop()
            self.analysis_worker.wait(2000)  # Wait up to 2 seconds
        
        event.accept()

