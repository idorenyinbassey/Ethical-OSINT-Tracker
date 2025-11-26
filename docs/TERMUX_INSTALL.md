# Termux Installation Guide

Complete guide for installing and running Ethical OSINT Tracker on Android devices using Termux terminal emulator.

## Prerequisites

### 1. Install Termux
- **Recommended**: Install from [F-Droid](https://f-droid.org/en/packages/com.termux/) (official source)
- **NOT recommended**: Google Play version is outdated and unmaintained
- Minimum Android version: 7.0 (API 24)
- Recommended: Android 10+ for better compatibility

### 2. Termux Add-ons (Optional but Recommended)
- **Termux:API**: Access device sensors, contacts, SMS (for enhanced features)
- **Termux:Widget**: Create home screen shortcuts to launch the app
- **Termux:Boot**: Auto-start the app on device boot

### 3. Device Requirements
- **RAM**: Minimum 2GB, recommended 4GB+
- **Storage**: Minimum 500MB free space
- **CPU**: ARM64 (aarch64) or ARMv7 architecture

## Installation Methods

### Method 1: Automated Installation (Recommended)

1. **Open Termux** and update packages:
   ```bash
   pkg update && pkg upgrade
   ```

2. **Grant storage permissions** (required for file uploads):
   ```bash
   termux-setup-storage
   ```
   Press "Allow" when prompted.

3. **Clone or transfer the repository**:
   
   If you have Git:
   ```bash
   pkg install git
   cd ~
   git clone https://github.com/yourusername/Ethical-OSINT-Tracker.git
   cd Ethical-OSINT-Tracker
   ```
   
   Or transfer the files via:
   - ADB: `adb push /path/to/project /sdcard/`
   - File manager to `/sdcard/Download/`
   - Then: `cp -r /sdcard/Download/Ethical-OSINT-Tracker ~/`

4. **Run the installation script**:
   ```bash
   bash install_termux.sh
   ```
   
   The script will:
   - ✓ Install Python 3.11+
   - ✓ Install uv package manager (fast, Rust-based)
   - ✓ Install system dependencies (Pillow, httpx requirements)
   - ✓ Create isolated virtual environment
   - ✓ Install Python packages via uv
   - ✓ Setup SQLite database
   - ✓ Run migrations
   - ✓ Create admin user
   - ✓ Generate launch script

5. **Start the application**:
   ```bash
   ./run_termux.sh
   ```

6. **Access the app**:
   - Open Chrome/Firefox on your Android device
   - Navigate to: `http://localhost:3000`
   - Login: `admin` / `changeme`
   - **⚠️ Change password immediately after first login!**

### Method 2: Manual Installation

If the automated script fails or you prefer manual control:

#### Step 1: Install System Packages
```bash
pkg update && pkg upgrade
pkg install -y python python-pip rust binutils clang libffi libjpeg-turbo zlib freetype git which
```

#### Step 2: Install uv Package Manager
```bash
pip install --upgrade pip
pip install uv
```

Verify:
```bash
uv --version  # Should show uv 0.x.x
```

#### Step 3: Setup Project
```bash
cd ~/Ethical-OSINT-Tracker

# Create virtual environment
uv venv .venv --python python

# Activate environment
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

#### Step 4: Database Setup
```bash
# Create data directory
mkdir -p data

# Run migrations
alembic upgrade head

# Create admin user
python reset_admin.py
```

#### Step 5: Configure Ports
Edit `rxconfig.py` and add at the end:
```python
# Termux-specific configuration
import os
config.backend_port = int(os.environ.get("PORT", 8000))
config.frontend_port = int(os.environ.get("FRONTEND_PORT", 3000))
```

#### Step 6: Launch
```bash
export PORT=8000
export FRONTEND_PORT=3000
export REFLEX_DEV_MODE=false

reflex run --backend-port 8000 --frontend-port 3000
```

## Configuration

### Port Configuration

Default ports for Termux (different from desktop to avoid conflicts):
- **Backend**: 8000 (instead of 8001)
- **Frontend**: 3000 (instead of 3001)

To change ports, edit `run_termux.sh`:
```bash
export PORT=8000        # Backend API
export FRONTEND_PORT=3000  # Web interface
```

### Performance Optimization

1. **Disable Hot-Reload** (already set in `run_termux.sh`):
   ```bash
   export REFLEX_DEV_MODE=false
   ```

2. **Reduce Worker Count** (if experiencing crashes):
   Edit `rxconfig.py`:
   ```python
   config.gunicorn_workers = 1  # Reduce from default 2
   ```

3. **Enable Battery Optimization Exceptions**:
   - Settings → Apps → Termux → Battery → "Don't optimize"
   - Prevents Android from killing the process

### Storage Access

File upload feature requires storage permissions:
```bash
termux-setup-storage
```

This creates symbolic links:
- `~/storage/downloads` → `/sdcard/Download`
- `~/storage/dcim` → `/sdcard/DCIM`
- `~/storage/pictures` → `/sdcard/Pictures`

Upload images from:
```
~/storage/pictures/
~/storage/dcim/Camera/
```

## Troubleshooting

### Issue: Pillow Installation Fails

**Symptoms**:
```
ERROR: Could not build wheels for Pillow
```

**Solution 1** - Install system dependencies:
```bash
pkg install libjpeg-turbo zlib freetype
pip install --upgrade pip
uv pip install --force-reinstall Pillow
```

**Solution 2** - Use precompiled wheel:
```bash
pkg install pillow
```

### Issue: httpx Timeout Errors

**Symptoms**:
```
httpx.TimeoutException: Request timed out
```

**Solution**:
- Check internet connection (WiFi preferred over mobile data)
- Increase timeout in client files:
  ```python
  async with httpx.AsyncClient(timeout=30) as client:  # Increase from 10
  ```
- Test with: `ping 8.8.8.8`

### Issue: Port Already in Use

**Symptoms**:
```
ERROR: Address already in use
```

**Solution**:
```bash
# Kill processes on ports 8000/3000
fuser -k 8000/tcp
fuser -k 3000/tcp

# Or use the helper in run_termux.sh
./run_termux.sh
```

### Issue: Database Migration Errors

**Symptoms**:
```
alembic.util.exc.CommandError: Can't locate revision
```

**Solution**:
```bash
# Reset database (⚠️ deletes all data)
rm -rf data/app.db
alembic upgrade head
python reset_admin.py
```

### Issue: App Crashes on Low Memory

**Symptoms**:
- Termux process killed by Android
- "Process terminated" message

**Solution 1** - Free up RAM:
```bash
# Close other apps
# Restart Termux
# Reduce worker count (see Performance Optimization)
```

**Solution 2** - Use swap file (requires root):
```bash
# Not recommended for non-rooted devices
# Can damage flash storage
```

**Solution 3** - Use lightweight browser:
- Try "Bromite" or "Kiwi Browser" instead of Chrome

### Issue: Permission Denied Errors

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied
```

**Solution**:
```bash
# Re-run storage setup
termux-setup-storage

# Check file permissions
ls -la ~/Ethical-OSINT-Tracker

# Fix permissions
chmod -R 755 ~/Ethical-OSINT-Tracker
```

### Issue: SSL Certificate Errors

**Symptoms**:
```
ssl.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**Solution**:
```bash
# Update CA certificates
pkg install ca-certificates
```

## Advanced Configuration

### Auto-Start on Boot

1. Install Termux:Boot add-on from F-Droid

2. Create boot script:
   ```bash
   mkdir -p ~/.termux/boot
   nano ~/.termux/boot/start-osint.sh
   ```

3. Add content:
   ```bash
   #!/data/data/com.termux/files/usr/bin/bash
   cd ~/Ethical-OSINT-Tracker
   source .venv/bin/activate
   nohup ./run_termux.sh > /dev/null 2>&1 &
   ```

4. Make executable:
   ```bash
   chmod +x ~/.termux/boot/start-osint.sh
   ```

5. Reboot device to test

### Access from Other Devices on Same Network

1. **Find your Android device's IP**:
   ```bash
   ifconfig wlan0 | grep "inet addr"
   # Or
   ip -4 addr show wlan0 | grep inet
   ```

2. **Note the IP address** (e.g., `192.168.1.100`)

3. **Update Reflex configuration** in `rxconfig.py`:
   ```python
   config.backend_host = "0.0.0.0"  # Listen on all interfaces
   ```

4. **Restart the app**:
   ```bash
   ./run_termux.sh
   ```

5. **Access from other devices**:
   - On laptop/desktop: `http://192.168.1.100:3000`
   - On another phone: `http://192.168.1.100:3000`

**⚠️ Security Warning**: Only do this on trusted networks (home WiFi). Never on public WiFi.

### Custom Domain/HTTPS (Advanced)

For production deployment with custom domain:

1. Use **Cloudflare Tunnel** (free):
   ```bash
   pkg install cloudflared
   cloudflared tunnel --url http://localhost:3000
   ```

2. Or use **ngrok**:
   ```bash
   pkg install wget
   wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm64.tgz
   tar xvzf ngrok-stable-linux-arm64.tgz
   ./ngrok http 3000
   ```

## Performance Benchmarks

Expected performance on typical devices:

| Device RAM | Startup Time | Response Time | Concurrent Users |
|-----------|--------------|---------------|------------------|
| 2GB       | ~60s         | 2-5s          | 1                |
| 4GB       | ~45s         | 1-3s          | 2-3              |
| 6GB+      | ~30s         | <1s           | 5+               |

## Keeping the App Running

### Method 1: Wake Lock (No Root)
Install "Wake Lock - CPU Awake" from Play Store:
- Keep screen on
- Prevent Termux from sleeping

### Method 2: Termux:Wake-Lock (Recommended)
```bash
termux-wake-lock
./run_termux.sh
```

To release:
```bash
termux-wake-unlock
```

### Method 3: Background Service (Root)
Requires rooted device - not recommended for most users.

## Updating the Application

```bash
cd ~/Ethical-OSINT-Tracker

# Stop the running app (Ctrl+C)

# Pull latest changes
git pull origin main

# Activate environment
source .venv/bin/activate

# Update dependencies
uv pip install --upgrade -r requirements.txt

# Run migrations
alembic upgrade head

# Restart
./run_termux.sh
```

## Uninstallation

```bash
# Stop the app (Ctrl+C)

# Remove virtual environment and data
cd ~
rm -rf Ethical-OSINT-Tracker

# Optional: Remove system packages
pkg uninstall python rust clang
```

## FAQ

**Q: Can I use this with Termux from Google Play?**  
A: No, the Google Play version is outdated. Use F-Droid.

**Q: Does this work on rooted devices?**  
A: Yes, but root is NOT required.

**Q: Can I access this from my computer?**  
A: Yes, see "Access from Other Devices" section.

**Q: Will this drain my battery?**  
A: Yes, significantly. Use while charging or with power bank.

**Q: Can I run this 24/7 on my phone?**  
A: Not recommended. Use a dedicated device or cloud server for 24/7 operation.

**Q: Is uv required or can I use pip?**  
A: uv is recommended for speed (10-100x faster), but pip works. Edit `install_termux.sh` to use pip instead.

**Q: What about iOS/iPad?**  
A: Not supported. iOS doesn't allow terminal emulators with Python. Use:
- **iSH** (limited, Alpine Linux-based)
- **a-Shell** (partial Python support)
- **Cloud deployment** (recommended)

## Support

- **Documentation**: `docs/` directory
- **Issues**: GitHub Issues (if repository is public)
- **Community**: Termux Wiki (https://wiki.termux.com/)

## Security Considerations

1. **Change default password** immediately after first login
2. **Only use on trusted networks** (home WiFi)
3. **Don't expose to internet** without proper authentication
4. **Keep Termux updated**: `pkg upgrade`
5. **Enable device encryption**: Android Settings → Security
6. **Use VPN** when investigating sensitive targets
7. **Clear browser cache** after investigations

## Known Limitations

1. **Performance**: Slower than desktop/server deployment
2. **Battery**: High power consumption
3. **Memory**: Limited to device RAM (no swap without root)
4. **Network**: Mobile data may have restrictions/costs
5. **Background**: Android may kill the process
6. **File Upload**: Limited to 50MB (adjust in settings if needed)

## License

See `LICENSE` file in project root.

---

**Last Updated**: November 26, 2025  
**Tested On**: Termux 0.118+, Android 11-14
