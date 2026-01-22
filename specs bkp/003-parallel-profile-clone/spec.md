# Feature Specification: Parallel Default Profile Loading & Cloning for Multiple Windows

Feature Branch: [003-parallel-profile-clone]
Created: 2025-09-29
Status: Draft
Input: User description: "additional fix to asynchronous processing in the subproject EXPERIMENTAL; the parallel system works, but the default profile should load correctly for all instances. there should be a verification to make sure it loads. currently 3 windows are opened and none has the default profile active on it. Approach: load window A with default profile (as in single worker). then window B loads with a perfect temporary copy of default profile and window C loads with another perfect copy of the default profile. Need tests with real multiple windows loading with default profile and its clones."

## Execution Flow (main)
```
1. Parse user description
   → Actors: system, parallel workers/windows, default Edge profile, cloned profiles
   → Actions: load default profile in window A; clone source profile for windows B and C; verify each window truly uses the intended profile
   → Data: profile location(s), verification signals, number of windows
   → Constraints: parallel workers must not corrupt or lock the base profile; cloning must be consistent and fast
2. Identify ambiguities
   → Source profile definition and location
   → Verification method(s) acceptable as proof of correct profile load
   → Handling profile locks and concurrent cloning
3. Define user scenarios and acceptance tests
4. Generate functional requirements (testable, unambiguous)
5. Identify key entities
6. Review for non-technical clarity and testability
```

---

## User Scenarios & Testing (mandatory)

### Primary User Story
As an operator running the EXPERIMENTAL parallel downloader, I want every browser window to start with the expected user context so that cookies, sessions, and Coupa access behave exactly as when running a single window with the default profile.

### Acceptance Scenarios
1. Given the operator sets N parallel workers (N ≥ 1), When the system starts the first window (A), Then it must load the configured default Edge profile and confirm it is active before proceeding.
2. Given N workers are configured, When windows B..N start, Then each must use a faithful temporary clone of the default profile (1 profile instance per worker) and confirm the clone is active.
3. Given all N windows are running, When each navigates to a verification target (e.g., a Coupa page requiring an authenticated cookie), Then the session appears authenticated in all windows without an additional login prompt.
4. Given profile instances are per-worker, When any window terminates, Then its temporary cloned profile directory is removed without affecting other windows or the base profile.
5. Given per-worker verification is required, When verification fails for a specific worker k, Then the system must diagnose and attempt remediation for worker k only (retry/reload/restart with a fresh clone), without restarting or pausing other workers; results are recorded.
6. Given real multiple windows (N ≥ 3), When the test run exercises actual browser instances concurrently, Then verification and per-worker remediation behave as specified and do not cross-impact unrelated workers.

### Edge Cases
- Base profile is locked or in use by another program: the system must detect and wait or provide a clear error flow.
- Partial profile clone (interrupted copy) results in missing state: verification must catch this, triggering a controlled retry with backoff.
- Profile path misconfigured: system must fail fast with a clear message and no workers launched.
- High concurrency (>= 6 windows): cloning time increases; system must queue or throttle clones to avoid disk thrash and lock contention while still meeting startup SLAs.
- Mixed headless/visible mode: verification method must work consistently in both modes.
- Different OS user accounts or sandboxed environments: ensure paths and permissions are handled or surfaced clearly.

---

## Requirements (mandatory)

### Functional Requirements
- FR-001: The system MUST start the first window (A) using the configured default Edge profile path.
- FR-002: The system MUST start subsequent windows (B, C, …) using isolated temporary clones of the default profile, each per window.
- FR-003: The system MUST verify that the intended profile (default or clone) is actually active for each window before proceeding with downloads.
- FR-004: On verification failure, the system MUST perform a configurable retry sequence (at least one retry) and report detailed diagnostics for that window.
- FR-005: The system MUST clean up temporary cloned profile directories after each window exits, without altering or deleting the base profile.
- FR-006: The system MUST prevent concurrent access to the base profile by more than one running window; only window A may attach to the base profile at a time.
- FR-007: The system MUST ensure cloned profiles are byte-consistent with the base profile for key state artifacts required for authentication and site behavior.
- FR-008: The system MUST produce an operator-facing summary indicating for each window which profile was used and whether verification succeeded.
- FR-009: The system MUST allow configuration of the verification strategy and retry counts (with best-practices defaults), and MUST set maximum concurrent clones equal to the number of user-defined workers (N). Note: For this release, the base profile path remains fixed as currently defined in the project; external configuration will be evaluated for future iterations.
- FR-010: The system MUST support both visible and headless modes with the same verification guarantees.

- FR-011: The operator MUST be able to define the number of parallel workers (N); the system SHALL create exactly one profile instance per worker (total profile instances = N).
- FR-012: The first worker SHOULD use the configured default profile (policy default), and the remaining (N-1) workers MUST use temporary cloned profiles; [NEEDS CLARIFICATION: allow policy to force "all clones" to protect base profile?].
- FR-013: The system MUST perform per-worker verification; upon failure for worker k, it MUST attempt remediation targeting only worker k (diagnose → retry verification → re-clone → reload → restart), using a bounded, configurable retry policy.
- FR-014: The system MUST NOT restart, pause, or otherwise disrupt other workers when one worker undergoes remediation.
- FR-015: The system MUST expose per-worker verification and remediation results (success/failure, attempts, timings) in an operator-facing summary/logs.
- FR-016: The system MUST allow throttling or queueing of clone creation when N is large to avoid lock contention and disk thrashing, while meeting startup SLAs.

### Non-Functional Requirements
- NFR-001: Cloning overhead SHOULD not add more than a configurable threshold (e.g., < 5 seconds per clone on SSD) under typical conditions.
- NFR-002: The process SHOULD be resilient to transient file-system errors; retries/backoff SHOULD be applied.
- NFR-003: The approach SHOULD avoid corrupting the base profile; no write operations SHOULD occur on the base profile by cloned instances.
- NFR-004: Logs SHOULD clearly attribute verification and cloning events per window/worker for diagnostics.

- NFR-005: Per-worker remediation SHOULD complete within a bounded time budget (configurable) and SHOULD minimize impact on throughput of other workers.
- NFR-006: Startup SHOULD scale to higher N via controlled clone concurrency and SHOULD surface progress/diagnostics when clone backpressure occurs.
- NFR-007: Disk footprint for cloned profiles SHOULD be managed (e.g., temporary storage), with prompt cleanup on worker exit or failure.

### Verification Methods
- VM-001: Cookie presence and session check at a known authenticated endpoint (e.g., a lightweight Coupa page) without redirect to login.
- VM-002: Browser-level introspection signals (e.g., profile directory path reported by driver capabilities) matching the intended path (base for A, distinct cloned path for B/C).
- VM-003: Optional file signature checksum of critical profile artifacts (e.g., SQLite cookie db, Local State) between base and clone immediately after clone completes.

### Key Entities
- Default Profile: The operator-configured Edge profile directory containing cookies and session state.
- Profile Clone: A per-window temporary directory created as a faithful copy of the Default Profile for isolated usage.
- Profile Verification Report: Structured record per window containing verification steps, results, timings, and any retry attempts.

---

## Review & Acceptance Checklist

Content Quality
- [x] No implementation details (kept at behavior-level; no APIs or code)
- [x] Focused on user value and outcomes
- [x] Written for non-technical stakeholders
- [x] Mandatory sections completed

Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Ambiguities / Needs Clarification
- NC-001: What exact path constitutes the “default Edge profile” on the target environment(s)? Is it fixed via configuration or auto-detected? Confirm expected macOS and Windows paths.
- NC-002: Which verification method(s) are acceptable as proof (VM-001, VM-002, VM-003)? Any environment where VM-001 (auth check) isn’t possible?
- NC-003: Desired per-worker retry policy for verification failures (max attempts, backoff), and the remediation sequence ordering (retry vs re-clone vs restart)?
- NC-004: Maximum number of parallel windows expected in production (impacts cloning throttle).
- NC-005: Any constraints for OS portability (macOS vs Windows) that change the default profile location rules?
- NC-006: Confirm policy preference for first worker using the base profile vs forcing all workers to use clones (trade-off: protect base profile vs fastest startup).
