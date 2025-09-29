# Memcord Data Protection & Recovery Guide

## 🚨 Critical Data Loss Prevention

This guide addresses the critical issue where **ALL memory slots can be permanently deleted** during memcord installation/upgrade **without any warning or backup**.

### The Problem

When running `uv pip install -e .` to upgrade memcord:
- ❌ **ALL memory slots are permanently destroyed**
- ❌ **No warning is given to users**
- ❌ **No automatic backup is created**
- ❌ **Months of project history can be lost in seconds**

---

## 🛡️ Prevention (BEFORE Installation)

### Option 1: Automated Protection Script (Recommended)

```bash
# Run this BEFORE any installation/upgrade
python utilities/protect_data.py
```

This script will:
- ✅ Detect existing memory data
- ⚠️  Show data loss warning
- 🛡️  Create automatic backup
- 📋 Provide recovery instructions

### Option 2: Manual Backup

```bash
# Create manual backup with timestamp
cp -r memory_slots ~/backup_memory_slots_$(date +%Y%m%d_%H%M%S)

# Verify backup was created
ls -la ~/backup_memory_slots_*
```

### Option 3: Export Important Slots

Use memcord's built-in tools before installation:

```bash
# Export individual slots
memcord_export slot_name="project_alpha" format="json"
memcord_export slot_name="client_meetings" format="md"

# Archive slots for long-term storage
memcord_archive action="archive" slot_name="project_alpha"
memcord_archive action="archive" slot_name="client_meetings"
```

---

## 🔧 Recovery (AFTER Data Loss)

### If You Used the Protection Script

1. **Find your backup:**
   ```bash
   ls emergency_backups/
   ```

2. **Restore automatically:**
   ```bash
   # Replace 'emergency_backup_YYYYMMDD_HHMMSS' with actual backup name
   cp -r emergency_backups/emergency_backup_*/. memory_slots/
   ```

3. **Verify restoration:**
   ```bash
   # Check that files are restored
   ls memory_slots/

   # Start memcord and verify data
   memcord_list
   ```

### If You Have Manual Backup

1. **Restore from backup:**
   ```bash
   # Replace with your actual backup path
   cp -r ~/backup_memory_slots_*/. memory_slots/
   ```

2. **Verify restoration:**
   ```bash
   ls memory_slots/
   memcord_list
   ```

### If You Used Export/Archive Tools

1. **List available archives:**
   ```bash
   memcord_archive action="list"
   ```

2. **Restore from archives:**
   ```bash
   memcord_archive action="restore" slot_name="project_alpha"
   memcord_archive action="restore" slot_name="client_meetings"
   ```

3. **Import exported files:**
   ```bash
   # If you have exported .json, .md, or .txt files
   memcord_import source="project_alpha.json" slot_name="project_alpha"
   ```

---

## 🚨 Emergency Recovery

### If You Have NO Backup

1. **Check for hidden backups:**
   ```bash
   # Look for .bak files (temporary backups)
   find . -name "*.bak" -type f

   # Check archives directory
   ls archives/

   # Check shared memories
   ls shared_memories/
   ```

2. **Check system-level backups:**
   ```bash
   # Time Machine (macOS)
   # Check /Users/[username]/.Trash
   # Check system backup tools
   ```

3. **File recovery tools:**
   - Use disk recovery software (PhotoRec, TestDisk)
   - Check operating system recycle bin/trash
   - Contact system administrator if on managed system

---

## 🔒 Best Practices for Data Protection

### Before ANY System Changes

1. **Always create backups:**
   ```bash
   python utilities/protect_data.py --backup-only
   ```

2. **Export critical data:**
   ```bash
   # Export your most important slots
   memcord_export slot_name="critical_project" format="json"
   memcord_export slot_name="important_notes" format="md"
   ```

3. **Use archival for long-term storage:**
   ```bash
   memcord_archive action="archive" slot_name="completed_project"
   ```

### Regular Maintenance

1. **Weekly backups:**
   ```bash
   # Add to crontab for weekly automated backups
   0 0 * * 0 python /path/to/memcord/utilities/protect_data.py --backup-only
   ```

2. **Monitor data growth:**
   ```bash
   # Check data size regularly
   du -sh memory_slots/
   ```

3. **Clean old backups:**
   ```bash
   # Keep only last 5 backups
   ls -t emergency_backups/ | tail -n +6 | xargs -I {} rm -rf emergency_backups/{}
   ```

---

## 🛠️ Advanced Recovery Techniques

### Backup Verification

```bash
# Verify backup integrity
python utilities/protect_data.py --check-only --memory-dir emergency_backups/emergency_backup_YYYYMMDD_HHMMSS
```

### Selective Restoration

```bash
# Restore only specific slots
cp emergency_backups/emergency_backup_*/project_alpha.json memory_slots/
cp emergency_backups/emergency_backup_*/client_meetings.json memory_slots/
```

### Data Migration

```bash
# Migrate data to new installation
mkdir new_memcord_installation/memory_slots
cp -r old_installation/memory_slots/* new_memcord_installation/memory_slots/
```

---

## 📞 Getting Help

### If You've Lost Data

1. **Stop immediately** - Don't install anything else
2. **Don't write to the affected disk** - This can overwrite deleted files
3. **Create an issue** with details:
   - When the data loss occurred
   - What installation command was used
   - Operating system details
   - Whether any backups exist

### Support Resources

- **GitHub Issues**: [Create data loss report](https://github.com/ukkit/memcord/issues)
- **Emergency Contact**: Include "DATA LOSS" in issue title for priority
- **Recovery Tools**: Links to file recovery software

---

## 🔮 Future Improvements

### Planned Features

- [ ] Automatic daily backups
- [ ] Cloud backup integration
- [ ] Real-time data replication
- [ ] Installation rollback capability
- [ ] Data integrity monitoring

### Contributing

Help improve data protection:
- Report data loss incidents
- Suggest backup improvements
- Test recovery procedures
- Contribute to protection scripts

---

## ⚠️ Legal Disclaimer

While memcord provides data protection tools, **users are responsible for their own data backups**. Always maintain independent backups of critical information. The memcord project cannot be held responsible for data loss, regardless of cause.

Remember: **No backup = No mercy**. Always protect your data!