# Security Guide for VSCode and GitHub Copilot Integration

This guide provides security best practices and considerations for deploying memcord with VSCode and GitHub Copilot in secure environments.

## Table of Contents

- [Security Overview](#security-overview)
- [Threat Model](#threat-model)
- [Data Privacy and Protection](#data-privacy-and-protection)
- [Access Control](#access-control)
- [Network Security](#network-security)
- [Input Validation](#input-validation)
- [Audit and Monitoring](#audit-and-monitoring)
- [Compliance Considerations](#compliance-considerations)
- [Incident Response](#incident-response)
- [Security Checklist](#security-checklist)

---

## Security Overview

### Core Security Principles

Memcord is designed with security and privacy as foundational principles:

**1. Privacy-First Architecture**
- 100% local storage - no cloud dependencies
- Zero external API calls or telemetry
- No data transmission to third parties
- Air-gapped environment compatible

**2. Minimal Attack Surface**
- Operates entirely offline
- No network listeners or exposed ports
- Runs with user-level permissions
- Limited file system access

**3. Defense in Depth**
- Input validation at all entry points
- Path traversal prevention
- Injection attack protection
- Safe character set enforcement

---

## Threat Model

### Assets to Protect

1. **Conversation Memory Data**
   - Historical chat conversations
   - Code snippets and technical decisions
   - Potentially sensitive project information
   - Personal identifiable information (PII)

2. **Configuration Data**
   - MCP server configuration
   - File system paths
   - Environment variables

3. **System Resources**
   - Disk space (memory slots storage)
   - CPU (summarization operations)
   - File system access

### Threat Actors

**External Attackers:**
- Cannot directly access memcord (no network exposure)
- Would need to compromise developer machine first
- Limited to attacks via VSCode extension vulnerabilities

**Insider Threats:**
- Developers with legitimate access
- Malicious MCP server configurations
- Social engineering attacks

**Supply Chain:**
- Compromised dependencies
- Malicious VSCode extensions
- Tampered memcord installation

### Attack Vectors

1. **Configuration Manipulation**
   - Malicious MCP configuration pointing to attacker-controlled paths
   - Environment variable injection
   - Path traversal in configuration

2. **Input Injection**
   - Command injection via tool parameters
   - Path traversal in slot names
   - XSS in exported HTML/Markdown

3. **Data Exfiltration**
   - Unauthorized memory slot exports
   - File system access beyond intended directories
   - Log file analysis

4. **Resource Exhaustion**
   - Excessive memory slot creation
   - Large file imports causing disk exhaustion
   - CPU-intensive summarization operations

---

## Data Privacy and Protection

### Local Storage Security

**1. File System Permissions**

Restrict access to memory directories:

```bash
# Set restrictive permissions on memory slots
chmod 0700 ~/.memcord
chmod 0600 ~/.memcord/memory_slots/*.json

# For shared memories, use group permissions
chgrp dev-team /shared/team-memories
chmod 0770 /shared/team-memories
chmod 0660 /shared/team-memories/*.json
```

**2. Encryption at Rest**

Enable file system encryption for sensitive data:

**Linux (ecryptfs):**
```bash
# Encrypt memory directory
sudo apt-get install ecryptfs-utils
ecryptfs-migrate-home -u username

# Or use LUKS for full disk encryption
```

**macOS (FileVault):**
```bash
# Enable FileVault for home directory encryption
sudo fdesetup enable
```

**Windows (BitLocker):**
```powershell
# Enable BitLocker for drive encryption
Enable-BitLocker -MountPoint "C:" -EncryptionMethod XtsAes256
```

**3. Secure Deletion**

When deleting sensitive memory slots:

```bash
# Linux/macOS - secure deletion
shred -vfz -n 3 memory_slots/sensitive-slot.json

# Windows - secure deletion with cipher
cipher /w:memory_slots\
```

### Data Classification

**Public Data:**
- Non-sensitive technical discussions
- Public API documentation
- Open-source code references
- Standard: Basic file permissions (0644)

**Internal Data:**
- Project architecture decisions
- Code review feedback
- Team meeting notes
- Standard: Restricted permissions (0600)

**Confidential Data:**
- Security vulnerability details
- Authentication credentials (should never be stored!)
- Customer PII
- Standard: Encrypted storage + restricted access

**Regulated Data (HIPAA, PCI-DSS, etc.):**
- Healthcare information
- Payment card data
- Financial records
- Standard: Encrypted + audited + compliance controls

### Privacy Mode

**Zero Mode** prevents accidental storage of sensitive information:

```json
{
  "env": {
    "MEMCORD_DEFAULT_SLOT": "zero"
  }
}
```

**Best Practices:**
1. Enable zero mode by default for sensitive discussions
2. Explicitly switch to named slots only when needed
3. Train team members on when to use zero mode
4. Audit slot creation for policy compliance

---

## Access Control

### File System Access Control

**Principle of Least Privilege:**

Memcord only needs access to:
- Memory slots directory (configured path)
- Shared memories directory (if team features used)
- Archive directory (if archival features used)

**Restrict Access:**

```json
{
  "env": {
    "MEMCORD_MEMORY_DIR": "/restricted/project/memories",
    "MEMCORD_SHARED_DIR": "/restricted/shared/memories"
  }
}
```

Ensure directories have appropriate ACLs:

```bash
# Linux ACL example
setfacl -m u:username:rwx /restricted/project/memories
setfacl -m g:dev-team:rx /restricted/shared/memories
```

### GitHub Organization Policies

**MCP Policy Controls:**

1. **Default: Disabled**
   - MCP is disabled by default in GitHub organizations
   - Must be explicitly enabled by administrators

2. **Selective Enablement**
   - Enable only for specific teams that need it
   - Use allowlists to restrict which servers can be used

3. **Audit Trail**
   - Monitor which teams have MCP enabled
   - Review MCP server configurations regularly

**Configuration:**

```json
{
  "mcpServers": {
    "policy": "allowlist",
    "allowList": ["memcord"],
    "enabledTeams": ["senior-engineers", "security-team"]
  }
}
```

### User-Level Isolation

**Workspace vs Global Configuration:**

- **Workspace config** (`.vscode/mcp.json`): Project-specific
  - Isolated to single project
  - Can be version controlled and reviewed
  - Recommended for most use cases

- **Global config** (user profile): Applies to all projects
  - More convenient but less secure
  - Harder to audit and control
  - Use only for trusted environments

### Role-Based Tool Access

**Basic Mode (11 tools) - For all developers:**
```json
{
  "env": {
    "MEMCORD_ENABLE_ADVANCED": "false"
  }
}
```

**Advanced Mode (19 tools) - For senior engineers only:**
```json
{
  "env": {
    "MEMCORD_ENABLE_ADVANCED": "true"
  }
}
```

Advanced tools include:
- Import (potential for malicious file execution)
- Export (data exfiltration risk)
- Archive/compression (resource exhaustion)

---

## Network Security

### No Network Exposure

Memcord has **zero network exposure** by design:
- No listening ports
- No outbound connections
- No DNS lookups
- No external API calls

**Verification:**

```bash
# Monitor network connections while running memcord
lsof -i -P | grep memcord  # Should return nothing

# Or use netstat
netstat -tuln | grep memcord  # Should return nothing
```

### Air-Gapped Compatibility

Memcord works perfectly in air-gapped environments:

**Installation in Air-Gapped Environment:**

1. Download on internet-connected machine:
```bash
git clone https://github.com/ukkit/memcord.git
tar -czf memcord.tar.gz memcord/
```

2. Transfer to air-gapped machine (USB, etc.)

3. Install dependencies offline:
```bash
# Prepare wheels on connected machine
pip download -d memcord-deps -r memcord/requirements.txt

# Install on air-gapped machine
pip install --no-index --find-links=memcord-deps -r requirements.txt
```

### Proxy Considerations

If your organization uses an HTTP proxy:

**Memcord does NOT use proxy settings** - it makes no network calls.

---

## Input Validation

### Built-in Security Features

Memcord includes comprehensive input validation:

**1. Slot Name Validation**
- Alphanumeric characters, hyphens, underscores only
- No path traversal characters (`..`, `/`, `\`)
- Maximum length limits
- Reserved name protection

```python
# Example validation (internal)
SAFE_SLOT_NAME = r'^[a-zA-Z0-9_-]+$'
```

**2. Path Traversal Prevention**
- All file operations use absolute paths
- Relative path resolution is blocked
- Symlink following is controlled

**3. Injection Attack Prevention**
- No shell command execution from user input
- SQL injection N/A (no database)
- XSS prevention in exported HTML/Markdown

**4. Content Validation**
- File size limits for imports
- MIME type validation
- Malicious file pattern detection

### Custom Validation Rules

**Organization-Specific Rules:**

Create a validation wrapper:

```python
# custom_validation.py
from memcord.security import SecurityMiddleware

class CustomSecurityMiddleware(SecurityMiddleware):
    def validate_slot_name(self, name: str) -> bool:
        # Enforce organization naming convention
        if not name.startswith("proj-"):
            raise ValueError("Slot names must start with 'proj-'")
        return super().validate_slot_name(name)
```

### Sandboxing (Optional)

Run memcord in restricted environment:

**Using Firejail (Linux):**

```json
{
  "command": "firejail",
  "args": [
    "--quiet",
    "--private=/tmp/memcord-sandbox",
    "--private-dev",
    "--private-tmp",
    "--nonetwork",
    "--caps.drop=all",
    "uv",
    "--directory", "/opt/memcord",
    "run", "memcord"
  ]
}
```

**Using Docker:**

```dockerfile
FROM python:3.10-slim
RUN useradd -m -u 1000 memcord
USER memcord
WORKDIR /app
COPY memcord/ /app/
RUN pip install -e .
CMD ["memcord"]
```

---

## Audit and Monitoring

### Logging

**VSCode MCP Logs:**

Location:
- **macOS:** `~/Library/Application Support/Code/logs/*/exthost/output_logging_*`
- **Linux:** `~/.config/Code/logs/*/exthost/output_logging_*`
- **Windows:** `%APPDATA%\Code\logs\*\exthost\output_logging_*`

**Log Contents:**
- All tool calls with parameters
- Tool responses
- Error messages and stack traces
- Performance metrics

**Accessing Logs:**
1. Open Command Palette: `Ctrl+Shift+P` / `Cmd+Shift+P`
2. Run: `Developer: Show Logs`
3. Select: "MCP"

**Log Retention:**
- VSCode rotates logs automatically
- Old logs are archived
- Configure retention via VSCode settings

### Centralized Logging

**Forward Logs to SIEM:**

```bash
# Linux/macOS - forward to syslog
tail -f ~/.config/Code/logs/*/exthost/output_logging_* | \
  logger -t memcord -p local0.info -n siem.company.com

# Or use Filebeat for structured logging
filebeat.inputs:
  - type: log
    paths:
      - ~/.config/Code/logs/*/exthost/output_logging_*
    tags: ["memcord", "mcp"]
```

### Monitoring Checklist

**Audit These Events:**

1. **Memory Slot Operations**
   - Creation of new slots
   - Deletion of slots
   - Slot renames

2. **Content Operations**
   - Large saves (potential data exfiltration)
   - Exports to external formats
   - Imports from external sources

3. **Search Operations**
   - Search patterns (identify data mining)
   - Frequency of queries

4. **Configuration Changes**
   - MCP config modifications
   - Environment variable changes
   - Path changes

5. **Errors and Failures**
   - Permission denied errors
   - Invalid input attempts
   - Resource exhaustion events

### Anomaly Detection

**Red Flags to Monitor:**

- Unusual slot creation rate (>10 per minute)
- Large content saves (>10MB)
- Frequent export operations
- Search patterns matching sensitive keywords
- Access to memory slots outside normal hours

---

## Compliance Considerations

### GDPR (General Data Protection Regulation)

**Right to Erasure:**
```bash
# Delete individual's data
rm memory_slots/user-john-smith*.json
```

**Data Portability:**
```python
# Export all user data
memcord_export "user-data" "json"
```

**Data Minimization:**
- Only store necessary information
- Use zero mode for temporary discussions
- Regular cleanup of old slots

**Consent Management:**
- Document user consent for memory storage
- Provide opt-out mechanisms
- Clear privacy policy

### HIPAA (Healthcare)

**Protected Health Information (PHI) Handling:**

1. **Encryption Required**
   - Enable file system encryption
   - Use encrypted network shares for shared memories

2. **Access Controls**
   - Implement role-based access
   - Audit all PHI access
   - Use zero mode for PHI discussions

3. **Breach Notification**
   - Monitor for unauthorized access
   - Document all PHI exposures
   - Have incident response plan

**Configuration for HIPAA:**

```json
{
  "env": {
    "MEMCORD_MEMORY_DIR": "/encrypted/hipaa-compliant/memories",
    "MEMCORD_DEFAULT_SLOT": "zero",
    "MEMCORD_ENABLE_ADVANCED": "false"
  }
}
```

### PCI-DSS (Payment Card Industry)

**Never Store Cardholder Data in Memcord:**
- No credit card numbers
- No CVV codes
- No PINs or authentication data

**If Discussing Payment Systems:**
- Use zero mode
- Refer to systems by codenames
- Sanitize all examples

### SOC 2

**Control Objectives:**

1. **CC6.1 - Logical Access Controls**
   - File system permissions
   - GitHub organization policies
   - Role-based tool access

2. **CC7.2 - System Monitoring**
   - VSCode MCP logs
   - File system auditing
   - Anomaly detection

3. **CC8.1 - Change Management**
   - Version control for configurations
   - Review process for MCP server changes
   - Rollback procedures

### ISO 27001

**Information Security Controls:**

- **A.9.4.1 - Information Access Restriction**
  - File permissions
  - Access control lists
  - Workspace isolation

- **A.12.4.1 - Event Logging**
  - MCP protocol logs
  - File system audit logs
  - Centralized log aggregation

- **A.18.1.5 - Privacy Regulation**
  - Data classification
  - Retention policies
  - Privacy by design

---

## Incident Response

### Security Incident Types

**1. Unauthorized Access**
- Unexpected memory slot access
- File permission changes
- Configuration tampering

**2. Data Exfiltration**
- Unusual export operations
- Large file transfers
- Unauthorized sharing

**3. Malicious Input**
- Injection attack attempts
- Path traversal attempts
- Resource exhaustion

### Incident Response Playbook

**Phase 1: Detection**

```bash
# Check for unusual activity
find memory_slots/ -type f -mtime -1  # Recent modifications
grep "error\|denied" ~/.config/Code/logs/*/exthost/output_logging_*
```

**Phase 2: Containment**

```bash
# Disable memcord immediately
mv .vscode/mcp.json .vscode/mcp.json.disabled

# Backup affected data
tar -czf incident-backup-$(date +%Y%m%d).tar.gz memory_slots/
```

**Phase 3: Investigation**

1. Review MCP logs for suspicious tool calls
2. Check file system audit logs
3. Interview affected developers
4. Document timeline of events

**Phase 4: Eradication**

1. Remove malicious configuration
2. Delete compromised memory slots
3. Update security controls
4. Patch vulnerabilities

**Phase 5: Recovery**

1. Restore from clean backups
2. Re-enable memcord with enhanced controls
3. Monitor for recurring issues

**Phase 6: Post-Incident**

1. Document lessons learned
2. Update security policies
3. Conduct team training
4. Improve monitoring

### Emergency Contacts

**Internal:**
- Security Team: security@company.com
- IT Operations: ops@company.com
- Legal/Compliance: legal@company.com

**External:**
- Memcord Issues: https://github.com/ukkit/memcord/issues
- Security Vulnerabilities: memcord-security@ultrafastidio.us

---

## Security Checklist

### Initial Setup

- [ ] Enable file system encryption
- [ ] Set restrictive file permissions (0600 for slots)
- [ ] Configure organization MCP policy
- [ ] Review and approve MCP configuration
- [ ] Enable audit logging
- [ ] Document security controls
- [ ] Train team on security best practices

### Regular Maintenance

- [ ] Review MCP logs weekly
- [ ] Audit memory slot access monthly
- [ ] Update memcord to latest version
- [ ] Review GitHub organization policies
- [ ] Rotate sensitive memory slots
- [ ] Test incident response procedures
- [ ] Conduct security awareness training

### Before Production Deployment

- [ ] Security review of configuration
- [ ] Penetration testing (if required)
- [ ] Compliance validation
- [ ] Disaster recovery plan
- [ ] Data retention policy
- [ ] User privacy notice
- [ ] Incident response plan

### For Sensitive Projects

- [ ] Use zero mode by default
- [ ] Implement data classification
- [ ] Enable advanced monitoring
- [ ] Require code review for configs
- [ ] Regular security audits
- [ ] Encrypted backups
- [ ] Access control reviews

---

## Best Practices Summary

1. **Default to Privacy**
   - Use zero mode for sensitive discussions
   - Enable file encryption
   - Minimize data retention

2. **Restrict Access**
   - File system permissions
   - Organization policies
   - Role-based tool access

3. **Monitor Activity**
   - Enable logging
   - Review logs regularly
   - Detect anomalies

4. **Validate Input**
   - Trust built-in validation
   - Add custom rules as needed
   - Consider sandboxing

5. **Plan for Incidents**
   - Document procedures
   - Practice response
   - Have contacts ready

6. **Stay Updated**
   - Keep memcord current
   - Monitor security advisories
   - Review policies regularly

---

## Resources

- **Security Issues:** https://github.com/ukkit/memcord/security
- **Documentation:** https://github.com/ukkit/memcord/docs
- **Enterprise Setup:** [enterprise-setup.md](enterprise-setup.md)
- **VSCode Setup:** [vscode-setup.md](vscode-setup.md)

---

**Last Updated:** January 2026
**Audience:** Security Engineers, Compliance Officers, System Administrators
