# Codex Config Guardrails

Bay Delivery Codex work should use the repo project config for generic safety defaults only.

- Keep user-level Codex config local to each machine.
- Keep `.codex/config.toml` generic and portable.
- Do not commit machine-specific absolute paths, local writable roots, or per-user project entries.
- Use `approval_policy = "on-request"`, `sandbox_mode = "workspace-write"`, and `network_access = false` for Bay Delivery repo work.
- Do not use `danger-full-access` for routine Bay Delivery implementation.
