# 🔒 MixLab DJ - Privacy Policy

## Overview

MixLab DJ is a **completely private, offline-first** DJ application. We take your privacy seriously and have designed the software to minimize any external communication.

---

## 📊 What Data is Collected

### **NONE - Zero Personal Data Collection**

MixLab DJ does **NOT** collect, store, or transmit any personal information including:

- ❌ Your name, email, or contact information
- ❌ Your location or IP address
- ❌ Your music library or track names
- ❌ Usage patterns or behavior analytics
- ❌ System information beyond what's needed locally
- ❌ Crash reports or error logs (unless you manually share them)
- ❌ Any identifiable information whatsoever

---

## 🌐 Network Activity

### What Happens Online

MixLab DJ makes **minimal, anonymous** network requests:

#### 1. **PyPI Version Checks** (Optional, Can Be Disabled)

**What:** Queries public Python Package Index (PyPI) to check for package updates
**When:** Once per 24 hours on app startup (if auto-updater is enabled)
**Data Sent:** Only the package name (e.g., "numpy", "PyQt6")
**Who Sees It:** PyPI servers (run by Python Software Foundation)
**Can Be Disabled:** Yes - see [UPDATE_SYSTEM.md](UPDATE_SYSTEM.md)

**Example Request:**
```
GET https://pypi.org/pypi/numpy/json
```

**What This Reveals:**
- That someone is checking if numpy has updates
- Generic HTTP metadata (standard for any web request)

**What This Does NOT Reveal:**
- Who you are
- Where you are
- What you're doing with MixLab DJ
- Your music library
- Any personal information

#### 2. **No Other Network Activity**

- ❌ No telemetry
- ❌ No crash reporting
- ❌ No usage statistics
- ❌ No update servers (besides public PyPI)
- ❌ No authentication servers
- ❌ No cloud services
- ❌ No third-party integrations

---

## 💾 Local Data Storage

### What's Stored on Your Computer

All MixLab DJ data stays **on your computer** in the `cache/` folder:

```
cache/
├── bpm/              # BPM analysis results (for faster loading)
├── waveforms/        # Waveform images (for faster rendering)
├── fft/              # Audio analysis data
├── keys/             # Musical key detection results
├── cache_metadata.json          # File hashes and timestamps
└── last_update_check.json       # Last time updates were checked
```

**What This Contains:**
- ✅ Audio analysis results (BPM, beats, keys)
- ✅ Waveform visualization data
- ✅ File checksums (to detect if files changed)
- ✅ Last update check timestamp

**What This Does NOT Contain:**
- ❌ Personal information
- ❌ Track names or metadata (only file paths on YOUR computer)
- ❌ Anything identifiable
- ❌ Anything uploaded anywhere

**Who Can Access It:**
- ✅ You (it's on your computer)
- ❌ Nobody else

---

## 🔐 Security & Privacy Features

### Built-in Privacy Protections

#### 1. **Offline-First Design**
- App works **completely offline** except for optional update checks
- All core features work without internet
- Music analysis happens **locally** on your computer

#### 2. **No Accounts or Authentication**
- ❌ No login required
- ❌ No user accounts
- ❌ No passwords to manage
- ❌ No cloud sync

#### 3. **Local Processing Only**
- All audio analysis done **on your computer**
- BPM detection: Local (native C++ library)
- Key detection: Local (librosa library)
- Waveform rendering: Local (GPU/CPU)
- Everything stays on your machine

#### 4. **No Third-Party Services**
- ❌ No Google Analytics
- ❌ No Facebook Pixel
- ❌ No tracking SDKs
- ❌ No ad networks
- ❌ No external dependencies (except PyPI for optional updates)

---

## 🛡️ How We Protect Your Privacy

### Design Principles

1. **Data Minimization**
   - Only store what's necessary for functionality
   - Cache can be deleted anytime without data loss

2. **Local-First**
   - Everything happens on your computer
   - No cloud storage or remote processing

3. **No Tracking**
   - No unique identifiers
   - No session tracking
   - No user profiling

4. **Transparent**
   - Open source (you can inspect the code)
   - Clear documentation of all network activity
   - No hidden features

---

## 🌍 PyPI Queries Explained

### What is PyPI?

PyPI (Python Package Index) is the **official, public** repository for Python packages. It's run by the Python Software Foundation (a non-profit).

- **Website:** https://pypi.org
- **Purpose:** Distribute Python packages
- **Privacy Policy:** https://www.python.org/privacy/

### Why We Query PyPI

To check if your installed packages have updates (security patches, bug fixes, new features).

### What PyPI Knows

**From MixLab DJ Update Checks:**
- That someone requested version info for a package (e.g., "numpy")
- Standard HTTP metadata (IP address, user agent - standard for all web requests)

**PyPI Does NOT Know:**
- Who you are specifically
- What you're using MixLab DJ for
- Your music library
- Anything about your usage

**PyPI Privacy Policy:**
PyPI is operated by the Python Software Foundation and follows their privacy policy: https://www.python.org/privacy/

### Disable PyPI Checks

If you prefer **zero network activity**:

**Option 1: Remove auto-updater call**
Edit `djapp.py`, remove:
```python
try:
    from auto_updater import quick_update_check
    quick_update_check()
except:
    pass
```

**Option 2: Work offline**
- Disconnect from internet
- App continues working normally
- Update checks are skipped automatically

**Option 3: Firewall rules**
- Block `pypi.org` in your firewall
- App works fine, just skips update checks

---

## 📝 What About Music Files?

### Your Music Library

**What MixLab DJ Does:**
- ✅ Reads audio files from **your computer**
- ✅ Analyzes them **locally** (BPM, key, waveforms)
- ✅ Caches results **on your computer**

**What MixLab DJ Does NOT Do:**
- ❌ Upload files anywhere
- ❌ Share file names or metadata
- ❌ Connect to music services (Spotify, Apple Music, etc.)
- ❌ Send any information about your library

**Your music stays on your computer, period.**

---

## 🔍 How to Verify

### Audit Network Activity

Want to see for yourself? Monitor network traffic:

**Windows (PowerShell):**
```powershell
# Monitor all network connections
Get-NetTCPConnection | Where-Object {$_.OwningProcess -eq (Get-Process python).Id}
```

**Linux/macOS:**
```bash
# Monitor network activity
sudo lsof -i -P | grep python

# Or use tcpdump
sudo tcpdump -i any host pypi.org
```

**Expected Results:**
- Connections to `pypi.org` (only if update check runs)
- No other network activity
- Update check happens once per 24 hours max

---

## 📜 Data Retention

### How Long We Keep Data

**Forever (on your computer):**
- Cache files stay until you delete them
- Helps app load faster next time
- Can be deleted anytime: `rm -rf cache/`

**We Don't Keep Data:**
- Because we don't receive any data
- Everything stays on your computer

---

## 🌐 Third-Party Services

### Services Used

1. **PyPI (pypi.org)** - Public package index
   - Purpose: Check for package updates
   - Data Sent: Package name only
   - Privacy Policy: https://www.python.org/privacy/
   - Optional: Can be disabled

2. **No Other Services**
   - That's it. Just PyPI for optional update checks.

---

## 👤 Your Rights

### What You Can Do

✅ **Use Completely Offline**
- Disable internet
- App works perfectly

✅ **Delete All Data**
```bash
# Delete cache
rm -rf cache/

# Reinstall from scratch
rm -rf venv
```

✅ **Inspect Code**
- MixLab DJ is transparent
- All code is readable
- No obfuscation

✅ **Disable Features**
- Turn off auto-updater
- Work completely offline
- Full control

---

## 🆘 Questions or Concerns?

### Contact

- **Issues:** File an issue on GitHub (if available)
- **Questions:** Read documentation
- **Privacy Concerns:** Review code yourself

### What We Will Never Ask For

- ❌ Personal information
- ❌ Credit card or payment
- ❌ Email or phone number
- ❌ Access to your music library
- ❌ System passwords
- ❌ Any identifiable data

---

## 📊 Comparison with Other DJ Software

| Feature | MixLab DJ | Commercial DJ Software |
|---------|-----------|----------------------|
| **Requires Account** | ❌ No | ✅ Usually Yes |
| **Cloud Sync** | ❌ No | ✅ Often Yes |
| **Telemetry** | ❌ None | ✅ Usually Yes |
| **Crash Reporting** | ❌ None | ✅ Usually Yes |
| **License Server** | ❌ No | ✅ Often Yes |
| **Update Servers** | ⚠️ PyPI only | ✅ Proprietary |
| **Works Offline** | ✅ Yes | ⚠️ Sometimes |

---

## 🎯 Summary

### What MixLab DJ Does

✅ Works **completely offline** (except optional update checks)
✅ Processes everything **locally** on your computer
✅ Stores cache **only on your computer**
✅ Makes **minimal, anonymous** queries to public PyPI (optional)

### What MixLab DJ Does NOT Do

❌ Collect **any personal data**
❌ Track **your usage**
❌ Upload **your music**
❌ Share **any information** about you
❌ Require **accounts or authentication**
❌ Use **third-party analytics**
❌ Send **crash reports** (unless you manually share them)

### The Bottom Line

**MixLab DJ respects your privacy by design. Your data is yours, and it stays on your computer.**

---

## 📅 Policy Updates

**Last Updated:** October 31, 2025

**Changes:** Initial privacy policy

**Future Updates:** This policy may be updated to reflect new features. Any changes will be clearly documented.

---

**Your privacy is important. MixLab DJ is designed to be private by default. 🔒✨**

