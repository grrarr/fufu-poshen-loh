"""pytest config: skip the policy hook's timestamped backups.

The hook's dbox_bak.backup() leaves `<name>.bak-<YYYY-MM-DDTHHMMZ>.py` next to an
edited file for a few hours; plain `pytest` here would try to import
`test_x.bak-....py` and stop at collection (ModuleNotFoundError). Added 2026-11-18.
Nothing else lives here - tests behave exactly as before.
"""
collect_ignore_glob = ["*.bak-*"]
