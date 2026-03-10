# Profiles Guide

HandsFree supports context-aware profiles that tune response style and safety behavior.

Source of truth for profile behavior:
- `src/handsfree/commands/profiles.py`

## Supported Profiles

- `default`
- `workout`
- `kitchen`
- `commute`
- `focused`
- `relaxed`

## What Profiles Change

Each profile controls:

- spoken response length (`max_spoken_words`)
- summary length (`max_summary_sentences`)
- inbox item cap (`max_inbox_items`)
- detail level (`minimal`, `brief`, `moderate`, `detailed`)
- speech rate multiplier
- whether extra confirmation is required
- privacy mode default

## Practical Defaults

- `workout`: shortest responses, stricter confirmations, top priority items only
- `kitchen`: moderate detail, slower speech rate for noisy environments
- `commute`: concise responses with fewer interruptions
- `focused`: actionable-first filtering and minimal verbosity
- `relaxed`: highest detail and largest inbox window
- `default`: balanced behavior for day-to-day use

## Mobile App Usage

The mobile app exposes profile selection through the profile selector UI.

Relevant client files:
- `mobile/src/components/ProfileSelector.js`
- `mobile/src/storage/profileStorage.js`

## Notes

- Profile behavior is deterministic and enforced server-side.
- New profiles should be added in both backend profile config and mobile selector storage.
