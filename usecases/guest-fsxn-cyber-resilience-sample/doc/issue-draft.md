# Issue Draft: aws-samples/baseline-environment-on-aws-for-financial-services-institute

> Target: https://github.com/aws-samples/baseline-environment-on-aws-for-financial-services-institute/issues
> Status: Draft (pending review)

---

## Title

`[Feature Request] Add FSx for NetApp ONTAP cyber resilience use case with FISC compliance`

## Body

### Summary

I would like to propose a new guest system use case that demonstrates multi-layered cyber resilience using Amazon FSx for NetApp ONTAP's native data protection features, designed for financial institutions under FISC security guidelines.

### Business Problem

Financial institutions face sophisticated ransomware attacks where threat actors:
1. Compromise administrator credentials
2. Delete or encrypt backup data
3. Encrypt production data and demand ransom

Traditional backup strategies (AWS Backup alone) cannot defend against credential-compromised scenarios because administrators can delete backups. This use case provides **admin-proof data protection** where even a compromised `fsxadmin` cannot destroy protected data.

### Motivation

BLEA for FSI currently provides governance base and compliance frameworks, but lacks:
- Storage-level ransomware defense patterns
- Admin-credential-compromise scenarios
- ONTAP-native immutability (SnapLock, Tamperproof Snapshots)
- Multi-account air-gapped backup architecture
- Automated network isolation on threat detection

### Proposed Architecture

```
[Workload Account]
├── VPC (Multi-AZ, Isolated — no IGW/NAT)
│   └── FSx for NetApp ONTAP
│       ├── Production Volume + Tamperproof Snapshots (admin-undeletable)
│       ├── ARP/AI (autonomous ransomware detection, learning mode)
│       └── SnapLock Enterprise Volume (WORM, configurable retention)
├── AWS Backup → Cross-account copy to Data Banker
├── GuardDuty HIGH/CRITICAL → EventBridge → Lambda → NACL deny-all
└── CloudWatch Alarms (4) + SNS

[Data Banker Account]
├── Logically Air-gapped Backup Vault (Vault Lock, deny-delete policy)
└── AWS RAM Share → Restore Account

[Restore Account]
└── StepFunctions Automated Recovery (RTO < 4 hours)
```

### Key Design Decisions

- **Multi-account architecture** (Workload / Data Banker / Restore)
- **ONTAP Custom Resources** via CloudFormation Custom Resources backed by Lambda (for TPS, ARP configuration)
- **SnapLock Enterprise** with parameterized retention (1-7 years for FISC)
- **Network Isolation**: GuardDuty → EventBridge → Lambda → NACL (automated containment)
- **All IaC** — no manual Console operations required
- **ONTAP version requirements** documented (TPS 9.12+, ARP 9.13+, SnapLock 9.7+)

### FISC Security Standards Mapping

| FISC Standard | Countermeasure | Implementation |
|---------------|---------------|----------------|
| Practice 43 | Backup | Snapshot + AWS Backup + Air-gapped Vault |
| Practice 44 | Recovery | StepFunctions (RTO < 4h) |
| Practice 116 | Cyber attack defense | ARP/AI + GuardDuty + auto-isolation |
| Practice 117 | Data protection | TPS + SnapLock (WORM) |
| Practice 8 | Availability | Multi-AZ + automatic failover |

### Implementation Status

| Item | Status |
|---|---|
| CDK code complete (TypeScript strict, 3 stacks) | ✅ |
| 13 Jest tests passing | ✅ |
| Workload stack deployed and verified (49 resources, TPS/ARP/SnapLock/Backup/Isolation confirmed) | ✅ |
| Bilingual documentation with FISC mapping | ✅ |
| Cost estimates included (~$625/month) | ✅ |

### Checklist

- [x] TypeScript CDK v2 (aws-cdk-lib ^2.236.0)
- [x] Multi-account architecture (3 stacks)
- [x] parameter.ts with dev/prod configurations
- [x] Monitoring with CloudWatch + SNS (Chatbot optional)
- [x] Snapshot + assertion tests (13 tests)
- [x] FISC compliance mapping documented
- [x] Bilingual documentation (Japanese + English)
- [x] MIT-0 license compatible
- [x] No real account IDs or secrets in code
- [x] Deployment verified in real AWS account

### Related Resources

- [ONTAP Tamperproof Snapshots](https://docs.netapp.com/us-en/ontap/snaplock/snapshot-lock-concept.html)
- [ONTAP Autonomous Ransomware Protection](https://docs.netapp.com/us-en/ontap/anti-ransomware/index.html)
- [FSx for ONTAP SnapLock](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/snaplock.html)
- [AWS Backup Logically Air-gapped Vault](https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html)

### Next Steps

If maintainers are interested, I will submit a PR with the complete implementation.
