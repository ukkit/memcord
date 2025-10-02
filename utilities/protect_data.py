#!/usr/bin/env python3
"""Data protection script for memcord installation/upgrade.

This script should be run BEFORE installing or upgrading memcord to prevent data loss.
It creates automatic backups and provides warnings about potential data loss.

Usage:
    python utilities/protect_data.py
    python utilities/protect_data.py --backup-only
    python utilities/protect_data.py --check-only
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def detect_memory_data(memory_dir: str = "memory_slots") -> tuple[bool, int, int, list[str]]:
    """Detect existing memory data and return statistics.

    Returns:
        Tuple of (data_exists, slot_count, total_size_bytes, slot_names)
    """
    memory_path = Path(memory_dir)

    if not memory_path.exists():
        return False, 0, 0, []

    slot_files = list(memory_path.glob("*.json"))
    # Exclude backup metadata file from slot count
    slot_files = [f for f in slot_files if f.name != "backup_metadata.json"]
    slot_names = [f.stem for f in slot_files]

    total_size = 0
    for file_path in memory_path.rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size

    return len(slot_files) > 0, len(slot_files), total_size, slot_names


def create_emergency_backup(memory_dir: str = "memory_slots", backup_dir: str = "emergency_backups") -> str:
    """Create an emergency backup of memory data.

    Returns:
        Path to the created backup
    """
    memory_path = Path(memory_dir)
    backup_path = Path(backup_dir)
    backup_path.mkdir(exist_ok=True)

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    microseconds = now.microsecond
    backup_name = f"emergency_backup_{timestamp}_{microseconds}"
    target_backup = backup_path / backup_name

    # Create backup
    shutil.copytree(memory_path, target_backup)

    # Create metadata file
    metadata = {
        "backup_type": "emergency",
        "timestamp": datetime.now().isoformat(),
        "source_path": str(memory_path.absolute()),
        "backup_path": str(target_backup.absolute()),
        "trigger": "pre_installation_protection",
        "memcord_version": "unknown",
    }

    metadata_file = target_backup / "backup_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    return str(target_backup)


def display_warning(slot_count: int, total_size: int, slot_names: list[str]):
    """Display data loss warning to user."""
    size_mb = total_size / (1024 * 1024)

    print("🚨" * 50)
    print("🚨 CRITICAL DATA LOSS WARNING 🚨")
    print("🚨" * 50)
    print()
    print("EXISTING MEMORY DATA DETECTED:")
    print(f"  • {slot_count} memory slots found")
    print(f"  • Total size: {size_mb:.1f} MB")
    print(f"  • Slots: {', '.join(slot_names[:10])}")
    if len(slot_names) > 10:
        print(f"    ... and {len(slot_names) - 10} more")
    print()
    print("⚠️  DANGER: Installing/upgrading memcord may cause PERMANENT data loss!")
    print("⚠️  ALL your project history and session data could be destroyed!")
    print()


def display_protection_options():
    """Display data protection options."""
    print("🛡️  DATA PROTECTION OPTIONS:")
    print()
    print("1. AUTOMATIC BACKUP (RECOMMENDED)")
    print("   • This script will create a complete backup")
    print("   • Backup will be stored in 'emergency_backups' directory")
    print("   • You can restore manually if data is lost")
    print()
    print("2. MANUAL BACKUP")
    print("   • Copy the entire 'memory_slots' directory to a safe location")
    print("   • Example: cp -r memory_slots ~/backup_memory_slots_$(date +%Y%m%d)")
    print()
    print("3. EXPORT IMPORTANT SLOTS")
    print("   • Use memcord tools to export critical data:")
    print("   • memcord_export for individual slots")
    print("   • memcord_archive for long-term storage")
    print()


def display_recovery_instructions(backup_path: str):
    """Display recovery instructions."""
    print("🔧 RECOVERY INSTRUCTIONS (if data is lost):")
    print()
    print("1. AUTOMATIC RESTORE:")
    print(f"   cp -r {backup_path}/* memory_slots/")
    print()
    print("2. MANUAL RESTORE:")
    print(f"   • Your backup is located at: {backup_path}")
    print("   • Copy all files from backup to memory_slots directory")
    print("   • Restart memcord server")
    print()
    print("3. VERIFY RESTORATION:")
    print("   • Use memcord_list to verify all slots are restored")
    print("   • Check that data content is intact")
    print()


def main():
    parser = argparse.ArgumentParser(description="Protect memcord data before installation")
    parser.add_argument("--backup-only", action="store_true", help="Only create backup without warnings")
    parser.add_argument("--check-only", action="store_true", help="Only check for data without creating backup")
    parser.add_argument("--memory-dir", default="memory_slots", help="Memory slots directory (default: memory_slots)")
    parser.add_argument(
        "--backup-dir", default="emergency_backups", help="Backup directory (default: emergency_backups)"
    )
    parser.add_argument("--force", action="store_true", help="Force backup creation without user confirmation")

    args = parser.parse_args()

    print("🔍 Checking for existing memory data...")
    data_exists, slot_count, total_size, slot_names = detect_memory_data(args.memory_dir)

    if not data_exists:
        print("✅ No existing memory data found - installation should be safe.")
        print("ℹ️  You can proceed with installation normally.")
        return 0

    if args.check_only:
        print(f"📊 Found {slot_count} memory slots ({total_size / (1024 * 1024):.1f} MB)")
        print(f"📂 Location: {Path(args.memory_dir).absolute()}")
        print("⚠️  Data protection recommended before installation!")
        return 0

    if not args.backup_only:
        display_warning(slot_count, total_size, slot_names)
        display_protection_options()
        print()

    # Ask for user confirmation unless forced
    if not args.force and not args.backup_only:
        print("Do you want to create an automatic backup now? (recommended)")
        while True:
            choice = input("Enter [y]es, [n]o, or [c]ancel installation: ").lower().strip()
            if choice in ["y", "yes"]:
                break
            elif choice in ["n", "no"]:
                print("⚠️  Proceeding without backup - data loss risk remains!")
                print("🔧 Consider using memcord_export or memcord_archive tools instead.")
                return 1
            elif choice in ["c", "cancel"]:
                print("✋ Installation cancelled - your data is safe.")
                print("💡 Create backups when ready, then retry installation.")
                return 2
            else:
                print("Please enter 'y', 'n', or 'c'")

    # Create backup
    print("🛡️  Creating emergency backup...")
    try:
        backup_path = create_emergency_backup(args.memory_dir, args.backup_dir)
        print("✅ Backup created successfully!")
        print(f"📂 Backup location: {backup_path}")
        print()

        # Verify backup
        backup_data_exists, backup_slot_count, backup_size, _ = detect_memory_data(backup_path)
        if backup_data_exists and backup_slot_count == slot_count:
            print("✅ Backup verification passed - all data backed up correctly.")
        else:
            print("⚠️  Backup verification failed - please check manually!")
            return 3

        print()
        display_recovery_instructions(backup_path)

        if not args.backup_only:
            print("🚀 You can now proceed with memcord installation.")
            print("🛡️  Your data is protected and can be restored if needed.")

        return 0

    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        print("🚨 CRITICAL: Installation should NOT proceed without backup!")
        print("💡 Try manual backup: cp -r memory_slots ~/backup_memory_slots")
        return 4


if __name__ == "__main__":
    sys.exit(main())
