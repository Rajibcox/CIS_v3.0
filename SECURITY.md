# QUANTUM TRADER V1 - Security Documentation

## Security Overview

QUANTUM TRADER V1 implements defense-in-depth security to protect trading credentials, user data, and trading operations.

## Credential Security

### Encryption Architecture

- **Algorithm**: AES-256-GCM (authenticated encryption)
- **Key Derivation**: Argon2id with configurable memory and iterations
- **Salt**: Unique per credential (32 bytes, cryptographically random)
- **IV**: Unique per encryption operation (12 bytes)

### Storage

- No plaintext API credentials stored on disk
- Encrypted credentials in database with per-exchange isolation
- Master key derived from user passphrase at runtime
- Credentials decrypted only in memory during active sessions

### Key Management

```
User Passphrase
       │
       ▼
   Argon2id (memory=64MB, iterations=3, parallelism=4)
       │
       ▼
Master Key (32 bytes)
       │
       ├──────► Data Encryption Key (per credential)
       │              │
       │              ▼
       │         AES-256-GCM
       │              │
       │              ▼
       │         Encrypted Payload
       │
       ▼
   Key Verification Token (for passphrase validation)
```

### Passphrase Requirements

- Minimum 12 characters
- Maximum 128 characters
- Recommended: 20+ characters with mixed case, numbers, symbols
- Not stored anywhere - validated via verification token only

## API Security

### Exchange API Keys

- Stored encrypted in database
- Decrypted only when needed for API calls
- Never logged or exposed in error messages
- Automatic IP whitelist validation where supported

### Web API Security

- JWT-based authentication (HS256 or RS256)
- Short-lived access tokens (15-30 minutes)
- Refresh token rotation
- CSRF protection on state-changing operations
- Rate limiting on all endpoints

### Telegram Bot Security

- User ID whitelist for command authorization
- Admin-only commands separated from user commands
- Rate limiting per user
- Audit logging of all commands

## Network Security

### Default Configuration

- Localhost-only binding (127.0.0.1:8000)
- No external network exposure by default
- HTTPS/TLS 1.3 for production deployment
- HSTS headers enforced

### Exchange Communication

- All API calls over HTTPS
- Certificate validation enforced
- Request signing where required by exchange
- Rate limit compliance built-in

## Data Protection

### Database Security

- PostgreSQL with row-level security
- Encrypted connections (SSL mode required)
- Column-level encryption for sensitive fields
- Regular automated backups with encryption

### Application Data

- Market data: Public, no encryption needed
- Trade history: Encrypted at rest
- Configuration: Encrypted sensitive fields
- Audit logs: Append-only, tamper-evident

### Log Security

- No credentials in logs
- Structured JSON logging
- Log rotation with retention policies
- Separate error log for debugging

## Operational Security

### Deployment Security

- Portable deployment with no system dependencies
- Self-contained runtime environment
- File integrity verification on startup
- Secure default configuration

### Access Control

- Role-based access (Admin, Trader, Viewer)
- Principle of least privilege
- Session management with timeout
- Concurrent session limits

### Audit Trail

All security-relevant events logged:
- Authentication attempts (success/failure)
- Configuration changes
- Trade execution
- API key usage
- Backup/restore operations
- System errors and exceptions

## Security Best Practices for Users

### Required

1. **Strong Passphrase**: Use 20+ character passphrase for credential encryption
2. **API Key Restrictions**: Enable IP whitelisting on exchange accounts
3. **Permissions**: Use read-only + trade permissions only (no withdrawal)
4. **Regular Updates**: Keep application and dependencies updated

### Recommended

1. **Network Isolation**: Run on dedicated machine or VLAN
2. **Monitoring**: Enable audit log review
3. **Backups**: Regular encrypted backups of database
4. **Testing**: Verify recovery procedures monthly

### For Live Trading

1. **Separate Credentials**: Use different API keys for paper vs live
2. **Position Limits**: Set exchange-level position limits
3. **Daily Loss Limits**: Configure exchange risk limits
4. **Kill Switch**: Test emergency stop procedures

## Threat Model

### Protected Against

- Credential theft from disk
- Unauthorized API access
- SQL injection (parameterized queries)
- XSS (CSP headers, input validation)
- CSRF (token validation)
- Man-in-the-middle (TLS enforcement)
- Replay attacks (nonce/timestamp validation)
- Brute force (rate limiting, account lockout)

### Mitigations

- Input validation on all user data
- Output encoding for all rendered content
- Secure headers (CSP, HSTS, X-Frame-Options)
- Dependency scanning (automated in CI)
- Security headers on all responses

## Incident Response

### Breach Detection

- Anomalous login detection
- Unusual API call patterns
- Configuration change alerts
- Database integrity checks

### Response Procedures

1. **Immediate**: Revoke compromised credentials
2. **Investigation**: Review audit logs
3. **Containment**: Isolate affected components
4. **Recovery**: Restore from verified backup
5. **Post-Incident**: Update threat model and controls

## Compliance

### Standards Alignment

- OWASP Top 10 mitigations
- NIST Cybersecurity Framework basics
- PCI DSS relevant controls (no card data)
- GDPR data minimization (no PII stored)

### Data Handling

- No personal data collected by default
- Optional Telegram user IDs (minimal)
- Trade data retained per configuration
- Right to deletion via database purge

## Security Checklist

### Pre-Deployment

- [ ] Change default secret key
- [ ] Generate strong master passphrase
- [ ] Configure exchange API IP whitelists
- [ ] Set up HTTPS certificates
- [ ] Review and customize rate limits
- [ ] Enable audit logging
- [ ] Test backup and recovery
- [ ] Verify no credentials in logs

### Ongoing

- [ ] Monitor audit logs weekly
- [ ] Apply security updates monthly
- [ ] Rotate API keys quarterly
- [ ] Review access permissions quarterly
- [ ] Test incident response annually

## Vulnerability Reporting

Report security issues to: security@quantum-trader.local

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-11-26 | Initial security architecture |