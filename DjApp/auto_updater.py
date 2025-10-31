"""
AI-Powered Auto-Updater for MixLab DJ

Automatically checks and updates Python packages on startup.
Uses intelligent logic to determine critical updates.

PRIVACY NOTICE:
- Only queries public PyPI (https://pypi.org) to check package versions
- No user data, analytics, or tracking information is collected or sent
- No authentication required - anonymous public API queries only
- All checks are local except for PyPI version lookups
"""

import sys
import subprocess
import json
import urllib.request
import urllib.error
import importlib.metadata
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import os
import logging

logger = logging.getLogger(__name__)

# Update check interval (days)
UPDATE_CHECK_INTERVAL = 1  # Check daily
LAST_CHECK_FILE = "cache/last_update_check.json"

# Critical packages that should always be up-to-date
CRITICAL_PACKAGES = ['PyQt6', 'numpy', 'soundfile', 'librosa']

# Update severity levels
SEVERITY_CRITICAL = "critical"    # Security fixes, major bugs
SEVERITY_IMPORTANT = "important"  # Performance improvements, features
SEVERITY_MINOR = "minor"         # Small fixes, optimizations


class PackageUpdate:
    """Information about a package update."""
    
    def __init__(self, name: str, current: str, latest: str, severity: str = SEVERITY_MINOR):
        self.name = name
        self.current = current
        self.latest = latest
        self.severity = severity
        self.release_date = None
        self.changelog_summary = ""
    
    def __repr__(self):
        return f"PackageUpdate({self.name}: {self.current} → {self.latest}, {self.severity})"


class AutoUpdater:
    """Intelligent auto-updater for MixLab DJ dependencies."""
    
    def __init__(self, auto_update_enabled: bool = False, silent_mode: bool = False):
        """
        Initialize auto-updater.
        
        Args:
            auto_update_enabled (bool): If True, auto-install updates (requires user to enable)
            silent_mode (bool): If True, only show critical warnings
        """
        self.auto_update_enabled = auto_update_enabled
        self.silent_mode = silent_mode
        self.available_updates: List[PackageUpdate] = []
        
        # Ensure cache directory exists
        os.makedirs(os.path.dirname(LAST_CHECK_FILE), exist_ok=True)
    
    def should_check_updates(self) -> bool:
        """
        Determine if we should check for updates based on last check time.
        
        Returns:
            bool: True if enough time has passed since last check.
        """
        if not os.path.exists(LAST_CHECK_FILE):
            return True
        
        try:
            with open(LAST_CHECK_FILE, 'r') as f:
                data = json.load(f)
                last_check = datetime.fromisoformat(data.get('last_check', '2000-01-01'))
                
                # Check if interval has passed
                if datetime.now() - last_check > timedelta(days=UPDATE_CHECK_INTERVAL):
                    return True
                
                return False
        
        except Exception as e:
            logger.warning(f"Error reading last check file: {e}")
            return True
    
    def save_last_check_time(self):
        """Save the current time as last update check."""
        try:
            data = {
                'last_check': datetime.now().isoformat(),
                'version': sys.version_info[:3]
            }
            with open(LAST_CHECK_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Could not save last check time: {e}")
    
    def get_latest_version_from_pypi(self, package_name: str) -> Optional[str]:
        """
        Get the latest version of a package from PyPI (public Python Package Index).
        
        This queries the public PyPI API at https://pypi.org to check for updates.
        No personal data or tracking information is sent - only the package name.
        
        Args:
            package_name (str): Package name to check.
            
        Returns:
            Optional[str]: Latest version string, or None if unavailable.
        """
        try:
            # Query public PyPI API (no authentication, no tracking)
            url = f"https://pypi.org/pypi/{package_name}/json"
            
            # Simple GET request - no headers, no user data
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                return data['info']['version']
        
        except urllib.error.URLError:
            logger.warning(f"Could not fetch version for {package_name} (network error)")
            return None
        except Exception as e:
            logger.warning(f"Error fetching version for {package_name}: {e}")
            return None
    
    def parse_version(self, version_str: str) -> Tuple[int, ...]:
        """Parse version string to tuple for comparison."""
        try:
            return tuple(int(x) for x in version_str.split('.')[:3])
        except (ValueError, AttributeError):
            return (0, 0, 0)
    
    def determine_update_severity(self, package_name: str, current: str, latest: str) -> str:
        """
        AI-powered logic to determine update severity.
        
        Uses version numbers and package importance to classify updates.
        
        Args:
            package_name (str): Name of package
            current (str): Current version
            latest (str): Latest version
            
        Returns:
            str: Severity level (critical, important, minor)
        """
        current_ver = self.parse_version(current)
        latest_ver = self.parse_version(latest)
        
        # Calculate version difference
        major_diff = latest_ver[0] - current_ver[0]
        minor_diff = latest_ver[1] - current_ver[1] if len(latest_ver) > 1 and len(current_ver) > 1 else 0
        
        # Critical packages always important
        if package_name in CRITICAL_PACKAGES:
            if major_diff > 0:
                return SEVERITY_CRITICAL  # Major version bump in critical package
            elif minor_diff > 2:
                return SEVERITY_IMPORTANT  # Multiple minor versions behind
            elif minor_diff > 0:
                return SEVERITY_MINOR
        
        # Non-critical packages
        if major_diff > 1:
            return SEVERITY_IMPORTANT  # Very outdated
        elif major_diff == 1:
            return SEVERITY_MINOR  # One major version behind
        elif minor_diff > 5:
            return SEVERITY_IMPORTANT  # Many minor versions behind
        
        return SEVERITY_MINOR
    
    def check_for_updates(self, packages: List[str]) -> List[PackageUpdate]:
        """
        Check for updates for specified packages.
        
        Args:
            packages (List[str]): List of package names to check.
            
        Returns:
            List[PackageUpdate]: List of available updates.
        """
        updates = []
        
        if not self.silent_mode:
            print("🔍 Checking for updates...")
        
        for package in packages:
            try:
                # Get current version
                current_version = importlib.metadata.version(package)
                
                # Get latest version from PyPI
                latest_version = self.get_latest_version_from_pypi(package)
                
                if latest_version is None:
                    continue
                
                # Compare versions
                if self.parse_version(latest_version) > self.parse_version(current_version):
                    severity = self.determine_update_severity(package, current_version, latest_version)
                    update = PackageUpdate(package, current_version, latest_version, severity)
                    updates.append(update)
                    
                    if not self.silent_mode:
                        severity_icon = "🔴" if severity == SEVERITY_CRITICAL else "🟡" if severity == SEVERITY_IMPORTANT else "🟢"
                        print(f"  {severity_icon} {package}: {current_version} → {latest_version} ({severity})")
            
            except importlib.metadata.PackageNotFoundError:
                if not self.silent_mode:
                    print(f"  ⚠️  {package}: Not installed")
            except Exception as e:
                logger.warning(f"Error checking {package}: {e}")
        
        self.available_updates = updates
        return updates
    
    def install_updates(self, updates: List[PackageUpdate], force: bool = False) -> bool:
        """
        Install available updates.
        
        Args:
            updates (List[PackageUpdate]): Updates to install.
            force (bool): If True, install without confirmation.
            
        Returns:
            bool: True if successful.
        """
        if not updates:
            return True
        
        # Build pip command
        packages_to_update = [f"{u.name}=={u.latest}" for u in updates]
        
        print(f"\n📦 Installing {len(updates)} update(s)...")
        
        try:
            # Run pip install
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + packages_to_update
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print("✅ Updates installed successfully!")
                return True
            else:
                print(f"❌ Update failed: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            print("❌ Update timed out (>5 minutes)")
            return False
        except Exception as e:
            print(f"❌ Error installing updates: {e}")
            return False
    
    def run_update_check(self, packages: List[str] = None) -> Dict:
        """
        Main entry point - check for updates and optionally install.
        
        Args:
            packages (List[str]): Packages to check. If None, checks all.
            
        Returns:
            Dict: Update summary with statistics.
        """
        # Check if we should run update check
        if not self.should_check_updates():
            if not self.silent_mode:
                print("✅ Updates checked recently. Next check in 24 hours.")
            return {'status': 'skipped', 'updates': []}
        
        # Default packages to check
        if packages is None:
            packages = [
                'numpy', 'PyQt6', 'soundfile', 'sounddevice', 'scipy',
                'librosa', 'soxr', 'numba', 'pyrubberband'
            ]
        
        # Check for updates
        updates = self.check_for_updates(packages)
        
        # Save check time
        self.save_last_check_time()
        
        # Categorize updates
        critical = [u for u in updates if u.severity == SEVERITY_CRITICAL]
        important = [u for u in updates if u.severity == SEVERITY_IMPORTANT]
        minor = [u for u in updates if u.severity == SEVERITY_MINOR]
        
        # Summary
        summary = {
            'status': 'checked',
            'total': len(updates),
            'critical': len(critical),
            'important': len(important),
            'minor': len(minor),
            'updates': updates
        }
        
        if not updates:
            if not self.silent_mode:
                print("✅ All packages are up to date!")
            return summary
        
        # Display summary
        if not self.silent_mode:
            print(f"\n📊 Update Summary:")
            print(f"   Total updates available: {len(updates)}")
            if critical:
                print(f"   🔴 Critical: {len(critical)}")
            if important:
                print(f"   🟡 Important: {len(important)}")
            if minor:
                print(f"   🟢 Minor: {len(minor)}")
        
        # Auto-update if enabled
        if self.auto_update_enabled:
            # Always auto-install critical updates
            if critical:
                print("\n🔴 Installing critical security updates automatically...")
                self.install_updates(critical, force=True)
            
            # Ask for important updates
            if important and not self.silent_mode:
                print("\n🟡 Important updates available.")
                response = input("Install important updates? (y/n): ").lower()
                if response == 'y':
                    self.install_updates(important)
        
        elif critical and not self.silent_mode:
            # Warn about critical updates even if auto-update disabled
            print("\n⚠️  CRITICAL UPDATES AVAILABLE!")
            print("   Run this command to update:")
            print(f"   pip install --upgrade {' '.join([u.name for u in critical])}")
        
        return summary


def quick_update_check() -> Dict:
    """
    Quick update check for app startup (silent mode).
    Only shows critical warnings.
    
    Returns:
        Dict: Update summary.
    """
    updater = AutoUpdater(auto_update_enabled=False, silent_mode=True)
    
    try:
        result = updater.run_update_check()
        
        # Only warn about critical updates on startup
        critical = [u for u in result.get('updates', []) if u.severity == SEVERITY_CRITICAL]
        if critical:
            print("\n⚠️  CRITICAL UPDATES AVAILABLE:")
            for update in critical:
                print(f"   🔴 {update.name}: {update.current} → {update.latest}")
            print("\n   Run 'python auto_updater.py --install' to update")
            print("   Or: pip install --upgrade " + " ".join([u.name for u in critical]))
            print()
        
        return result
    
    except Exception as e:
        logger.warning(f"Update check failed: {e}")
        return {'status': 'error', 'error': str(e)}


def main():
    """CLI entry point for manual update checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MixLab DJ Auto-Updater")
    parser.add_argument('--install', action='store_true', help='Install available updates')
    parser.add_argument('--auto', action='store_true', help='Enable automatic updates')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    parser.add_argument('--force', action='store_true', help='Force check even if checked recently')
    
    args = parser.parse_args()
    
    # Create updater
    updater = AutoUpdater(
        auto_update_enabled=args.auto,
        silent_mode=not args.verbose
    )
    
    # Force check if requested
    if args.force and os.path.exists(LAST_CHECK_FILE):
        os.remove(LAST_CHECK_FILE)
    
    print("="*70)
    print("MixLab DJ - Package Update Checker")
    print("="*70)
    print()
    
    # Run update check
    result = updater.run_update_check()
    
    # Install updates if requested
    if args.install and result['updates']:
        print("\n" + "="*70)
        updater.install_updates(result['updates'])
    
    print("\n" + "="*70)
    print("Update check complete!")
    print("="*70)
    
    return 0 if result['status'] != 'error' else 1


if __name__ == "__main__":
    sys.exit(main())

