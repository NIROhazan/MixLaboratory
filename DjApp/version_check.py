"""
Python Version and Dependency Checker for MixLab DJ

Ensures compatibility and provides helpful messages for users.
"""

import sys
import importlib.metadata
import warnings

# Python version requirements
REQUIRED_PYTHON = (3, 11, 0)      # Minimum supported
RECOMMENDED_PYTHON = (3, 12, 0)   # Best stability & package support
EXPERIMENTAL_PYTHON = (3, 13, 0)  # Experimental JIT compiler
CUTTING_EDGE_PYTHON = (3, 14, 0)  # Latest (Oct 2025), testing only

REQUIRED_PACKAGES = {
    'numpy': '1.26.0',
    'PyQt6': '6.6.0',
    'soundfile': '0.12.1',
    'sounddevice': '0.4.6',
    'scipy': '1.11.0',
    'librosa': '0.10.1',
}

OPTIONAL_PACKAGES = {
    'pyrubberband': '0.3.0',
    'soxr': '0.3.7',
    'numba': '0.58.0',
}


def parse_version(version_str):
    """Parse version string to tuple of integers."""
    try:
        return tuple(int(x) for x in version_str.split('.')[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def check_python_version():
    """Check Python version and provide recommendations."""
    current = sys.version_info[:3]
    
    if current < REQUIRED_PYTHON:
        print(f"❌ ERROR: Python {'.'.join(map(str, REQUIRED_PYTHON))}+ is required.")
        print(f"   Current: Python {'.'.join(map(str, current))}")
        print(f"\n   Please upgrade Python:")
        print(f"   - Download from: https://www.python.org/downloads/")
        print(f"   - Or use pyenv: pyenv install 3.12")
        return False
    
    # Python 3.14+ (cutting edge)
    if current >= CUTTING_EDGE_PYTHON:
        print(f"🔬 Python {'.'.join(map(str, current))} - Cutting-edge!")
        print(f"   You're using the latest Python release (October 2025).")
        print(f"   ⚠️  WARNING: Some packages may not have pre-built wheels yet.")
        print(f"   If you encounter installation issues, use Python 3.12.")
        print()
    
    # Python 3.13 (experimental JIT)
    elif current >= EXPERIMENTAL_PYTHON:
        print(f"⚡ Python {'.'.join(map(str, current))} - Experimental JIT!")
        print(f"   You're using Python with the new experimental JIT compiler.")
        print(f"   ⚠️  Note: Some packages may have limited support.")
        print(f"   For most stable experience, consider Python 3.12.")
        print()
    
    # Python 3.12 (recommended)
    elif current >= RECOMMENDED_PYTHON:
        print(f"✅ Python {'.'.join(map(str, current))} - Perfect! (Recommended)")
        print(f"   Best balance of stability, performance, and package support.")
    
    # Python 3.11 (minimum)
    else:
        print(f"✅ Python {'.'.join(map(str, current))} - Good!")
        print(f"   💡 Consider upgrading to Python 3.12 for best experience.")
        print()
    
    return True


def check_package_version(package_name, required_version):
    """Check if a package meets minimum version requirement."""
    try:
        installed_version = importlib.metadata.version(package_name)
        installed = parse_version(installed_version)
        required = parse_version(required_version)
        
        if installed >= required:
            return True, installed_version, None
        else:
            return False, installed_version, f"Version {required_version}+ required"
    
    except importlib.metadata.PackageNotFoundError:
        return False, None, "Not installed"


def check_dependencies(verbose=True):
    """
    Check all required and optional dependencies.
    
    Args:
        verbose (bool): Print detailed information.
        
    Returns:
        tuple: (all_required_ok, missing_required, missing_optional)
    """
    if verbose:
        print("\n" + "="*70)
        print("MixLab DJ - Dependency Check")
        print("="*70 + "\n")
    
    # Check Python version
    if not check_python_version():
        return False, [], []
    
    if verbose:
        print("\n" + "-"*70)
        print("Required Dependencies:")
        print("-"*70)
    
    missing_required = []
    outdated_required = []
    
    for package, min_version in REQUIRED_PACKAGES.items():
        ok, installed_version, message = check_package_version(package, min_version)
        
        if ok:
            if verbose:
                print(f"✅ {package:20s} {installed_version:12s} (>= {min_version})")
        else:
            if installed_version:
                outdated_required.append((package, min_version, installed_version))
                if verbose:
                    print(f"⚠️  {package:20s} {installed_version:12s} (needs {min_version}+)")
            else:
                missing_required.append(package)
                if verbose:
                    print(f"❌ {package:20s} {'NOT INSTALLED':12s} (needs {min_version}+)")
    
    if verbose:
        print("\n" + "-"*70)
        print("Optional Dependencies (for enhanced features):")
        print("-"*70)
    
    missing_optional = []
    
    for package, min_version in OPTIONAL_PACKAGES.items():
        ok, installed_version, message = check_package_version(package, min_version)
        
        if ok:
            if verbose:
                print(f"✅ {package:20s} {installed_version:12s} (>= {min_version})")
        else:
            missing_optional.append(package)
            if installed_version:
                if verbose:
                    print(f"⚠️  {package:20s} {installed_version:12s} (needs {min_version}+)")
            else:
                if verbose:
                    print(f"ℹ️  {package:20s} {'NOT INSTALLED':12s} (optional)")
    
    # Summary
    if verbose:
        print("\n" + "="*70)
        print("Summary:")
        print("="*70)
    
    all_required_ok = len(missing_required) == 0 and len(outdated_required) == 0
    
    if all_required_ok:
        if verbose:
            print("✅ All required dependencies are installed and up to date!")
    else:
        if verbose:
            print("❌ Some required dependencies need attention:")
            if missing_required:
                print(f"   Missing: {', '.join(missing_required)}")
            if outdated_required:
                for pkg, needed, current in outdated_required:
                    print(f"   Outdated: {pkg} (need {needed}+, have {current})")
    
    if missing_optional:
        if verbose:
            print(f"\nℹ️  Optional packages not installed: {', '.join(missing_optional)}")
            print("   Install for enhanced features:")
            print("   pip install pyrubberband soxr numba")
    
    # Installation instructions
    if not all_required_ok:
        if verbose:
            print("\n" + "="*70)
            print("Installation Instructions:")
            print("="*70)
            print("\n1. Install/upgrade all dependencies:")
            print("   pip install -r requirements.txt --upgrade")
            print("\n2. Or install individually:")
            if missing_required or outdated_required:
                packages = missing_required + [p[0] for p in outdated_required]
                print(f"   pip install --upgrade {' '.join(packages)}")
    
    if verbose:
        print("\n" + "="*70 + "\n")
    
    return all_required_ok, missing_required + [p[0] for p in outdated_required], missing_optional


def check_optional_features():
    """Check which optional features are available."""
    features = {
        'professional_tempo': False,
        'fast_resampling': False,
        'jit_compilation': False,
    }
    
    messages = []
    
    # Check pyrubberband
    try:
        import pyrubberband
        features['professional_tempo'] = True
        messages.append("✅ Professional tempo shifting (Rubber Band) available")
    except ImportError:
        messages.append("⚠️  Professional tempo shifting unavailable (install pyrubberband)")
    
    # Check soxr
    try:
        import soxr
        features['fast_resampling'] = True
        messages.append("✅ Fast resampling (soxr) available")
    except ImportError:
        messages.append("ℹ️  Standard resampling will be used (install soxr for 2x speed)")
    
    # Check numba
    try:
        import numba
        features['jit_compilation'] = True
        messages.append("✅ JIT compilation (numba) available - librosa will be faster")
    except ImportError:
        messages.append("ℹ️  JIT compilation unavailable (install numba for faster analysis)")
    
    return features, messages


def main():
    """Main entry point for standalone execution."""
    all_ok, missing_required, missing_optional = check_dependencies(verbose=True)
    
    if all_ok:
        print("Checking optional features...")
        print("-"*70)
        features, messages = check_optional_features()
        for msg in messages:
            print(msg)
        print("-"*70 + "\n")
        
        print("🎉 System ready to run MixLab DJ!")
        
        if missing_optional:
            print("\n💡 Tip: Install optional packages for enhanced performance:")
            print("   pip install pyrubberband soxr numba")
        
        return 0
    else:
        print("\n⚠️  Please install missing dependencies before running MixLab DJ.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

