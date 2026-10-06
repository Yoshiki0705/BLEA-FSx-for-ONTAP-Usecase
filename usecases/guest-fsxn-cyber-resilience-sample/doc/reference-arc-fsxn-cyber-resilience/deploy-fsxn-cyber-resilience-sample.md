# CDK サンプルコード デプロイ手順 [FSx for ONTAP サイバーレジリエンス]

## 前提条件

- AWS CDK CLI >= 2.236.0
- Node.js >= 20.x
- 3 つの AWS アカウント（ワークロード / データバンカー / リストア）
- AWS CLI 認証情報（各アカウントの profile 設定済み）
- CDK Bootstrap 実施済み（各アカウント）

## 事前準備

### 1. Secrets Manager にFSx for ONTAP 管理パスワードを登録

ワークロードアカウントで実行:

```bash
aws secretsmanager create-secret \
  --name fsxn-cyber-resilience-admin \
  --secret-string '{"password":"YOUR_FSXADMIN_PASSWORD"}' \
  --region ap-northeast-1
```

> ⚠️ パスワードは十分な強度を確保してください（英大小文字 + 数字 + 特殊文字、12文字以上推奨）

### 2. parameter.ts の設定

`parameter.ts` を編集し、各環境に合わせた値を設定します:

```typescript
export const devParameter: AppParameter = {
  envName: 'Development',
  // 作成したシークレットの ARN を設定
  ontapSecretArn: 'arn:aws:secretsmanager:ap-northeast-1:<ACCOUNT_ID>:secret:<SECRET_NAME>',
  // 各アカウント ID を設定
  env: { account: '<WORKLOAD_ACCOUNT_ID>', region: 'ap-northeast-1' },
  dataBankerAccountId: '<DATA_BANKER_ACCOUNT_ID>',
  restoreAccountId: '<RESTORE_ACCOUNT_ID>',
  // ... 他のパラメータ
};
```

## デプロイ手順

### デプロイ順序（重要）

3つのスタックは以下の順序でデプロイしてください：

```
1. Data Banker → 2. Workload → 3. Restore
```

### Step 1: 依存パッケージインストール

```bash
cd usecases/guest-fsxn-cyber-resilience-sample
npm ci
```

### Step 2: ビルド・テスト確認

```bash
npx tsc --noEmit          # コンパイル確認
npx jest --no-coverage    # 13 テスト通過確認
npx cdk synth             # 3 スタック合成確認
```

### Step 3: Data Banker アカウントにデプロイ

```bash
npx cdk deploy Dev-FSxNCyberResilience-DataBanker \
  --profile data-banker \
  --require-approval never
```

デプロイ完了後、Vault ARN を確認:
```bash
aws backup describe-backup-vault \
  --backup-vault-name <vault-name> \
  --profile data-banker \
  --query 'BackupVaultArn' --output text
```

### Step 4: Workload アカウントにデプロイ

> ⚠️ `parameter.ts` の `dataBankerVaultArn` に Step 3 で取得した ARN を設定してください

```bash
npx cdk deploy Dev-FSxNCyberResilience-Workload \
  --profile workload \
  --require-approval never
```

デプロイ時間: 約 25-35 分（FSx for ONTAP 作成に時間がかかります）

### Step 5: Restore アカウントにデプロイ

```bash
npx cdk deploy Dev-FSxNCyberResilience-Restore \
  --profile restore \
  --require-approval never
```

### Step 6: SnapVault 有効化（オプション）

FSx for ONTAP が完全に AVAILABLE になった後、SnapVault レプリケーションを有効化:

```bash
# parameter.ts を編集
# enableSnapVault: true に変更

npx cdk deploy Dev-FSxNCyberResilience-Workload \
  --profile workload \
  --require-approval never
```

### Step 7: ARP learning → active 遷移（旧世代 ARP のみ）

この手順は旧世代 ARP（FlexVol は 9.10.1〜9.15.1）にだけ関係します。旧世代 ARP は NAS FlexVol で 30 日の学習期間を経てから active へ移り、9.13.1 以降は自動で切り替わります。FlexVol で 9.16.1 以降の ARP/AI には学習期間がなく、有効化した直後から保護するので、30 日待つ必要はありません。FlexGroup の境界と出典は [ARP の世代と学習期間（Hub ノート）](https://github.com/Yoshiki0705/FSx-for-ONTAP-Adoption-Playbook/blob/main/docs/ja/domains/data-protection/notes/snaplock-and-layered-ransomware-readiness.md) にあります（`documented`、このリポジトリでは実測していません）。

旧世代 ARP を手動で active モードへ移す場合:

```bash
# ONTAP REST API 経由
curl -X PATCH "https://management.<fs-id>.fsx.<region>.amazonaws.com/api/storage/volumes/<vol-uuid>" \
  -H "Content-Type: application/json" \
  -d '{"anti_ransomware": {"state": "active"}}' \
  -u "fsxadmin:<password>" -k
```

## デプロイ後の確認

### 基本確認

```bash
# スタック状態確認
aws cloudformation describe-stacks \
  --stack-name Dev-FSxNCyberResilience-Workload \
  --query 'Stacks[0].StackStatus'

# FSx for ONTAP 状態確認
aws fsx describe-file-systems \
  --query 'FileSystems[?Tags[?Value==`Dev-FSxNCyberResilience-Workload`]].[FileSystemId,Lifecycle]'

# アラーム状態確認
aws cloudwatch describe-alarms \
  --alarm-name-prefix "Dev-FSxNCyberResilience" \
  --query 'MetricAlarms[*].[AlarmName,StateValue]'
```

### TPS 確認

Lambda ログで TPS 設定成功を確認:
```bash
aws logs filter-log-events \
  --log-group-name <log-group-name> \
  --filter-pattern "ontap_cr_success" \
  --query 'events[*].message'
```

### ネットワーク隔離テスト

GuardDuty のテストイベントで隔離 Lambda が動作することを確認:
```bash
aws guardduty create-sample-findings \
  --detector-id <detector-id> \
  --finding-types "Recon:EC2/PortProbeUnprotectedPort"
```

## クリーンアップ

### 推奨: 共通クリーンアップスクリプト使用

```bash
# Workload スタック（FSx for ONTAP + VPC を含む）の完全クリーンアップ
bash shared/scripts/cleanup-fsxn-stack.sh Dev-FSxNCyberResilience-Workload ap-northeast-1

# Data Banker / Restore は通常の cdk destroy で削除可能
npx cdk destroy Dev-FSxNCyberResilience-Restore --profile restore
npx cdk destroy Dev-FSxNCyberResilience-DataBanker --profile data-banker
```

### 手動クリーンアップ（スクリプトが失敗した場合）

FSx for ONTAP は `RemovalPolicy.RETAIN` のため `cdk destroy` では削除されません。以下の順序で手動削除してください:

```bash
# 1. Volume 削除（SnapLock ボリュームも含む）
aws fsx delete-volume --volume-id <vol-id> \
  --ontap-configuration '{"SkipFinalBackup":true,"BypassSnaplockEnterpriseRetention":true}'

# 2. Volume 削除完了を待機（60-90秒）
aws fsx describe-volumes --volume-ids <vol-id>  # Lifecycle が消えるまで待機

# 3. SVM 削除
aws fsx delete-storage-virtual-machine --storage-virtual-machine-id <svm-id>

# 4. SVM 削除完了を待機（60-90秒）

# 5. FileSystem 削除
aws fsx delete-file-system --file-system-id <fs-id>

# 6. FS 削除完了を待機（20-30分）— VPC ENI が解放されるまで

# 7. CloudFormation スタック削除
aws cloudformation delete-stack --stack-name <name> --retain-resources <LogicalId1> <LogicalId2> ...

# 8. 孤立 VPC/Subnet 削除（FS 削除完了後）
aws ec2 delete-subnet --subnet-id <subnet-id>
aws ec2 delete-vpc --vpc-id <vpc-id>
```

> ⚠️ ONTAP のクラスターピアリング/SVM ピアリングは FSx for ONTAP 削除時に自動的に破棄されるため、明示的な解除は不要です。

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| SnapLock Volume 作成失敗 | `StorageEfficiencyEnabled` 未設定 | CDK コードを確認（自動設定済み） |
| SnapVault Lambda `fetch failed` | 管理エンドポイント DNS 未解決 | `enableSnapVault: false` で初回デプロイ後、2回目で有効化 |
| SVM 削除失敗（ROLLBACK時） | RETAIN ボリュームが存在 | 手動で Volume → SVM → FS の順に削除 |
| Backup Vault 名前衝突 | 前回のデプロイ残骸 | Vault を手動削除してからリデプロイ |
