"""
Debug Logger for MixLab DJ
Provides toggleable debug logging for development vs production.
"""

import os
import json
from datetime import datetime

class DebugLogger:
    """
    Singleton debug logger that can be enabled/disabled via settings.
    """
    _instance = None
    _debug_enabled = False
    _verbose_enabled = False
    _log_file = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DebugLogger, cls).__new__(cls)
            cls._instance._load_settings()
        return cls._instance
    
    def _load_settings(self):
        """Load debug settings from settings.json"""
        try:
            settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self._debug_enabled = settings.get('debug_mode', False)
                    self._verbose_enabled = settings.get('verbose_logging', False)
        except Exception:
            # Default to disabled if settings can't be loaded
            self._debug_enabled = False
            self._verbose_enabled = False
    
    @classmethod
    def is_enabled(cls):
        """Check if debug logging is enabled"""
        instance = cls()
        return instance._debug_enabled
    
    @classmethod
    def is_verbose(cls):
        """Check if verbose logging is enabled"""
        instance = cls()
        return instance._verbose_enabled
    
    @classmethod
    def debug(cls, message):
        """Log debug message (only if debug enabled)"""
        if cls.is_enabled():
            print(f"[DEBUG] {message}")
    
    @classmethod
    def verbose(cls, message):
        """Log verbose message (only if verbose enabled)"""
        if cls.is_verbose():
            print(f"[VERBOSE] {message}")
    
    @classmethod
    def info(cls, message):
        """Log info message (always shown)"""
        print(f"ℹ️  {message}")
    
    @classmethod
    def warning(cls, message):
        """Log warning message (always shown)"""
        print(f"⚠️  {message}")
    
    @classmethod
    def error(cls, message):
        """Log error message (always shown)"""
        print(f"❌ {message}")
    
    @classmethod
    def success(cls, message):
        """Log success message (always shown)"""
        print(f"✅ {message}")
    
    @classmethod
    def enable(cls):
        """Enable debug logging"""
        instance = cls()
        instance._debug_enabled = True
        cls._save_setting('debug_mode', True)
    
    @classmethod
    def disable(cls):
        """Disable debug logging"""
        instance = cls()
        instance._debug_enabled = False
        cls._save_setting('debug_mode', False)
    
    @classmethod
    def _save_setting(cls, key, value):
        """Save debug setting to settings.json"""
        try:
            settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
            settings = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            
            settings[key] = value
            
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving debug setting: {e}")


# Convenience functions for quick access
debug = DebugLogger.debug
verbose = DebugLogger.verbose
info = DebugLogger.info
warning = DebugLogger.warning
error = DebugLogger.error
success = DebugLogger.success

# Default: Debug mode OFF for production performance
# To enable: Add "debug_mode": true to settings.json

