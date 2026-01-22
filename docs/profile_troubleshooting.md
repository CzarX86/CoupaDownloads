# Profile Troubleshooting Guide

This guide helps diagnose issues with profile cloning, verification, and cleanup.

- Clone failures
  - Check base path permissions and existence
  - See warnings for skipped items or timeout messages
  - Circuit breaker may open after repeated failures (wait recovery window)

- Verification failures
  - Ensure verification methods are enabled and properly configured
  - For now, tests patch `verify_profile`; real implementation pending in Phase 3.3

- Cleanup issues on macOS/Windows
  - Some files can be locked briefly; the manager retries removal
  - If breaker open, manager still attempts best-effort cleanup

- Disk usage growth
  - Use `get_status()` on WorkerPool for `profile_metrics`
  - Consider increasing cleanup frequency or reducing cloned items

- Reporting
  - Enable verbose logs when investigating persistent issues
