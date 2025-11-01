import sys
import os
import time
import traceback
import logging
import json

# Check Python version and dependencies before importing heavy modules
try:
    from version_check import check_python_version, check_dependencies, check_optional_features
    
    # Quick Python version check
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies (non-verbose for startup)
    all_ok, missing_req, missing_opt = check_dependencies(verbose=False)
    if not all_ok:
        print("\n❌ Missing required dependencies. Run: python version_check.py")
        print(f"   Missing: {', '.join(missing_req)}")
        sys.exit(1)
    
    # Show optional features status
    features, messages = check_optional_features()
    for msg in messages:
        if '⚠️' in msg or 'ℹ️' in msg:
            print(msg)
    
    # Auto-check for package updates (AI-powered)
    try:
        from auto_updater import quick_update_check
        quick_update_check()  # Silently checks, only warns if critical
    except ImportError:
        pass  # auto_updater not available
    except Exception as e:
        # Don't block app startup if update check fails
        pass

except ImportError:
    # version_check.py not available, continue anyway
    pass

import PyQt6
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QSizePolicy, QMessageBox,
    QLineEdit, QScrollArea, QDialog, QTabWidget, QButtonGroup, QRadioButton,
    QCheckBox,QListWidget,QListWidgetItem
)
from PyQt6.QtCore import (
    Qt, QTimer, QUrl, qInstallMessageHandler, QtMsgType
)
from PyQt6.QtGui import QPalette, QColor, QIcon
from PyQt6.QtMultimedia import QMediaDevices

# Suppress Qt CSS warnings for unsupported properties
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.stylesheet.warning=false'

from file_management import FileBrowserDialog

from audio_analyzer_bridge import AudioAnalyzerBridge
from cache_manager import AudioCacheManager
from deck_widgets import DeckWidget
from tutorial import TutorialManager, ConceptsGuide, HighlightOverlay
from PyQt6.QtGui import QIntValidator
from recording_worker import RealTimeRecordingWorker
from automix_dialog import AutoMixDialog
from automix_engine import TrackInfo
from debug_logger import debug, info, warning, error, success
import ctypes
import stat
import subprocess

class DJApp(QMainWindow):
    """
    Main DJ application window.
    
    This class represents the main application window and manages the overall DJ software,
    including dual deck controls, mixing features, recording capabilities, and UI layout.
    """

    def __init__(self):
        """
        Initialize the main DJ application window.
        """
        super().__init__()
        self.fonts = None
        self.colors = None
        self.setWindowTitle("MixLab DJ")

        self.tutorial_manager = TutorialManager(self)
        
        # Logo setup
        # Set AppUserModelID for Windows taskbar icon
        if sys.platform == 'win32':
            try:
                myappid = u'MixLab.DJApp.NoVersion' # An arbitrary but unique string for the app
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except AttributeError:
                print("Warning: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID not found. Taskbar icon might not be optimal on Windows.")
            except Exception as e:
                print(f"Warning: Error setting AppUserModelID for taskbar: {e}")

        # Determine the absolute path to the icon
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "MixLabLogo.png")
        self.setWindowIcon(QIcon(icon_path))
        
        self.audio_directory = None
        self.file_browser = None
        self.track_list_button = None
        
        # Add BPM cache
        self.bpm_cache = {}
        
        # Clean up any leftover temp files from previous sessions
        self._cleanup_all_temp_files()
        
        # Recording variables
        self.recording_folder = None
        self.is_recording = False
        self.recording_worker = None
        self.recording_file_path = None
        self.recordings_list = []  # Keep track of all recordings in this session
        
        # Sync state - Professional DJ sync system
        self.sync_master = None # None, 1, or 2
        self.sync_lock_enabled = True  # Maintains beat phase lock continuously
        self.quantize_enabled = True  # Snap actions to nearest beat
        self.keylock_enabled = True  # Maintain pitch when changing tempo
        
        # Beat phase monitoring for continuous sync
        self.beat_phase_monitor = QTimer(self)
        self.beat_phase_monitor.timeout.connect(self._monitor_beat_phase)
        self.beat_phase_monitor.setInterval(500)  # Check every 500ms (less aggressive)
        self.beat_phase_tolerance_ms = 150  # ±150ms tolerance before auto-correction
        self.last_phase_correction_time = 0  # Track last correction to prevent loops
        self.phase_correction_cooldown_ms = 3000  # 3 seconds cooldown between corrections
        self.last_phase_drift = 0  # Track previous drift to detect increasing drift
        
        # Auto-mix playlist queue
        self.automix_playlist = []
        self.automix_current_index = 0
        self.automix_active = False
        self.automix_crossfade_duration = 15  # seconds
        self.automix_timer = QTimer()
        self.automix_timer.timeout.connect(self._automix_check_transition)

        # --- Initialize Cache Manager ---
        try:
            self.cache_manager = AudioCacheManager()
            print(f"Cache manager initialized: {self.cache_manager.cache_dir}")
        except Exception as e:
            print(f"Error initializing cache manager: {e}")
            self.cache_manager = None

        # --- Initialize Audio Analyzer --- 
        self.audio_analyzer = None # Initialize as None
        try:
            # Determine library path based on operating system
            lib_folder = os.path.dirname(os.path.abspath(__file__))
            
            if sys.platform == 'win32': # Windows
                lib_path = os.path.join(lib_folder, "AudioAnalyzerBridge.dll")
                lib_name = "native library"
            elif sys.platform == 'darwin':  # macOS
                lib_path = os.path.join(lib_folder, "libAudioAnalyzerBridge.dylib")
                lib_name = "dynamic library"
            else:  # Linux and other Unix-like systems
                lib_path = os.path.join(lib_folder, "libAudioAnalyzerBridge.so")
                lib_name = "native library"
            
            print(f"Attempting to load Audio Analyzer Bridge {lib_name} from: {lib_path}")

            self.audio_analyzer = AudioAnalyzerBridge(lib_path, self.cache_manager)

            if not self.audio_analyzer.is_available():
                 print(f"Audio Analyzer Bridge {lib_name} loaded but failed to initialize.")
                 QMessageBox.warning(self, "Audio Analyzer Bridge Warning", 
                                   f"Could not initialize Audio Analyzer Bridge from:\n{lib_path}\n\n"+
                                   "BPM detection and tempo features will be disabled.")
                 self.audio_analyzer = None # Set back to None if unavailable
            else:
                 print("Audio Analyzer Bridge initialized successfully.")
                 
        except Exception as e: # Catch potential errors during instantiation (e.g., library not found)
             print(f"Error loading Audio Analyzer Bridge: {e}")
             error_message = f"Failed to load the Audio Analyzer Bridge {lib_name} from:\n{lib_path}\n\n{e}\n\n" + \
                           "BPM detection and tempo features will be disabled."
             
             QMessageBox.critical(self, "Audio Analyzer Bridge Error", error_message)
             self.audio_analyzer = None
        # --------------------------------

        # --- List Audio Devices --- 
        print("--- Available Audio Output Devices ---")
        available_devices = QMediaDevices.audioOutputs()
        if not available_devices:
             print("  No audio output devices found by Qt Multimedia!")
        else:
             for device in available_devices:
                  print(f"  - {device.description()}")
        default_device = QMediaDevices.defaultAudioOutput()
        if not default_device.isNull():
             print(f"--- Default Audio Output: {default_device.description()} ---")
        else:
             print("--- No default audio output device found! ---")
        # ------------------------


        
        # Add resolution presets
        self.resolution_presets = {
            "1080p (1920x1080)": (1920, 1080),
            "720p (1280x720)": (1280, 720),
            "Small (1024x768)": (1024, 768),
            "Compact (800x600)": (800, 600),
        }
        
        # Add theme presets
        self.theme_presets = {
            "Dark Mode": {
                "main_bg": "#1a1a1a",
                "accent": "#f3cf2c",
                "text": "#f3cf2c",
                "button_bg": "rgba(50, 50, 50, 200)",
                "glass_bg": "rgba(40, 40, 40, 180)"
            },
            "Light Mode": {
                "main_bg": "#f0f0f0",
                "accent": "#2c7bf3",
                "text": "#000000",
                "button_bg": "rgba(220, 220, 220, 200)",
                "glass_bg": "rgba(240, 240, 240, 180)"
            },
            "Neon Purple": {
                "main_bg": "#1a1a1a",
                "accent": "#bf2cf3",
                "text": "#bf2cf3",
                "button_bg": "rgba(50, 50, 50, 200)",
                "glass_bg": "rgba(40, 40, 40, 180)"
            },
            "Forest": {
                "main_bg": "#1c2e1c",
                "accent": "#2cf35d",
                "text": "#2cf35d",
                "button_bg": "rgba(40, 60, 40, 200)",
                "glass_bg": "rgba(40, 60, 40, 180)"
            }
        }
        
        # Load saved theme or use Dark Mode as default 
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        debug(f"Settings file path: {self.settings_file}")
        self.current_theme = self.load_theme_setting()
        debug(f"Current theme after loading: {self.current_theme}")
        
        # Initialize styles framework
        self.define_styles()
        
        # Setup UI and add tooltips first
        self.setup_ui()
        self.setup_tooltips()
        
        # Initialize tutorial flag BEFORE theme and window setup
        self._tutorial_shown = False
        
        # Now apply the saved theme after UI is created
        debug(f"About to apply theme after UI setup: {self.current_theme}")
        self.apply_theme_without_dialog(self.current_theme)
        
        # Maximize window to full screen (no scrolling needed)
        self.showMaximized()
        
    def define_styles(self):
        """
        Initialize the basic style framework.
        Theme-specific styles will be applied later.
        """
        
        # Don't force dark palette here - let the theme system handle it
        # The palette will be set appropriately in apply_theme_without_dialog()
        
        # Color palette for reference
        self.colors = {
            'primary': '#f3cf2c',      # Neon yellow
            'secondary': '#00ff9f',    # Neon green
            'accent': '#ff00ff',       # Neon magenta
            'dark': '#111111',         # Near black
            'darker': '#0a0a0a',       # Darker black
            'glass': 'rgba(17, 17, 17, 0.7)'
        }
        
        # Font definitions
        self.fonts = {
            'display': 'Segoe UI',
            'text': 'Segoe UI'
        }
        
        # Note: Actual stylesheet will be loaded by apply_theme_without_dialog()
        print("Style framework initialized - theme will be applied next")

    @staticmethod
    def force_dark_palette():
        """
        Force a dark color palette to override system theme settings.
        """
        try:
            # Create a dark palette
            dark_palette = QPalette()
            
            # Set dark colors for all roles
            dark_palette.setColor(QPalette.ColorRole.Window, QColor(26, 26, 26))
            dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(243, 207, 44))
            dark_palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))
            dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
            dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 0, 0))
            dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(243, 207, 44))
            dark_palette.setColor(QPalette.ColorRole.Text, QColor(243, 207, 44))
            dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(243, 207, 44))
            dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
            dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
            
            # Apply the dark palette to the application
            QApplication.instance().setPalette(dark_palette)
            
            print("Forced dark palette applied successfully")
            
        except Exception as e:
            print(f"Error applying dark palette: {e}")

    def force_light_palette(self):
        """
        Force a light color palette to override system theme settings.
        """
        try:
            # Create a light palette
            light_palette = QPalette()
            
            # Set light colors for all roles
            light_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
            light_palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
            light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
            light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
            light_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
            light_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
            light_palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
            light_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
            light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
            light_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
            light_palette.setColor(QPalette.ColorRole.Link, QColor(44, 123, 243))
            light_palette.setColor(QPalette.ColorRole.Highlight, QColor(44, 123, 243))
            light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            
            # Apply the light palette to the application
            QApplication.instance().setPalette(light_palette)
            
            print("Forced light palette applied successfully")
            
        except Exception as e:
            print(f"Error applying light palette: {e}")

    def reset_to_system_palette(self):
        """
        Reset to the system's default palette.
        """
        try:
            # Reset to system palette
            QApplication.instance().setPalette(QApplication.instance().style().standardPalette())
            print("Reset to system palette successfully")
            
        except Exception as e:
            print(f"Error resetting to system palette: {e}")

    def setup_ui(self):
        """
        Set up the main application user interface.
        
        Creates and arranges all UI elements including decks, controls, and file browser.
        """
        # Create a scroll area to contain everything
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # Disable scrolling - everything fits in maximized window
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Optimize viewport for custom-painted children
        viewport = scroll_area.viewport()
        viewport.setAutoFillBackground(False)
        # Make the viewport palette fully transparent
        pal = viewport.palette()
        pal.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        viewport.setPalette(pal)

        # Create the central widget that will be inside the scroll area
        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Set the central widget to the scroll area
        self.setCentralWidget(scroll_area)
        scroll_area.setWidget(central_widget)
        
        # Main layout - Professional & Responsive
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(3)  # Professional spacing for clarity
        main_layout.setContentsMargins(4, 4, 4, 4)  # Professional margins
        
        # Set responsive size policy for better scaling
        central_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        central_widget.setMinimumSize(1000, 700)  # Minimum usable size
        
        # Set window size constraints for responsive design
        self.setMinimumSize(1000, 700)  # Minimum window size
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Top controls layout - Professional & Responsive
        top_controls_layout = QHBoxLayout()
        top_controls_layout.setSpacing(8)  # Consistent spacing
        top_controls_layout.setContentsMargins(4, 4, 4, 4)
        
        # === FILE MANAGEMENT SECTION ===
        select_dir_button = QPushButton("📁 Select Directory")
        select_dir_button.setObjectName("select_dir_button")
        select_dir_button.clicked.connect(self.select_audio_directory)
        select_dir_button.setMinimumWidth(140)
        select_dir_button.setMaximumWidth(180)
        select_dir_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        select_dir_button.setMinimumHeight(32)
        select_dir_button.setProperty("class", "neonBorder")
        
        self.track_list_button = QPushButton("🎵 Track List")
        self.track_list_button.clicked.connect(self.show_file_browser)
        self.track_list_button.setEnabled(False)
        self.track_list_button.setMinimumWidth(110)
        self.track_list_button.setMaximumWidth(140)
        self.track_list_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.track_list_button.setMinimumHeight(32)
        
        top_controls_layout.addWidget(select_dir_button)
        top_controls_layout.addWidget(self.track_list_button)
        
        # Separator
        top_controls_layout.addSpacing(12)
        
        # === AUTOMIX SECTION ===
        self.automix_button = QPushButton("🎚️ AutoMix")
        self.automix_button.setProperty("class", "neonBorder")
        self.automix_button.clicked.connect(self.auto_mix)
        self.automix_button.setMinimumWidth(100)
        self.automix_button.setMaximumWidth(130)
        self.automix_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.automix_button.setMinimumHeight(32)
        top_controls_layout.addWidget(self.automix_button)
        
        # Separator
        top_controls_layout.addSpacing(12)
        
        # === RECORDING SECTION ===
        self.record_button = QPushButton("⏺ Record")
        self.record_button.setCheckable(True)
        self.record_button.setProperty("class", "recordButton")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setMinimumWidth(90)
        self.record_button.setMaximumWidth(120)
        self.record_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.record_button.setMinimumHeight(32)
        
        record_folder_button = QPushButton("📂 Rec Folder")
        record_folder_button.setProperty("class", "recordButton")
        record_folder_button.clicked.connect(self.select_recording_folder)
        record_folder_button.setMinimumWidth(100)
        record_folder_button.setMaximumWidth(130)
        record_folder_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        record_folder_button.setMinimumHeight(32)
        
        self.recording_status_label = QLabel("🔴 REC 00:00")
        self.recording_status_label.setProperty("class", "recordingStatusLabel")
        self.recording_status_label.setVisible(False)
        self.recording_status_label.setMinimumHeight(32)
        
        self.view_recordings_button = QPushButton("📼 View Recs")
        self.view_recordings_button.setProperty("class", "syncDefault")
        self.view_recordings_button.clicked.connect(self.show_recordings_list)
        self.view_recordings_button.setEnabled(False)
        self.view_recordings_button.setMinimumWidth(120)
        self.view_recordings_button.setMaximumWidth(150)
        self.view_recordings_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.view_recordings_button.setMinimumHeight(32)
        
        top_controls_layout.addWidget(self.record_button)
        top_controls_layout.addWidget(record_folder_button)
        top_controls_layout.addWidget(self.recording_status_label)
        top_controls_layout.addWidget(self.view_recordings_button)
        
        # Flexible spacer
        top_controls_layout.addStretch(1)
        
        # === UTILITY BUTTONS SECTION (Right side) ===
        settings_button = QPushButton("⚙️ Settings")
        settings_button.setProperty("class", "helpButton")
        settings_button.clicked.connect(self.show_settings_dialog)
        settings_button.setMinimumWidth(90)
        settings_button.setMaximumWidth(120)
        settings_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        settings_button.setMinimumHeight(32)
        
        help_button = QPushButton("❓ Help")
        help_button.setProperty("class", "helpButton")
        help_button.clicked.connect(self.show_help)
        help_button.setMinimumWidth(80)
        help_button.setMaximumWidth(110)
        help_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        help_button.setMinimumHeight(32)
        
        new_features_button = QPushButton("🆕 New")
        new_features_button.setProperty("class", "helpButton")
        new_features_button.clicked.connect(self.show_new_features_tutorial)
        new_features_button.setMinimumWidth(70)
        new_features_button.setMaximumWidth(100)
        new_features_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        new_features_button.setMinimumHeight(32)
        
        top_controls_layout.addWidget(settings_button)
        top_controls_layout.addWidget(help_button)
        top_controls_layout.addWidget(new_features_button)
        
        # Decks layout - Professional & Balanced
        decks_layout = QHBoxLayout()
        decks_layout.setSpacing(4)  # Professional spacing between decks
        decks_layout.setContentsMargins(0, 2, 0, 2)
        
        # Create deck widgets with responsive sizing
        self.deck1 = DeckWidget(1, main_app=self, audio_analyzer=self.audio_analyzer)
        self.deck2 = DeckWidget(2, main_app=self, audio_analyzer=self.audio_analyzer)
        
        # Set size policies for responsive layout
        self.deck1.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.deck2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        decks_layout.addWidget(self.deck1)
        decks_layout.addWidget(self.deck2)
        
        # --- Connect Sync Button Signals --- 
        # Use lambda to pass the deck number to the toggle_sync function
        self.deck1.sync_button.clicked.connect(lambda: self.toggle_sync(1))
        self.deck2.sync_button.clicked.connect(lambda: self.toggle_sync(2))
        # ---------------------------------
        

        
        # Professional DJ Mixer Section - MODERN & RESPONSIVE
        mixer_section = QHBoxLayout()
        mixer_section.setSpacing(10)  # Reduced spacing
        mixer_section.setContentsMargins(8, 1, 8, 1)  # Reduced vertical margins
        
        # Master Volume Control (Left side) - PROFESSIONAL SIZE
        master_section = QVBoxLayout()
        master_section.setSpacing(3)
        master_label = QLabel("MASTER")
        master_label.setProperty("class", "mixerLabel")
        master_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        master_label.setStyleSheet("font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        
        self.master_volume_slider = QSlider(Qt.Orientation.Vertical)
        self.master_volume_slider.setMinimum(0)
        self.master_volume_slider.setMaximum(100)
        self.master_volume_slider.setValue(100)
        self.master_volume_slider.setFixedHeight(85)  # Increased height
        self.master_volume_slider.setFixedWidth(32)   # Easier to grab
        self.master_volume_slider.setProperty("class", "masterVolumeSlider")
        
        self.master_volume_display = QLabel("100%")
        self.master_volume_display.setProperty("class", "volumeDisplay")
        self.master_volume_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.master_volume_display.setStyleSheet("font-size: 11px; font-weight: bold; padding: 2px 6px;")
        
        master_section.addWidget(master_label)
        master_section.addWidget(self.master_volume_slider, 0, Qt.AlignmentFlag.AlignCenter)
        master_section.addWidget(self.master_volume_display)
        
        # Crossfader Section (Center - Main feature) - PROFESSIONAL SIZE
        crossfader_section = QVBoxLayout()
        crossfader_section.setSpacing(2)
        
        crossfader_title = QLabel("CROSSFADER")
        crossfader_title.setProperty("class", "mixerLabel")
        crossfader_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        crossfader_title.setStyleSheet("font-size: 11px; font-weight: bold; letter-spacing: 2px;")
        
        # Deck indicators above crossfader - CLEAR & VISIBLE
        deck_indicators_layout = QHBoxLayout()
        deck_indicators_layout.setSpacing(0)
        self.deck1_indicator = QLabel("◄ DECK A")
        self.deck1_indicator.setProperty("class", "deckIndicator")
        self.deck1_indicator.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.deck1_indicator.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 4px;")
        
        self.deck2_indicator = QLabel("DECK B ►")
        self.deck2_indicator.setProperty("class", "deckIndicator")
        self.deck2_indicator.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.deck2_indicator.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 4px;")
        
        deck_indicators_layout.addWidget(self.deck1_indicator)
        deck_indicators_layout.addStretch()
        deck_indicators_layout.addWidget(self.deck2_indicator)
        
        # Crossfader slider - PROFESSIONAL SIZE
        self.crossfader = QSlider(Qt.Orientation.Horizontal)
        self.crossfader.setMinimum(0)
        self.crossfader.setMaximum(100)
        self.crossfader.setValue(50)
        self.crossfader.setFixedHeight(26)  # Professional height
        self.crossfader.setMinimumWidth(300)  # Longer for better control
        self.crossfader.setProperty("class", "crossfaderSlider")
        
        # Position display below crossfader - CLEAR & READABLE
        self.crossfader_display = QLabel("CENTER")
        self.crossfader_display.setProperty("class", "crossfaderDisplay")
        self.crossfader_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.crossfader_display.setStyleSheet("font-size: 11px; font-weight: bold; padding: 2px 8px;")
        
        crossfader_section.addWidget(crossfader_title)
        crossfader_section.addLayout(deck_indicators_layout)
        crossfader_section.addWidget(self.crossfader)
        crossfader_section.addWidget(self.crossfader_display)
        
        # Assemble mixer section - BALANCED LAYOUT
        mixer_section.addStretch()
        mixer_section.addLayout(master_section)
        mixer_section.addSpacing(20)
        mixer_section.addLayout(crossfader_section)
        mixer_section.addStretch()
        
        # Add all components to main layout
        main_layout.addLayout(top_controls_layout)
        main_layout.addLayout(decks_layout)
        main_layout.addLayout(mixer_section)  # Professional mixer section below decks
        
        # Connect volume control signals
        # All volume changes trigger the main volume handler
        self.crossfader.valueChanged.connect(self._update_crossfader_display)
        self.crossfader.valueChanged.connect(self._on_volume_changed)
        self.master_volume_slider.valueChanged.connect(self._update_master_volume_display)
        self.master_volume_slider.valueChanged.connect(self._on_volume_changed)
        self.deck1.volumeChanged.connect(self._on_volume_changed)
        self.deck2.volumeChanged.connect(self._on_volume_changed)
        
        # Initial volume application
        self._on_volume_changed()

    def setup_tooltips(self):
        """
        Add helpful tooltips to UI elements.
        """
        # Directory selection
        if hasattr(self, 'select_dir_button'):
            self.select_dir_button.setToolTip(
                "Choose a folder containing your music files.\n"
                "Supported formats: MP3, WAV, AIFF, etc."
            )
        
        # Track list button
        if self.track_list_button:
            self.track_list_button.setToolTip(
                "Browse and load tracks into either deck.\n"
                "Double-click a track to preview it."
            )
        
        # Master volume
        self.master_volume_slider.setToolTip(
            "Controls the overall output volume.\n"
            "Recommended: Keep around 75-80% for best sound quality."
        )
        
        # Crossfader
        self.crossfader.setToolTip(
            "Slide left/right to mix between decks.\n"
            "Center position plays both decks equally.\n"
            "TIP: Move slowly for smooth transitions!"
        )
        
        # Recording controls
        self.record_button.setToolTip(
            "Start/Stop recording your mix.\n"
            "Make sure to set a recording folder first!"
        )
        
        # Deck-specific tooltips
        for deck in [self.deck1, self.deck2]:
            # Volume slider
            deck.volume_slider.setToolTip(
                "Controls this deck's volume.\n"
                "TIP: Use in combination with the crossfader for smooth transitions."
            )
            
            # Sync button
            if hasattr(deck, 'sync_button'):
                deck.sync_button.setToolTip(
                    "Automatically match tempo and beats with the other deck.\n"
                    "First click: Make this deck the master\n"
                    "Second click on other deck: Match to master"
                )
            
            # BPM controls
            if hasattr(deck, 'bpm_display'):
                deck.bpm_display.setToolTip(
                    "Shows the current tempo (Beats Per Minute).\n"
                    "Use +/- buttons to adjust speed.\n"
                    "Click number to enter exact BPM."
                )
            
            # Waveform
            if hasattr(deck, 'waveform_display'):
                deck.waveform_display.setToolTip(
                    "Visual representation of the audio.\n"
                    "Taller sections = louder parts\n"
                    "Markers show beats for easy mixing."
                )

    def showEvent(self, event):
        """
        Handle window show event.
        
        Args:
            event: The QShowEvent instance.
        """
        super().showEvent(event)
        
        # Only show tutorial once and only if it's the first launch
        if not self._tutorial_shown:
            self._tutorial_shown = True
            print("Checking if tutorial should be shown...")
            if hasattr(self, 'tutorial_manager') and self.tutorial_manager.is_first_launch():
                print("First launch detected, starting tutorial...")
                # Use a slightly longer delay to ensure window is fully ready
                QTimer.singleShot(1000, self._start_tutorial)
            else:
                print("Not first launch or tutorial manager not found.")

    def _start_tutorial(self):
        """
        Start the tutorial with proper error handling.
        """
        try:
            print("Attempting to start tutorial...")
            if hasattr(self, 'tutorial_manager'):
                self.tutorial_manager.start_tutorial()
            else:
                print("Error: Tutorial manager not found!")
        except Exception as e:
            print(f"Error starting tutorial: {e}")
            traceback.print_exc()

    def show_help(self):
        """
        Show the help dialog with DJ concepts guide.
        """
        # Create and show the concepts guide
        guide = ConceptsGuide(self)
        guide.exec()
    
    def show_new_features_tutorial(self):
        """
        Show the new features tutorial highlighting professional DJ features.
        """
        try:
            if hasattr(self, 'tutorial_manager'):
                # Reset tutorial manager state
                if self.tutorial_manager.is_running:
                    self.tutorial_manager.stop_tutorial()
                
                # Setup tutorial steps with actual widget references
                self.tutorial_manager.setup_tutorial_steps()
                
                # Create overlay for highlighting
                self.tutorial_manager.overlay = HighlightOverlay(self)
                self.tutorial_manager.overlay.setGeometry(self.geometry())
                self.tutorial_manager.overlay.show()
                
                # Show the new features tutorial
                self.tutorial_manager.start_new_features_tutorial()
                print("✨ New Features Tutorial started!")
            else:
                QMessageBox.information(self, "Tutorial", 
                    "Tutorial system not available. Showing help instead...")
                self.show_help()
        except Exception as e:
            print(f"Error showing new features tutorial: {e}")
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Could not load tutorial: {str(e)}")

    def select_audio_directory(self):
        """
        Open a dialog to select the audio directory and update the file browser.
        """
        # Let the user choose an audio directory using PyQt6 QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Audio Directory",
            os.path.expanduser("~") # Start in user's home directory
        )
        
        if directory:
            self.audio_directory = directory
            print(f"Audio directory selected: {self.audio_directory}")
            if self.track_list_button:
                 self.track_list_button.setEnabled(True)
            if self.file_browser:
                 self.file_browser.set_directory(self.audio_directory)
        else:
             print("Directory selection cancelled.")
            
    def show_file_browser(self):
        """
        Display the audio file browser window.
        
        Opens a dialog for browsing and selecting audio files to load into decks.
        """
        if not self.audio_directory:
            QMessageBox.information(self, "Information", "Please select an audio directory first.")
            return

        if self.file_browser is None:
            self.file_browser = FileBrowserDialog(self.audio_directory, parent=self, audio_analyzer=self.audio_analyzer, cache_manager=self.cache_manager)
            self.file_browser.file_selected.connect(self.load_track_from_browser)
            # Connect BPM analysis signal
            self.file_browser.bpm_analyzed.connect(self.update_bpm_cache)
            print("File browser created.")
        else:
             self.file_browser.set_directory(self.audio_directory)
             print("Updating file browser directory.")

        self.file_browser.show()
        self.file_browser.raise_()
        self.file_browser.activateWindow()
        
        # Apply current theme to the file browser after it's shown
        # This ensures proper style application when the dialog is visible
        self._apply_theme_to_dialog(self.file_browser)

    def update_bpm_cache(self, file_path,bpm):
        """
        Update the BPM cache when new analysis is available.
        
        Args:
            file_path (str): Path to the audio file.
            bpm (int): BPM value.
        """
        self.bpm_cache[file_path] = bpm
        print(f"Updated BPM cache for {file_path}: {bpm} BPM")

    def load_track_from_browser(self, deck_number, file_path):
        """
        Load a track into the specified deck, using cached BPM if available.
        
        Args:
            deck_number (int): Deck number (1 or 2).
            file_path (str): Path to the audio file.
        """
        print(f"Attempting to load into Deck {deck_number}: {file_path}")
        
        # Check if BPM is already cached
        cached_bpm = self.bpm_cache.get(file_path, 0)
        if cached_bpm > 0:
            print(f"Using cached BPM value: {cached_bpm}")
            
        if deck_number == 1:
            if cached_bpm > 0:
                self.deck1.original_bpm = cached_bpm
                self.deck1.current_bpm = cached_bpm
            self.deck1.load_file(file_path)
        elif deck_number == 2:
            if cached_bpm > 0:
                self.deck2.original_bpm = cached_bpm
                self.deck2.current_bpm = cached_bpm
            self.deck2.load_file(file_path)
        else:
             print(f"Error: Invalid deck number {deck_number}")

    def _on_volume_changed(self):
        """
        Handle volume changes from master volume, crossfader, or deck volume sliders.
        """
        try:
            # Get the master volume (0.0-1.0)
            master_volume = self.master_volume_slider.value() / 100.0
            
            # Get the crossfader position (0-100) and convert to -1.0 to 1.0 range
            crossfader_raw = self.crossfader.value()
            crossfader_pos = (crossfader_raw - 50) / 50.0
            
            # Get individual deck volumes (0.0-1.0)
            deck1_volume = self.deck1.volume_slider.value() / 100.0
            deck2_volume = self.deck2.volume_slider.value() / 100.0
            
            # Calculate crossfader multipliers with smooth curve
            crossfade_curve_exponent = 1.5  # Higher values create sharper crossfade curve
            
            if crossfader_pos <= 0:  # Crossfader on left side or center
                deck1_multiplier = 1.0
                deck2_multiplier = pow(1.0 + crossfader_pos, crossfade_curve_exponent)
            else:  # Crossfader on right side
                deck1_multiplier = pow(1.0 - crossfader_pos, crossfade_curve_exponent)
                deck2_multiplier = 1.0
            
            # Ensure multipliers stay in valid range
            deck1_multiplier = max(0.0, min(1.0, deck1_multiplier))
            deck2_multiplier = max(0.0, min(1.0, deck2_multiplier))
            
            # Calculate final volumes
            final_volume1 = master_volume * deck1_volume * deck1_multiplier
            final_volume2 = master_volume * deck2_volume * deck2_multiplier
            
            # Ensure volumes are within 0.0-1.0 range
            final_volume1 = max(0.0, min(1.0, final_volume1))
            final_volume2 = max(0.0, min(1.0, final_volume2))
            
            print(f"Master: {master_volume:.2f}, Deck1: {deck1_volume:.2f} -> {final_volume1:.2f}, Deck2: {deck2_volume:.2f} -> {final_volume2:.2f}")
            
            # Apply volumes to decks
            self._apply_volume_to_deck(self.deck1, final_volume1)
            self._apply_volume_to_deck(self.deck2, final_volume2)
            
            # Update master volume display
            self._update_master_volume_display()
                
        except Exception as e:
            print(f"Error in volume calculation: {e}")
            traceback.print_exc()

    def _update_master_volume_display(self):
        """
        Update the master volume percentage display.
        """
        try:
            volume_percent = self.master_volume_slider.value()
            self.master_volume_display.setText(f"{volume_percent}%")
            
            # Add visual feedback for master volume
            if volume_percent < 100:
                # Use reduced volume class
                self.master_volume_display.setProperty("class", "volumeDisplayReduced")
            else:
                # Full volume - show normal style
                self.master_volume_display.setProperty("class", "volumeDisplay")
                
            # Update the widget style
            self.master_volume_display.style().unpolish(self.master_volume_display)
            self.master_volume_display.style().polish(self.master_volume_display)
            
        except Exception as e:
            print(f"Error updating master volume display: {e}")
            traceback.print_exc()

    def _apply_volume_to_deck(self, deck, volume):
        """
        Apply volume to a deck, taking into account crossfader position.
        
        Args:
            deck: DeckWidget instance.
            volume (float): Volume value (0.0-1.0).
        """
        try:
            # Apply volume to audio output
            if hasattr(deck, 'audio_output') and deck.audio_output:
                # Ensure volume is in valid range
                volume = max(0.0, min(1.0, volume))
                deck.audio_output.setVolume(volume)
                print(f"Deck {deck.deck_number} volume set to: {volume:.2f}")
            else:
                print(f"Deck {deck.deck_number}: No valid audio output")
                
            # Apply a visual effect to the volume slider to indicate the actual volume after crossfader
            # Only change appearance, not the actual value (which represents user's setting)
            crossfader_pos = (self.crossfader.value() - 50) / 50.0
            
            # Get the deck-specific crossfader multiplier
            if (deck.deck_number == 1 and crossfader_pos > 0) or (deck.deck_number == 2 and crossfader_pos < 0):
                # This deck is being reduced by crossfader position
                deck.volume_slider.setProperty("class", "volumeSliderDimmed")
            else:
                # No crossfader effect on this deck
                deck.volume_slider.setProperty("class", "volumeSliderNormal")
                
            # Update the style
            deck.volume_slider.style().unpolish(deck.volume_slider)
            deck.volume_slider.style().polish(deck.volume_slider)
                
        except Exception as e:
            print(f"Error applying volume to deck {deck.deck_number}: {e}")
            traceback.print_exc()

    def closeEvent(self, event):
        """
        Handle application closure.
        
        Args:
            event: The QCloseEvent instance.
        
        Performs cleanup operations before closing the application.
        """
        try:
            print("Starting application cleanup...")
            
            # Stop playback and clear media on both decks
            if hasattr(self, 'deck1'):
                print("Stopping deck 1...")
                self.deck1.player.stop()
                self.deck1.player.setSource(QUrl())
                if hasattr(self.deck1, 'position_timer') and self.deck1.position_timer.isActive():
                    self.deck1.position_timer.stop()
                    
            if hasattr(self, 'deck2'):
                print("Stopping deck 2...")
                self.deck2.player.stop()
                self.deck2.player.setSource(QUrl())
                if hasattr(self.deck2, 'position_timer') and self.deck2.position_timer.isActive():
                    self.deck2.position_timer.stop()
            
            # Stop any active recording
            if hasattr(self, 'is_recording') and self.is_recording:
                print("Stopping active recording...")
                try:
                    if hasattr(self, 'recording_worker') and self.recording_worker:
                        self.recording_worker.stop_recording()
                        self.recording_worker.wait()  # Wait for the worker to finish
                except Exception as e:
                    print(f"Error stopping recording: {e}")

            print("Cleaning up temporary files...")
            # Directly call cleanup instead of using timer
            self._cleanup_all_temp_files()
            
            print("Application cleanup completed.")
            # Accept the close event
            event.accept()
            
        except Exception as e:
            print(f"Error during application cleanup: {e}")
            event.accept()  # Still accept the close event even if cleanup fails

    # --- Sync Logic --- 
    def calculate_key_semitone_difference(self, key1, key2):
        """
        Calculate the semitone difference between two musical keys.
        
        Args:
            key1 (str): First key (e.g., "C", "Am", "F#")
            key2 (str): Second key (e.g., "G", "Em", "Bb")
            
        Returns:
            int: Semitone difference (0-11), or None if keys are invalid
        """
        # Camelot wheel for harmonic mixing
        camelot_wheel = {
            # Major keys
            'C': 0, 'G': 7, 'D': 2, 'A': 9, 'E': 4, 'B': 11, 'F#': 6, 'Gb': 6, 'Db': 1, 'C#': 1, 'Ab': 8, 'G#': 8, 'Eb': 3, 'D#': 3, 'Bb': 10, 'A#': 10, 'F': 5,
            # Minor keys (adding 'm' suffix)
            'Cm': 0, 'Gm': 7, 'Dm': 2, 'Am': 9, 'Em': 4, 'Bm': 11, 'F#m': 6, 'Gbm': 6, 'Dbm': 1, 'C#m': 1, 'Abm': 8, 'G#m': 8, 'Ebm': 3, 'D#m': 3, 'Bbm': 10, 'A#m': 10, 'Fm': 5
        }
        
        if not key1 or not key2 or key1 not in camelot_wheel or key2 not in camelot_wheel:
            return None
        
        diff = (camelot_wheel[key2] - camelot_wheel[key1]) % 12
        # Return the shortest path (either up or down the chromatic scale)
        return diff if diff <= 6 else diff - 12
    
    def are_keys_compatible(self, key1, key2):
        """
        Check if two keys are harmonically compatible for mixing.
        
        Args:
            key1 (str): First key
            key2 (str): Second key
            
        Returns:
            bool: True if keys are compatible, False otherwise
        """
        if not key1 or not key2:
            return False
        
        # Same key is always compatible
        if key1 == key2:
            return True
        
        # Compatible intervals: Perfect 5th (7 semitones), Perfect 4th (5 semitones), Minor 3rd (3 semitones)
        # Also relative major/minor relationships
        diff = self.calculate_key_semitone_difference(key1, key2)
        if diff is None:
            return False
        
        compatible_intervals = [0, 2, 3, 5, 7]  # Same, whole tone, minor 3rd, perfect 4th, perfect 5th
        return abs(diff) in compatible_intervals

    def toggle_sync(self, deck_number):
        """
        Handles clicks on the SYNC buttons.
        Professional DJ sync: matches BPM, beats, and key.
        
        Args:
            deck_number (int): Deck number (1 or 2).
        """
        print(f"Toggle Sync called for Deck {deck_number}")
        
        other_deck_number = 2 if deck_number == 1 else 1
        this_deck = self.deck1 if deck_number == 1 else self.deck2
        other_deck = self.deck2 if deck_number == 1 else self.deck1

        # Case 1: No sync master currently set
        if self.sync_master is None:
             # Make this deck the master
             print(f"Setting Deck {deck_number} as Sync Master.")
             self.sync_master = deck_number
             self.update_sync_button_style(deck_number, "master")
             self.update_sync_button_style(other_deck_number, "default") # Ensure other is default
             # Start beat phase monitoring
             if not self.beat_phase_monitor.isActive():
                 self.beat_phase_monitor.start()
                 print("🔄 Beat phase monitoring activated")

        # Case 2: The clicked deck is the current sync master
        elif self.sync_master == deck_number:
             print(f"Deactivating Sync (Master Deck {deck_number} clicked).")
             # Deactivate sync entirely
             self.sync_master = None
             # Reset slave deck tempo if it was synced
             if other_deck.sync_button.text() == "SYNCED":
                  other_deck.reset_tempo()
             # Reset button styles
             self.update_sync_button_style(deck_number, "default")
             self.update_sync_button_style(other_deck_number, "default")
             # Stop beat phase monitoring
             if self.beat_phase_monitor.isActive():
                 self.beat_phase_monitor.stop()
                 print("⏸ Beat phase monitoring deactivated")

        # Case 3: The OTHER deck is the sync master
        else: 
             # Check if this deck is currently synced
             if this_deck.sync_button.text() == "SYNCED":
                  # Unsync this deck
                  print(f"Unsyncing Deck {deck_number} from Master Deck {self.sync_master}.")
                  this_deck.reset_tempo()
                  self.update_sync_button_style(deck_number, "default")
             else:
                  # Sync this deck to the master
                  print(f"Syncing Deck {deck_number} to Master Deck {self.sync_master}.")
                  master_bpm = other_deck.current_bpm
                  if master_bpm > 0:
                       # Check if tracks are loaded
                       if not this_deck.current_file or not other_deck.current_file:
                           QMessageBox.warning(self, "Sync Error", "Both decks must have tracks loaded to sync.")
                           return
                       
                       # === PROFESSIONAL DJ SYNC: BPM + KEY + BEATS ===
                       
                       # 1. Apply BPM sync INSTANTLY first (always)
                       print(f"⚡ Applying Master BPM ({master_bpm}) to Deck {deck_number} INSTANTLY.")
                       this_deck.set_deck_tempo_instant(master_bpm)
                       
                       # 2. Apply KEY SYNC for harmonic mixing (like Pioneer CDJ)
                       master_key = other_deck.detected_key
                       slave_key = this_deck.detected_key
                       
                       if master_key and slave_key:
                           key_diff = self.calculate_key_semitone_difference(slave_key, master_key)
                           if key_diff is not None and key_diff != 0:
                               # Check if keys are compatible
                               compatible = self.are_keys_compatible(master_key, slave_key)
                               
                               if compatible:
                                   print(f"🎹 Keys are compatible: {slave_key} → {master_key} ({key_diff:+d} semitones)")
                                   # Show brief notification for compatible keys
                                   self.statusBar().showMessage(f"✓ Keys are compatible: {slave_key} ↔ {master_key}", 3000)
                               else:
                                   print(f"🎹 KEY SYNC: Adjusting {slave_key} → {master_key} ({key_diff:+d} semitones)")
                                   # Store the key transpose for display
                                   this_deck.key_transpose = key_diff
                                   this_deck._update_key_display()
                                   
                                   # In professional apps, key sync uses pitch shift or playback rate adjustment
                                   # We'll use a subtle playback rate adjustment for key matching
                                   # Note: 1 semitone ≈ 5.95% change in frequency
                                   pitch_adjust = 2 ** (key_diff / 12.0)  # Musical semitone formula
                                   current_rate = this_deck.player.playbackRate()
                                   new_rate = current_rate * pitch_adjust
                                   new_rate = max(0.5, min(new_rate, 2.0))  # Safety limits
                                   
                                   this_deck.player.setPlaybackRate(new_rate)
                                   print(f"✓ Playback rate adjusted: {current_rate:.3f}x → {new_rate:.3f}x for key match")
                                   # Show notification for key adjustment
                                   self.statusBar().showMessage(f"🎹 Key Synced: {slave_key} → {master_key} ({key_diff:+d} semitones)", 5000)
                           else:
                               print(f"✓ Keys already match: {master_key}")
                       else:
                           print(f"⚠ Key sync unavailable (Master: {master_key or 'unknown'}, Slave: {slave_key or 'unknown'})")
                       
                       self.update_sync_button_style(deck_number, "synced")
                       
                       # 3. Then try beat alignment if beat positions are available
                       if this_deck.beat_positions and other_deck.beat_positions:
                           print(f"🎵 Beat positions available - applying beat alignment...")
                           master_pos = other_deck.player.position()
                           slave_pos = this_deck.player.position()

                           master_closest_beat_time, master_beat_index = other_deck.find_closest_beat(master_pos)
                           slave_closest_beat_time, slave_beat_index = this_deck.find_closest_beat(slave_pos)

                           if master_closest_beat_time is not None and slave_closest_beat_time is not None:
                               # Calculate the phase within the beat grid for master
                               master_offset = master_pos - master_closest_beat_time
                               slave_offset = slave_pos - slave_closest_beat_time
                               
                               # Professional Quantization: If quantize is enabled, snap to nearest beat
                               if self.quantize_enabled:
                                   # Snap to the nearest beat/bar (4 beats)
                                   # Find the next bar boundary for smooth mixing
                                   if master_beat_index is not None and len(other_deck.beat_positions) > master_beat_index + 1:
                                       # Calculate next bar (every 4 beats)
                                       beats_to_next_bar = 4 - (master_beat_index % 4)
                                       if beats_to_next_bar > 0 and master_beat_index + beats_to_next_bar < len(other_deck.beat_positions):
                                           next_bar_time = other_deck.beat_positions[master_beat_index + beats_to_next_bar]
                                           master_offset = next_bar_time - master_pos
                                           print(f"📍 Quantize: Snapping to next bar in {beats_to_next_bar} beats ({master_offset:.0f}ms)")
                               
                               # Calculate adjustment needed to align beats perfectly
                               adjustment = master_offset - slave_offset
                               
                               # Calculate target position with smooth alignment
                               duration_ms = this_deck.player.duration()
                               calculated_target = slave_pos + adjustment
                               
                               if duration_ms > 0:
                                   target_slave_pos = max(0, min(int(calculated_target), duration_ms))
                               else:
                                   target_slave_pos = max(0, int(calculated_target))
                                   
                               print(f"🎵 Beat Sync: Master Pos={master_pos}ms, Master Beat={master_closest_beat_time}ms, Phase={master_offset}ms")
                               print(f"🎵 Beat Sync: Slave Pos={slave_pos}ms, Slave Beat={slave_closest_beat_time}ms, Phase={slave_offset}ms")
                               print(f"🎵 Beat Sync: Adjustment={adjustment}ms → Moving to {target_slave_pos}ms for perfect alignment")
                               
                               # If currently playing, apply the position immediately for instant sync
                               if this_deck.is_playing:
                                   this_deck.player.setPosition(target_slave_pos)
                                   print(f"✓ Instant beat alignment applied to playing deck")
                           else:
                               print("⚠ Beat Sync: Could not find closest beats for alignment. BPM only.")
                       else:
                           print("⚠ Beat positions not available. BPM sync only (instant).")
                  else:
                       print(f"Cannot sync Deck {deck_number}: Master Deck {self.sync_master} has invalid BPM ({master_bpm})")
                       QMessageBox.warning(self, "Sync Error", f"Master deck (Deck {self.sync_master}) has no valid BPM detected.")

    def _monitor_beat_phase(self):
        """
        Professional beat phase monitoring - continuously checks and corrects beat alignment.
        Runs every 500ms when sync is active to maintain perfect beat lock with intelligent dampening.
        """
        if self.sync_master is None or not self.sync_lock_enabled:
            return
        
        master_deck = self.deck1 if self.sync_master == 1 else self.deck2
        slave_deck_number = 2 if self.sync_master == 1 else 1
        slave_deck = self.deck2 if self.sync_master == 1 else self.deck1
        
        # Only monitor if slave is synced and both decks are playing
        if slave_deck.sync_button.text() != "SYNCED":
            self.last_phase_drift = 0  # Reset drift tracking
            return
        
        if not master_deck.is_playing or not slave_deck.is_playing:
            self.last_phase_drift = 0  # Reset drift tracking
            return
        
        # Check if both decks have beat positions
        if not master_deck.beat_positions or not slave_deck.beat_positions:
            return
        
        try:
            # Check cooldown - prevent corrections too frequently
            import time
            current_time = time.time() * 1000  # Convert to milliseconds
            time_since_last_correction = current_time - self.last_phase_correction_time
            
            if time_since_last_correction < self.phase_correction_cooldown_ms:
                # Still in cooldown period
                return
            
            master_pos = master_deck.player.position()
            slave_pos = slave_deck.player.position()
            
            master_closest_beat_time, _ = master_deck.find_closest_beat(master_pos)
            slave_closest_beat_time, _ = slave_deck.find_closest_beat(slave_pos)
            
            if master_closest_beat_time is not None and slave_closest_beat_time is not None:
                # Calculate phase difference
                master_offset = master_pos - master_closest_beat_time
                slave_offset = slave_pos - slave_closest_beat_time
                phase_diff = abs(master_offset - slave_offset)
                
                # Only correct if:
                # 1. Drift exceeds tolerance
                # 2. Drift is increasing (not a temporary fluctuation)
                # 3. Cooldown period has passed
                if phase_diff > self.beat_phase_tolerance_ms:
                    # Check if drift is actually increasing (not just fluctuating)
                    if self.last_phase_drift > 0 and phase_diff < self.last_phase_drift * 1.5:
                        # Drift is stable or decreasing, don't correct
                        self.last_phase_drift = phase_diff
                        return
                    
                    # Drift is significant and increasing - apply correction
                    adjustment = master_offset - slave_offset
                    new_slave_pos = slave_pos + adjustment
                    duration_ms = slave_deck.player.duration()
                    
                    if duration_ms > 0:
                        new_slave_pos = max(0, min(int(new_slave_pos), duration_ms))
                    else:
                        new_slave_pos = max(0, int(new_slave_pos))
                    
                    # Apply smooth micro-correction
                    slave_deck.player.setPosition(new_slave_pos)
                    
                    # Update tracking variables
                    self.last_phase_correction_time = current_time
                    self.last_phase_drift = phase_diff
                    
                    print(f"🔄 Beat phase correction: {phase_diff:.0f}ms drift → corrected (cooldown: {self.phase_correction_cooldown_ms/1000}s)")
                else:
                    # Within tolerance - update drift tracking
                    self.last_phase_drift = phase_diff
        except Exception as e:
            # Fail silently to not interrupt playback
            pass
    
    def sync_slave_deck_tempo(self, master_new_bpm):
         """
         Called when the master deck's tempo changes, updates the slave if synced.
         
         Args:
             master_new_bpm (int): The new BPM to sync to.
         """
         if self.sync_master is None: return

         slave_deck_number = 2 if self.sync_master == 1 else 1
         slave_deck = self.deck2 if self.sync_master == 1 else self.deck1

         if slave_deck.sync_button.text() == "SYNCED":
             print(f"⚡ Sync Master (Deck {self.sync_master}) tempo changed to {master_new_bpm}. INSTANT update Slave (Deck {slave_deck_number}).")
             slave_deck.set_deck_tempo_instant(master_new_bpm)
         
    def update_sync_button_style(self, deck_number, state="default"):
        """
        Updates the visual style and text of a sync button.
        
        Args:
            deck_number (int): Deck number (1 or 2).
            state (str): Sync state ('default', 'master', 'synced').
        """
        deck = self.deck1 if deck_number == 1 else self.deck2
        if not deck or not deck.sync_button: return

        if state == "master":
             deck.sync_button.setText("MASTER")
             # Apply direct inline styling for guaranteed blue color
             deck.sync_button.setStyleSheet("""
                 QPushButton {
                     background: qlineargradient(
                         spread:pad, x1:0, y1:0, x2:0, y2:1,
                         stop:0 rgba(0, 150, 255, 0.95),
                         stop:1 rgba(0, 120, 255, 0.85)
                     );
                     color: #ffffff;
                     border: 3px solid #0096ff;
                     border-radius: 16px;
                     padding: 10px 20px;
                     font-size: 14px;
                     font-weight: 800;
                     min-height: 24px;
                     min-width: 80px;
                     text-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
                 }
                 QPushButton:hover {
                     background: qlineargradient(
                         spread:pad, x1:0, y1:0, x2:0, y2:1,
                         stop:0 rgba(0, 170, 255, 1.0),
                         stop:1 rgba(0, 140, 255, 0.95)
                     );
                     border: 3px solid #00d4ff;
                 }
                 QPushButton:pressed {
                     background: qlineargradient(
                         spread:pad, x1:0, y1:0, x2:0, y2:1,
                         stop:0 rgba(0, 130, 235, 0.95),
                         stop:1 rgba(0, 100, 215, 0.85)
                     );
                     border: 3px solid #0096ff;
                     padding: 10px 20px;
                 }
             """)
        elif state == "synced":
             deck.sync_button.setText("SYNCED")
             # Apply direct inline styling for guaranteed blue color
             deck.sync_button.setStyleSheet("""
                 QPushButton {
                     background: qlineargradient(
                         spread:pad, x1:0, y1:0, x2:0, y2:1,
                         stop:0 rgba(0, 150, 255, 0.95),
                         stop:1 rgba(0, 120, 255, 0.85)
                     );
                     color: #ffffff;
                     border: 3px solid #0096ff;
                     border-radius: 16px;
                     padding: 10px 20px;
                     font-size: 14px;
                     font-weight: 800;
                     min-height: 24px;
                     min-width: 80px;
                     text-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
                 }
                 QPushButton:hover {
                     background: qlineargradient(
                         spread:pad, x1:0, y1:0, x2:0, y2:1,
                         stop:0 rgba(0, 170, 255, 1.0),
                         stop:1 rgba(0, 140, 255, 0.95)
                     );
                     border: 3px solid #00d4ff;
                 }
                 QPushButton:pressed {
                     background: qlineargradient(
                         spread:pad, x1:0, y1:0, x2:0, y2:1,
                         stop:0 rgba(0, 130, 235, 0.95),
                         stop:1 rgba(0, 100, 215, 0.85)
                     );
                     border: 3px solid #0096ff;
                     padding: 10px 20px;
                 }
             """)
        else: # Default state
             deck.sync_button.setText("SYNC")
             # Reset to default styling
             deck.sync_button.setStyleSheet("")
             deck.sync_button.setProperty("class", "syncDefault")
             deck.sync_button.style().unpolish(deck.sync_button)
             deck.sync_button.style().polish(deck.sync_button)
             
    def _update_crossfader_display(self):
        """
        Update the crossfader position display with professional styling.
        """
        value = self.crossfader.value()
        
        # Create descriptive position text
        if value == 50:
            position_text = "CENTER"
            # Set both deck indicators to normal brightness
            self.deck1_indicator.setProperty("class", "deckIndicator")
            self.deck2_indicator.setProperty("class", "deckIndicator")
            self.deck1_indicator.setStyleSheet("font-size: 9px; font-weight: bold; padding: 1px; color: #888;")
            self.deck2_indicator.setStyleSheet("font-size: 9px; font-weight: bold; padding: 1px; color: #888;")
        elif value < 50:
            # Calculate percentage bias toward Deck A
            bias_percent = int((50 - value) * 2)
            position_text = f"◄ A {bias_percent}%"
            
            # Highlight Deck A, dim Deck B
            self.deck1_indicator.setProperty("class", "deckIndicatorActive")
            self.deck2_indicator.setProperty("class", "deckIndicatorDimmed")
            self.deck1_indicator.setStyleSheet("font-size: 9px; font-weight: bold; padding: 1px; color: #f3cf2c;")
            self.deck2_indicator.setStyleSheet("font-size: 9px; font-weight: bold; padding: 1px; color: #444;")
        else:
            # Calculate percentage bias toward Deck B
            bias_percent = int((value - 50) * 2)
            position_text = f"B {bias_percent}% ►"
            
            # Highlight Deck B, dim Deck A
            self.deck2_indicator.setProperty("class", "deckIndicatorActive")
            self.deck1_indicator.setProperty("class", "deckIndicatorDimmed")
            self.deck2_indicator.setStyleSheet("font-size: 9px; font-weight: bold; padding: 1px; color: #f3cf2c;")
            self.deck1_indicator.setStyleSheet("font-size: 9px; font-weight: bold; padding: 1px; color: #444;")
        
        # Update the styles
        self.deck1_indicator.style().unpolish(self.deck1_indicator)
        self.deck1_indicator.style().polish(self.deck1_indicator)
        self.deck2_indicator.style().unpolish(self.deck2_indicator)
        self.deck2_indicator.style().polish(self.deck2_indicator)
            
        self.crossfader_display.setText(position_text)

    def _cleanup_all_temp_files(self):
        """
        Clean up all temporary files created during the session.
        
        Removes any temporary audio files created for tempo adjustments and processing.
        """
        try:
            # First ensure all media resources are released
            if hasattr(self, 'deck1'):
                self.deck1.player.stop()
                self.deck1.player.setSource(QUrl())
                if hasattr(self.deck1, 'position_timer') and self.deck1.position_timer.isActive():
                    self.deck1.position_timer.stop()
            if hasattr(self, 'deck2'):
                self.deck2.player.stop()
                self.deck2.player.setSource(QUrl())
                if hasattr(self.deck2, 'position_timer') and self.deck2.position_timer.isActive():
                    self.deck2.position_timer.stop()

            # Get directory paths
            temp_audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_audio")
            temp_tempo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_tempo")

            # Function to forcefully delete files in a directory
            def force_delete_files(directory):
                """Force-delete all files in a directory with retries.

                Attempts to remove each file in the specified directory, retrying on
                transient PermissionError cases (e.g., file still in use) with a brief
                backoff. Removes the directory itself if it becomes empty.

                Args:
                    directory (str): Absolute or relative path to the directory to clean.
                """
                if not os.path.exists(directory):
                    return

                print(f"Cleaning up directory: {directory}")
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    try:
                        if os.path.isfile(file_path):
                            # Try multiple times with increasing delays
                            max_attempts = 3
                            for attempt in range(max_attempts):
                                try:
                                    os.remove(file_path)
                                    print(f"Deleted: {file_path}")
                                    break
                                except PermissionError:
                                    if attempt < max_attempts - 1:
                                        print(f"File in use, retrying: {file_path}")
                                        time.sleep(0.5 * (attempt + 1))  # Increasing delay
                                    else:
                                        print(f"Could not delete after {max_attempts} attempts: {file_path}")
                                except Exception as e:
                                    print(f"Error deleting {file_path}: {e}")
                                    break
                    except Exception as e:
                        print(f"Error processing {filename}: {e}")

                # Try to remove the directory itself if empty
                try:
                    if os.path.exists(directory) and not os.listdir(directory):
                        os.rmdir(directory)
                        print(f"Removed empty directory: {directory}")
                except Exception as e:
                    print(f"Could not remove directory {directory}: {e}")

            # Clean up temp directories
            force_delete_files(temp_audio_dir)
            force_delete_files(temp_tempo_dir)

        except Exception as e:
            print(f"Error during temp file cleanup: {e}")

    def toggle_recording(self):
        """
        Toggle the recording state of the application.
        
        Starts or stops recording the mixed output from both decks.
        """
        if not self.recording_folder:
            QMessageBox.warning(self, "Recording Error", "Please set a recording folder first.")
            self.record_button.setChecked(False) # Uncheck button if folder not set
            return
            
        # First check if recording folder exists and is accessible
        if not os.path.exists(self.recording_folder):
            try:
                # Try to create the folder if it doesn't exist
                os.makedirs(self.recording_folder, exist_ok=True)
                print(f"Created recording folder: {self.recording_folder}")
            except Exception as e:
                QMessageBox.critical(self, "Recording Folder Error", 
                    f"The recording folder doesn't exist and couldn't be created:\n{self.recording_folder}\n\nError: {str(e)}")
                self.record_button.setChecked(False)
                return
        
        # Make sure the folder is writable
        if not os.access(self.recording_folder, os.W_OK):
            QMessageBox.critical(self, "Recording Folder Error", 
                f"Cannot write to recording folder:\n{self.recording_folder}\n\nPlease choose another folder.")
            self.record_button.setChecked(False)
            return

        if self.record_button.isChecked(): # Start recording
            if self.is_recording: return # Already recording

            self.is_recording = True
            self.record_button.setText("Stop Recording")
            self.record_button.setProperty("class", "recordButtonActive")
            self.record_button.style().unpolish(self.record_button)
            self.record_button.style().polish(self.record_button)
            self.recording_status_label.setText("🔴 REC 00:00")
            self.recording_status_label.setVisible(True)

            # Generate filename with absolute path to avoid any confusion
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"MixLab_mix_{timestamp}.wav"
            self.recording_file_path = os.path.abspath(os.path.join(self.recording_folder, filename))

            print(f"Starting recording to: {self.recording_file_path}")

            # --- Start Recording Worker ---
            self.recording_worker = RealTimeRecordingWorker(self.recording_file_path)
            self.recording_worker.finished.connect(self._handle_recording_finished)
            self.recording_worker.error.connect(self._handle_recording_error)
            self.recording_worker.progress.connect(self._update_recording_status)
            self.recording_worker.start()
            # -----------------------------

        else: # Stop recording
            if not self.is_recording: return # Not recording

            # Set flag immediately, worker will handle actual stop
            self.is_recording = False
            self.record_button.setText("Record")
            self.record_button.setProperty("class", "recordButton")
            self.record_button.style().unpolish(self.record_button)
            self.record_button.style().polish(self.record_button)
            self.recording_status_label.setVisible(False)

            print("Signaling recording worker to stop...")

            # --- Stop Recording Worker ---
            if self.recording_worker and self.recording_worker.isRunning():
               self.recording_worker.stop_recording()
               # Worker will emit finished/error signal upon completion
            else:
               # This case shouldn't happen if is_recording was true, but handle defensively
               print("Warning: Stop requested but no worker was running.")
               self._handle_recording_finished(None) # Call finished manually with no path
            # ----------------------------
            
    def _handle_recording_finished(self, output_path):
        """
        Handles cleanup after recording is finished.
        
        Args:
            output_path (str): Path to the recorded file.
        """
        self.is_recording = False
        self.recording_worker = None
        
        if output_path:
            # Add to recordings list
            if output_path not in self.recordings_list:
                self.recordings_list.append(output_path)
                self.view_recordings_button.setEnabled(True)
            
            # First verify the file exists and is accessible
            if not os.path.exists(output_path):
                QMessageBox.warning(self, "Recording Issue", 
                    f"Recording completed, but the file could not be found at:\n{output_path}\n\n"
                    "This might be due to permission issues or a system configuration problem.")
                return
                
            # Get file size for verification
            try:
                file_size = os.path.getsize(output_path)
                file_size_mb = file_size / (1024 * 1024)  # Convert to MB
                print(f"Recording saved: {output_path} ({file_size_mb:.2f} MB)")
                
                # If file size is suspiciously small, warn the user
                if file_size_mb < 0.1:  # Less than 100KB
                    print("Warning: Recorded file is very small, may be empty or corrupted")
            except Exception as e:
                print(f"Error checking file size: {e}")
            
            # Make the file readable by all users on the system to avoid permission issues
            try:
                current_permissions = os.stat(output_path).st_mode
                os.chmod(output_path, current_permissions | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                print(f"Updated file permissions for {output_path}")
            except Exception as e:
                print(f"Could not update file permissions: {e}")
                
            # Save recording info to a log file in the same directory
            try:
                log_path = os.path.join(os.path.dirname(output_path), "recording_log.txt")
                with open(log_path, 'a') as log_file:
                    log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {os.path.basename(output_path)} - {file_size_mb:.2f} MB\n")
                print(f"Recording log updated: {log_path}")
            except Exception as e:
                print(f"Error updating recording log: {e}")
            
            # Display a more detailed message with options
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Recording Complete")
            msg_box.setText(f"Recording saved to:\n{output_path}\n\nFile size: {file_size_mb:.2f} MB")
            
            # Apply current theme to the message box
            self._apply_theme_to_dialog(msg_box)
            
            # Add buttons for different options
            reveal_button = msg_box.addButton("Reveal File", QMessageBox.ButtonRole.ActionRole)
            open_folder_button = msg_box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
            play_button = msg_box.addButton("Play Recording", QMessageBox.ButtonRole.ActionRole)
            ok_button = msg_box.addButton(QMessageBox.StandardButton.Ok)
            msg_box.setDefaultButton(ok_button)
            
            result = msg_box.exec()
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == reveal_button:
                self._reveal_file(output_path)
            elif clicked_button == open_folder_button:
                self._open_recording_folder(os.path.dirname(output_path))
            elif clicked_button == play_button:
                self._play_recording(output_path)
                
    def _reveal_file(self, file_path):
        """
        Reveals/highlights a specific file in the file explorer.
        
        Args:
            file_path (str): Path to the file to reveal.
        """
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", "The recording file could not be found.")
            return
            
        try:
            # Platform-specific commands to reveal file (highlight/select it in file explorer)
            if sys.platform == 'win32':
                # On Windows, use explorer.exe /select to highlight the file
                subprocess.run(['explorer.exe', '/select,', os.path.normpath(file_path)])
            elif sys.platform == 'darwin':  # macOS
                # On macOS, AppleScript can reveal and select the file
                script = f'tell application "Finder" to reveal POSIX file "{file_path}"'
                subprocess.run(['osascript', '-e', script])
                script = f'tell application "Finder" to activate'
                subprocess.run(['osascript', '-e', script])
            else:  # Linux and other Unix
                # On Linux, just open the containing folder; exact file highlighting varies by file manager
                subprocess.run(['xdg-open', os.path.dirname(file_path)])
            
            print(f"Revealed file: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not reveal the file: {str(e)}")
            # Fallback to opening the folder
            self._open_recording_folder(os.path.dirname(file_path))
            
    def _play_recording(self, file_path):
        """
        Play the recording in the default system audio player.
        
        Args:
            file_path (str): Path to the recording file.
        """
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", "The recording file could not be found.")
            return
            
        try:
            # Platform-specific commands to play audio file with default player
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux and other Unix
                subprocess.run(['xdg-open', file_path])
            
            print(f"Playing recording: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not play the recording: {str(e)}")
            
    def show_recordings_list(self):
        """
        Shows a list of all recordings made in this session.
        """
        if not self.recordings_list:
            QMessageBox.information(self, "Recordings", "No recordings have been made in this session.")
            return
            
        # Create a custom dialog to show recordings 
        dialog = QDialog(self)
        dialog.setWindowTitle("Session Recordings")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        # Add instructions
        instructions = QLabel("All recordings made in this session:")
        layout.addWidget(instructions)
        
        # Create a list widget to show recordings
        list_widget = QListWidget()
        for recording_path in self.recordings_list:
            # Show file name and size
            try:
                file_size_mb = os.path.getsize(recording_path) / (1024 * 1024)
                file_name = os.path.basename(recording_path)
                item_text = f"{file_name} ({file_size_mb:.2f} MB)"
            except:
                item_text = os.path.basename(recording_path)
                
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, recording_path)  # Store full path
            list_widget.addItem(item)
            
        layout.addWidget(list_widget)
        
        # Add buttons for actions
        button_layout = QHBoxLayout()
        
        reveal_button = QPushButton("Reveal File")
        play_button = QPushButton("Play Recording")
        open_folder_button = QPushButton("Open Folder")
        close_button = QPushButton("Close")
        
        button_layout.addWidget(reveal_button)
        button_layout.addWidget(play_button)
        button_layout.addWidget(open_folder_button)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # Connect button signals
        def on_reveal_clicked():
            """Reveal the selected recording in the system file explorer."""
            selected_items = list_widget.selectedItems()
            if selected_items:
                path = selected_items[0].data(Qt.ItemDataRole.UserRole)
                self._reveal_file(path)
                
        def on_play_clicked():
            """Play the selected recording with the default system audio player."""
            selected_items = list_widget.selectedItems()
            if selected_items:
                path = selected_items[0].data(Qt.ItemDataRole.UserRole)
                self._play_recording(path)
                
        def on_open_folder_clicked():
            """Open the folder containing the selected recording."""
            selected_items = list_widget.selectedItems()
            if selected_items:
                path = selected_items[0].data(Qt.ItemDataRole.UserRole)
                self._open_recording_folder(os.path.dirname(path))
        
        reveal_button.clicked.connect(on_reveal_clicked)
        play_button.clicked.connect(on_play_clicked)
        open_folder_button.clicked.connect(on_open_folder_clicked)
        close_button.clicked.connect(dialog.accept)
        
        # Apply current theme to the dialog after all widgets are added
        self._apply_theme_to_dialog(dialog)
        
        # Show the dialog
        dialog.exec()

    def _open_recording_folder(self, folder_path):
        """
        Opens the recording folder in the system file explorer.
        
        Args:
            folder_path (str): Path to the folder to open.
        """
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.warning(self, "Folder Not Found", "The recording folder could not be found.")
            return
            
        try:
            # Platform-specific commands to open folder
            if sys.platform == 'win32':
                os.startfile(folder_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux and other Unix
                subprocess.run(['xdg-open', folder_path])
            
            print(f"Opened recording folder: {folder_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open the folder: {str(e)}")

    # Add recording error handler
    def _handle_recording_error(self, error_message):
        """
        Handles recording errors.
        
        Args:
            error_message (str): Error message.
        """
        self.is_recording = False
        self.record_button.setChecked(False)
        self.record_button.setText("Record")
        self.record_button.setProperty("class", "recordButton") 
        self.record_button.style().unpolish(self.record_button)
        self.record_button.style().polish(self.record_button)
        self.recording_status_label.setVisible(False)
        
        QMessageBox.critical(self, "Recording Error", f"Error during recording:\n{error_message}")

    def select_recording_folder(self):
        """
        Lets the user choose where to save recordings.
        """
        folder = QFileDialog.getExistingDirectory(
            self, "Select Recording Folder", 
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.recording_folder = folder
            print(f"Recording folder set to: {folder}")
            
            # Create a more detailed message with an option to open the folder
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Recording Folder")
            msg_box.setText(f"Recordings will be saved to:\n{folder}")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
            
            # Custom button text for "Open"
            open_button = msg_box.button(QMessageBox.StandardButton.Open)
            open_button.setText("Open Folder")
            
            # Apply current theme to the message box
            self._apply_theme_to_dialog(msg_box)
            
            result = msg_box.exec()
            
            # If user clicked "Open Folder"
            if result == QMessageBox.StandardButton.Open:
                self._open_recording_folder(folder)

    def _update_recording_status(self, seconds):
        """
        Updates the recording status label with time.
        
        Args:
            seconds (int): Number of seconds recorded.
        """
        try:
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            self.recording_status_label.setText(f"🔴 REC {time_str}")
            # Force immediate update of the label
            self.recording_status_label.repaint()
        except Exception as e:
            print(f"Error updating recording status: {e}")

    def resizeEvent(self, event):
        """
        Handle window resize events.
        
        Args:
            event: The QResizeEvent instance.
        """
        super().resizeEvent(event)
        # Update tutorial overlay if active
        if hasattr(self, 'tutorial_manager'):
            self.tutorial_manager.update_overlay_position()

    def moveEvent(self, event):
        """
        Handle window move events.
        
        Args:
            event: The QMoveEvent instance.
        """
        super().moveEvent(event)
        # Update tutorial overlay if active
        if hasattr(self, 'tutorial_manager'):
            self.tutorial_manager.update_overlay_position()

    def auto_mix(self):
        """
        Open AI-powered auto-mix dialog for intelligent playlist generation.
        """
        # Open auto-mix dialog
        dialog = AutoMixDialog(self.audio_analyzer, self)
        dialog.playlist_ready.connect(self._load_automix_playlist)
        dialog.exec()
    
    def _load_automix_playlist(self, playlist):
        """
        Load auto-mix playlist and start automatic playback with crossfading.
        
        Args:
            playlist (List[TrackInfo]): Generated playlist from AutoMix engine.
        """
        if not playlist:
            return
        
        self.automix_playlist = playlist
        self.automix_current_index = 0
        self.automix_active = True
        self._automix_crossfading = False
        
        print(f"AutoMix: Loading playlist with {len(playlist)} tracks")
        
        # Load first track into deck 1
        first_track = playlist[0]
        self.deck1.load_file(first_track.file_path)
        
        # If playlist has more than one track, preload second track into deck 2
        if len(playlist) > 1:
            second_track = playlist[1]
            self.deck2.load_file(second_track.file_path)
            print(f"AutoMix: Preloaded track 2 into Deck 2")
        
        # Start auto-mix monitoring
        self.automix_timer.start(1000)  # Check every second
        
        # Auto-start playback after a short delay (to ensure files are loaded)
        QTimer.singleShot(1500, self._start_automix_playback)
        
        QMessageBox.information(
            self,
            "Auto-Mix Started",
            f"Loaded {len(playlist)} tracks. Auto-mix will begin playback automatically."
        )
    
    def _start_automix_playback(self):
        """Start playback of the first track in automix."""
        if self.automix_active and not self.deck1.is_playing:
            print("AutoMix: Starting playback of first track")
            self.deck1.toggle_playback()
    
    def _automix_check_transition(self):
        """
        Monitor playback and handle automatic transitions between tracks.
        """
        if not self.automix_active or not self.automix_playlist:
            self.automix_timer.stop()
            return
        
        # Check which deck is currently playing
        deck1_playing = self.deck1.is_playing
        deck2_playing = self.deck2.is_playing
        
        # Debug info
        if deck1_playing or deck2_playing:
            current_idx = self.automix_current_index
            total_tracks = len(self.automix_playlist)
            print(f"AutoMix Monitor: Deck1={deck1_playing}, Deck2={deck2_playing}, Track {current_idx+1}/{total_tracks}")
        
        # If both decks stopped, something went wrong
        if not deck1_playing and not deck2_playing:
            print("AutoMix: WARNING - Both decks stopped!")
            # Don't stop immediately, maybe they're loading
            return
        
        # Get current deck's position and duration
        if deck1_playing and not deck2_playing:
            current_deck = self.deck1
            next_deck = self.deck2
            current_position = current_deck.player.position()
            current_duration = current_deck.player.duration()
            
            # Check if next deck has a track loaded and ready
            if not next_deck.current_file:
                print(f"AutoMix: Waiting for Deck 2 to have a track loaded...")
                return  # Wait for track to be loaded
            
            # Time remaining until crossfade should start
            time_remaining = current_duration - current_position
            crossfade_start_time = self.automix_crossfade_duration * 1000  # Convert to ms
            
            if time_remaining <= crossfade_start_time and time_remaining > 0:
                # Prevent multiple crossfades
                if not hasattr(self, '_automix_crossfading') or not self._automix_crossfading:
                    print(f"AutoMix: Triggering crossfade - {time_remaining}ms remaining")
                    self._automix_crossfading = True
                    self._start_automix_crossfade(current_deck, next_deck)
        
        elif deck2_playing and not deck1_playing:
            current_deck = self.deck2
            next_deck = self.deck1
            current_position = current_deck.player.position()
            current_duration = current_deck.player.duration()
            
            # Check if next deck has a track loaded and ready
            if not next_deck.current_file:
                print(f"AutoMix: Waiting for Deck 1 to have a track loaded...")
                return  # Wait for track to be loaded
            
            time_remaining = current_duration - current_position
            crossfade_start_time = self.automix_crossfade_duration * 1000
            
            if time_remaining <= crossfade_start_time and time_remaining > 0:
                # Prevent multiple crossfades
                if not hasattr(self, '_automix_crossfading') or not self._automix_crossfading:
                    print(f"AutoMix: Triggering crossfade - {time_remaining}ms remaining")
                    self._automix_crossfading = True
                    self._start_automix_crossfade(current_deck, next_deck)
        
        # If both decks are playing (during crossfade), don't trigger another transition
        elif deck1_playing and deck2_playing:
            return
    
    def _start_automix_crossfade(self, current_deck, next_deck):
        """
        Begin crossfade transition between decks.
        
        Args:
            current_deck: Deck currently playing.
            next_deck: Deck to fade in.
        """
        # Move to next track in playlist
        old_index = self.automix_current_index
        self.automix_current_index += 1
        
        print(f"AutoMix: Crossfade started - transitioning from track {old_index+1} to track {self.automix_current_index+1}")
        print(f"AutoMix: Playlist has {len(self.automix_playlist)} tracks total")
        
        if self.automix_current_index >= len(self.automix_playlist):
            # Playlist finished
            print("AutoMix: Reached end of playlist!")
            self.automix_active = False
            self.automix_timer.stop()
            QMessageBox.information(self, "Auto-Mix Complete", "Playlist finished!")
            return
        
        # Start next deck if not already playing
        print(f"AutoMix: Starting Deck {next_deck.deck_number} (currently playing: {next_deck.is_playing})")
        if not next_deck.is_playing:
            next_deck.toggle_playback()
            print(f"AutoMix: Deck {next_deck.deck_number} playback toggled")
        
        # Perform smooth crossfade over specified duration
        # This is a simple implementation - could be enhanced with volume curves
        crossfade_steps = 30  # Number of steps in crossfade
        step_duration = (self.automix_crossfade_duration * 1000) // crossfade_steps
        
        current_volume = current_deck._current_volume
        next_volume = 0.0
        
        def crossfade_step(step_num):
            if step_num >= crossfade_steps:
                # Crossfade complete - load next track if available
                print(f"AutoMix: Crossfade complete, stopping {current_deck.deck_number}, continuing on Deck {next_deck.deck_number}")
                
                # Stop current deck
                if current_deck.is_playing:
                    current_deck.toggle_playback()
                
                # Reset volume for both decks
                current_deck.set_volume(current_volume)
                next_deck.set_volume(1.0)
                
                # Load next track into the now-free deck if available
                if self.automix_current_index + 1 < len(self.automix_playlist):
                    next_track = self.automix_playlist[self.automix_current_index + 1]
                    print(f"AutoMix: Loading next track into Deck {current_deck.deck_number}: {next_track.filename}")
                    current_deck.load_file(next_track.file_path)
                else:
                    print(f"AutoMix: No more tracks to load, current track will be the last")
                
                # Ensure automix timer continues running for next transition
                if self.automix_active and not self.automix_timer.isActive():
                    print("AutoMix: Restarting timer to monitor next transition")
                    self.automix_timer.start(1000)  # Check every second
                
                # Reset crossfading flag to allow next transition
                self._automix_crossfading = False
                print("AutoMix: Ready for next transition")
                
                return
            
            # Calculate volume levels with smooth logarithmic curve
            fade_progress = step_num / crossfade_steps
            # Smooth crossfade using power curve
            current_volume_level = current_volume * ((1.0 - fade_progress) ** 2)
            next_volume_level = fade_progress ** 0.5
            
            current_deck.set_volume(max(0.0, current_volume_level))
            next_deck.set_volume(min(1.0, next_volume_level))
            
            # Schedule next step
            QTimer.singleShot(step_duration, lambda: crossfade_step(step_num + 1))
        
        # Start crossfade
        print(f"AutoMix: Starting crossfade from Deck {current_deck.deck_number} to Deck {next_deck.deck_number}")
        crossfade_step(0)

    def show_settings_dialog(self):
        """
        Show dialog for selecting resolution and theme.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Create tabs
        tabs = QTabWidget()
        resolution_tab = QWidget()
        theme_tab = QWidget()
        cache_tab = QWidget()
        tutorial_tab = QWidget()
        
        tabs.addTab(resolution_tab, "Resolution")
        tabs.addTab(theme_tab, "Theme")
        tabs.addTab(cache_tab, "Cache")
        tabs.addTab(tutorial_tab, "Tutorial")
        
        # Resolution tab
        res_layout = QVBoxLayout(resolution_tab)
        
        # Add explanation label
        explanation = QLabel("Choose a resolution that fits your screen:")
        explanation.setWordWrap(True)
        explanation.setProperty("class", "neonText")
        res_layout.addWidget(explanation)
        
        # Add resolution buttons
        for name, (width, height) in self.resolution_presets.items():
            btn = QPushButton(name)
            btn.setProperty("class", "neonBorder")
            btn.clicked.connect(lambda checked, w=width, h=height: self.set_resolution(w, h, dialog))
            res_layout.addWidget(btn)
        
        # Add custom resolution option
        custom_layout = QHBoxLayout()
        custom_label = QLabel("Custom:")
        custom_label.setProperty("class", "neonText")
        width_input = QLineEdit()
        width_input.setPlaceholderText("Width")
        width_input.setValidator(QIntValidator(800, 3840))  # Min 800, Max 4K
        height_input = QLineEdit()
        height_input.setPlaceholderText("Height")
        height_input.setValidator(QIntValidator(600, 2160))  # Min 600, Max 4K
        
        apply_button = QPushButton("Apply Custom")
        apply_button.setProperty("class", "neonBorder")
        apply_button.clicked.connect(lambda: self.apply_custom_resolution(width_input, height_input, dialog))
        
        custom_layout.addWidget(custom_label)
        custom_layout.addWidget(width_input)
        custom_layout.addWidget(QLabel("x"))
        custom_layout.addWidget(height_input)
        custom_layout.addWidget(apply_button)
        
        res_layout.addLayout(custom_layout)
        
        # Theme tab
        theme_layout = QVBoxLayout(theme_tab)
        
        theme_label = QLabel("Select a theme:")
        theme_label.setProperty("class", "neonText")
        theme_layout.addWidget(theme_label)
        
        # Add theme buttons
        theme_group = QButtonGroup(dialog)
        for i, theme_name in enumerate(self.theme_presets.keys()):
            radio = QRadioButton(theme_name)
            if theme_name == self.current_theme:
                radio.setChecked(True)
            theme_group.addButton(radio, i)
            theme_layout.addWidget(radio)
        
        # Apply theme button
        apply_theme_btn = QPushButton("Apply Theme")
        apply_theme_btn.setProperty("class", "neonBorder")
        apply_theme_btn.clicked.connect(lambda: self.apply_theme(theme_group, dialog))
        theme_layout.addWidget(apply_theme_btn)
        
        # Cache tab
        cache_layout = QVBoxLayout(cache_tab)
        
        cache_label = QLabel("Cache Management:")
        cache_label.setProperty("class", "neonText")
        cache_layout.addWidget(cache_label)
        
        # Cache statistics
        if hasattr(self, 'cache_manager') and self.cache_manager:
            try:
                stats = self.cache_manager.get_cache_stats()
                stats_text = f"""
                Cache Statistics:
• Total files: {stats.get('total_files', 0)}
• BPM cached: {stats.get('bpm_cached', 0)}
• Waveforms cached: {stats.get('waveform_cached', 0)}
• FFT cached: {stats.get('fft_cached', 0)}
• Cache size: {stats.get('cache_size_mb', 0)} MB
• Location: {stats.get('cache_directory', 'Unknown')}
""".strip()
            except Exception as e:
                stats_text = f"Error getting cache stats: {e}"
        else:
            stats_text = "Cache manager not available"
            
        stats_label = QLabel(stats_text)
        stats_label.setProperty("class", "cacheStats")
        stats_label.setWordWrap(True)
        cache_layout.addWidget(stats_label)
        
        # Cache management buttons
        cache_buttons_layout = QHBoxLayout()
        
        clear_cache_btn = QPushButton("Clear All Cache")
        clear_cache_btn.setProperty("class", "neonBorder")
        clear_cache_btn.clicked.connect(lambda: self.clear_cache_with_confirmation(dialog))
        
        cleanup_old_btn = QPushButton("Cleanup Old Cache")
        cleanup_old_btn.setProperty("class", "neonBorder")
        cleanup_old_btn.clicked.connect(lambda: self.cleanup_old_cache_with_confirmation(dialog))
        
        refresh_stats_btn = QPushButton("Refresh Stats")
        refresh_stats_btn.setProperty("class", "neonBorder")
        refresh_stats_btn.clicked.connect(lambda: self.refresh_cache_stats(stats_label))
        
        cache_buttons_layout.addWidget(clear_cache_btn)
        cache_buttons_layout.addWidget(cleanup_old_btn)
        cache_buttons_layout.addWidget(refresh_stats_btn)
        
        cache_layout.addLayout(cache_buttons_layout)
        
        # Tutorial tab
        tutorial_layout = QVBoxLayout(tutorial_tab)
        
        tutorial_label = QLabel("Tutorial Settings:")
        tutorial_label.setProperty("class", "neonText")
        tutorial_layout.addWidget(tutorial_label)
        
        # Tutorial explanation
        tutorial_explanation = QLabel(
            "The tutorial helps new users learn how to use MixLab DJ.\n"
            "You can enable or disable it here. If disabled, the tutorial\n"
            "will not show automatically on startup."
        )
        tutorial_explanation.setProperty("class", "dialogLabel")
        tutorial_explanation.setWordWrap(True)
        tutorial_layout.addWidget(tutorial_explanation)
        
        # Tutorial enable/disable toggle
        tutorial_toggle_layout = QHBoxLayout()
        tutorial_toggle_label = QLabel("Enable Tutorial:")
        tutorial_toggle_label.setProperty("class", "neonText")
        
        self.tutorial_enabled_checkbox = QCheckBox()
        self.tutorial_enabled_checkbox.setChecked(self.load_tutorial_setting())
        
        tutorial_toggle_layout.addWidget(tutorial_toggle_label)
        tutorial_toggle_layout.addWidget(self.tutorial_enabled_checkbox)
        tutorial_toggle_layout.addStretch()
        
        tutorial_layout.addLayout(tutorial_toggle_layout)
        
        # Tutorial action buttons
        tutorial_buttons_layout = QHBoxLayout()
        
        start_tutorial_btn = QPushButton("Start Tutorial Now")
        start_tutorial_btn.setProperty("class", "neonBorder")
        start_tutorial_btn.clicked.connect(self._start_tutorial_from_settings)
        
        reset_tutorial_btn = QPushButton("Reset Tutorial")
        reset_tutorial_btn.setProperty("class", "neonBorder")
        reset_tutorial_btn.clicked.connect(self._reset_tutorial_from_settings)
        
        save_tutorial_btn = QPushButton("Save Settings")
        save_tutorial_btn.setProperty("class", "neonBorder")
        save_tutorial_btn.clicked.connect(self._save_tutorial_setting)
        
        tutorial_buttons_layout.addWidget(start_tutorial_btn)
        tutorial_buttons_layout.addWidget(reset_tutorial_btn)
        tutorial_buttons_layout.addWidget(save_tutorial_btn)
        
        tutorial_layout.addLayout(tutorial_buttons_layout)
        
        layout.addWidget(tabs)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.setProperty("class", "neonBorder")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        # Apply current theme to the dialog after all widgets are added
        self._apply_theme_to_dialog(dialog)
        
        dialog.exec()

    def clear_cache_with_confirmation(self, parent_dialog):
        """Clear all cache with user confirmation."""
        if not hasattr(self, 'cache_manager') or not self.cache_manager:
            QMessageBox.warning(parent_dialog, "Error", "Cache manager not available")
            return
            
        result = QMessageBox.question(
            parent_dialog,
            "Clear Cache",
            "Are you sure you want to clear all cached data?\n\n"
            "This will remove all cached BPM, waveform, and FFT data.\n"
            "Files will need to be reanalyzed on next load.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            try:
                self.cache_manager.clear_all_cache()
                QMessageBox.information(parent_dialog, "Success", "Cache cleared successfully!")
            except Exception as e:
                QMessageBox.critical(parent_dialog, "Error", f"Failed to clear cache: {e}")

    def cleanup_old_cache_with_confirmation(self, parent_dialog):
        """Cleanup old cache entries with user confirmation."""
        if not hasattr(self, 'cache_manager') or not self.cache_manager:
            QMessageBox.warning(parent_dialog, "Error", "Cache manager not available")
            return
            
        result = QMessageBox.question(
            parent_dialog,
            "Cleanup Old Cache",
            "Remove cache entries older than 30 days?\n\n"
            "This will free up disk space by removing old cached data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if result == QMessageBox.StandardButton.Yes:
            try:
                self.cache_manager.cleanup_old_cache(30)
                QMessageBox.information(parent_dialog, "Success", "Old cache entries cleaned up!")
            except Exception as e:
                QMessageBox.critical(parent_dialog, "Error", f"Failed to cleanup cache: {e}")

    def refresh_cache_stats(self, stats_label):
        """Refresh the cache statistics display."""
        if not hasattr(self, 'cache_manager') or not self.cache_manager:
            stats_label.setText("Cache manager not available")
            return
            
        try:
            stats = self.cache_manager.get_cache_stats()
            stats_text = f"""
Cache Statistics:
• Total files: {stats.get('total_files', 0)}
• BPM cached: {stats.get('bpm_cached', 0)}
• Waveforms cached: {stats.get('waveform_cached', 0)}
• FFT cached: {stats.get('fft_cached', 0)}
• Cache size: {stats.get('cache_size_mb', 0)} MB
• Location: {stats.get('cache_directory', 'Unknown')}
                        """.strip()
            stats_label.setText(stats_text)
        except Exception as e:
            stats_label.setText(f"Error getting cache stats: {e}")

    def _auto_fit_to_screen(self):
        """
        Automatically fit the window to the screen resolution on startup.
        Uses 90% of available screen space and centers the window.
        """
        try:
            # Get the primary screen and its available geometry
            screen = QApplication.primaryScreen()
            if not screen:
                print("⚠️  No screen detected, using default size (1200x800)")
                self.resize(1200, 800)
                return
            
            available_geometry = screen.availableGeometry()
            screen_width = available_geometry.width()
            screen_height = available_geometry.height()
            
            info(f"🖥️  Detected screen resolution: {screen_width}x{screen_height}")
            
            # Use 90% of screen size for optimal viewing (not overwhelming)
            window_width = int(screen_width * 0.90)
            window_height = int(screen_height * 0.90)
            
            # Ensure minimum size for usability
            window_width = max(1000, window_width)
            window_height = max(700, window_height)
            
            # Ensure we don't exceed screen size
            window_width = min(window_width, screen_width)
            window_height = min(window_height, screen_height)
            
            # Calculate center position
            x = (screen_width - window_width) // 2 + available_geometry.x()
            y = (screen_height - window_height) // 2 + available_geometry.y()
            
            # Set geometry (position and size)
            self.setGeometry(x, y, window_width, window_height)
            
            success(f"✅ Window auto-sized to: {window_width}x{window_height} (90% of screen)")
            debug(f"   Centered at position: ({x}, {y})")
            
        except Exception as e:
            warning(f"⚠️  Error auto-fitting to screen: {e}")
            info("   Using default size (1200x800)")
            self.resize(1200, 800)
    
    def set_resolution(self, width, height, dialog=None):
        """
        Set the window resolution.
        
        Args:
            width (int): Window width.
            height (int): Window height.
            dialog (QDialog, optional): Dialog to close after setting resolution.
        """
        try:
            # Get the available geometry of the screen
            screen = QApplication.primaryScreen()
            available_geometry = screen.availableGeometry()
            
            # Check if the requested resolution fits the screen
            if width > available_geometry.width() or height > available_geometry.height():
                result = QMessageBox.warning(
                    self,
                    "Resolution Warning",
                    f"The selected resolution ({width}x{height}) is larger than your screen.\n"
                    "Do you want to proceed anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if result == QMessageBox.StandardButton.No:
                    return
            
            # Calculate center position
            x = (available_geometry.width() - width) // 2
            y = (available_geometry.height() - height) // 2
            
            # Set the new geometry
            self.setGeometry(x, y, width, height)
            
            if dialog:
                dialog.close()
                
            # Show confirmation
            QMessageBox.information(
                self,
                "Resolution Changed",
                f"Window size set to {width}x{height}.\n"
                "If the window is too large, you can use the scroll bars to view all content."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to set resolution: {str(e)}"
            )

    def apply_custom_resolution(self, width_input, height_input, dialog):
        """Apply custom resolution from input fields."""
        try:
            width = int(width_input.text())
            height = int(height_input.text())
            
            if width < 800 or height < 600:
                QMessageBox.warning(
                    self,
                    "Invalid Resolution",
                    "Minimum resolution is 800x600."
                )
                return
                
            self.set_resolution(width, height, dialog)
            
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter valid numbers for width and height."
            )

    def load_theme_setting(self):
        """Load the saved theme setting or return Dark Mode as default."""
        default_theme = "Dark Mode"
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    saved_theme = settings.get('theme', default_theme)
                    if saved_theme in self.theme_presets:
                        print(f"Loaded saved theme: {saved_theme}")
                        return saved_theme
        except Exception as e:
            print(f"Error loading theme setting: {e}")
        
        print(f"Using default theme: {default_theme}")
        return default_theme

    def save_theme_setting(self, theme_name):
        """Save the current theme setting."""
        try:
            settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            
            settings['theme'] = theme_name
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            print(f"Saved theme setting: {theme_name}")
        except Exception as e:
            print(f"Error saving theme setting: {e}")

    def apply_theme_without_dialog(self, theme_name):
        """Apply theme without showing dialog or confirmation."""
        print(f"apply_theme_without_dialog called with: {theme_name}")
        if theme_name not in self.theme_presets:
            print(f"ERROR: Theme '{theme_name}' not found in presets!")
            return
            
        self.current_theme = theme_name
        print(f"Setting current_theme to: {self.current_theme}")
        
        # Apply appropriate palette based on theme
        if theme_name == "Light Mode":
            print("Applying light palette for Light Mode theme")
            self.force_light_palette()
        else:
            # For all other themes (Dark Mode, Neon Purple, Forest), use dark palette
            print("Applying dark palette for non-light themes")
            self.force_dark_palette()
        
        # Load styles from styles.qss file and set theme property
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            qss_path = os.path.join(script_dir, "styles.qss")
            
            if os.path.exists(qss_path):
                print(f"Loading styles from: {qss_path}")
                with open(qss_path, "r", encoding='utf-8') as qss_file:
                    stylesheet = qss_file.read()
                
                # Apply theme properties to all widgets
                print(f"Applying theme properties for: {theme_name}")
                self._apply_theme_properties(theme_name)
                
                # Apply the stylesheet
                self.setStyleSheet(stylesheet)
                
                # Force style refresh on all widgets
                print("Refreshing widget styles...")
                self._refresh_all_widget_styles()
                
                # Update elements that can't be styled with CSS
                self._update_non_css_elements(theme_name)
                
                print(f"Theme applied successfully: {theme_name}")
            else:
                print(f"Warning: Stylesheet file not found at {qss_path}")
                # Fallback to minimal styling
                self.setStyleSheet("QMainWindow { background-color: #1a1a1a; color: #f3cf2c; }")
        except Exception as e:
            print(f"Error loading stylesheet: {e}")
                        # Fallback to minimal styling
            self.setStyleSheet("QMainWindow { background-color: #1a1a1a; color: #f3cf2c; }")

    def _apply_theme_properties(self, theme_name):
        """Apply theme properties to all widgets."""
        # Get all widgets in the application
        all_widgets = self.findChildren(QWidget)
        all_widgets.append(self)  # Include the main window
        
        print(f"Updating theme properties on {len(all_widgets)} widgets")
        
        buttons_updated = 0
        for widget in all_widgets:
            # Clear existing theme properties
            widget.setProperty("lightMode", False)
            widget.setProperty("purpleMode", False)
            widget.setProperty("forestMode", False)
            
            # Set the appropriate theme property
            if theme_name == "Light Mode":
                widget.setProperty("lightMode", True)
                if widget.__class__.__name__ == "QPushButton":
                    buttons_updated += 1
            elif theme_name == "Neon Purple":
                widget.setProperty("purpleMode", True)
            elif theme_name == "Forest":
                widget.setProperty("forestMode", True)
            # Dark Mode uses no special property (base styles)
        
        if theme_name == "Light Mode":
            print(f"Updated {buttons_updated} buttons with lightMode property")

    def _refresh_all_widget_styles(self):
        """Force style refresh on all widgets."""
        # Get all widgets in the application
        all_widgets = self.findChildren(QWidget)
        all_widgets.append(self)  # Include the main window
        
        for widget in all_widgets:
            try:
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
            except Exception as e:
                # Ignore errors on individual widgets
                pass

    def _apply_theme_to_dialog(self, dialog):
        """Apply current theme properties to a dialog and all its children."""
        # Apply theme properties to the dialog and all its children
        all_widgets = dialog.findChildren(QWidget)
        all_widgets.append(dialog)  # Include the dialog itself
        
        for widget in all_widgets:
            # Clear existing theme properties
            widget.setProperty("lightMode", False)
            widget.setProperty("purpleMode", False)
            widget.setProperty("forestMode", False)
            
            # Set the appropriate theme property based on current theme
            if self.current_theme == "Light Mode":
                widget.setProperty("lightMode", True)
            elif self.current_theme == "Neon Purple":
                widget.setProperty("purpleMode", True)
            elif self.current_theme == "Forest":
                widget.setProperty("forestMode", True)
            # Dark Mode uses no special property (base styles)
        
        # Force style refresh on all widgets in the dialog
        for widget in all_widgets:
            try:
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
            except Exception as e:
                # Ignore errors on individual widgets
                pass

    def _show_themed_message_box(self, icon, title, text, parent=None, buttons=None):
        """Show a themed message box with the current theme applied."""
        if parent is None:
            parent = self
            
        msg_box = QMessageBox(parent)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        
        if buttons:
            msg_box.setStandardButtons(buttons)
        
        # Apply current theme to the message box
        self._apply_theme_to_dialog(msg_box)
        
        return msg_box.exec()

    def _update_non_css_elements(self, theme_name):
        """Update elements that can't be styled with CSS (custom painted widgets)."""
        if not hasattr(self, 'deck1') or not hasattr(self, 'deck2'):
            return
            
        # Get theme colors
        if theme_name == "Dark Mode":
            accent_color = "#f3cf2c"
        else:
            theme = self.theme_presets[theme_name]
            accent_color = theme["accent"]
        
        # Convert hex to QColor
        accent_qcolor = QColor(accent_color)
        
        # Update custom painted widgets for both decks
        for deck in [self.deck1, self.deck2]:
            # Update waveform colors (custom painted)
            if hasattr(deck, 'waveform') and deck.waveform:
                deck.waveform.waveform_color_future = accent_qcolor
                deck.waveform.waveform_color_past = QColor(accent_qcolor.red(), accent_qcolor.green(), accent_qcolor.blue(), 100)
                deck.waveform.playhead_color = accent_qcolor
                deck.waveform.grid_color = QColor(accent_qcolor.red(), accent_qcolor.green(), accent_qcolor.blue(), 40)
                deck.waveform.timeline_text_color = accent_qcolor
                deck.waveform.setStyleSheet("")  # Remove hardcoded styles
                deck.waveform.update()
            
            # Update spectrogram
            if hasattr(deck, 'spectrogram') and deck.spectrogram:
                deck.spectrogram.setStyleSheet("")  # Remove hardcoded styles
            
            # Update GlassWidget hover effects (custom painted)
            deck._theme_accent_color = accent_qcolor
            deck.update()
            
            # Update turntable colors (custom painted)
            if hasattr(deck, 'turntable') and deck.turntable:
                deck.turntable.colors['primary'] = accent_qcolor
                deck.turntable.colors['glow'] = accent_qcolor
                deck.turntable.colors['outer_ring'] = accent_qcolor.darker(120)
                deck.turntable.update()

    def apply_theme(self, theme_group, dialog):
        """Apply the selected theme and save the setting."""
        selected_button = theme_group.checkedButton()
        if not selected_button:
            return
            
        theme_name = selected_button.text()
        if theme_name not in self.theme_presets:
            return
            
        # Apply the theme
        self.apply_theme_without_dialog(theme_name)
        
        # Save the theme setting
        self.save_theme_setting(theme_name)
        
        message = "Theme changed to " + theme_name
        if theme_name == "Dark Mode":
            message += " (using original styles)"
        message += ".\nSome changes may require a restart to take full effect."
        
        QMessageBox.information(
            self,
            "Theme Applied",
            message
        )
        
        if dialog:
            dialog.close()

    def load_tutorial_setting(self):
        """Load tutorial enabled setting from config file."""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tutorial_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    return config.get('tutorial_enabled', True)  # Default to enabled
            return True  # Default to enabled if file doesn't exist
        except Exception as e:
            print(f"Error loading tutorial setting: {e}")
            return True  # Default to enabled on error

    @staticmethod
    def save_tutorial_setting(enabled):
        """Save tutorial enabled setting to config file."""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tutorial_config.json")
            
            # Load existing config or create new one
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            
            # Update tutorial settings
            config['tutorial_enabled'] = enabled
            
            # Preserve tutorial_completed status if it exists
            if 'tutorial_completed' not in config:
                config['tutorial_completed'] = False
            
            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            print(f"Tutorial setting saved: enabled={enabled}")
        except Exception as e:
            print(f"Error saving tutorial setting: {e}")

    def _start_tutorial_from_settings(self):
        """Start tutorial from settings dialog."""
        if hasattr(self, 'tutorial_manager'):
            self.tutorial_manager.start_tutorial()
        else:
            QMessageBox.information(self, "Tutorial", "Tutorial manager not available.")

    def _reset_tutorial_from_settings(self):
        """Reset tutorial completion status."""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tutorial_config.json")
            
            # Load existing config or create new one
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            
            # Reset tutorial completion status
            config['tutorial_completed'] = False
            
            # Preserve tutorial_enabled setting if it exists
            if 'tutorial_enabled' not in config:
                config['tutorial_enabled'] = True
            
            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            QMessageBox.information(self, "Tutorial Reset", "Tutorial has been reset. It will show again on next startup.")
            print("Tutorial reset successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset tutorial: {e}")
            print(f"Error resetting tutorial: {e}")

    def _save_tutorial_setting(self):
        """Save the current tutorial setting from the checkbox."""
        enabled = self.tutorial_enabled_checkbox.isChecked()
        self.save_tutorial_setting(enabled)
        QMessageBox.information(self, "Settings Saved", f"Tutorial {'enabled' if enabled else 'disabled'} successfully!")

def main():
    """Application entry point for MixLab DJ.

    Sets up logging, initializes the Qt application, constructs the main
    `DJApp` window, and starts the Qt event loop.
    """
    # Configure logging (optional, can be more sophisticated)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    app = QApplication(sys.argv)
    
    # Suppress Qt warnings for unsupported CSS properties
    def qt_message_handler(mode, context, message):
        # Filter out "Unknown property" warnings from QSS
        if "Unknown property" in message:
            return
        # Allow all other messages through
        if mode == QtMsgType.QtDebugMsg:
            print(f"Qt Debug: {message}")
        elif mode == QtMsgType.QtWarningMsg:
            print(f"Qt Warning: {message}")
        elif mode == QtMsgType.QtCriticalMsg:
            print(f"Qt Critical: {message}")
        elif mode == QtMsgType.QtFatalMsg:
            print(f"Qt Fatal: {message}")
    
    # Install the message handler
    qInstallMessageHandler(qt_message_handler)
    
    # Set application-wide style to Fusion and ensure it doesn't follow system theme
    app.setStyle("Fusion")
    
    # Set application-wide style to Fusion
    print("Setting application style to Fusion...")
    
    # Create and show the main window
    window = DJApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 