# BLEA for FSI: FSx for ONTAP サイバーレジリエンス サンプル

## 概要

Amazon FSx for NetApp ONTAP のネイティブセキュリティ機能を活用した、多層防御のサイバーレジリエンスソリューションです。ランサムウェア攻撃に対して、管理者アカウントが侵害された場合でもデータを保護します。

## アーキテクチャ

```
[ワークロードアカウント]
├── VPC (Multi-AZ, プライベートサブネット)
│   └── FSx for NetApp ONTAP
│       ├── 本番ボリューム
│       │   ├── Tamperproof Snapshot (管理者でも削除不可)
│       │   ├── ARP/AI (ランサムウェア自動検知)
│       │   └── ストレージ効率化
│       └── SnapLock Enterprise ボリューム (WORM)
├── AWS Backup → Air-gapped Vault (別アカウント)
├── GuardDuty → 自動ネットワーク隔離
└── CloudWatch アラーム + SNS

[データバンカーアカウント]
├── Logically Air-gapped Vault (Vault Lock)
└── RAM 共有 → リストアアカウント

[リストアアカウント]
└── StepFunctions 自動復旧ワークフロー (RTO < 4時間)
```

## 防御レイヤー

| レイヤー | 機能 | 実装 |
|---------|------|------|
| 検知 | ランサムウェア自動検知 | ARP/AI (ONTAP Custom Resource) |
| 保護 | 管理者でも削除不可な Snapshot | Tamperproof Snapshot (TPS) |
| 保護 | WORM バックアップ | SnapLock Enterprise Volume |
| 隔離 | バックアップの論理的隔離 | Air-gapped Vault (別アカウント) |
| 対応 | 自動ネットワーク遮断 | GuardDuty → Lambda → NACL |
| 復旧 | 自動リストア | StepFunctions (4時間以内) |

## 前提条件

1. AWS CDK CLI + Node.js >= 20.x
2. 3つの AWS アカウント（ワークロード / データバンカー / リストア）
3. **FSx for ONTAP 管理パスワードを Secrets Manager に事前登録**:
   ```bash
   aws secretsmanager create-secret \
     --name fsxn-admin-password \
     --secret-string '{"password":"YOUR_FSXADMIN_PASSWORD"}'
   ```
4. ONTAP バージョン要件:
   - Tamperproof Snapshot (TPS): ONTAP 9.12+
   - ARP: 稼働するモデルと学習期間は ONTAP の版とボリューム種別で決まります。FlexVol では 9.16.1 以降が ARP/AI で学習期間はなく、9.10.1〜9.15.1 は旧世代 ARP で、NAS FlexVol に 30 日の学習期間があります（詳細は下記）
   - SnapLock Enterprise: ONTAP 9.7+

### ARP learning → active 遷移手順

この遷移が要るかどうかは、稼働している ARP の世代で決まります。

- 旧世代 ARP（FlexVol は 9.10.1〜9.15.1、FlexGroup は 9.13.1〜9.17.1）: NAS FlexVol で 30 日の学習期間があります。9.13.1 以降はアクティブへ自動で切り替わります
- ARP/AI（FlexVol は 9.16.1 以降、FlexGroup は 9.18.1 以降）: 学習期間はなく、有効化した直後から保護します。30 日待つ必要はありません

版とボリューム種別による違いと出典は [ARP の世代と学習期間（Hub ノート）](https://github.com/Yoshiki0705/FSx-for-ONTAP-Adoption-Playbook/blob/main/docs/ja/domains/data-protection/notes/snaplock-and-layered-ransomware-readiness.md) にあります。区分は `documented` で、このリポジトリでは実測していません。稼働中のモデルは `security anti-ransomware` の `version` で確認できます。

旧世代 ARP で学習期間の後に手動で active モードへ移す場合は、次のコマンドを使います:

```bash
# ONTAP CLI (SSH or System Manager)
security anti-ransomware volume enable -volume vol_production -vserver svm-resilience
```

または ONTAP REST API:
```bash
curl -X PATCH "https://<mgmt-endpoint>/api/storage/volumes/<vol-uuid>" \
  -H "Content-Type: application/json" \
  -d '{"anti_ransomware": {"state": "active"}}' \
  -u "fsxadmin:<password>"
```

## デプロイ手順

### デプロイ順序（重要）

1. **Data Banker アカウント** → Air-gapped Vault 作成
2. **Workload アカウント** → FSx for ONTAP + TPS + ARP + Backup
3. **Restore アカウント** → StepFunctions ワークフロー

```bash
# 1. Data Banker
npx cdk deploy Dev-FSxNCyberResilience-DataBanker --profile data-banker

# 2. Workload (parameter.ts に Data Banker Vault ARN を設定後)
npx cdk deploy Dev-FSxNCyberResilience-Workload --profile workload

# 3. Restore
npx cdk deploy Dev-FSxNCyberResilience-Restore --profile restore
```

## FISC 安全対策基準マッピング

| 基準 | 対策 | 実装 |
|------|------|------|
| 実43 | バックアップ | Snapshot + AWS Backup + Air-gapped Vault |
| 実44 | 復旧 | StepFunctions 自動リストア (RTO < 4h) |
| 実116 | サイバー攻撃対策 | ARP/AI + GuardDuty + 自動隔離 |
| 実117 | データ保護 | TPS (管理者削除不可) + SnapLock (WORM) |
| 実8 | 可用性 | Multi-AZ + 自動フェイルオーバー |

## コスト見積もり

| 構成 | 月額概算 (USD) |
|------|-------------|
| Workload (Multi-AZ, 128MBps, 1TiB + SnapLock 50GiB) | ~$600 |
| Data Banker (Backup Vault storage) | ~$25/TiB |
| Restore (待機: StepFunctions のみ) | < $1 |

## ライセンス

MIT-0
