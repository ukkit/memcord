# Enterprise Setup and Policy Guide

This guide provides detailed information for enterprise administrators deploying memcord with GitHub Copilot in organizational settings.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [MCP Policy Configuration](#mcp-policy-configuration)
- [Deployment Options](#deployment-options)
- [Security Considerations](#security-considerations)
- [Team Configuration](#team-configuration)
- [Access Control](#access-control)
- [Monitoring and Auditing](#monitoring-and-auditing)
- [Compliance](#compliance)
- [Troubleshooting](#troubleshooting)

---

## Overview

Memcord can be deployed in enterprise GitHub Copilot environments to provide team-wide conversation memory capabilities while maintaining security and compliance requirements.

### Key Enterprise Features

- **100% Local Storage** - All data stored on developer machines, no cloud dependencies
- **Zero External Calls** - No telemetry, no external APIs, fully air-gapped compatible
- **Configurable Access** - Control via GitHub organization MCP policies
- **Audit Friendly** - All operations logged via VSCode MCP logs
- **Team Sharing** - Optional shared memory directories for team collaboration

---

## Prerequisites

### Organizational Requirements

- **GitHub Copilot Enterprise or Business** subscription
- **Organization Administrator** access for policy management
- **VSCode 1.102+** across developer machines
- **Python 3.10+** available on developer machines
- **Network isolation** (optional) - Works in air-gapped environments

### Technical Requirements

- Central repository for shared configurations (recommended)
- Shared file storage for team memories (optional)
- Standard developer tooling (git, python, uv package manager)

---

## MCP Policy Configuration

### Understanding MCP Policy

As of 2026, Model Context Protocol (MCP) support in GitHub Copilot is controlled by organization policies. **MCP is disabled by default for security.**

### Enabling MCP for Your Organization

**Step 1: Access Organization Settings**

1. Navigate to your GitHub organization
2. Go to: **Settings** → **Copilot** → **Policies**
3. Locate: **"MCP servers in Copilot"** policy

**Step 2: Enable the Policy**

```
Policy: MCP servers in Copilot
Status: Enabled
Scope: All members / Specific teams
```

Options:
- **Disabled** (default) - No MCP servers allowed
- **Enabled for all members** - All organization members can use MCP
- **Enabled for specific teams** - Limit to designated teams

**Step 3: Configure Allow List (Optional)**

Restrict which MCP servers can be used:

```json
{
  "mcpServers": {
    "allowList": [
      "memcord",
      "github",
      "other-approved-servers"
    ]
  }
}
```

**Step 4: Apply and Communicate**

- Save policy changes
- Notify development teams of new capabilities
- Provide setup documentation

### Enterprise vs Business Considerations

**GitHub Copilot Enterprise:**
- Full policy control at organization level
- Custom agent configuration support
- Centralized MCP server management

**GitHub Copilot Business:**
- Policy control available
- Standard MCP integration
- Team-level configuration

---

## Deployment Options

### Option 1: Centralized Configuration Repository

**Best for:** Organizations wanting standardized deployments.

**Setup:**

1. Create configuration repository:
```bash
git clone https://github.com/your-org/vscode-config-template.git
cd vscode-config-template
```

2. Add memcord configuration:
```bash
mkdir -p .vscode
cat > .vscode/mcp.json <<EOF
{
  "servers": {
    "memcord": {
      "command": "uv",
      "args": [
        "--directory",
        "/opt/memcord",
        "run",
        "memcord"
      ],
      "env": {
        "PYTHONPATH": "/opt/memcord/src",
        "MEMCORD_MEMORY_DIR": "${workspaceFolder}/.memcord/slots",
        "MEMCORD_SHARED_DIR": "/shared/team-memories"
      }
    }
  }
}
EOF
```

3. Developers clone and use:
```bash
git clone https://github.com/your-org/vscode-config-template.git my-project
cd my-project
code .  # Opens VSCode with memcord configured
```

**Benefits:**
- Consistent configuration across teams
- Version controlled
- Easy to update and distribute changes

---

### Option 2: User Profile Installation

**Best for:** Individual developer flexibility.

**Setup:**

Provide developers with installation script:

```bash
#!/bin/bash
# install-memcord.sh

# Install memcord
git clone https://github.com/ukkit/memcord.git /opt/memcord
cd /opt/memcord
uv venv
source .venv/bin/activate
uv pip install -e .

# Configure VSCode user profile
VSCODE_USER_DIR="$HOME/.config/Code/User"
mkdir -p "$VSCODE_USER_DIR"

cat > "$VSCODE_USER_DIR/mcp.json" <<EOF
{
  "servers": {
    "memcord": {
      "command": "uv",
      "args": ["--directory", "/opt/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/opt/memcord/src"
      }
    }
  }
}
EOF

echo "Memcord installed! Restart VSCode to activate."
```

**Benefits:**
- Developers control their own installations
- Works across all projects automatically
- Simpler deployment

---

### Option 3: Custom GitHub Copilot Agents

**Best for:** Enterprise deployments with custom agents.

**Setup:**

Create custom agent configuration:

```json
{
  "agents": {
    "memcord-enterprise": {
      "description": "Corporate memory and knowledge management",
      "mcpServers": {
        "memcord": {
          "command": "uv",
          "args": ["--directory", "/opt/memcord", "run", "memcord"],
          "env": {
            "PYTHONPATH": "/opt/memcord/src",
            "MEMCORD_ENABLE_ADVANCED": "true",
            "MEMCORD_SHARED_DIR": "/mnt/team-shared/memories"
          }
        }
      },
      "tools": ["memcord_*"],
      "prompts": [
        "Use memcord to track all architectural decisions",
        "Save code review outcomes to team knowledge base"
      ]
    }
  }
}
```

Deploy via GitHub organization settings.

**Benefits:**
- Centrally managed
- Pre-configured workflows
- Consistent experience across organization

---

## Security Considerations

### Data Privacy and Sovereignty

**Local Storage Only:**
- All memcord data stored on local machines
- No cloud synchronization
- No external API calls
- No telemetry or tracking

**Data Location Control:**
```json
{
  "env": {
    "MEMCORD_MEMORY_DIR": "/company/secure/storage/memories",
    "MEMCORD_SHARED_DIR": "/company/shared/team-knowledge"
  }
}
```

**Recommendations:**
- Use encrypted file systems for sensitive data
- Configure backups for memory directories
- Apply appropriate file permissions (0600 for slot files)

### Access Control

**File System Permissions:**

```bash
# Individual developer memories
chmod 0700 ~/.memcord
chmod 0600 ~/.memcord/memory_slots/*.json

# Shared team memories
chown -R :dev-team /shared/team-memories
chmod 0770 /shared/team-memories
chmod 0660 /shared/team-memories/*.json
```

**Network Isolation:**

Memcord is safe for air-gapped environments:
- No internet connectivity required
- No DNS lookups
- No external dependencies at runtime

**Code Review and Auditing:**

- Memcord is open source: https://github.com/ukkit/memcord
- Review source code before deployment
- Audit tool calls via VSCode logs
- Monitor file system changes

### Security Hardening

**Input Validation:**
- All tool inputs validated against injection attacks
- Path traversal prevention
- XSS/script injection protection
- Safe character sets enforced

**Sandboxing (Optional):**

Run memcord in restricted environment:

```json
{
  "command": "firejail",
  "args": [
    "--quiet",
    "--private=/tmp/memcord-sandbox",
    "uv",
    "--directory", "/opt/memcord",
    "run", "memcord"
  ]
}
```

---

## Team Configuration

### Shared Memory Setup

**Scenario:** Team wants to share meeting notes and decisions.

**1. Create Shared Directory:**

```bash
sudo mkdir -p /shared/team-memories
sudo chown -R :dev-team /shared/team-memories
sudo chmod 0770 /shared/team-memories
```

**2. Configure Memcord:**

```json
{
  "env": {
    "MEMCORD_SHARED_DIR": "/shared/team-memories"
  }
}
```

**3. Usage:**

```
@workspace Save our sprint planning to shared memory
```

Memcord automatically uses shared directory for team-wide slots.

### Project-Specific Configuration

**Scenario:** Different teams need different memory locations.

**Team A (.vscode/mcp.json):**
```json
{
  "env": {
    "MEMCORD_MEMORY_DIR": "/projects/team-a/.memcord",
    "MEMCORD_SHARED_DIR": "/projects/team-a/shared"
  }
}
```

**Team B (.vscode/mcp.json):**
```json
{
  "env": {
    "MEMCORD_MEMORY_DIR": "/projects/team-b/.memcord",
    "MEMCORD_SHARED_DIR": "/projects/team-b/shared"
  }
}
```

### Multi-Instance Deployment

**Scenario:** Separate instances for production vs. development.

```json
{
  "servers": {
    "memcord-dev": {
      "command": "uv",
      "args": ["--directory", "/opt/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/opt/memcord/src",
        "MEMCORD_MEMORY_DIR": "/projects/dev/memories"
      }
    },
    "memcord-prod": {
      "command": "uv",
      "args": ["--directory", "/opt/memcord", "run", "memcord"],
      "env": {
        "PYTHONPATH": "/opt/memcord/src",
        "MEMCORD_MEMORY_DIR": "/projects/prod/memories"
      }
    }
  }
}
```

---

## Access Control

### Role-Based Configuration

**Junior Developers (Basic Mode):**
```json
{
  "env": {
    "MEMCORD_ENABLE_ADVANCED": "false"
  }
}
```
Access to 11 basic tools only.

**Senior Developers (Advanced Mode):**
```json
{
  "env": {
    "MEMCORD_ENABLE_ADVANCED": "true"
  }
}
```
Access to all 19 tools including import, export, compression.

### Team-Based Restrictions

Use GitHub Teams to control MCP policy scope:

**Organization Settings:**
```
MCP servers in Copilot: Enabled
Scope: Teams "senior-engineers" and "tech-leads"
```

Only specified teams can use memcord.

---

## Monitoring and Auditing

### Logging

**VSCode MCP Logs:**

1. Open Command Palette: `Ctrl+Shift+P` / `Cmd+Shift+P`
2. Run: `Developer: Show Logs`
3. Select: "MCP"
4. View memcord tool calls and responses

**Log Location:**
```
~/.config/Code/logs/*/exthost/output_logging_*
```

**Centralized Logging (Optional):**

Redirect logs to central server:
```bash
# Add to developer machines
tail -f ~/.config/Code/logs/*/exthost/output_logging_* | \
  logger -t memcord-audit -n syslog.company.com
```

### Audit Trail

**Track Tool Usage:**

All memcord operations appear in VSCode logs:
```
[MCP] Calling tool: memcord_name
[MCP] Arguments: {"name": "project-xyz"}
[MCP] Response: Created memory slot "project-xyz"
```

**File System Auditing:**

Monitor memory slot access:
```bash
# Linux/macOS
auditctl -w /shared/team-memories -p rwa -k memcord-access

# View audit logs
ausearch -k memcord-access
```

### Metrics

**Track Adoption:**
- Number of memory slots created
- Tool usage frequency
- Storage consumption

```bash
# Count active memory slots
find /shared/team-memories -name "*.json" | wc -l

# Total storage used
du -sh /shared/team-memories
```

---

## Compliance

### Data Retention

**Configure Archival Policies:**

```bash
# Archive slots older than 90 days
find /shared/team-memories -name "*.json" -mtime +90 -exec \
  python utilities/archive_old_slots.py {} \;
```

**Deletion Policies:**

```bash
# Permanently delete archived slots after 7 years
find /archives -name "*.json" -mtime +2555 -delete
```

### Regulatory Compliance

**GDPR:**
- Right to erasure: Delete individual slots on request
- Data portability: Export slots as JSON/Markdown
- Local storage ensures data sovereignty

**HIPAA (Healthcare):**
- Memcord operates offline (no PHI transmission)
- Encrypted storage recommended
- Access controls via file permissions

**SOC 2:**
- Audit logs available via VSCode
- Access control via GitHub organization policies
- Change tracking via version control

### Data Classification

**Sensitive Data Handling:**

1. Enable privacy mode by default:
```
Workflow: Always use memcord_zero for sensitive discussions
```

2. Separate storage for classified data:
```json
{
  "env": {
    "MEMCORD_MEMORY_DIR": "/secure/classified/memories"
  }
}
```

3. File encryption:
```bash
# Encrypt memory directory
ecryptfs-mount /secure/classified/memories
```

---

## Troubleshooting

### Policy Not Taking Effect

**Symptoms:**
- MCP policy enabled but users can't access memcord

**Solutions:**

1. Verify policy scope includes target teams
2. Check user is in correct GitHub team
3. Ensure users have restarted VSCode
4. Verify allow list includes "memcord" if configured

### Installation Across Teams

**Issue:** Inconsistent installations across developers

**Solution:** Provide automated installation script

```bash
#!/bin/bash
# enterprise-install-memcord.sh

set -e

MEMCORD_VERSION="2.3.6"
INSTALL_DIR="/opt/memcord"

echo "Installing memcord $MEMCORD_VERSION..."

# Clone repository
git clone --branch v$MEMCORD_VERSION \
  https://github.com/ukkit/memcord.git $INSTALL_DIR

cd $INSTALL_DIR

# Setup virtual environment
uv venv
source .venv/bin/activate
uv pip install -e .

# Configure VSCode
VSCODE_CONFIG="$HOME/.config/Code/User/mcp.json"
mkdir -p "$(dirname $VSCODE_CONFIG)"

cat > $VSCODE_CONFIG <<EOF
{
  "servers": {
    "memcord": {
      "command": "uv",
      "args": ["--directory", "$INSTALL_DIR", "run", "memcord"],
      "env": {
        "PYTHONPATH": "$INSTALL_DIR/src",
        "MEMCORD_SHARED_DIR": "/shared/team-memories"
      }
    }
  }
}
EOF

echo "✓ Memcord installed successfully!"
echo "✓ Restart VSCode to activate"
```

### Shared Directory Permissions

**Issue:** Developers can't write to shared memories

**Solution:**

```bash
# Fix permissions
sudo chown -R :dev-team /shared/team-memories
sudo chmod -R 0770 /shared/team-memories
sudo chmod -R 0660 /shared/team-memories/*.json

# Add users to group
sudo usermod -aG dev-team username
```

---

## Support and Resources

### Internal Support

**Recommended:**
- Create internal documentation wiki
- Designate memcord champions in each team
- Setup Slack/Teams channel for questions

### External Resources

- **GitHub Issues:** https://github.com/ukkit/memcord/issues
- **Documentation:** https://github.com/ukkit/memcord/docs
- **Community:** https://github.com/ukkit/memcord/discussions

### Professional Services

For enterprise deployment assistance, contact:
- Email: memcord@ultrafastidio.us
- Custom training available
- Configuration consulting

---

## Next Steps

1. **Review security requirements** with InfoSec team
2. **Enable MCP policy** in GitHub organization
3. **Pilot with small team** (5-10 developers)
4. **Gather feedback** and iterate
5. **Roll out organization-wide**

---

**Related Documentation:**
- [VSCode Setup Guide](vscode-setup.md)
- [Security Guide](security-vscode.md)
- [Tools Reference](tools-reference.md)

---

**Last Updated:** January 2026
**Target:** Enterprise Administrators
