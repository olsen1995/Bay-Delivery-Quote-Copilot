# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

## [1.1.0](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/compare/v1.0.6...v1.1.0) (2026-01-23)


### Features

* **api:** add FastAPI wrapper for ModeRouter endpoint ([5b29c8d](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/5b29c8d65f6177b2f82c774cf4a1d6c0816e0eb2))
* **api:** add openapi spec for /route endpoint ([7893290](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/78932903325a2802901d7dc41313a3f42545163c))
* **api:** serve GPT plugin manifest and ignore bytecode files ([2c86a7c](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/2c86a7c5139fb6ca29c8d9e81643ebc5f7b6643c))
* **router:** add detect_mode method to ModeRouter class ([7c54f59](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/7c54f59ded896cfdb73ab9248a8a5029cfca8a9a))


### Bug Fixes

* **api:** inject servers field for GPT plugin schema compatibility ([c62014e](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/c62014e0c7e696f5cbb41a539a9e5649cbf01b06))
* **ci:** correct paths to PowerShell scripts and GitHub release action ([558d5bd](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/558d5bd84e4ed5352f8a66fb4cc31a46386a3c07))
* **ci:** correct PowerShell script paths and release push logic ([a1d47ae](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/a1d47aeba51a9c0a5360ceec41b0b9395c188a98))
* **ci:** skip release if tag exists and make PS scripts optional ([b58485d](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/b58485d02dae420fa7627a1639c94a0a8377e17a))
* **manifest-lint:** correct Test-Path logic and key validations ([1da0c42](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/1da0c424261b5ae68ae583452732e60d5d37089f))
* **plugin:** separate ai-plugin.json and openapi.json into correct files ([8dc4f42](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/8dc4f42fdf2b207067e7a15ba7cdfacbb0f486c5))
* **plugin:** update ai-plugin.json with correct OpenAPI URL ([20555d9](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/20555d9b4ed41b62068892d695fddf2d0aceec8b))
* **router:** update main and mode_router to resolve detect_mode error ([aee0634](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/aee0634363a5e925e513dcea09b4a16dcebd5ec6))

### [1.0.6](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/compare/v1.0.5...v1.0.6) (2026-01-18)

### 1.0.5 (2026-01-18)

### 1.0.4 (2026-01-18)

### 1.0.3 (2026-01-18)

### 1.0.2 (2026-01-18)


### Bug Fixes

* **ci:** final release workflow with auth + identity ([d121e5f](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/commit/d121e5f93aa2dc241ff9d02205e85d75e8dd5467))

### [1.0.1](https://github.com/olsen1995/Life-OS-Private-Practical-Co-Pilot/compare/v0.2.0...v1.0.1) (2026-01-18)

# Changelog — Life OS Practical Co-Pilot

## [v0.1.3] - 2026-01-11 — Safety Guardrails

### Added in v0.1.3

- System Health Check guardrails document to reduce behavioral drift and define degraded safe-mode rules

---

## [v0.1.2] — Tier 2 Safety Polish

### Changed in v0.1.2

- Stop/Check, confidence, least-risk-first, and escalation rules

---

## [v0.1.1] — Release Discipline

### Added in v0.1.1

- VERSION, CHANGELOG, release process  
- ModeRouter_Cases.md introduced
