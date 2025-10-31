# 🔄 MixLab DJ - Auto-Update System

## Overview

MixLab DJ now features an **AI-powered auto-update system** that intelligently manages package updates to keep your DJ software running smoothly and securely.

---

## 🤖 AI-Powered Update Intelligence

### How It Works

The system uses **intelligent logic** to categorize updates:

#### 🔴 **Critical Updates** (Auto-alert)
- **Security vulnerabilities** fixed
- **Major bugs** that could crash the app
- **Data corruption** issues
- **Critical packages** (PyQt6, numpy, soundfile, librosa)

**Action:** System warns you immediately on startup

#### 🟡 **Important Updates** (Recommended)
- **Performance improvements** (10%+ faster)
- **New features** you might want
- **Multiple minor versions** behind (>2 versions)
- **Compatibility** improvements

**Action:** Notify when convenient, suggest updating

#### 🟢 **Minor Updates** (Optional)
- **Small bug fixes**
- **Documentation updates**
- **Cosmetic changes**
- **Single version** behind

**Action:** Silent check, mention in update summary

---

## ⚙️ Automatic Behavior

### On App Startup

**Every time you run `python djapp.py`:**

1. ✅ Checks Python version (ensures 3.11+)
2. ✅ Verifies required packages installed
3. 🔍 **Quick update check** (once per 24 hours)
4. ⚠️ **Warns about critical updates** only
5. 🚀 Continues loading app (doesn't block)

### Silent Operation

- **No interruptions** for minor updates
- **Only warns** if critical security issues
- **Checks daily** automatically
- **Caches results** for 24 hours

---

## 🛠️ Manual Update Commands

### Check for Updates

```bash
# Quick check (what auto-check does)
python auto_updater.py

# Verbose check (see all details)
python auto_updater.py --verbose

# Force check (ignore 24-hour cache)
python auto_updater.py --force --verbose
```

**Example Output:**
```
🔍 Checking for updates...
  🔴 PyQt6: 6.6.0 → 6.7.0 (critical)
  🟡 librosa: 0.10.1 → 0.10.2 (important)
  🟢 numpy: 1.26.0 → 1.26.3 (minor)

📊 Update Summary:
   Total updates available: 3
   🔴 Critical: 1
   🟡 Important: 1
   🟢 Minor: 1
```

### Install Updates

```bash
# Install all available updates
python auto_updater.py --install --verbose

# Or use pip directly (for specific packages)
pip install --upgrade PyQt6 librosa numpy
```

### Auto-Update Mode

```bash
# Enable automatic installation of updates
python auto_updater.py --auto --install

# This will:
# - Auto-install critical updates (security)
# - Ask permission for important updates
# - List minor updates
```

---

## 📊 Update Categories Explained

### How AI Determines Severity

The system analyzes:

1. **Version Jump Size**
   - Major version (3.0 → 4.0) = More severe
   - Minor version (3.1 → 3.5) = Less severe
   - Patch version (3.1.1 → 3.1.2) = Least severe

2. **Package Importance**
   - **Critical packages** (PyQt6, numpy, soundfile, librosa) = Higher priority
   - **Optional packages** (pyrubberband, soxr) = Lower priority

3. **Version Gap**
   - Multiple versions behind (>5) = More urgent
   - One version behind = Less urgent

4. **Time Since Release**
   - Older stable releases = More stable
   - Brand new releases = May wait for bugs to be found

### Examples

```python
# CRITICAL - Security fix in critical package
PyQt6: 6.6.0 → 6.7.0 (major version bump)
Action: Warn immediately

# IMPORTANT - Performance improvement
librosa: 0.10.0 → 0.10.5 (multiple minor versions)
Action: Recommend updating soon

# MINOR - Small fix
numpy: 1.26.0 → 1.26.1 (patch version)
Action: Silent check, update when convenient
```

---

## 🔒 Security Features

### Automatic Security Monitoring

- **Checks PyPI** for latest versions
- **Compares** with installed versions
- **Alerts** for critical security updates
- **Recommends** immediate action

### What's Monitored

```python
CRITICAL_PACKAGES = [
    'PyQt6',      # GUI framework (security important)
    'numpy',      # Core computation (memory safety)
    'soundfile',  # Audio I/O (file parsing vulnerabilities)
    'librosa'     # Audio analysis (potential exploits)
]
```

### Privacy & Network Activity

**What We Query:**
- ✅ **Public PyPI** (https://pypi.org) - to check package versions
- ✅ **Anonymous requests** - only package name sent (e.g., "numpy")
- ✅ **Standard HTTP** - no authentication, no special headers

**What's NOT Collected/Sent:**
- ❌ **No user tracking** or identification
- ❌ **No usage analytics** or telemetry
- ❌ **No personal data** collection
- ❌ **No data to private servers** - only public PyPI
- ❌ **Local cache only** - results stored on your computer

**See [PRIVACY.md](PRIVACY.md) for complete privacy policy.**

---

## 📅 Update Schedule

### Automatic Checks

- **Interval:** Once per 24 hours
- **Trigger:** App startup
- **Cache Location:** `cache/last_update_check.json`
- **Network Required:** Yes (brief PyPI query)

### Manual Checks

Run anytime with:
```bash
python auto_updater.py --force --verbose
```

---

## 🎯 Usage Scenarios

### Scenario 1: Daily Use (Automatic)

**What Happens:**
1. Start app: `python djapp.py`
2. System checks (if 24h passed)
3. Warns if critical updates
4. App continues loading

**User Action:** None required (unless critical)

### Scenario 2: Pre-Important Gig

**Best Practice:**
```bash
# 1. Check for updates
python auto_updater.py --verbose

# 2. Install critical/important only
python auto_updater.py --install

# 3. Test app
python djapp.py

# 4. Do a test mix to verify
```

### Scenario 3: Monthly Maintenance

**Recommended:**
```bash
# Once a month, update everything
pip install -r requirements.txt --upgrade

# Then verify
python version_check.py
```

---

## ⚠️ Important Notes

### When Updates Happen

- ✅ **Automatic check** on startup (silent)
- ❌ **No automatic installation** without permission
- ⚠️ **Only critical updates** show warnings

### What Gets Updated

- ✅ Python packages (numpy, PyQt6, etc.)
- ❌ MixLab DJ app itself (manual git pull)
- ❌ Python version (manual upgrade)
- ❌ System libraries (manual OS updates)

### Network Requirements

- **Online:** Required for update checks
- **Offline:** App works fine, skips checks
- **Slow Connection:** Times out after 5 seconds per package

---

## 🚫 Disable Auto-Update Checks

If you prefer manual updates:

### Option 1: Delete Cache Daily
```bash
# Remove cache file to prevent checks
rm cache/last_update_check.json
```

### Option 2: Modify djapp.py
Remove these lines from `djapp.py`:
```python
try:
    from auto_updater import quick_update_check
    quick_update_check()
except ImportError:
    pass
```

### Option 3: Set Long Interval
Edit `auto_updater.py`:
```python
UPDATE_CHECK_INTERVAL = 365  # Check once per year
```

---

## 🔧 Configuration

### Modify Update Behavior

Edit `auto_updater.py`:

```python
# Check interval (days)
UPDATE_CHECK_INTERVAL = 1  # Daily (default)
# UPDATE_CHECK_INTERVAL = 7  # Weekly
# UPDATE_CHECK_INTERVAL = 30  # Monthly

# Critical packages (always high priority)
CRITICAL_PACKAGES = ['PyQt6', 'numpy', 'soundfile', 'librosa']
# Add more: CRITICAL_PACKAGES.append('your_package')
```

---

## 🐛 Troubleshooting

### "Could not fetch version" Error

**Cause:** Network timeout or PyPI unavailable

**Solution:**
- Check internet connection
- Try again later
- Use: `python auto_updater.py --force`

### "Permission denied" During Install

**Cause:** Need admin/sudo rights

**Solution:**
```bash
# Linux/macOS
sudo python auto_updater.py --install

# Windows
# Run terminal as Administrator
python auto_updater.py --install

# OR use user install
pip install --user --upgrade package_name
```

### Updates Break Something

**Solution:**
```bash
# Rollback to specific version
pip install package_name==old_version

# Example
pip install PyQt6==6.6.0

# Or reinstall all at known-good versions
pip install -r requirements.txt --force-reinstall
```

### App Won't Start After Update

**Recovery:**
```bash
# 1. Check what changed
pip list

# 2. Reinstall from requirements
pip install -r requirements.txt --force-reinstall

# 3. Verify installation
python version_check.py

# 4. If still broken, clean install
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📈 Statistics & Monitoring

### View Update History

```bash
# Check cache file
cat cache/last_update_check.json
```

**Example:**
```json
{
  "last_check": "2025-10-31T15:30:00",
  "version": [3, 12, 0]
}
```

### Monitor Package Versions

```bash
# Current versions
pip list

# Outdated packages
pip list --outdated

# Detailed info
pip show package_name
```

---

## 🎯 Best Practices

### ✅ Do:
- Let auto-check run (it's fast and non-intrusive)
- Update critical packages immediately
- Test after important updates
- Read changelogs for major updates

### ❌ Don't:
- Ignore critical security updates
- Update right before a performance
- Auto-update without testing
- Mix Python versions

### 💡 Tips:
- Keep Python 3.12 (most stable)
- Update monthly for maintenance
- Read warnings carefully
- Backup before major updates

---

## 🏆 Summary

### What You Get:

✅ **Automatic** update checks on startup
✅ **AI-powered** severity analysis
✅ **Silent** operation (no interruptions)
✅ **Security** alerts for critical issues
✅ **Manual** control when you want it
✅ **Configurable** behavior
✅ **Safe** - never auto-installs without permission

### The Result:

🎵 Always up-to-date and secure
🚀 Maximum performance
🔒 Protected from vulnerabilities
⚡ Zero effort required

---

## 📚 Related Documentation

- [version_check.py](version_check.py) - Dependency verification
- [PYTHON_VERSIONS.md](PYTHON_VERSIONS.md) - Python version guide
- [INSTALLATION.md](INSTALLATION.md) - Setup instructions
- [NEW_FEATURES.md](NEW_FEATURES.md) - Feature documentation

---

**Your MixLab DJ now keeps itself updated automatically! 🎵🔄✨**

