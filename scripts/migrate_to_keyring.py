#!/usr/bin/env python3
"""
Migration script to move CalDAV passwords from config file to system keyring.

This script:
1. Reads existing accounts from ~/.chronos/accounts.json
2. Stores each password in the system keyring
3. Removes password fields from the JSON file
4. Creates a backup before modifying

Usage:
    python scripts/migrate_to_keyring.py [--dry-run]
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from chronos_mcp.credentials import get_credential_manager
    from chronos_mcp.logging_config import setup_logging
except ImportError:
    print("Error: Could not import chronos_mcp modules.")
    print(
        "Make sure you're running this from the project root or have chronos_mcp installed."
    )
    sys.exit(1)

logger = setup_logging()


def create_backup(config_file: Path) -> Path:
    """Create a timestamped backup of the config file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = config_file.parent / f"accounts.json.backup_{timestamp}"
    shutil.copy2(config_file, backup_file)
    return backup_file


def migrate_passwords(dry_run: bool = False) -> int:
    """
    Migrate passwords from config file to keyring.

    Args:
        dry_run: If True, only show what would be done without making changes

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    config_dir = Path.home() / ".chronos"
    config_file = config_dir / "accounts.json"

    # Check if config file exists
    if not config_file.exists():
        print(f"No config file found at {config_file}")
        print("Nothing to migrate.")
        return 0

    # Get credential manager
    cred_manager = get_credential_manager()

    # Check keyring availability
    status = cred_manager.get_status()
    if not status["keyring_available"]:
        print("❌ Error: Keyring is not available on this system.")
        print("   Cannot migrate passwords to keyring.")
        print(f"   Status: {status}")
        return 1
    print(f"✓ Keyring available: {status['backend_type']}")
    print(f"  Backend: {status['backend']}")
    print(f"  Secure: {'Yes' if status['secure'] else 'No'}")
    print()

    # Load config file
    try:
        with open(config_file, "r") as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        return 1

    accounts = config_data.get("accounts", {})
    if not accounts:
        print("No accounts found in config file.")
        return 0

    print(f"Found {len(accounts)} account(s) to process:")
    print()

    # Process each account
    migrated_count = 0
    error_count = 0

    for alias, account_data in accounts.items():
        print(f"Processing account: {alias}")

        # Check if password exists in config
        password = account_data.get("password")
        if not password:
            print("  ⚠️  No password in config file")
            continue

        if dry_run:
            print(f"  🔍 Would migrate password ({len(password)} chars)")
            migrated_count += 1
        else:
            # Store password in keyring
            if cred_manager.set_password(alias, password):
                print("  ✓ Password migrated to keyring")
                migrated_count += 1

                # Verify it was stored correctly
                retrieved = cred_manager.get_password(alias)
                if retrieved != password:
                    print("  ❌ Verification failed - passwords don't match!")
                    error_count += 1
            else:
                print("  ❌ Failed to store password in keyring")
                error_count += 1

    print()

    if error_count > 0:
        print(f"❌ Errors occurred during migration: {error_count} account(s) failed")
        return 1

    if migrated_count == 0:
        print("No passwords to migrate.")
        return 0
    # Create backup and update config file
    if not dry_run and migrated_count > 0:
        print("Creating backup...")
        backup_file = create_backup(config_file)
        print(f"  ✓ Backup created: {backup_file}")

        # Remove passwords from config
        print("Updating config file...")
        for alias in accounts:
            if "password" in accounts[alias]:
                del accounts[alias]["password"]

        # Save updated config
        try:
            with open(config_file, "w") as f:
                json.dump(config_data, f, indent=2)
            print("  ✓ Config file updated (passwords removed)")
        except Exception as e:
            print(f"  ❌ Error updating config file: {e}")
            print(f"  Restore from backup: {backup_file}")
            return 1

    print()
    print(f"✅ Migration complete: {migrated_count} password(s) migrated")

    if dry_run:
        print()
        print("This was a dry run. Run without --dry-run to perform actual migration.")

    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate Chronos MCP passwords to system keyring"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    print("Chronos MCP Password Migration")
    print("=" * 40)
    print()

    exit_code = migrate_passwords(dry_run=args.dry_run)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
