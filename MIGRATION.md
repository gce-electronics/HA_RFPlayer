# Schema migration: 1.1 → 1.2

## Summary

Release 1.3 bumps integration schema version from minor version 1.1 to 1.2. The key change is a migration of device entity unique identifier to a slugified format (hyphens removed). The migration will update config entries and the device registry handling so the integration uses the new ID format going forward.

## What changed

- Device entity unique id format is now slugified (no hyphens). Old-style IDs containing hyphens are considered legacy and will be migrated.
- If migrations fails the device entities may be duplicated.
- Config entry migration increments the stored minor version to 1.2.

## User impact / breaking changes

- If migrations fails the device entities may be duplicated.
- ID migration may conflict with an existing entity.

## Developer notes

- The migration logic is implemented in `custom_components/rfplayer/migration.py`.

## Rollback / recovery

- If the migration causes unexpected device loss, restore from a backup.
