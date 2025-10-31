# 🚀 MixLab DJ - Installation Guide

## System Requirements

### Python Version
- **Required**: Python 3.11 or higher
- **Recommended**: Python 3.12 (best stability & package support)
- **Experimental**: Python 3.13 (JIT compiler, faster but newer)
- **Cutting-edge**: Python 3.14 (October 2025 release, testing only)
- **Not supported**: Python 3.10 or lower

**💡 Recommendation**: Use Python 3.12 for the best experience. See [PYTHON_VERSIONS.md](PYTHON_VERSIONS.md) for detailed comparison.

### Operating Systems
- ✅ **Windows** 10/11 (64-bit)
- ✅ **Linux** (Ubuntu 20.04+, Debian 11+, or equivalent)
- ✅ **macOS** 11.0+ (Big Sur or newer)

### Hardware Requirements
- **CPU**: Dual-core processor (Quad-core+ recommended)
- **RAM**: 4GB minimum (8GB+ recommended)
- **Storage**: 500MB for application + space for music library
- **Audio**: Sound card with stereo output

---

## Installation Steps

### 1. Check Python Version

```bash
python --version
```

Should show Python 3.11.x or 3.12.x

**If you have an older version:**

#### Windows
Download latest Python from [python.org](https://www.python.org/downloads/)
- Check "Add Python to PATH" during installation

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

#### macOS
```bash
brew install python@3.12
```

Or download from [python.org](https://www.python.org/downloads/)

---

### 2. Create Virtual Environment (Recommended)

```bash
# Navigate to project directory
cd path/to/MyMixLab

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate
```

You should see `(venv)` in your command prompt.

---

### 3. Install Dependencies

#### Option A: Install Everything (Recommended)

```bash
cd DjApp
pip install -r requirements.txt --upgrade
```

#### Option B: Install Core Only (Faster)

```bash
pip install numpy>=1.26.0 PyQt6>=6.6.0 soundfile>=0.12.1 sounddevice>=0.4.6 scipy>=1.11.0 librosa>=0.10.1
```

---

### 4. Install Optional Professional Features

For best audio quality, install Rubber Band Library:

#### Windows
1. Download Rubber Band from [https://breakfastquay.com/rubberband/](https://breakfastquay.com/rubberband/)
2. Extract to `C:\Program Files\RubberBand`
3. Add to PATH:
   - Open System Properties → Environment Variables
   - Add `C:\Program Files\RubberBand\bin` to PATH
4. Install Python wrapper:
   ```bash
   pip install pyrubberband
   ```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install rubberband-cli librubberband-dev
pip install pyrubberband soxr numba
```

#### macOS
```bash
brew install rubberband
pip install pyrubberband soxr numba
```

---

### 5. Verify Installation

Run the dependency checker:

```bash
cd DjApp
python version_check.py
```

You should see:
```
✅ Python 3.12.x - Excellent!
✅ All required dependencies are installed and up to date!
✅ Professional tempo shifting (Rubber Band) available
✅ Fast resampling (soxr) available
✅ JIT compilation (numba) available
```

---

### 6. Run MixLab DJ

```bash
python djapp.py
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'PyQt6'"

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Python version 3.11+ is required"

**Solution**: Upgrade Python
- Download from [python.org](https://www.python.org/downloads/)
- Install Python 3.12

### Issue: Audio files won't load

**Solution**: Install audio codecs
```bash
# For MP3 support on Linux
sudo apt-get install libsndfile1

# For additional formats
pip install audioread
```

### Issue: "pyrubberband not available"

**Solution**: This is optional. App will work without it, but with lower audio quality for tempo changes.

To install:
- See "Install Optional Professional Features" above

### Issue: High CPU usage

**Solutions**:
1. Install `numba` for faster processing:
   ```bash
   pip install numba llvmlite
   ```

2. Upgrade to Python 3.12 for better performance

3. Close other applications while DJing

### Issue: "ImportError: DLL load failed" (Windows)

**Solution**: Install Visual C++ Redistributables
- Download from [Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
- Install both x64 and x86 versions

### Issue: Waveform display is slow

**Solutions**:
1. Install performance packages:
   ```bash
   pip install numba soxr
   ```

2. Reduce window size (Settings → Resolution)

3. Close spectrogram view if not needed

---

## Performance Optimization

### For Best Performance

1. **Use Python 3.12**
   - 10-60% faster than Python 3.11
   - Better memory management

2. **Install Performance Packages**
   ```bash
   pip install numba soxr
   ```

3. **Enable Hardware Acceleration**
   - Use dedicated audio device (not USB headphones)
   - Lower buffer size in audio settings

4. **System Settings**
   - Close background applications
   - Disable antivirus real-time scanning for music folder
   - Use SSD for music library (not HDD)

### Benchmark Your System

```bash
cd DjApp
python -c "import timeit; print(f'NumPy performance: {timeit.timeit(\"import numpy as np; a = np.random.rand(1000, 1000); b = a @ a\", number=10):.2f}s')"
```

Good systems: <1.0s
Excellent systems: <0.5s

---

## Updating

### Update MixLab DJ

```bash
git pull origin main  # If using git
```

### Update Dependencies

```bash
cd DjApp
pip install -r requirements.txt --upgrade
```

### Check What's New

```bash
python version_check.py
```

---

## Uninstallation

### Remove Virtual Environment

```bash
# Deactivate first
deactivate

# Remove directory
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows
```

### Remove System Packages (Optional)

#### Linux
```bash
sudo apt-get remove rubberband-cli librubberband-dev
```

#### macOS
```bash
brew uninstall rubberband
```

---

## Development Setup

For developers who want to modify MixLab DJ:

### Install Development Tools

```bash
pip install -r requirements.txt
pip install pytest black mypy pylint
```

### Run Tests

```bash
cd DjApp
pytest tests/
```

### Code Formatting

```bash
black *.py
```

### Type Checking

```bash
mypy djapp.py --ignore-missing-imports
```

---

## Getting Help

### Check Versions
```bash
python version_check.py
```

### Check Logs
Logs are saved in `DjApp/cache/logs/`

### Report Issues
Include:
1. Python version (`python --version`)
2. OS and version
3. Output of `python version_check.py`
4. Error message and traceback
5. Steps to reproduce

---

## Platform-Specific Notes

### Windows

- Use **Windows Terminal** or **PowerShell** (not Command Prompt)
- Install **Visual C++ Redistributables** if you get DLL errors
- **Windows Defender** may slow down file scanning - add music folder to exclusions

### Linux

- Install `python3-dev` for building native extensions
- Use `pulseaudio` or `pipewire` for audio (JACK is also supported)
- Grant audio group permissions: `sudo usermod -aG audio $USER`

### macOS

- Grant microphone/audio permissions in System Preferences → Security
- Use **Homebrew** for installing system dependencies
- If using M1/M2, ensure you have ARM64 Python (not Rosetta)

---

## FAQ

**Q: Can I use Python 3.10?**
A: No, Python 3.11+ is required for latest numpy and other dependencies.

**Q: Do I need Rubber Band Library?**
A: No, it's optional. The app uses librosa (included) if Rubber Band isn't available.

**Q: How much disk space do I need?**
A: 500MB for app + ~1GB for cache with large library (1000+ tracks).

**Q: Can I run this on Raspberry Pi?**
A: Yes, but performance will be limited. Use Pi 4 with 8GB RAM minimum.

**Q: Does this work with MIDI controllers?**
A: Not yet, but planned for future release.

**Q: Can I record my mixes?**
A: Yes! Built-in recording feature available in the app.

---

## Next Steps

1. ✅ Installation complete
2. 📖 Read [NEW_FEATURES.md](NEW_FEATURES.md) to learn about features
3. 🎵 Add music to a folder
4. 🚀 Run `python djapp.py`
5. 🎧 Start mixing!

Enjoy your professional DJ experience! 🎵🎧✨

