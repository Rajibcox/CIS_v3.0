# QUANTUM TRADER V1 - Recovery Guide

## Overview

This guide covers disaster recovery procedures for QUANTUM TRADER V1, including database recovery, position reconciliation, and system restoration.

## Recovery Scenarios

### Scenario 1: Application Crash During Trading
**Severity**: High  
**RTO**: < 5 minutes  
**RPO**: 0 (no data loss expected)

#### Symptoms
- Application process terminated unexpectedly
- Web dashboard unavailable
- Telegram bot stops responding

#### Recovery Steps

1. **Check for Running Processes**
   ```cmd
   STOP_QUANTUM_TRADER.bat
   ```

2. **Verify Database Integrity**
   ```cmd
   DIAGNOSTICS_QUANTUM_TRADER.bat
   ```

3. **Restart Application**
   ```cmd
   START_QUANTUM_TRADER.bat
   ```

4. **Verify Position Reconciliation**
   - Check dashboard: Positions page
   - Verify all open positions match exchange
   - Check TP/SL orders are active on exchange
   - Review logs for reconciliation messages

5. **Verify Telegram Bot**
   - Send `/status` command
   - Verify response includes current positions

#### Expected Outcome
- All positions recovered with correct TP/SL stages
- No duplicate orders placed
- Trading resumes automatically

### Scenario 2: Database Corruption
**Severity**: Critical  
**RTO**: < 30 minutes  
**RPO**: Last backup (up to 24 hours)

#### Symptoms
- SQLite error on startup
- "Database disk image is malformed"
- Application fails to start

#### Recovery Steps

1. **Stop Application**
   ```cmd
   STOP_QUANTUM_TRADER.bat
   ```

2. **Assess Damage**
   ```cmd
   # Check database file
   dir data\database\quantum.db
   
   # Try to read with sqlite3
   sqlite3 data\database\quantum.db ".tables"
   ```

3. **Restore from Latest Backup**
   ```cmd
   RECOVERY_QUANTUM_TRADER.bat
   ```

4. **If No Backup Available**
   ```cmd
   # Recreate database
   del data\database\quantum.db
   python src\backend\database\init_db.py
   
   # Manually reconcile positions from exchange
   # (Requires API credentials configured)
   ```

5. **Verify Restoration**
   ```cmd
   START_QUANTUM_TRADER.bat
   DIAGNOSTICS_QUANTUM_TRADER.bat
   ```

#### Expected Outcome
- Database restored to last backup state
- Positions reconciled with exchange
- Manual entry of any trades since backup

### Scenario 3: Exchange Disconnection
**Severity**: Medium  
**RTO**: < 2 minutes  
**RPO**: 0 (exchange maintains state)

#### Symptoms
- "Connection timeout" in logs
- Market data stops updating
- Order placement fails

#### Recovery Steps

1. **Check Internet Connection**
   ```cmd
   ping google.com
   ping fapi.binance.com
   ping api.bitget.com
   ```

2. **Check Exchange Status**
   - Visit exchange status pages
   - Check Twitter for outages

3. **Restart Market Data Service**
   - Application auto-reconnects
   - Check logs for "Reconnected" messages

4. **Verify Position State**
   - Dashboard Positions page
   - Compare with exchange web/app

5. **If Prolonged Outage**
   - Monitor positions manually on exchange
   - Be prepared to manage TP/SL manually
   - Application will queue orders for retry

#### Expected Outcome
- Automatic reconnection when exchange available
- No position state loss
- Queued orders executed on reconnect

### Scenario 4: Incorrect Position State (Ghost Positions)
**Severity**: High  
**RTO**: < 10 minutes  
**RPO**: 0

#### Symptoms
- Dashboard shows position not on exchange
- Exchange shows position not in dashboard
- TP/SL orders missing or duplicated

#### Recovery Steps

1. **Identify Discrepancy**
   ```cmd
   # Check dashboard vs exchange
   # Note: symbol, side, quantity, entry price
   ```

2. **Run Manual Reconciliation**
   - Dashboard → Positions → "Reconcile" button
   - Or restart application (auto-reconciles on startup)

3. **If Dashboard Has Ghost Position**
   - Verify on exchange: position truly closed
   - Manually close in dashboard (force close)
   - Update PnL manually if needed

4. **If Exchange Has Extra Position**
   - Verify it's from this application
   - If unknown: DO NOT TOUCH - investigate
   - If from app: Dashboard will detect on next reconcile

4. **If TP/SL Orders Mismatched**
   - Cancel all TP/SL on exchange for affected symbol
   - Restart application
   - Application will recreate correct orders

#### Expected Outcome
- Dashboard and exchange state synchronized
- Correct TP/SL orders active
- No orphaned orders

### Scenario 5: SSD Failure / Data Loss
**Severity**: Critical  
**RTO**: Hours (depends on replacement)  
**RPO**: Last off-site backup

#### Recovery Steps

1. **Replace SSD**
   - New SSD with same or larger capacity
   - Format NTFS

2. **Restore from Off-Site Backup**
   - Copy project folder from backup location
   - Verify all files present

3. **Reinstall on New SSD**
   ```cmd
   INSTALL_QUANTUM_TRADER.bat
   ```

4. **Restore Database**
   ```cmd
   RECOVERY_QUANTUM_TRADER.bat
   ```

5. **Reconfigure Credentials**
   - Enter exchange API credentials
   - Enter Telegram bot token
   - Enter master passphrase

6. **Full Reconciliation**
   - Start application
   - Verify all positions match exchange
   - Verify all TP/SL orders active

#### Expected Outcome
- Full system restored
- Trading capability restored
- Historical data from backup

### Scenario 6: Configuration Corruption
**Severity**: Low  
**RTO**: < 5 minutes  
**RPO**: 0

#### Symptoms
- Application starts but behaves incorrectly
- Settings not saving
- Error messages about config

#### Recovery Steps

1. **Backup Current Config**
   ```cmd
   copy .env .env.corrupted
   ```

2. **Restore Default Config**
   ```cmd
   # From backup
   copy data\backups\env_YYYYMMDD_HHMMSS.bak .env
   
   # Or recreate
   del .env
   START_QUANTUM_TRADER.bat
   ```

3. **Re-enter Settings**
   - Use dashboard Configuration Center
   - Re-enter all settings

#### Expected Outcome
- Clean configuration
- All settings re-entered via UI

## Automated Recovery Features

### Startup Reconciliation
On every startup, the application:
1. Fetches all open positions from exchanges
2. Compares with local database
3. Updates local state to match exchange
4. Verifies all TP/SL orders are active
5. Recreates missing protective orders
6. Alerts on discrepancies

### Health Monitoring
Background health checks every 60 seconds:
- Database connectivity
- Exchange API connectivity
- WebSocket connections
- Disk space
- Memory usage

### Automatic Failover
- If primary exchange fails, continues with secondary
- If market data stream fails, falls back to REST polling
- If database write fails, queues writes for retry

## Manual Recovery Procedures

### Force Position Close (Emergency)
```python
# Via Python console or emergency script
from src.backend.services.execution_service import ExecutionService

service = ExecutionService(config)
await service.emergency_close_all_positions()
```

### Cancel All Orders
```python
# Cancel all open orders on exchange
await service.cancel_all_orders("BTCUSDT")
```

### Reset Paper Trading
```cmd
# Via Telegram
/paper_reset

# Or via dashboard
# Paper Trading page → Reset button
```

### Recalculate PnL
```python
# If PnL seems incorrect
from src.backend.services.pnl_service import PnLService

service = PnLService(config)
await service.recalculate_all_pnl()
```

## Recovery Verification Checklist

After any recovery, verify:

- [ ] Application starts without errors
- [ ] Dashboard accessible at localhost:8000
- [ ] Health endpoint returns 200 OK
- [ ] Database tables accessible
- [ ] Exchange connections working
- [ ] Market data streaming
- [ ] All open positions match exchange
- [ ] All TP/SL orders active on exchange
- [ ] PnL values reasonable
- [ ] Telegram bot responding
- [ ] No error messages in logs
- [ ] Risk limits enforced
- [ ] Configuration accessible

## Contact Information

For recovery assistance:
- Check `data/logs/quantum_trader_error.log`
- Run `DIAGNOSTICS_QUANTUM_TRADER.bat`
- Review this guide
- GitHub Issues: [repository]/issues

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-11-26 | Initial recovery guide |