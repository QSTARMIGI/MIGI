# Security Policy

## Supported Scope

Security reports are welcome for the MIGI repository and its documented core boundaries, especially:

- receipt integrity and ChainLog tampering;
- authorization bypasses in LUFITGuard or Tre Logic handling;
- identity, key-management, and device-signing flaws;
- exposure of sensitive capture data or secrets;
- unsafe task routing or tool-permission escalation;
- replay, audit, and provenance failures;
- mobile edge-storage or transport weaknesses.

## Reporting a Vulnerability

Please do not post unpatched vulnerabilities in public issues.

Send a private report to **security@qstarmigi.com** with:

1. a clear description of the issue;
2. affected repository path, version, or commit;
3. steps to reproduce or a proof of concept;
4. impact assessment;
5. suggested remediation, if available.

Do not include real user data, private keys, access tokens, or sensitive production information in the report.

## Response Goals

MIGI is currently an architecture-and-MVP project. Reports will be triaged in good faith, but no service-level response time is guaranteed. The initial goals are:

```text
Acknowledgment → assessment → containment → fix or mitigation → documented resolution
```

## Secure Development Expectations

- Keep secrets out of commits, logs, and receipts.
- Use platform keystores or dedicated secret stores for signing material.
- Minimize collection and retention of source data.
- Separate original evidence from generated or derived outputs.
- Require explicit authority before consequential external actions.
- Treat simulation outputs as non-authoritative unless independently verified.
- Preserve auditability without exposing private content.

## Out of Scope

The following are generally out of scope unless they directly affect MIGI-maintained changes:

- vulnerabilities solely in upstream dependencies or mirrors that have not been modified by MIGI;
- unsupported research concepts with no executable implementation;
- social engineering attacks against third parties;
- findings requiring unauthorized access to accounts or systems.
