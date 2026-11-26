# QUANTUM TRADER V1 - Portability Guide

## Overview

This guide describes how to deploy, move, and run QUANTUM TRADER V1 on different Windows 11 computers using a portable external SSD.

## Requirements

### Host System
- Windows 11 64-bit (version 22H2 or later)
- Minimum 8 GB RAM (16 GB recommended)
- Minimum 10 GB free space on SSD
- Internet connection for exchange APIs
- Administrator rights for initial setup

### Portable SSD
- NTFS formatted
- Minimum 32 GB capacity (128 GB recommended)
- USB 3.0+ interface for performance
- Assigned drive letter (e.g., N:) on each host

## Directory Structure

```
N:\Trading\CIS_v3.0\QUANTUM_TRADER_V1\
├── INSTALL_QUANTUM_TRADER.bat
├── START_QUANTUM_TRADER.bat
├── STOP_QUANTUM_TRADER.bat
├── DIAGNOSTICS_QUANTUM_TRADER.bat
├── BACKUP_QUANTUM_TRADER.bat
├── RECOVERY_QUANTUM_TRADER.bat
├── README.md
├── ARCHITECTURE.md
├── BUILD_STATUS.md
├── CHANGELOG.md
├── SECURITY.md
├── RISK_MODEL.md
├── EXCHANGE_INTEGRATION.md
├── DATABASE_SCHEMA.md
├── TEST_REPORT.md
├── PORTABILITY_GUIDE.md
├── RECOVERY_GUIDE.md
├── USER_GUIDE.md
├── .env                          # Local configuration
├── runtime/
│   ├── python/                   # Embedded Python (optional)
│   └── venv/                     # Virtual environment
├── src/
│   ├── backend/
│   ├── frontend/
│   └── shared/
├── data/
│   ├── market_data/
│   ├── database/
│   ├── logs/
│   ├── backups/
│   └── temp/
└── config/
    ├── default.yaml
    ├── exchanges/
    └── strategies/
```

## Installation on New Host

### Step 1: Connect SSD
1. Connect portable SSD to new Windows 11 computer
2. Note the assigned drive letter (e.g., N:, E:, F:)
3. Navigate to the project folder

### Step 2: Run Installer
```cmd
# From the project root directory
INSTALL_QUANTUM_TRADER.bat
```

The installer will:
- Check Python availability
- Create virtual environment in `runtime/venv`
- Install all Python dependencies
- Initialize SQLite database
- Create default configuration
- Set up directory structure

### Step 3: Configure
Edit `.env` file with your settings:
```env
# Required for live trading
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BITGET_API_KEY=your_key
BITGET_API_SECRET=your_secret
BITGET_PASSPHRASE=your_passphrase

# Optional
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_ALLOWED_USERS=123456789
```

### Step 4: Start Application
```cmd
START_QUANTUM_TRADER.bat
```

### Step 5: Access Dashboard
Open browser to: `http://localhost:8000`

## Moving Between Computers

### Pre-Move Checklist
- [ ] Stop application: `STOP_QUANTUM_TRADER.bat`
- [ ] Run backup: `BACKUP_QUANTUM_TRADER.bat`
- [ ] Verify backup files in `data/backups/`
- [ ] Safely eject SSD

### On New Computer
1. Connect SSD
2. Run diagnostics: `DIAGNOSTICS_QUANTUM_TRADER.bat`
3. If database needs recovery: `RECOVERY_QUANTUM_TRADER.bat`
4. Start application: `START_QUANTUM_TRADER.bat`

## Drive Letter Independence

The application uses relative paths and is designed to work regardless of the drive letter assigned to the SSD.

### Path Resolution
All internal paths are resolved from the executable location:
```python
import sys
from pathlib import Path

def get_project_root():
    if getattr(sys, 'frozen', False):
        # Running as packaged executable
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent.parent.parent
```

### Configuration Paths
- Database: `data/database/quantum.db` (relative)
- Logs: `data/logs/` (relative)
- Backups: `data/backups/` (relative)
- Config: `.env` and `config/` (relative)

## Embedded Python Runtime (Optional)

For true portability without host Python:

### Option 1: Python Embeddable Package
1. Download Python 3.11 embeddable package from python.org
2. Extract to `runtime/python/`
3. Modify `START_QUANTUM_TRADER.bat` to use embedded Python

### Option 2: PyInstaller (Future)
```bash
# Build standalone executable
pyinstaller --onefile --name quantum_trader src/backend/main.py
```

## Network Configuration

### Firewall
Windows Defender Firewall may prompt on first run:
- Allow "Python" on Private networks
- This enables localhost WebSocket connections

### Antivirus
Add exclusions for:
- Project folder (N:\Trading\CIS_v3.0\QUANTUM_TRADER_V1)
- Python executable (runtime\venv\Scripts\python.exe)

### Proxy
If behind corporate proxy:
```env
HTTP_PROXY=http://proxy:port
HTTPS_PROXY=http://proxy:port
```

## Data Persistence

### What Persists Across Moves
- Database (SQLite file)
- Configuration (.env, config/*.yaml)
- Market data cache
- Logs
- Backups
- Trade history

### What Does Not Persist
- Virtual environment (recreated on install)
- Python packages (reinstalled on install)
- Temporary files
- Process locks

## Troubleshooting Portability Issues

### Issue: "Python not found"
**Solution**: Run `INSTALL_QUANTUM_TRADER.bat` to create virtual environment

### Issue: "Database locked"
**Solution**: Ensure no other instance running, check for `.db-wal` files

### Issue: "Port 8000 in use"
**Solution**: Change PORT in .env, or stop conflicting application

### Issue: "Module not found"
**Solution**: Re-run installer, or activate venv and `pip install -r requirements.txt`

### Issue: "Permission denied"
**Solution**: Run as Administrator, or check folder permissions

### Issue: "Exchange connection failed"
**Solution**: Check internet, firewall, proxy settings, API credentials

## Performance on Different Hardware

### Minimum Specs
- CPU: 2 cores, 2.0 GHz
- RAM: 8 GB
- Disk: SSD (USB 3.0)

### Recommended Specs
- CPU: 4+ cores, 3.0 GHz
- RAM: 16 GB
- Disk: NVMe SSD (USB 3.2/4.0)

### Performance Tuning
```env
# Reduce for lower specs
MARKET_DATA_INTERVAL=120
STRATEGY_SCAN_INTERVAL=600
MAX_CONCURRENT_REQUESTS=5

# Increase for higher specs
MARKET_DATA_INTERVAL=30
STRATEGY_SCAN_INTERVAL=120
MAX_CONCURRENT_REQUESTS=20
```

## Backup Strategy for Portability

### Automated Backups
The application creates daily backups in `data/backups/`

### Manual Backup Before Move
```cmd
BACKUP_QUANTUM_TRADER.bat
```

### What Gets Backed Up
- Database (quantum_YYYYMMDD_HHMMSS.db)
- Environment config (env_YYYYMMDD_HHMMSS.bak)

### Restore on New Machine
```cmd
RECOVERY_QUANTUM_TRADER.bat
```

## Security Considerations

### Credential Portability
- API credentials encrypted with master passphrase
- Passphrase NOT stored - must be entered on each host
- Different encryption key per host (derived from passphrase + host ID)

### Data Protection
- Database encrypted at rest (future enhancement)
- Backup files not encrypted by default
- Consider encrypting entire SSD with BitLocker

## Version Compatibility

### Forward Compatibility
- Newer app version can read older database
- Migrations run automatically on startup

### Backward Compatibility
- Older app version CANNOT read newer database
- Always backup before upgrading

## Checklist for Production Deployment

- [ ] SSD encrypted (BitLocker)
- [ ] Strong master passphrase set
- [ ] Exchange API keys with IP whitelist
- [ ] Exchange API keys with trade-only permissions
- [ ] Telegram bot configured with admin user
- [ ] Firewall rules configured
- [ ] Antivirus exclusions added
- [ ] Backup schedule verified
- [ ] Recovery tested
- [ ] Monitoring alerts configured
- [ ] Documentation accessible
- [ ] Emergency stop procedure documented

## Support

For portability issues:
1. Run `DIAGNOSTICS_QUANTUM_TRADER.bat`
2. Check `data/logs/quantum_trader.log`
3. Review this guide
4. Check GitHub issues

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-11-26 | Initial portability guide |