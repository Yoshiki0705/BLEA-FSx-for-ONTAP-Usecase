# AGENTS.md

> BLEA guest system use case: Amazon FSx for NetApp ONTAP enterprise file storage with data analytics and AI

## Project Overview

CDK templates for BLEA that provide enterprise file storage (FSx for ONTAP) with S3 Access Point integration for AWS analytics (Athena, Glue) and AI services (Bedrock, SageMaker). Intended for upstream contribution to `aws-samples/baseline-environment-on-aws`.

## Build & Test Commands

```bash
npm ci          # Install dependencies
npm run build   # TypeScript compilation
npm test        # Jest unit tests
npx aws-cdk synth --app 'npx ts-node bin/blea-guest-fsxn-data-analytics-sample.ts'  # CDK synth
```

## Coding Conventions

- TypeScript strict mode
- AWS CDK v2 (aws-cdk-lib)
- Jest for testing (snapshot + assertion)
- Follow BLEA existing patterns exactly
- parameter.ts for deployment configuration

## Supply-Chain Security

- All third-party Actions pinned to SHA
- gitleaks for secret detection
- zizmor for workflow security
- `.githooks/pre-commit` for local checks

## Common Pitfalls

| Pitfall | Root Cause | Solution |
|---------|-----------|----------|
| AgentCore Gateway assumed us-east-1 only | Workshop examples default to us-east-1 | **ap-northeast-1 で利用可能（検証済み 2026-07）**。CDK で Gateway + Lambda を同一リージョンに合成すること |
| `create-gateway-target` で Lambda not found | Gateway と Lambda のリージョン不一致 | 同一リージョン配置必須。クロスリージョン Lambda 呼び出しは不可 |

## Agent Output Standards

> Mirror of Kiro global steering rules. Ensures compliance even when steering is not loaded.

> CI: `.github/workflows/agent-output-audit.yml` (naming / neutrality / leak / parity) and `gitleaks.yml` (secrets).

### Naming (NetApp / AWS)

- First mention uses **Amazon FSx for NetApp ONTAP**, thereafter **FSx for ONTAP**. `FSxN` / bare `FSx` / `FSx ONTAP` are forbidden.
- S3 Access Point: **FSx for ONTAP S3 AP** (not "FSx S3 AP", not bare "S3 AP" when FSx-for-ONTAP context matters).
- Do NOT propose: NetApp Workload Factory / NetApp Console / BlueXP. Use native equivalents (CloudWatch, ONTAP REST API, FabricPool, AWS DataSync, Snapshot/FlexClone/SnapMirror).
- Exception: verbatim external citation titles — annotate the line with `<!-- allow:naming -->`.

### Vendor neutrality (right-tool-for-the-job)

- No vendor-versus / superiority framing: "best", "beats X", "X より優れている", "競合ツール", "優位性", "game-changer" are prohibited.
- Present alternatives as options suited to different contexts with symmetric trade-offs (recommended option's constraints included).

### Public-output safety

- Never commit: personal names / persona names, emails, AWS account IDs, internal IPs/hostnames, support case numbers, vendor-internal ticket IDs.
- Use role-based references: "Storage Specialist lens", "Partner SA feedback", "an internal product request (tracked)".
- No process-metadata noise in public docs: "Persona Review Summary", review rounds/dates/lens counts, `R1/F2/EXT/Round` tags. Weave findings inline as role-based lens notes (`> **Topic** (Role lens): ...`); relocate provenance to `.private/` (gitignored).

### Bilingual docs (JA primary + EN)

- JA/EN parity: matching section structure/count and equivalent inline notes.
- When one language version is modified, apply the same change to the other in the same commit.

### Technical reference / guide docs

- Required elements: executive summary with conclusion, FAQ/common misconceptions, selection flowchart (mermaid OK), OT/IT security considerations (when applicable), staged adoption steps, Related Documents (back-links), ≥10 inline role-based lens reviews.

### Before committing docs

```bash
gitleaks detect --config .gitleaks.toml --no-git --source .
# CI mirrors agent-output checks: .github/workflows/agent-output-audit.yml
```
