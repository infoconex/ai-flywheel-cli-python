# Tool Usage

Use tools according to the active goal, repository constraints, and human authority.

## General Rules

- Prefer deterministic tools for repeatable actions and validation.
- Use AI reasoning for interpretation, planning, classification, and adaptation where deterministic rules are insufficient.
- Record commands, material inputs, outputs, failures, and resulting evidence.
- Do not introduce a runtime, dependency, hosted service, or automation platform without authorization.
- Do not enable GitHub Actions or other billed or externally executing services unless explicitly approved.
- Treat destructive operations, production access, credential use, releases, merges, and external communications as approval-sensitive unless governance explicitly permits them.

## Flywheel Tool Independence

The technology used for Flywheel operating tools is selected independently from the target repository's application stack. Existing repository technologies are evidence and possible options, not automatic defaults.

## Bootstrap Operation

Before repository-specific Flywheel tools exist, the AI operator may maintain `.flywheel` artifacts directly. Once the minimum tools are validated, use them to operate the remainder of the bootstrap mission and future missions.
