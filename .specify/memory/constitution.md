<!--
Sync Impact Report:
- Version change: Initial creation → v1.0.0  
- New constitution establishing foundational governance for CoupaDownloads automation
- Added sections: Core Principles (5), Development Workflow, Security Requirements, Governance
- Templates requiring updates: ✅ aligned with existing .specify templates
- Follow-up TODOs: None - all placeholders filled with concrete values
-->

# CoupaDownloads Constitution

## Core Principles

### I. Documentation-Driven Development
Every change MUST follow the Proposal → Design → Implementation → Report workflow documented in AGENTS.md; Architecture decisions MUST be captured in ADRs when they have lasting impact; Documentation MUST be bilingual (Portuguese for users, English for technical interfaces) to serve enterprise stakeholders effectively.

### II. Automation Reliability  
Core automation workflows MUST be deterministic, resumable, and fail-safe; Browser automation MUST handle network interruptions, authentication timeouts, and session failures gracefully without corrupting data or requiring manual intervention; Configuration changes MUST be propagated consistently across all execution modes (sequential, process pool, headless/visible).

### III. Security by Design (NON-NEGOTIABLE)
Credentials MUST never be committed to version control; Sensitive data MUST be handled through environment variables or secure configuration; Browser automation MUST respect corporate security policies and profile isolation; PII MUST be masked in logs and external communications.

### IV. Human-in-the-Loop Validation
Critical business decisions (PO validation, contract interpretation, field extraction) MUST provide human review workflows with clear approval/rejection paths; AI predictions MUST be marked with confidence scores; Procurement processes MUST maintain complete audit trails for compliance requirements.

### V. Quality Assurance Standards
Code MUST follow PEP 8 with type hints; Test coverage MUST exist for critical paths with `poetry run pytest`; Browser automation changes MUST be validated through complete end-to-end flows; Breaking changes to public contracts (CLI interfaces, data schemas) MUST be explicitly reviewed.

## Security Requirements

Procurement data protection policies: No credentials in repository; Use `storage/` only for local artifacts ignored by Git; Downloads of external binaries require approved Design Documents; Standard logs MUST avoid supplier names and PO numbers (use masking).

## Development Workflow  

Branch naming: `feature/<descriptor>` or `fix/<ticket>`; Commit messages MUST be descriptive and ≤72 characters; Completed work artifacts move to `PR_PLANS/Implemented/`; Subprojects (EXPERIMENTAL/, tools/) MAY have local AGENTS.md files that take precedence for their scope.

## Governance

This constitution supersedes conflicting practices in AGENTS.md or other guidance documents; Amendments require documented rationale and impact assessment; All feature specifications MUST pass constitutional compliance checks before implementation; Use AGENTS.md for detailed runtime development guidance that doesn't conflict with these principles.

**Version**: 1.0.0 | **Ratified**: 2025-01-15 | **Last Amended**: 2025-09-29