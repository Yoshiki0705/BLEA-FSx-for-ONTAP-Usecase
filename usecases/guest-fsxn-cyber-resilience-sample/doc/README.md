# BLEA for FSI: FSx for ONTAP Cyber Resilience Sample

## Overview

A multi-layered cyber resilience solution leveraging Amazon FSx for NetApp ONTAP native security features. Protects data against ransomware attacks even when administrator accounts are compromised.

## Architecture

```
[Workload Account]
├── VPC (Multi-AZ, Private Subnets)
│   └── FSx for NetApp ONTAP
│       ├── Production Volume
│       │   ├── Tamperproof Snapshot (undeletable even by admins)
│       │   ├── ARP/AI (automatic ransomware detection)
│       │   └── Storage Efficiency
│       └── SnapLock Enterprise Volume (WORM)
├── AWS Backup → Air-gapped Vault (separate account)
├── GuardDuty → Automatic Network Isolation
└── CloudWatch Alarms + SNS

[Data Banker Account]
├── Logically Air-gapped Vault (Vault Lock)
└── RAM Share → Restore Account

[Restore Account]
└── StepFunctions Automated Recovery Workflow (RTO < 4 hours)
```

## Defense Layers

| Layer | Capability | Implementation |
|-------|-----------|----------------|
| Detection | Automatic ransomware detection | ARP/AI (ONTAP Custom Resource) |
| Protection | Admin-proof snapshots | Tamperproof Snapshot (TPS) |
| Protection | WORM backup | SnapLock Enterprise Volume |
| Isolation | Logical backup isolation | Air-gapped Vault (separate account) |
| Response | Automatic network containment | GuardDuty → Lambda → NACL |
| Recovery | Automated restore | StepFunctions (within 4 hours) |

## Prerequisites

1. AWS CDK CLI + Node.js >= 20.x
2. 3 AWS accounts (Workload / Data Banker / Restore)
3. **FSx for ONTAP admin password stored in Secrets Manager**:
   ```bash
   aws secretsmanager create-secret \
     --name fsxn-admin-password \
     --secret-string '{"password":"YOUR_FSXADMIN_PASSWORD"}'
   ```
4. ONTAP version requirements:
   - Tamperproof Snapshot (TPS): ONTAP 9.12+
   - ARP: the running model and its learning period depend on the ONTAP version and the volume type. On FlexVol, 9.16.1 and later run ARP/AI with no learning period; 9.10.1–9.15.1 run the earlier ARP, which has a 30-day learning period on NAS FlexVol (details below)
   - SnapLock Enterprise: ONTAP 9.7+

### ARP Learning → Active Transition

Whether this transition applies depends on which ARP generation is running.

- Earlier ARP (FlexVol 9.10.1–9.15.1, FlexGroup 9.13.1–9.17.1): 30-day learning period on NAS FlexVol. From 9.13.1 it switches to active automatically
- ARP/AI (FlexVol 9.16.1 and later, FlexGroup 9.18.1 and later): no learning period; protection starts as soon as it is enabled. There is no 30-day wait

The version and volume-type boundaries and their sources are in [ARP generations and learning periods (Hub note, Japanese)](https://github.com/Yoshiki0705/FSx-for-ONTAP-Adoption-Playbook/blob/main/docs/ja/domains/data-protection/notes/snaplock-and-layered-ransomware-readiness.md). They are `documented`, not measured in this repository. Check the running model with the `version` field of `security anti-ransomware`.

To move the earlier ARP to active mode manually after its learning period:

```bash
# ONTAP CLI (SSH or System Manager)
security anti-ransomware volume enable -volume vol_production -vserver svm-resilience
```

Or via ONTAP REST API:
```bash
curl -X PATCH "https://<mgmt-endpoint>/api/storage/volumes/<vol-uuid>" \
  -H "Content-Type: application/json" \
  -d '{"anti_ransomware": {"state": "active"}}' \
  -u "fsxadmin:<password>"
```

## Deployment

### Deployment Order (Important)

1. **Data Banker Account** → Create Air-gapped Vault
2. **Workload Account** → FSx for ONTAP + TPS + ARP + Backup
3. **Restore Account** → StepFunctions workflow

```bash
# 1. Data Banker
npx cdk deploy Dev-FSxNCyberResilience-DataBanker --profile data-banker

# 2. Workload (set Data Banker Vault ARN in parameter.ts first)
npx cdk deploy Dev-FSxNCyberResilience-Workload --profile workload

# 3. Restore
npx cdk deploy Dev-FSxNCyberResilience-Restore --profile restore
```

## FISC Security Standards Mapping

| Standard | Countermeasure | Implementation |
|----------|---------------|----------------|
| Practice 43 | Backup | Snapshot + AWS Backup + Air-gapped Vault |
| Practice 44 | Recovery | StepFunctions automated restore (RTO < 4h) |
| Practice 116 | Cyber attack defense | ARP/AI + GuardDuty + automatic isolation |
| Practice 117 | Data protection | TPS (admin-undeletable) + SnapLock (WORM) |
| Practice 8 | Availability | Multi-AZ + automatic failover |

## Cost Estimate

| Component | Monthly Cost (USD) |
|-----------|-------------------|
| Workload (Multi-AZ, 128MBps, 1TiB + SnapLock 50GiB) | ~$600 |
| Data Banker (Backup Vault storage) | ~$25/TiB |
| Restore (standby: StepFunctions only) | < $1 |

## License

MIT-0
