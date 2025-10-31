import os
# PyQt6 Imports
from PyQt6.QtWidgets import (QDialog, QListWidget, QListWidgetItem, QLabel, 
                           QVBoxLayout, QHBoxLayout, QPushButton, QWidget, 
                           QSizePolicy, QMessageBox, QComboBox, QLineEdit)
from PyQt6.QtCore import QSize, pyqtSignal, QThread, Qt


class BPMAnalyzerThread(QThread):
    """
    Thread for analyzing BPM and musical keys of audio files in the background.
    Emits signals when analysis is complete for each file.
    """
    # Signals to update UI when analysis is complete
    bpm_analyzed = pyqtSignal(str, float)  # file, bpm
    key_analyzed = pyqtSignal(str, str, float)  # file, key, confidence
    analysis_completed = pyqtSignal()

    def __init__(self, audio_analyzer, directory, file_list, cache_manager=None):
        """
        Initialize the AudioAnalyzerThread.

        Args:
            audio_analyzer: Instance of AudioAnalyzerBridge or compatible analyzer.
            directory (str): Directory containing audio files.
            file_list (list): List of audio file names to analyze.
            cache_manager: Instance of AudioCacheManager for persistent caching.
        """
        super().__init__()
        self.audio_analyzer = audio_analyzer
        self.directory = directory
        self.file_list = file_list
        self.cache_manager = cache_manager
        self.running = True

    def run(self):
        """
        Run the BPM and Key analysis for each file in the list.
        Emits signals for each analysis type and when all analysis is completed.
        """
        for file in self.file_list:
            if not self.running:
                break

            try:
                if self.audio_analyzer:
                    file_path = os.path.join(self.directory, file)
                    
                    # Analyze BPM (fast)
                    bpm, _ = self.audio_analyzer.analyze_file(file_path)
                    
                    if bpm > 0:
                        # Pre-cache full track beat positions for later use
                        try:
                            full_track_beats = self.audio_analyzer.get_full_track_beat_positions_ms(file_path)
                            print(f"✅ BPM: {file} - {int(bpm)} BPM, {len(full_track_beats)} beats")
                        except Exception as beat_error:
                            print(f"⚠️  Beat analysis failed for {file}: {beat_error}")
                            
                        # Emit BPM signal
                        self.bpm_analyzed.emit(file, bpm)
                    
                    # Detect musical key (slower, but essential for harmonic mixing)
                    try:
                        key, confidence = self.audio_analyzer.detect_key(file_path)
                        if key:
                            print(f"🎹 Key: {file} - {key} ({confidence:.0%} confidence)")
                            
                            # Cache the key data for future use
                            if self.cache_manager:
                                self.cache_manager.cache_key_data(file_path, key, confidence)
                            
                            # Emit key signal
                            self.key_analyzed.emit(file, key, confidence)
                    except Exception as key_error:
                        print(f"⚠️  Key detection failed for {file}: {key_error}")
                    
            except Exception as e:
                print(f"Thread BPM analysis error for {file}: {str(e)}")

        # Signal that all files have been analyzed
        self.analysis_completed.emit()

    def stop(self):
        """
        Stop the BPM analysis thread.
        """
        self.running = False
    
    def add_files(self, new_files):
        """
        Add new files to the analysis queue.
        
        Args:
            new_files (list): List of new file names to analyze.
        """
        # Extend the file list with new files
        self.file_list.extend(new_files)

class FileBrowserDialog(QDialog):
    """
    Dialog for browsing and selecting audio files, with BPM analysis and deck loading support.
    """
    # Define signal to emit when a file is selected for loading
    file_selected = pyqtSignal(int, str)
    bpm_analyzed = pyqtSignal(str, float)  # Signal for BPM analysis
    key_analyzed = pyqtSignal(str, str, float)  # Signal for key analysis (file_path, key, confidence)

    def __init__(self, directory, parent=None, audio_analyzer=None, cache_manager=None):
        """
        Initialize the FileBrowserDialog.

        Args:
            directory (str): Directory to display.
            parent (QWidget, optional): Parent widget.
            audio_analyzer: Instance of AudioAnalyzerBridge or compatible analyzer.
            cache_manager: Instance of AudioCacheManager for persistent caching.
        """
        super().__init__(parent)
        self.directory = directory
        self.audio_analyzer = audio_analyzer
        self.cache_manager = cache_manager  # Use provided cache manager
        self.track_items = {}
        self.bpm_cache = {}
        self.key_cache = {}  # Cache for musical keys
        self.status_label = QLabel("Select an audio directory first.")
        self.analyzer_thread = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(600, 400) # Adjusted minimum size
        self.initUI()
        
        # Set proper window title and populate list if directory is provided
        if self.directory and os.path.isdir(self.directory):
            self.setWindowTitle(f"Track List - {os.path.basename(directory)}")
            self.populate_file_list()
        else:
            self.setWindowTitle("Track List")

    def resizeEvent(self, event):
        """
        Handle dialog resize events to adjust item sizes.

        Args:
            event: The QResizeEvent instance.
        """
        super().resizeEvent(event)
        if hasattr(self, 'list_widget'):
            width = self.width()
            item_height = 150
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item:
                    item.setSizeHint(QSize(width - 40, item_height))

    def initUI(self):
        """
        Initialize the user interface for the file browser dialog.
        """
        # Set class for external stylesheet
        self.setProperty("class", "fileBrowserDialog")
        self.setStyle(self.style())  # Force style update
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Add status label at the top
        self.status_label.setProperty("class", "fileBrowserStatus")
        self.status_label.setStyle(self.status_label.style())  # Force style update
        layout.addWidget(self.status_label)

        # Add search and sorting controls
        controls_layout = QHBoxLayout()
        
        # Search box
        search_label = QLabel("🔍 Search:")
        search_label.setProperty("class", "neonText")
        search_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to filter tracks...")
        self.search_box.setProperty("class", "neonBorder")
        self.search_box.textChanged.connect(self.filter_tracks)
        self.search_box.setMinimumWidth(200)
        self.search_box.setClearButtonEnabled(True)  # Add clear button
        
        controls_layout.addWidget(search_label)
        controls_layout.addWidget(self.search_box)
        controls_layout.addSpacing(20)
        
        # Sort dropdown
        sort_label = QLabel("Sort by:")
        sort_label.setProperty("class", "neonText")
        sort_label.setStyleSheet("font-size: 11px; font-weight: bold;")
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Name (A-Z)", "name_asc")
        self.sort_combo.addItem("Name (Z-A)", "name_desc")
        self.sort_combo.addItem("BPM (Low-High)", "bpm_asc")
        self.sort_combo.addItem("BPM (High-Low)", "bpm_desc")
        self.sort_combo.addItem("Key (A-Z)", "key_asc")
        self.sort_combo.addItem("Key (Z-A)", "key_desc")
        self.sort_combo.addItem("Duration (Short-Long)", "duration_asc")
        self.sort_combo.addItem("Duration (Long-Short)", "duration_desc")
        self.sort_combo.currentIndexChanged.connect(self.sort_tracks)
        self.sort_combo.setProperty("class", "neonBorder")
        
        controls_layout.addWidget(sort_label)
        controls_layout.addWidget(self.sort_combo)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        self.list_widget = QListWidget()
        self.list_widget.setProperty("class", "fileBrowserList")
        self.list_widget.setStyle(self.list_widget.style())  # Force style update
        layout.addWidget(self.list_widget)
        # self.setLayout(layout) # Set layout automatically via self
        
        # Store current sorting preference
        self.current_sort = "name_asc"
        self.track_metadata = []  # Store track metadata for sorting

    def set_directory(self, directory):
        """
        Set the directory and repopulate the list.

        Args:
            directory (str): Directory to display.
        """
        self.directory = directory
        if self.directory and os.path.isdir(self.directory):
             self.setWindowTitle(f"Track List - {os.path.basename(directory)}")
             self.populate_file_list()
        else:
             self.setWindowTitle("Track List")
             self.list_widget.clear()
             self.status_label.setText("Invalid directory selected.")
             self.directory = None

    def closeEvent(self, event):
        """
        Handle dialog close event to stop any running thread.

        Args:
            event: The QCloseEvent instance.
        """
        if self.analyzer_thread and self.analyzer_thread.isRunning():
            self.analyzer_thread.stop()
            self.analyzer_thread.wait()
        super().closeEvent(event) # Call base class method

    def filter_tracks(self):
        """
        Filter tracks based on search box text.
        """
        search_text = self.search_box.text().lower().strip()
        
        if not search_text:
            # Show all tracks if search is empty
            self.rebuild_track_list()
            return
        
        # Filter tracks by filename
        filtered_tracks = [
            track for track in self.track_metadata
            if search_text in track['filename'].lower()
        ]
        
        # Rebuild list with filtered tracks
        self.list_widget.clear()
        for track in filtered_tracks:
            self._add_track_widget_only(
                track['filename'], 
                track['bpm'], 
                track['key'], 
                track['key_confidence'],
                track['duration']
            )
        
        # Update status label
        if filtered_tracks:
            self.status_label.setText(f"Found {len(filtered_tracks)} track(s) matching '{search_text}'")
        else:
            self.status_label.setText(f"No tracks found matching '{search_text}'")
    
    def rebuild_track_list(self):
        """
        Rebuild the track list with all tracks (used after clearing search).
        """
        self.list_widget.clear()
        for track in self.track_metadata:
            self._add_track_widget_only(
                track['filename'], 
                track['bpm'], 
                track['key'], 
                track['key_confidence'],
                track['duration']
            )
        
        # Update status
        if self.track_metadata:
            self.status_label.setText(f"Showing all {len(self.track_metadata)} tracks")

    def sort_tracks(self):
        """
        Sort the track list based on the selected criterion.
        """
        sort_type = self.sort_combo.currentData()
        if not sort_type or not self.track_metadata:
            return
        
        self.current_sort = sort_type
        
        # Sort track metadata
        if sort_type == "name_asc":
            self.track_metadata.sort(key=lambda x: x['filename'].lower())
        elif sort_type == "name_desc":
            self.track_metadata.sort(key=lambda x: x['filename'].lower(), reverse=True)
        elif sort_type == "bpm_asc":
            self.track_metadata.sort(key=lambda x: (x['bpm'] if x['bpm'] > 0 else 999999, x['filename'].lower()))
        elif sort_type == "bpm_desc":
            self.track_metadata.sort(key=lambda x: (x['bpm'] if x['bpm'] > 0 else 0), reverse=True)
        elif sort_type == "key_asc":
            self.track_metadata.sort(key=lambda x: (x['key'] if x['key'] else 'ZZZ', x['filename'].lower()))
        elif sort_type == "key_desc":
            self.track_metadata.sort(key=lambda x: (x['key'] if x['key'] else '', x['filename'].lower()), reverse=True)
        elif sort_type == "duration_asc":
            self.track_metadata.sort(key=lambda x: (x['duration'] if x['duration'] > 0 else 999999, x['filename'].lower()))
        elif sort_type == "duration_desc":
            self.track_metadata.sort(key=lambda x: (x['duration'] if x['duration'] > 0 else 0), reverse=True)
        
        # After sorting, apply current search filter if any
        search_text = self.search_box.text().lower().strip()
        if search_text:
            # Re-apply the filter with sorted data
            self.filter_tracks()
        else:
            # Rebuild UI list in sorted order
            self.rebuild_track_list()

    def populate_file_list(self):
        """
        Populates the list with audio files in the selected folder.
        """
        self.list_widget.clear()
        self.track_items = {}
        self.track_metadata = []  # Reset metadata for new directory

        if not self.directory or not os.path.isdir(self.directory):
            self.status_label.setText("No valid directory selected.")
            return

        # Get all audio files (add more formats if needed)
        audio_files = []
        try:
            for file in os.listdir(self.directory):
                if file.lower().endswith((".mp3", ".wav", ".flac")):
                    audio_files.append(file)
        except OSError as e:
            self.status_label.setText(f"Error accessing directory: {e}")
            return

        if not audio_files:
            self.status_label.setText("No compatible audio tracks found.")
            QMessageBox.information(self, "No Audio Files", "No compatible audio tracks found in the selected directory.")
            return

        # First check cache and create UI elements for all files
        files_to_analyze = []
        cached_from_persistent = 0
        cached_from_memory = 0
        
        # Create log file for debugging (UTF-8 encoding for emoji support)
        log_file_path = os.path.join(self.directory, "track_list_debug.log")
        with open(log_file_path, 'w', encoding='utf-8') as log:
            log.write("=== TRACK LIST DEBUG LOG ===\n\n")
        
        for file in audio_files:
            full_path = os.path.join(self.directory, file)
            cached_bpm = 0
            cached_key = ""
            cached_key_confidence = 0.0
            
            with open(log_file_path, 'a', encoding='utf-8') as log:
                log.write(f"\n--- Processing: {file} ---\n")
                log.write(f"Full path: {full_path}\n")
            
            # Check persistent cache for BPM
            if self.cache_manager:
                cached_data = self.cache_manager.get_bpm_data(full_path)
                if cached_data and cached_data[0] is not None:
                    cached_bpm = cached_data[0]
                    self.bpm_cache[full_path] = cached_bpm
                    cached_from_persistent += 1
                
                with open(log_file_path, 'a', encoding='utf-8') as log:
                    log.write(f"BPM from cache: {cached_bpm}\n")
                
                # Check persistent cache for Key
                key_data = self.cache_manager.get_key_data(full_path)
                
                with open(log_file_path, 'a', encoding='utf-8') as log:
                    log.write(f"Key data from cache: {key_data}\n")
                
                if key_data:
                    cached_key = key_data[0] if key_data[0] else ""
                    cached_key_confidence = key_data[1] if len(key_data) > 1 else 0.0
                    if cached_key:  # Only cache if key is not empty
                        self.key_cache[full_path] = (cached_key, cached_key_confidence)
                        
                        with open(log_file_path, 'a', encoding='utf-8') as log:
                            log.write(f"✅ Key loaded: {cached_key}, confidence: {cached_key_confidence}\n")
            
            # If not in persistent cache, check in-memory cache
            if cached_bpm == 0:
                cached_bpm = self.bpm_cache.get(full_path, 0)
                if cached_bpm > 0:
                    cached_from_memory += 1
            
            if not cached_key and full_path in self.key_cache:
                cached_key, cached_key_confidence = self.key_cache[full_path]
            
            # Add track to list with BPM and Key if we have them
            has_cached_data = cached_bpm > 0 or cached_key
            
            with open(log_file_path, 'a', encoding='utf-8') as log:
                log.write(f"Adding to UI: BPM={cached_bpm}, Key='{cached_key}', Conf={cached_key_confidence}\n")
            
            if has_cached_data:
                self.add_track_to_list(file, cached_bpm, cached_key, cached_key_confidence)
            else:
                files_to_analyze.append(file)
                self.add_track_to_list(file, 0, "", 0.0)  # Add to UI without metadata

        cached_count = cached_from_persistent + cached_from_memory
        
        # Update status message based on cache and analysis state
        if cached_count > 0:
            if files_to_analyze:
                self.status_label.setText(f"{cached_count} tracks ready, analyzing {len(files_to_analyze)} more...")
            else:
                self.status_label.setText(f"All {cached_count} tracks ready!")
        else:
            self.status_label.setText(f"Analyzing {len(files_to_analyze)} tracks...")

        # Only start analysis thread if there are files that need analysis
        if files_to_analyze and self.audio_analyzer:
            # Create new analyzer thread only if one doesn't exist or isn't running
            if not self.analyzer_thread or not self.analyzer_thread.isRunning():
                self.analyzer_thread = BPMAnalyzerThread(
                    self.audio_analyzer, 
                    self.directory, 
                    files_to_analyze,
                    self.cache_manager  # Pass cache_manager for key persistence
                )
                self.analyzer_thread.bpm_analyzed.connect(self.update_track_bpm)
                self.analyzer_thread.key_analyzed.connect(self.update_track_key)
                self.analyzer_thread.analysis_completed.connect(self.analysis_completed)
                self.analyzer_thread.start()
            else:
                # If thread is already running, add new files to its queue
                self.analyzer_thread.add_files(files_to_analyze)
        else:
            # If all files were cached, mark as complete
            self.analysis_completed()              

    def add_track_to_list(self, file, bpm=0, key="", key_confidence=0.0, duration=0):
        """
        Add a track to the list widget with BPM, Key, and Duration information.

        Args:
            file (str): File name of the audio track.
            bpm (float, optional): BPM value if already known.
            key (str, optional): Musical key if already known.
            key_confidence (float, optional): Key detection confidence (0-1).
            duration (float, optional): Track duration in seconds.
        """
        # Store track metadata for sorting
        full_path = os.path.join(self.directory, file)
        
        # Get duration if not provided
        if duration == 0:
            try:
                import soundfile as sf
                with sf.SoundFile(full_path) as f:
                    duration = len(f) / f.samplerate
            except:
                duration = 0
        
        self.track_metadata.append({
            'filename': file,
            'bpm': bpm,
            'key': key,
            'key_confidence': key_confidence,
            'duration': duration,
            'full_path': full_path
        })
        
        # Add the visual widget
        self._add_track_widget_only(file, bpm, key, key_confidence, duration)
    
    def _add_track_widget_only(self, file, bpm=0, key="", key_confidence=0.0, duration=0):
        """
        Internal method: Add only the visual widget for a track without storing metadata.
        Used when rebuilding the list after sorting.
        """
        item = QListWidgetItem(self.list_widget)
        # Increase height to accommodate buttons with spacing
        item.setSizeHint(QSize(self.list_widget.width() - 40, 150))
        
        widget = QWidget()
        item_layout = QHBoxLayout(widget)
        item_layout.setContentsMargins(10, 10, 10, 20)  # Increased bottom margin
        item_layout.setSpacing(15)

        # Left side layout for file name and metadata
        left_layout = QVBoxLayout()
        left_layout.setSpacing(5)
        left_layout.setContentsMargins(0, 0, 0, 10)  # Added bottom margin
        
        # Track name
        base_name = os.path.splitext(os.path.basename(file))[0]
        file_label = QLabel(base_name)
        file_label.setProperty("class", "fileBrowserFileName")
        file_label.setStyle(file_label.style())  # Force style update
        file_label.setWordWrap(True)
        file_label.setToolTip(base_name)
        left_layout.addWidget(file_label)
        
        # Metadata line (BPM and Key)
        metadata_label = QLabel()
        metadata_label.setProperty("class", "fileBrowserMetadata")
        metadata_label.setWordWrap(True)
        metadata_label.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML rendering
        metadata_label.setVisible(True)  # ENSURE VISIBLE
        metadata_label.setMinimumHeight(20)  # Give it some space
        
        # Build metadata string - ALWAYS show something
        metadata_parts = []
        
        if bpm > 0:
            metadata_parts.append(f"🎵 {int(bpm)} BPM")
        else:
            metadata_parts.append(f"🎵 --- BPM")  # Show placeholder if no BPM
            
        if key:
            # Color-code by confidence
            if key_confidence > 0.7:
                key_color = "#00ff00"  # Green - high confidence
                confidence_icon = "✓"
            elif key_confidence > 0.5:
                key_color = "#ffff00"  # Yellow - medium confidence  
                confidence_icon = "~"
            else:
                key_color = "#ff6600"  # Orange - low confidence
                confidence_icon = "?"
            
            # Format key (remove Camelot notation from display for cleaner look)
            key_display = key.split('(')[0].strip() if '(' in key else key
            metadata_parts.append(f'🎹 <span style="color: {key_color};">{key_display} {confidence_icon}</span>')
        else:
            metadata_parts.append(f'🎹 <span style="color: #888;">---</span>')  # Show placeholder if no key
        
        # Add duration if available
        if duration > 0:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            metadata_parts.append(f"⏱️ {minutes}:{seconds:02d}")
        
        final_text = " | ".join(metadata_parts)
        metadata_label.setText(final_text)
        
        left_layout.addWidget(metadata_label)
        left_layout.addStretch()

        # Right side layout for buttons with fixed width
        buttons_layout = QHBoxLayout()  # Changed to QHBoxLayout for side by side buttons
        buttons_layout.setSpacing(15)  # Horizontal spacing between buttons
        buttons_layout.setContentsMargins(0, 5, 0, 15)
        
        button1 = QPushButton("Load Deck 1")
        button2 = QPushButton("Load Deck 2")
        button1.setFixedWidth(100)
        button2.setFixedWidth(100)
        
        # Set classes for external stylesheet
        button1.setProperty("class", "fileBrowserLoadButton")
        button2.setProperty("class", "fileBrowserLoadButton")
        button1.setStyle(button1.style())  # Force style update
        button2.setStyle(button2.style())  # Force style update
        
        buttons_layout.addWidget(button1)
        buttons_layout.addWidget(button2)

        # Connect buttons to emit the signal
        full_path = os.path.join(self.directory, file)
        button1.clicked.connect(lambda checked=False, p=full_path: self.file_selected.emit(1, p))
        button2.clicked.connect(lambda checked=False, p=full_path: self.file_selected.emit(2, p))

        # Wrap the horizontal button layout in a vertical layout to maintain alignment
        right_container = QVBoxLayout()
        right_container.addLayout(buttons_layout)
        right_container.addStretch()  # Push buttons to the top

        # Add layouts to main item layout
        item_layout.addLayout(left_layout, stretch=1)  # Give file name area more space
        item_layout.addLayout(right_container)  # Buttons take minimum needed space

        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

        # Store item for later updates (BPM and Key)
        self.track_items[file] = (item, file_label, metadata_label)

    def update_track_bpm(self, file, bpm):
        """
        Update the BPM display for a track after background analysis.

        Args:
            file (str): File name of the audio track.
            bpm (float): BPM value.
        """
        if file in self.track_items and bpm > 0:
            # Cache the BPM result
            full_path = os.path.join(self.directory, file)
            self.bpm_cache[full_path] = bpm
            
            item, file_label, metadata_label = self.track_items[file]
            
            # Update metadata display
            self._update_track_metadata(file)

            # Update status to show progress
            analyzed_count = sum(1 for _, _, meta_lbl in self.track_items.values()
                               if "BPM" in meta_lbl.text())
            total_count = len(self.track_items)
            remaining = total_count - analyzed_count
            
            if remaining > 0:
                self.status_label.setText(f"Analyzing BPM: {analyzed_count} done, {remaining} remaining...")
            else:
                self.status_label.setText(f"All {total_count} tracks analyzed!")
            
            # Emit signal for the main app to update its cache
            self.bpm_analyzed.emit(full_path, bpm)
    
    def update_track_key(self, file, key, confidence):
        """
        Update the musical key display for a track after background analysis.

        Args:
            file (str): File name of the audio track.
            key (str): Musical key string (e.g., "C Major (8B)").
            confidence (float): Detection confidence (0-1).
        """
        print(f"🎹 update_track_key called: file={file}, key={key}, confidence={confidence}")  # DEBUG
        
        if file in self.track_items and key:
            # Cache the key result
            full_path = os.path.join(self.directory, file)
            self.key_cache[full_path] = (key, confidence)
            
            print(f"✅ Updating UI for {file} with key: {key}")  # DEBUG
            
            # Update metadata display
            self._update_track_metadata(file)
            
            # Emit signal to update main app
            self.key_analyzed.emit(full_path, key, confidence)
        else:
            print(f"⚠️  Cannot update key - file not in track_items or key empty")  # DEBUG
    
    def _update_track_metadata(self, file):
        """
        Update the metadata display (BPM and Key) for a track.

        Args:
            file (str): File name of the audio track.
        """
        if file not in self.track_items:
            print(f"❌ _update_track_metadata: {file} not in track_items")  # DEBUG
            return
        
        item, file_label, metadata_label = self.track_items[file]
        full_path = os.path.join(self.directory, file)
        
        print(f"🔄 Updating metadata for: {file}")  # DEBUG
        
        # Build metadata string - ALWAYS show something
        metadata_parts = []
        
        # Add BPM if available
        if full_path in self.bpm_cache:
            bpm = self.bpm_cache[full_path]
            metadata_parts.append(f"🎵 {int(bpm)} BPM")
            print(f"  BPM: {int(bpm)}")  # DEBUG
        else:
            metadata_parts.append(f"🎵 --- BPM")
        
        # Add Key if available
        if full_path in self.key_cache:
            key, confidence = self.key_cache[full_path]
            
            print(f"  Key found in cache: {key} (confidence: {confidence})")  # DEBUG
            
            # Color-code by confidence
            if confidence > 0.7:
                key_color = "#00ff00"  # Green - high confidence
                confidence_icon = "✓"
            elif confidence > 0.5:
                key_color = "#ffff00"  # Yellow - medium confidence
                confidence_icon = "~"
            else:
                key_color = "#ff6600"  # Orange - low confidence
                confidence_icon = "?"
            
            # Format key (remove Camelot notation for cleaner display)
            key_display = key.split('(')[0].strip() if '(' in key else key
            metadata_parts.append(f'🎹 <span style="color: {key_color};">{key_display} {confidence_icon}</span>')
        else:
            metadata_parts.append(f'🎹 <span style="color: #888;">---</span>')
            print(f"  No key in cache yet")  # DEBUG
        
        # Update label
        final_text = " | ".join(metadata_parts)
        print(f"  Setting label text: {final_text}")  # DEBUG
        metadata_label.setText(final_text)
        metadata_label.update()  # Force UI update

    def analysis_completed(self):
        """
        Called when all tracks have been analyzed.
        """
        # Simple completion message - detailed status already handled in update_track_bpm
        self.status_label.setText("Analysis complete!")

    def get_cached_bpm(self, file_path):
        """
        Get cached BPM for a file if available.

        Args:
            file_path (str): Path to the audio file.
        Returns:
            float: Cached BPM value or 0 if not available.
        """
        return self.bpm_cache.get(file_path, 0)

 