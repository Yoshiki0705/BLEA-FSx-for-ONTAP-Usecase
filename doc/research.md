# BLEA FSx for ONTAP ユースケース 調査レポート

> 作成日: 2026-06-02
> ステータス: 調査完了

---

## 1. BLEA コードベース分析サマリー

### 1.1 リポジトリ概要

| 項目 | 値 |
|------|-----|
| リポジトリ | [aws-samples/baseline-environment-on-aws](https://github.com/aws-samples/baseline-environment-on-aws) |
| 最新リリース | v3.1.0 (2025-10-07) |
| ライセンス | MIT-0 |
| 言語 | TypeScript 97.2% |
| Node.js | >= 18.0.0 (22 推奨) |
| CDK | aws-cdk-lib ^2.219.0 |
| コントリビューター | 23名 |

### 1.2 ディレクトリ構成

```
baseline-environment-on-aws/
├── .github/
├── .vscode/
├── doc/                          # ドキュメント（画像含む）
├── usecases/
│   ├── blea-gov-base-standalone/     # ガバナンスベース（スタンドアロン）
│   ├── blea-gov-base-ct/             # ガバナンスベース（Control Tower）
│   ├── blea-guest-ecs-app-sample/    # ECS Web アプリ
│   ├── blea-guest-ec2-app-sample/    # EC2 Web アプリ
│   └── blea-guest-serverless-api-sample/ # Serverless API
├── .editorconfig
├── .prettierrc.json
├── eslint.config.mjs
├── knip.config.ts
├── package.json                  # ルートワークスペース
├── tsconfig.json
├── tsconfig.base.json
└── CONTRIBUTING.md
```

### 1.3 既存ゲストユースケースのパターン分析

#### Serverless API サンプル（最もシンプル）

```
usecases/blea-guest-serverless-api-sample/
├── bin/
│   └── blea-guest-serverless-api-sample.ts   # CDK App エントリポイント
├── lib/
│   ├── stack/
│   │   └── blea-guest-serverless-api-sample-stack.ts  # 単一スタック
│   └── construct/
│       ├── api.ts            # API Gateway + Lambda
│       ├── datastore.ts      # DynamoDB
│       ├── lambda-nodejs.ts  # Lambda (Node.js)
│       ├── lambda-python.ts  # Lambda (Python)
│       └── monitoring.ts     # SNS + Chatbot
├── lambda/                   # Lambda ソースコード
├── test/
├── parameter.ts              # パラメータ定義
├── cdk.json
├── jest.config.js
├── package.json
└── tsconfig.json
```

#### ECS アプリサンプル（複数スタック構成）

```
usecases/blea-guest-ecs-app-sample/
├── bin/
│   ├── blea-guest-ecs-app-sample.ts
│   └── blea-guest-ecs-app-sample-via-cdk-pipelines.ts
├── lib/
│   ├── stack/
│   │   ├── blea-guest-ecs-app-sample-stack.ts          # メインスタック
│   │   ├── blea-guest-ecs-app-frontend-stack.ts        # フロントエンド
│   │   ├── blea-guest-ecs-app-monitoring-stack.ts      # モニタリング
│   │   └── blea-guest-ecs-app-sample-via-cdk-pipelines-stack.ts
│   ├── construct/
│   │   ├── canary.ts          # CloudWatch Synthetics
│   │   ├── dashboard.ts       # CloudWatch Dashboard
│   │   ├── datastore.ts       # RDS Aurora
│   │   ├── ecsapp.ts          # ECS Fargate
│   │   ├── frontend.ts        # CloudFront + S3
│   │   ├── monitoring.ts      # SNS + Chatbot
│   │   └── networking.ts      # VPC
│   └── stage/
├── test/
├── parameter.ts
└── ...
```

### 1.4 BLEA コーディングコンベンション

#### parameter.ts パターン

```typescript
import { Environment } from 'aws-cdk-lib';

export interface AppParameter {
  env?: Environment;
  envName: string;
  monitoringNotifyEmail: string;
  monitoringSlackWorkspaceId: string;
  monitoringSlackChannelId: string;
}

export const devParameter: AppParameter = {
  envName: 'Development',
  monitoringNotifyEmail: 'notify-security@example.com',
  monitoringSlackWorkspaceId: 'TXXXXXXXXXX',
  monitoringSlackChannelId: 'CYYYYYYYYYY',
  // env: { account: '123456789012', region: 'ap-northeast-1' },
};
```

#### bin/ エントリポイントパターン

```typescript
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { BLEAServerlessApiStack } from '../lib/stack/blea-guest-serverless-api-sample-stack';
import { devParameter } from '../parameter';

const app = new cdk.App();
new BLEAServerlessApiStack(app, 'Dev-BLEAServerlessApi', {
  description: 'BLEA Serverless API sample for guest accounts (uksb-1tupboc58) (tag:blea-guest-serverless-api-sample)',
  env: {
    account: devParameter.env?.account || process.env.CDK_DEFAULT_ACCOUNT,
    region: devParameter.env?.region || process.env.CDK_DEFAULT_REGION,
  },
  tags: {
    Repository: 'aws-samples/baseline-environment-on-aws',
    Environment: devParameter.envName,
  },
  monitoringNotifyEmail: devParameter.monitoringNotifyEmail,
  monitoringSlackWorkspaceId: devParameter.monitoringSlackWorkspaceId,
  monitoringSlackChannelId: devParameter.monitoringSlackChannelId,
});
```

#### Stack パターン

```typescript
import { Names, Stack, StackProps } from 'aws-cdk-lib';
import { Key } from 'aws-cdk-lib/aws-kms';
import { Construct } from 'constructs';

export interface BLEAServerlessApiStackProps extends StackProps {
  monitoringNotifyEmail: string;
  monitoringSlackWorkspaceId: string;
  monitoringSlackChannelId: string;
}

export class BLEAServerlessApiStack extends Stack {
  constructor(scope: Construct, id: string, props: BLEAServerlessApiStackProps) {
    super(scope, id, props);
    // Construct の組み合わせでシステムを構築
    const monitoring = new Monitoring(this, 'Monitoring', { ... });
    const cmk = new Key(this, 'CMK', { enableKeyRotation: true, ... });
    const datastore = new Datastore(this, 'Datastore', { ... });
    new Api(this, 'Api', { ... });
  }
}
```

#### Construct パターン（Monitoring）

```typescript
import { aws_chatbot as cb, aws_iam as iam, aws_sns as sns, Names } from 'aws-cdk-lib';
import { Construct } from 'constructs';

export interface MonitoringProps {
  monitoringNotifyEmail: string;
  monitoringSlackChannelId: string;
  monitoringSlackWorkspaceId: string;
}

export class Monitoring extends Construct {
  public readonly alarmTopic: sns.ITopic;

  constructor(scope: Construct, id: string, props: MonitoringProps) {
    super(scope, id);
    // SNS Topic → Email Subscription → Chatbot
  }
}
```

#### package.json パターン

```json
{
  "private": true,
  "name": "blea-guest-ecs-app-sample",
  "version": "1.0.0",
  "license": "MIT-0",
  "scripts": {
    "synth": "cdk synth -q",
    "build": "tsc --build",
    "clean": "tsc --build --clean && rm -rf cdk.out",
    "test": "jest",
    "cdk": "cdk"
  },
  "devDependencies": {
    "@types/jest": "^30.0.0",
    "@types/node": "^22.10.1",
    "aws-cdk": "^2.1029.4",
    "jest": "^30.2.0",
    "ts-jest": "^29.4.4",
    "ts-node": "^10.9.2",
    "typescript": "~5.9.3"
  },
  "dependencies": {
    "aws-cdk-lib": "^2.219.0",
    "constructs": "^10.4.2",
    "source-map-support": "^0.5.21"
  }
}
```

#### 設計原則

| 原則 | 説明 |
|------|------|
| Construct 分離 | 論理的な関心事ごとに Construct を分割（networking, datastore, monitoring, etc.） |
| Stack 分割 | 大規模ユースケースは複数 Stack に分割（ECS: main, frontend, monitoring） |
| Props パターン | Construct 間の依存は Props 経由で注入 |
| 公開プロパティは readonly | `public readonly` で外部からの書き込みを防止 |
| KMS 暗号化 | データストアには CMK を使用し、キーローテーション有効 |
| タグ付け | `Repository` と `Environment` タグを全リソースに設定 |
| description | Stack description にソリューション追跡コードを含める |

### 1.5 CONTRIBUTING.md サマリー

- Fork → Modify → Local tests pass → Clear commit messages → PR
- 重要な変更は先に Issue を作成して議論
- ライセンス: MIT-0
- セキュリティ問題は公開 Issue ではなく AWS vulnerability reporting page へ

---

## 2. FSx for ONTAP CDK サポート状況

### 2.1 利用可能な CloudFormation / CDK リソース

| リソース | CDK クラス | 状態 |
|----------|-----------|------|
| `AWS::FSx::FileSystem` | `CfnFileSystem` (L1) | ✅ 安定 |
| `AWS::FSx::StorageVirtualMachine` | `CfnStorageVirtualMachine` (L1) | ✅ 安定 |
| `AWS::FSx::Volume` | `CfnVolume` (L1) | ✅ 安定 |
| **`AWS::FSx::S3AccessPointAttachment`** | **`CfnS3AccessPointAttachment`** (L1) | ✅ **新規サポート確認** |

### 2.2 S3 Access Point の CloudFormation サポート（重要な発見）

**`AWS::FSx::S3AccessPointAttachment`** が CloudFormation で正式サポートされている。これにより Custom Resource / Lambda が不要。

#### CDK での利用例

```typescript
import { aws_fsx as fsx } from 'aws-cdk-lib';

new fsx.CfnS3AccessPointAttachment(this, 'S3AP', {
  name: 'my-fsxn-access-point',
  type: 'ONTAP',
  ontapConfiguration: {
    volumeId: volume.ref,
    fileSystemIdentity: {
      type: 'UNIX_USER',  // or 'WINDOWS_USER'
      unixUser: {
        name: 'nobody',   // UNIX ユーザー名
      },
    },
  },
  s3AccessPoint: {
    // S3 Access Point 設定（ネットワークオリジン等）
  },
});
```

#### 主要プロパティ

| プロパティ | 必須 | 説明 |
|-----------|------|------|
| `Name` | Yes | S3 AP 名（3-50文字、`[a-z0-9-]`） |
| `Type` | Yes | `ONTAP` または `OPENZFS` |
| `OntapConfiguration.volumeId` | Yes | FSx for ONTAP Volume ID |
| `OntapConfiguration.fileSystemIdentity` | Yes | アクセス時のファイルシステムID |

#### 返却値

- `Lifecycle`: AVAILABLE / CREATING / DELETING / FAILED / UPDATING
- `S3AccessPoint.Alias`: DNS エイリアス
- `S3AccessPoint.ResourceARN`: S3 AP の ARN

### 2.3 L2 Construct の状況

FSx for ONTAP には **L2 Construct は存在しない**（2026-06時点）。すべて L1 (Cfn*) を使用する必要がある。
これは本ユースケースでラッパー Construct を提供する価値が高いことを意味する。

### 2.4 S3 Access Point の制約（親プロジェクトで検証済み）

| カテゴリ | サポート状況 |
|---------|-------------|
| GetObject, PutObject, ListObjectsV2, DeleteObject | ✅ |
| Multipart Upload | ✅ |
| Athena (Glue Catalog 経由) | ✅ Internet-origin AP 必要 |
| Glue Crawler / ETL | ✅ Internet-origin AP 必要 |
| Bedrock Knowledge Base | ✅ Internet-origin AP 必要 |
| SageMaker | ✅ VPC or Internet |
| Lambda (VPC内) | ✅ VPC-origin AP |
| S3 Event Notifications | ❌ 非対応 |
| S3 Select | ❌ 非対応 |
| 条件付き書き込み (conditional writes) | ❌ 非対応 |
| Iceberg / Delta / Hudi 書き込み | ❌ 非対応（atomic rename 不可） |

---

## 3. 推奨ユースケースシナリオ

### 3.1 評価基準

| 基準 | 重み | 説明 |
|------|------|------|
| BLEA との整合性 | 高 | 既存パターンとの一貫性 |
| 実用性 | 高 | エンタープライズでの実際のニーズ |
| 実装の現実性 | 中 | CloudFormation サポート、制約の少なさ |
| 差別化 | 中 | 既存サンプルとの重複回避 |
| スコープの適正さ | 高 | BLEA ユースケースとして大きすぎない |

### 3.2 候補評価

| シナリオ | BLEA整合性 | 実用性 | 実現性 | 差別化 | スコープ | 総合 |
|---------|-----------|--------|--------|--------|---------|------|
| A: NAS + SQL 分析 | ◎ | ◎ | ◎ | ◎ | ◎ | **推奨** |
| B: ドキュメント + 生成AI | ○ | ◎ | △ | ◎ | ○ | 次候補 |
| C: データレイク統合 | ○ | ○ | △ | ○ | △ | - |
| D: ハイブリッド統合 | △ | ◎ | △ | ◎ | ✕ | スコープ過大 |

### 3.3 推奨: 候補A「エンタープライズ NAS + データ分析基盤」

#### 選定理由

1. **BLEA パターンとの親和性が最も高い**
   - ECS サンプルの VPC + Construct パターンをそのまま踏襲可能
   - Monitoring Construct を再利用
   - 複数 Stack 分割が自然

2. **CloudFormation サポートが完全**
   - FSx for ONTAP File System, SVM, Volume: すべて L1 サポート
   - **S3 Access Point: `AWS::FSx::S3AccessPointAttachment` で完全サポート**（Custom Resource 不要）
   - Glue, Athena: 完全な CDK サポート

3. **実装スコープが BLEA ユースケースとして適切**
   - Bedrock KB は設定が複雑で BLEA の「シンプルなリファレンス」方針と合わない
   - Athena + Glue は設定が宣言的で CDK テンプレートとして理解しやすい

4. **エンタープライズニーズとの合致**
   - ファイルサーバーからのデータ分析は最も一般的なユースケース
   - AWS 公式ブログでも Athena + Glue + FSx for ONTAP S3 AP パターンが推奨されている
   - 50以上の AWS サービスとの統合が S3 AP 経由で可能

5. **差別化**
   - BLEA に storage / data analytics ユースケースは存在しない
   - FSx for ONTAP は AWS マネージドストレージとして成熟

#### ユースケース概要

```
企業のファイルサーバー (FSx for ONTAP)
  ↓ NFS/SMB でデータ蓄積
  ↓ S3 Access Point でオブジェクトアクセスを提供
  ↓
AWS Glue Crawler → Glue Data Catalog
  ↓
Amazon Athena → SQL 分析
  ↓
(オプション) QuickSight → BI ダッシュボード
```

---

## 4. スタック構成案

### 4.1 推奨構成

BLEA ECS サンプルの「複数スタック + Construct 分離」パターンに従う：

```
usecases/blea-guest-fsxn-data-analytics-sample/
├── bin/
│   └── blea-guest-fsxn-data-analytics-sample.ts
├── lib/
│   ├── stack/
│   │   └── blea-guest-fsxn-data-analytics-sample-stack.ts  # 単一スタック
│   └── construct/
│       ├── networking.ts       # VPC + Subnets + VPC Endpoints
│       ├── fsxn-storage.ts     # FSx for ONTAP FileSystem + SVM + Volume
│       ├── s3-access-point.ts  # S3 Access Point Attachment
│       ├── data-analytics.ts   # Glue Crawler + Athena Workgroup
│       └── monitoring.ts       # CloudWatch Alarms + SNS + Chatbot
├── parameter.ts
├── cdk.json
├── jest.config.js
├── package.json
├── tsconfig.json
├── test/
│   └── snapshot.test.ts
└── doc/
    └── images/
```

### 4.2 単一スタック vs 複数スタック

**単一スタック（推奨）** を選択する理由：

- Serverless API サンプルと同様、比較的コンパクトなユースケース
- FSx for ONTAP → S3 AP → Glue → Athena は相互依存が強く、分割メリットが小さい
- BLEA の「独立デプロイ可能」の原則は Stack 間の分離であり、Construct 分離で十分

### 4.3 各 Construct の責務

| Construct | リソース | 依存 |
|-----------|---------|------|
| `Networking` | VPC, Private Subnets (2AZ), VPC Endpoints (S3, Glue, Athena), Security Groups | - |
| `FsxnStorage` | CfnFileSystem (MULTI_AZ_1), CfnStorageVirtualMachine, CfnVolume | Networking |
| `S3AccessPoint` | CfnS3AccessPointAttachment (Internet-origin) | FsxnStorage |
| `DataAnalytics` | Glue Database, Glue Crawler, Athena Workgroup, S3 Bucket (query results) | S3AccessPoint |
| `Monitoring` | SNS Topic, Email Subscription, Chatbot, CloudWatch Alarms (FSx for ONTAP metrics) | FsxnStorage |

### 4.4 parameter.ts 設計

```typescript
import { Environment } from 'aws-cdk-lib';

export interface AppParameter {
  env?: Environment;
  envName: string;

  // Monitoring
  monitoringNotifyEmail: string;
  monitoringSlackWorkspaceId: string;
  monitoringSlackChannelId: string;

  // Networking
  vpcCidr: string;

  // FSx for ONTAP
  fsxnStorageCapacityGiB: number;       // 1024 minimum
  fsxnThroughputCapacityMBps: number;   // 128 | 256 | 512 | 1024 | 2048 | 4096
  fsxnDeploymentType: 'MULTI_AZ_1' | 'SINGLE_AZ_1';

  // S3 Access Point
  s3AccessPointName: string;

  // Data Analytics
  glueDatabaseName: string;
}

export const devParameter: AppParameter = {
  envName: 'Development',
  monitoringNotifyEmail: 'notify-monitoring@example.com',
  monitoringSlackWorkspaceId: 'T8XXXXXXX',
  monitoringSlackChannelId: 'C00XXXXXXXX',
  vpcCidr: '10.0.0.0/16',
  fsxnStorageCapacityGiB: 1024,
  fsxnThroughputCapacityMBps: 128,
  fsxnDeploymentType: 'MULTI_AZ_1',
  s3AccessPointName: 'fsxn-data-analytics-ap',
  glueDatabaseName: 'fsxn_analytics_db',
  // env: { account: '123456789012', region: 'ap-northeast-1' },
};
```

---

## 5. 実装ロードマップ

### Phase 1: 基盤構築（Networking + FSx for ONTAP Storage）

| タスク | 成果物 |
|--------|--------|
| プロジェクトスキャフォールディング | bin/, lib/, parameter.ts, cdk.json, package.json |
| Networking Construct | VPC, Private Subnets, VPC Endpoints, Security Groups |
| FsxnStorage Construct | CfnFileSystem, CfnStorageVirtualMachine, CfnVolume |
| 基本テスト | Snapshot test |

### Phase 2: S3 Access Point + Data Analytics

| タスク | 成果物 |
|--------|--------|
| S3AccessPoint Construct | CfnS3AccessPointAttachment |
| DataAnalytics Construct | Glue Database, Crawler, Athena Workgroup |
| IAM ロール設計 | Glue / Athena 用の最小権限 IAM ロール |
| テスト拡充 | Fine-grained assertion tests |

### Phase 3: モニタリング + ドキュメント

| タスク | 成果物 |
|--------|--------|
| Monitoring Construct | CloudWatch Alarms (FSx for ONTAP metrics), SNS, Chatbot |
| ドキュメント | README_ja.md, README.md, アーキテクチャ図 |
| デプロイテスト | 実アカウントでのデプロイ検証 |

### Phase 4: 上流貢献準備

| タスク | 成果物 |
|--------|--------|
| コードレビュー | BLEA パターン厳密準拠チェック |
| Issue 作成 | aws-samples/baseline-environment-on-aws に提案 Issue |
| PR 準備 | Fork → コード移植 → PR 作成 |

---

## 6. Issue 文面ドラフト

### タイトル

`[Feature Request] Add FSx for NetApp ONTAP data analytics guest system use case`

### 本文

```markdown
## Summary

I would like to propose a new guest system use case that demonstrates
enterprise file storage with Amazon FSx for NetApp ONTAP, integrated with
AWS analytics services via S3 Access Points.

## Motivation

BLEA currently provides guest system samples for ECS web apps, EC2 web apps,
and Serverless APIs. However, there is no sample covering enterprise file
storage or data analytics use cases.

Amazon FSx for NetApp ONTAP is a fully managed enterprise NAS that supports
NFS, SMB, and iSCSI protocols. With the recent launch of S3 Access Points
for FSx for ONTAP (Dec 2025), customers can now access their file data
through the S3 API, enabling direct integration with AWS analytics and AI
services without data duplication.

This use case fills an important gap by demonstrating:
- How to provision FSx for ONTAP with CDK following BLEA security standards
- How to configure S3 Access Points for analytics service integration
- How to set up AWS Glue and Amazon Athena for SQL-based analysis of file data
- Proper monitoring with CloudWatch alarms for FSx for ONTAP-specific metrics

## Proposed Architecture

```
[BLEA Governance Base]
    │
[FSx for ONTAP Data Analytics Guest System]
    ├── VPC (Multi-AZ, Private Subnets, VPC Endpoints)
    ├── Amazon FSx for NetApp ONTAP (Multi-AZ)
    │   ├── Storage Virtual Machine
    │   ├── Volume (NFS/SMB)
    │   └── S3 Access Point (Internet-origin)
    ├── AWS Glue (Crawler + Data Catalog)
    ├── Amazon Athena (Workgroup + Query Results Bucket)
    └── Monitoring (CloudWatch Alarms + SNS + Chatbot)
```

## Implementation Details

- Single stack design (similar to blea-guest-serverless-api-sample)
- 5 constructs: Networking, FsxnStorage, S3AccessPoint, DataAnalytics, Monitoring
- Uses `AWS::FSx::S3AccessPointAttachment` (native CloudFormation, no custom resources)
- All FSx for ONTAP resources via L1 constructs (CfnFileSystem, CfnStorageVirtualMachine, CfnVolume)
- Follows BLEA conventions: parameter.ts, monitoring pattern, KMS encryption, tagging

## Checklist

- [ ] TypeScript CDK v2 (aws-cdk-lib)
- [ ] Single stack, independently deployable
- [ ] parameter.ts for configuration
- [ ] Monitoring with CloudWatch + SNS + Chatbot
- [ ] Snapshot tests + assertion tests
- [ ] Bilingual documentation (Japanese + English)
- [ ] MIT-0 license compatible

## Related Resources

- [S3 Access Points for FSx for ONTAP (Dec 2025 launch)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-fsx-netapp-ontap-s3-access/)
- [AWS::FSx::S3AccessPointAttachment (CloudFormation)](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-fsx-s3accesspointattachment.html)
- [Using access points with AWS services](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/using-access-points-with-aws-services.html)
- [Bridge legacy and modern applications with S3 AP for FSx](https://aws.amazon.com/blogs/storage/bridge-legacy-and-modern-applications-with-amazon-s3-access-points-for-amazon-fsx/)

I have a working implementation ready and would be happy to submit a PR
if the maintainers are interested.
```

---

## 7. 参考リンク

### BLEA リポジトリ

- [aws-samples/baseline-environment-on-aws](https://github.com/aws-samples/baseline-environment-on-aws)
- [CONTRIBUTING.md](https://github.com/aws-samples/baseline-environment-on-aws/blob/main/CONTRIBUTING.md)
- [Serverless API sample (参照実装)](https://github.com/aws-samples/baseline-environment-on-aws/tree/main/usecases/blea-guest-serverless-api-sample)
- [ECS sample (複数スタック参照)](https://github.com/aws-samples/baseline-environment-on-aws/tree/main/usecases/blea-guest-ecs-app-sample)

### FSx for ONTAP

- [FSx for ONTAP S3 AP 発表 (2025-12)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-fsx-netapp-ontap-s3-access/)
- [CloudFormation: AWS::FSx::S3AccessPointAttachment](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-fsx-s3accesspointattachment.html)
- [CDK: CfnS3AccessPointAttachment.S3AccessPointOntapConfigurationProperty](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_fsx.CfnS3AccessPointAttachment.S3AccessPointOntapConfigurationProperty.html)
- [Using access points with AWS services](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/using-access-points-with-aws-services.html)
- [Bridge legacy and modern applications with S3 AP](https://aws.amazon.com/blogs/storage/bridge-legacy-and-modern-applications-with-amazon-s3-access-points-for-amazon-fsx/)
- [Enabling AI-powered analytics with S3 AP + AD](https://aws.amazon.com/blogs/storage/enabling-ai-powered-analytics-on-enterprise-file-data-configuring-s3-access-points-for-amazon-fsx-for-netapp-ontap-with-active-directory/)
- [Deploying FSx for ONTAP with CloudFormation (AWS Blog)](https://aws.amazon.com/blogs/storage/deploying-amazon-fsx-for-netapp-ontap-with-aws-cloudformation/)
- [NetApp/FSx-ONTAP-samples-scripts](https://github.com/NetApp/FSx-ONTAP-samples-scripts)

### AWS Solutions / Guidance

- [Guidance for Multi-Protocol Workloads with FSx for ONTAP](https://aws.amazon.com/solutions/guidance/multi-protocol-workloads-with-amazon-fsx-for-netapp-ontap/)
- [Guidance for Deploying Enterprise Apps with FSx for ONTAP](https://aws.amazon.com/solutions/guidance/deploying-enterprise-apps-with-netapp-bluexp-workload-factory-for-aws-and-amazon-fsx-for-netapp-ontap/)
- [Secure SFTP with Transfer Family + FSx for ONTAP S3 AP](https://aws.amazon.com/blogs/storage/secure-sftp-file-sharing-with-aws-transfer-family-amazon-fsx-for-netapp-ontap-and-s3-access-points/)

### 類似 / 関連リポジトリ

- [aws-samples/amazon-fsx-for-netapp-ontap-python-client-examples](https://github.com/aws-samples/amazon-fsx-for-netapp-ontap-python-client-examples) — Python クライアント例
- [aws-samples/amazon-eks-fsx-for-netapp-ontap](https://github.com/aws-samples/amazon-eks-fsx-for-netapp-ontap) — EKS + FSx for ONTAP
- [rafalkrol-xyz/cdk-fsx-ontap](https://github.com/rafalkrol-xyz/cdk-fsx-ontap) — CDK L3 Construct (サードパーティ)
- [aws-samples/aws-cdk-ecs-windows-fsx](https://github.com/aws-samples/aws-cdk-ecs-windows-fsx) — ECS + FSx Windows (Python CDK)

**注記**: BLEA リポジトリに FSx for ONTAP / storage 関連の Issue や PR は存在しない（2026-06 時点）。本提案は完全に新規ユースケースとなる。

---

## 8. 重要な更新事項

### tech.md のアップデート必要箇所

`.kiro/steering/tech.md` に以下の記載があるが、調査により更新が必要：

**旧情報（修正必要）:**
> S3 AP for FSx for ONTAP is NOT a CloudFormation resource (as of 2026)
> Must use Custom Resource (Lambda) or manual setup

**実際（2026-06時点）:**
> `AWS::FSx::S3AccessPointAttachment` が正式に CloudFormation / CDK でサポートされている。
> CDK クラス: `aws_fsx.CfnS3AccessPointAttachment`
> Custom Resource は不要。

---

## 9. リスクと留意事項

| リスク | 影響 | 緩和策 |
|--------|------|--------|
| BLEA メンテナーの応答 | 上流貢献が受け入れられない可能性 | まず Issue で提案し、フィードバックを得てから実装 |
| CDK バージョン互換性 | BLEA が使用する CDK バージョンとの差 | BLEA 最新リリース (v3.1.0) の依存バージョンに合わせる |
| FSx for ONTAP コスト | 最小構成でも $500+/月 | ドキュメントにコスト見積もりを明記、SINGLE_AZ_1 開発パラメータを提供 |
| S3 AP の制約 | 書き込み系ユースケースの制限 | READ 主体の分析パターンに絞る（Athena は読み取り専用） |
| CfnS3AccessPointAttachment の成熟度 | 新しいリソースのため不具合の可能性 | デプロイテストで検証、代替として API コールの手順を文書化 |


---

## 10. 拡張ユースケース分析（地方自治体・公共セクター・金融向け）

### 10.1 BLEA for FSI の分析

#### リポジトリ概要

| 項目 | 値 |
|------|-----|
| リポジトリ | [aws-samples/baseline-environment-on-aws-for-financial-services-institute](https://github.com/aws-samples/baseline-environment-on-aws-for-financial-services-institute) |
| 最新リリース | v1.6.3 (2025-12-25) |
| コントリビューター | 5名 |
| 日本語主体 | ✅（金融庁・FISC 対応） |
| 構成 | WA FSI Lens + ベストプラクティス + CDK テンプレート |

#### ユースケース一覧

| ユースケース | ディレクトリ | FSx for ONTAP 関連性 |
|-------------|-------------|-------------|
| 勘定系システム | `guest-core-banking-sample` | △ DB ストレージ |
| 顧客チャネル | `guest-customer-channel-sample` | △ |
| オープン API | `guest-openapi-base-sample` | △ |
| マーケットデータ | `guest-market-data-sample` | ◎ 大量ファイルデータ |
| データ分析プラットフォーム | `guest-analytics-platform-sample` | ◎ データレイク |
| モバイルバンキング | `guest-mobile-banking-sample` | △ |
| **サイバーレジリエンス** | `guest-core-banking-sample/lib/primary/cyber-resilience` | **◎ バックアップ・復旧** |
| 生成 AI | （別リポジトリ） | ◎ ドキュメント RAG |

#### BLEA for FSI のサイバーレジリエンスパターン（重要参考）

BLEA for FSI は以下の構成でサイバーレジリエンスを実現している：

1. **ワークロードアカウント** → AWS Backup で日次バックアップ
2. **データバンカーアカウント** → Logically Air-gapped Vault に複製
3. **リストアアカウント** → RAM 共有 → StepFunctions 自動リストア
4. **フォレンジックアカウント** → GuardDuty トリガー → Lambda でネットワーク隔離

これは FSx for ONTAP のネイティブ機能（SnapLock, SnapMirror, ARP/AI）で**より強力に**実現可能。

---

### 10.2 地方自治体・公共セクターのニーズ分析

#### 主要課題マッピング

| 課題テーマ | FSx for ONTAP で解決できる機能 | BLEA ユースケースとの整合性 |
|-----------|---------------------|--------------------------|
| **高可用性** | Multi-AZ, 自動フェイルオーバー | ◎ ECS サンプルと同等パターン |
| **災害対策 (DR)** | SnapMirror クロスリージョン複製 | ◎ BLEA for FSI サイバーレジリエンス参考 |
| **ランサムウェア対策** | ARP/AI, SnapLock (WORM), Snapshot | ◎ BLEA for FSI サイバーレジリエンス参考 |
| **コスト効率** | 重複排除, 圧縮, FabricPool 自動階層化 | ◎ パラメータ設計で表現可能 |
| **レガシーモダナイゼーション** | マルチプロトコル (NFS/SMB/iSCSI/S3) | ○ データ移行パターン |
| **VMware 環境移行** | Amazon EVS + FSx for ONTAP 外部データストア | △ スコープ外（EVS は別サービス） |
| **データ分析基盤** | S3 Access Point → Athena/Glue/Bedrock | ◎ 当初推奨ユースケースA |

#### 地方自治体固有の要件

| 要件 | 説明 | FSx for ONTAP 対応 |
|------|------|----------|
| ガバメントクラウド準拠 | デジタル庁のガバメントクラウド基準 | ✅ AWS が対象クラウド |
| 3層分離 | α/β/γ 分離ネットワーク | ✅ VPC + SG で実現 |
| LGWAN 接続 | 総合行政ネットワーク | △ Direct Connect / VPN |
| 個人情報保護 | マイナンバー等の機微情報 | ✅ KMS暗号化 + SnapLock |
| BCP/DR | 72時間以内の業務復旧 | ✅ SnapMirror クロスリージョン |
| ランサムウェア対策 | NISC ガイドライン準拠 | ✅ ARP/AI + SnapLock + Air-gap |

---

### 10.3 FSx for ONTAP の差別化機能と BLEA ユースケースへのフィット

#### FSx for ONTAP 固有のセキュリティ・保護機能

| 機能 | 説明 | CloudFormation サポート | ユースケース候補 |
|------|------|----------------------|----------------|
| **ARP/AI** | AI ベースのランサムウェア自動検知・Snapshot作成 | ONTAP CLI (カスタムリソースで設定) | サイバーレジリエンス |
| **Tamperproof Snapshot (TPS)** | **管理者権限でも一定期間削除不可**な Snapshot ロック。SnapLock Compliance Clock で保持期間を強制 | ONTAP CLI / REST API (Custom Resource) | **サイバーレジリエンスの中核** |
| **SnapLock Compliance** | WORM (改ざん防止) ストレージ。ファイルレベルの不変性 | ✅ `CfnVolume.SnaplockConfiguration` | コンプライアンス・アーカイブ |
| **SnapLock Enterprise** | 柔軟な WORM (管理者削除可) | ✅ `CfnVolume.SnaplockConfiguration` | ランサムウェア対策 |
| **FlexCache** | リモートボリュームのローカルキャッシュ。Read + Write-back (2025/05 GA)。分散拠点間のレイテンシ削減・帯域節約 | ONTAP CLI / REST API (Custom Resource) | **分散環境効率化** |
| **SnapMirror** | 非同期レプリケーション (クロスリージョン) | ONTAP CLI (FSx for ONTAP コンソール / API) | DR |
| **Snapshot** | ポイントインタイムリカバリ | ✅ `CfnVolume.SnapshotPolicy` | バックアップ |
| **FlexClone** | ゼロコピークローン | ONTAP CLI / API | 開発・テスト環境 |
| **FabricPool** | 自動階層化 (SSD → S3) | ✅ `CfnVolume.TieringPolicy` | コスト最適化 |
| **重複排除/圧縮** | ストレージ効率化 (最大65%削減) | ✅ `CfnVolume.StorageEfficiencyEnabled` | コスト最適化 |
| **S3 Access Point** | S3 API での分析サービス統合 | ✅ `CfnS3AccessPointAttachment` | データ分析・AI |
| **マルチプロトコル** | NFS + SMB + iSCSI + S3 同時アクセス | ✅ Volume 設定 | レガシーモダナイゼーション |

#### Tamperproof Snapshot (TPS) の詳細

Tamperproof Snapshot は ONTAP の Snapshot Locking 機能であり、以下の特徴を持つ：

- **管理者でも削除不可**: SnapLock Compliance Clock に基づき、設定した保持期間中は `volume snapshot delete` が拒否される
- **通常ボリュームに適用可能**: SnapLock ボリュームでなくても TPS を有効化できる（FSx for ONTAP 固有のメリット）
- **FSx for ONTAP 固有の特性**: オンプレ ONTAP では FabricPool ボリュームで TPS 非対応だが、FSx for ONTAP はマネージド環境のため FabricPool + TPS が共存可能
- **脅威モデル**: 攻撃者が管理者アカウントを侵害 → Snapshot 削除 → ランサムウェア暗号化後に復旧不能にする攻撃を防止
- **AWS Backup Air-gapped Vault との補完**: Air-gapped Vault = アカウント間隔離。TPS = ストレージレベル保護。多層防御として組み合わせ可能

#### FlexCache の詳細

FlexCache は ONTAP の分散キャッシュ機能であり、以下のユースケースに対応：

- **広域分散拠点アクセス**: 本庁（東京）のデータを支所（大阪）の FSx for ONTAP に FlexCache → WAN レイテンシを解消
- **マルチリージョン開発**: us-east-1 のソースコードを ap-northeast-1 で FlexCache → 開発者のビルド時間短縮
- **Write-back モード** (2025/05 GA): 書き込みもローカルキャッシュ → 非同期で origin 更新。書き込み負荷の高いワークロードにも対応
- **AWS WorkSpaces 連携**: NetApp ブログで「FlexCache + WorkSpaces で分散拠点のリモートワーク高速化」パターンが紹介済み
- **Atlassian 事例**: 6000万リポジトリ移行、レイテンシ17%削減、年間$2.1M コスト削減

#### CloudFormation / CDK でネイティブ管理できないもの

| 機能 | 代替手段 | 影響 |
|------|---------|------|
| SnapMirror 設定 | FSx API (`CreateDataRepositoryAssociation` ではない。ONTAP CLI or AWS SDK) | DR ユースケースでは手動/スクリプト必要 |
| ARP/AI 有効化 | ONTAP REST API via Lambda Custom Resource | ランサムウェア対策で必要 |
| FlexClone 作成 | ONTAP REST API via Lambda Custom Resource | Dev/Test ユースケースで必要 |
| SVM Peering | ONTAP REST API | DR ユースケースで必要 |

---

### 10.4 候補ユースケース再評価（拡張版）

#### 評価マトリクス

| # | ユースケース名 | ターゲット | BLEA整合 | CfnサポRT | 差別化 | ニーズ | 実装難度 | 推奨度 |
|---|------------|-----------|---------|----------|--------|--------|---------|--------|
| A | **エンタープライズ NAS + データ分析** | BLEA (汎用) | ◎ | ◎ | ◎ | ◎ | 低 | **★★★★★** |
| B | **サイバーレジリエンス（ランサムウェア対策）** | BLEA for FSI / 公共 | ◎ | ○ | ◎ | ◎ | 中 | **★★★★☆** |
| B2 | **Tamperproof Snapshot + ARP/AI 多層防御** | BLEA for FSI / 公共 | ◎ | △ | **◎◎** | ◎ | 中 | **★★★★★** |
| C | **DR / BCP（クロスリージョン複製）** | BLEA for FSI / 公共 | ○ | △ | ◎ | ◎ | 高 | ★★★☆☆ |
| D | **コスト最適化ファイルストレージ** | BLEA (汎用) | ◎ | ◎ | ○ | ○ | 低 | ★★★☆☆ |
| E | **VMware 移行 (EVS + FSx for ONTAP)** | 独立 Guidance | △ | △ | ◎ | ◎ | 高 | ★★☆☆☆ |
| F | **レガシー NAS モダナイゼーション** | BLEA (汎用) | ○ | ◎ | ○ | ○ | 中 | ★★★☆☆ |
| **G** | **分散拠点ファイルアクセス高速化 (FlexCache)** | BLEA / 独立 | ○ | △ | **◎◎** | ◎ | 中-高 | **★★★★☆** |

> **B2 (Tamperproof Snapshot)** を B に統合するか独立させるかは設計次第。TPS は「管理者権限でも削除できない」という点で SnapLock Enterprise / AWS Backup Air-gapped Vault と明確に差別化される。

> **G (FlexCache)** は地方自治体の本庁↔支所パターンに非常にフィットするが、CloudFormation 非対応のため Custom Resource が必要。BLEA 本体より「公共セクター向け Guidance」が適切な可能性あり。

---

### 10.5 推奨アプローチ: 段階的ユースケース展開

#### Phase 1: 基本ユースケース（BLEA 本体向け）

**ユースケースA: エンタープライズ NAS + データ分析**

- ターゲット: `aws-samples/baseline-environment-on-aws`
- スコープ: FSx for ONTAP + S3 AP + Glue + Athena + Monitoring
- 理由: CloudFormation 完全サポート、BLEA パターン厳密準拠、最小スコープ

#### Phase 2: セキュリティ強化ユースケース（BLEA for FSI 向け）

**ユースケースB: サイバーレジリエンス（ランサムウェア対策付きファイルストレージ）**

- ターゲット: `aws-samples/baseline-environment-on-aws-for-financial-services-institute`
- スコープ:
  - FSx for ONTAP (SnapLock Enterprise ボリューム) でイミュータブルバックアップ
  - ARP/AI によるランサムウェア自動検知（Custom Resource）
  - AWS Backup 統合 + Logically Air-gapped Vault
  - クロスアカウント復旧フロー
- 理由:
  - BLEA for FSI のサイバーレジリエンスパターンを FSx for ONTAP ネイティブ機能で強化
  - 金融庁ガイドライン・FISC 安全対策基準に対応
  - 地方自治体の NISC ガイドライン対応にも転用可能
  - 既存の AWS Backup ベースよりも RPO/RTO が優れる

#### Phase 3: DR ユースケース（将来拡張）

**ユースケースC: クロスリージョン DR**

- ターゲット: BLEA for FSI またはスタンドアロン Guidance
- スコープ: SnapMirror + クロスリージョン自動フェイルオーバー
- 理由: SnapMirror の CDK/CloudFormation サポートが限定的なため、ONTAP REST API ラッパーが必要

---

### 10.6 貢献先の比較

| 観点 | BLEA (本体) | BLEA for FSI |
|------|------------|-------------|
| スコープ | 汎用的なゲストシステム | 金融・規制対応ワークロード |
| コンプライアンス要件 | なし | FISC 安全対策基準マッピング必須 |
| ドキュメント量 | README + デプロイ手順 | アーキテクチャ解説 + FISC マッピング + 手順書 |
| CDK 複雑度 | 中（単一スタック可） | 高（マルチアカウント、StepFunctions等） |
| 審査プロセス | GitHub Issue → PR | 同上（メンテナーは AWS Japan SA） |
| FSx for ONTAP との親和性 | データ分析パターン | サイバーレジリエンス + データ保護パターン |
| 地方自治体への適用 | ◎（汎用基盤として） | ◎（セキュリティ要件が類似） |

### 10.7 BLEA for FSI 向けユースケースの具体案

#### アーキテクチャ案: FSx for ONTAP サイバーレジリエンス

```
[ワークロードアカウント]
├── VPC (Multi-AZ)
│   └── Amazon FSx for NetApp ONTAP
│       ├── 本番ボリューム (通常運用)
│       │   ├── ARP/AI 有効化 (ランサムウェア自動検知)
│       │   ├── Snapshot ポリシー (日次/週次)
│       │   └── ストレージ効率化 (重複排除 + 圧縮)
│       └── SnapLock Enterprise ボリューム (イミュータブルバックアップ)
│           └── Snapshot → SnapLock ボリュームに自動コピー
├── AWS Backup
│   └── FSx for ONTAP Volume バックアップ → Logically Air-gapped Vault (別アカウント)
└── Monitoring
    ├── GuardDuty → Lambda → ネットワーク隔離
    ├── CloudWatch Alarms (FSx for ONTAP: ARP検知, 容量, スループット)
    └── SNS → Chatbot → Slack

[データバンカーアカウント]
├── AWS Backup Logically Air-gapped Vault
├── RAM 共有 (リストアアカウントへ)
└── SCPによる削除保護

[リストアアカウント]
├── CDK による環境自動再構築
├── StepFunctions による FSx for ONTAP バックアップリストア自動化
└── 復旧確認後の切替手順
```

#### FISC マッピング対応項目（想定）

| FISC 基準 | 対策 | FSx for ONTAP 機能 |
|-----------|------|----------|
| 実 43 (バックアップ) | 定期バックアップ + オフサイト保管 | Snapshot + SnapMirror + Air-gapped Vault |
| 実 44 (復旧) | 目標復旧時間内のリストア | Snapshot リストア (分単位) |
| 実 116 (サイバー攻撃対策) | ランサムウェア検知・隔離 | ARP/AI + ネットワーク隔離 |
| 実 117 (データ保護) | 改ざん防止バックアップ | **Tamperproof Snapshot** + SnapLock Compliance/Enterprise |
| 実 117 (管理者権限保護) | 特権アカウント侵害時の保護 | **TPS (管理者でも削除不可)** |
| 実 8 (可用性) | サービス継続性確保 | Multi-AZ + 自動フェイルオーバー |

---

### 10.8 VMware ワークロードのモダナイゼーション

#### 視点の再定義

VMware 移行は「EVS への Lift-and-Shift」だけではない。実際には以下の移行パスが存在し、**すべてに FSx for ONTAP が共有ストレージ基盤として関与できる**：

```
[VMware on-premises]
    │
    ├─→ [EVS (VMware on AWS)]          ... Lift-and-Shift (VMware 維持)
    │     └── FSx for ONTAP = NFS/iSCSI 外部データストア
    │
    ├─→ [EC2 (IaaS)]                   ... Rehost (ハイパーバイザー脱却)
    │     └── FSx for ONTAP = NFS/iSCSI 共有ストレージ
    │
    ├─→ [ECS / EKS (コンテナ)]          ... Replatform (コンテナ化)
    │     └── FSx for ONTAP = Persistent Volume (NFS CSI Driver)
    │
    ├─→ [Lambda + S3 AP]               ... Refactor (サーバーレス)
    │     └── FSx for ONTAP = S3 API 経由でデータアクセス
    │
    └─→ [AWS Batch / PCS]              ... Replatform (HPC/バッチ)
          └── FSx for ONTAP = NFS 共有ストレージ
```

#### コンピュート別の FSx for ONTAP 活用パターン

| コンピュート | プロトコル | ユースケース | 可用性 | コスト効率 |
|------------|-----------|------------|--------|-----------|
| **EC2** | NFS, SMB, iSCSI | ファイルサーバー、DB 共有ストレージ、SQL Server FCI | Multi-AZ HA | Dedup/Compression/Tiering |
| **ECS (Fargate/EC2)** | NFS (EFS-like) | コンテナ間共有データ、設定ファイル、ログ | Multi-AZ HA | FlexClone で Dev/Test |
| **EKS** | NFS (Trident CSI) | Persistent Volume、StatefulSet、ML パイプライン | Multi-AZ HA | Dynamic Provisioning |
| **Lambda** | S3 AP (VPC-origin) | サーバーレスファイル処理、イベント駆動 ETL | サーバーレス | 処理時間のみ課金 |
| **AWS Batch** | NFS | バッチジョブ間共有、入出力データ | ジョブレベル | Spot + FSx for ONTAP |
| **AWS PCS** | NFS | HPC ノード間共有、MPI 通信 | クラスタレベル | スケールイン/アウト |
| **WorkSpaces** | SMB/NFS | ユーザーホームディレクトリ | Multi-AZ HA | ユーザー数に非依存 |

#### S3 Access Point によるサーバーレスオペレーション

FSx for ONTAP + S3 AP の組み合わせにより、**サーバーレスなオペレーション最適化**が実現できる：

| オペレーション | 実装 | 効果 |
|-------------|------|------|
| ファイル自動処理 | Lambda + S3 AP (VPC-origin) | NFS クライアント不要でファイル操作 |
| モニタリング自動拡張 | Lambda + CloudWatch + FSx API | 容量/スループット自動スケーリング |
| パスワードローテーション | Lambda + Secrets Manager + ONTAP API | セキュリティ自動化 |
| データカタログ自動更新 | Glue Crawler + S3 AP (Internet-origin) | メタデータ管理の自動化 |
| AI/ML データパイプライン | Step Functions + Lambda + S3 AP → Bedrock/SageMaker | ファイルデータの AI 活用 |
| バックアップ検証 | Lambda + S3 AP → データ整合性チェック | DR 訓練の自動化 |

AWS 公式チュートリアル「[Process files serverlessly using Lambda](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/tutorial-process-files-with-lambda.html)」がまさにこのパターンを示している。

#### BLEA ユースケースとしての位置付け

**結論: 「VMware移行」単独ではなく、「共有ストレージ基盤 + モダナイゼーション」として広く捉えるべき**

| アプローチ | BLEA スコープ適合 | 理由 |
|-----------|-----------------|------|
| EVS + FSx for ONTAP (VMware維持) | △ スコープ外 | EVS は CDK テンプレートで管理しにくい |
| **EC2 + FSx for ONTAP (共有ストレージ)** | **◎** | BLEA blea-guest-ec2-app-sample のパターンに FSx for ONTAP 追加 |
| **ECS/EKS + FSx for ONTAP (PV)** | **◎** | BLEA blea-guest-ecs-app-sample のパターンに FSx for ONTAP 追加 |
| **Lambda + S3 AP (サーバーレス)** | **◎** | BLEA serverless-api-sample のパターン拡張 |
| Batch/PCS + FSx for ONTAP | ○ | HPC は BLEA スコープ外だが Guidance としては可能 |

これらは Phase 1 の「データ分析ユースケース」と組み合わせるか、**新たな Phase 1b**として「コンピュート移行 + FSx for ONTAP 共有ストレージ」ユースケースを追加する余地がある。

#### 考えられるユースケース構成案

**ユースケースH: モダナイゼーション基盤（共有ストレージ + サーバーレスオペレーション）**

```
[BLEA Governance Base]
    │
[FSx for ONTAP Modernization Platform]
    │
    ├── VPC (Multi-AZ)
    │   ├── FSx for NetApp ONTAP (共有ストレージ)
    │   │   ├── NFS Volume (EC2/ECS/EKS 共有)
    │   │   ├── iSCSI LUN (EC2 ブロックストレージ)
    │   │   ├── SMB Share (Windows ワークロード)
    │   │   └── S3 Access Point (サーバーレスアクセス)
    │   └── VPC Endpoints
    │
    ├── コンピュート層（選択的デプロイ）
    │   ├── EC2 Auto Scaling (レガシーアプリ)
    │   ├── ECS Fargate (コンテナ化アプリ)
    │   └── Lambda (イベント駆動処理)
    │
    ├── サーバーレスオペレーション
    │   ├── Lambda: 自動容量管理
    │   ├── Lambda: S3 AP 経由ファイル処理
    │   ├── Step Functions: バッチオーケストレーション
    │   └── EventBridge: スケジュール駆動タスク
    │
    ├── データ保護
    │   ├── Snapshot ポリシー + TPS
    │   ├── FlexClone (Dev/Test 環境即時作成)
    │   └── AWS Backup 統合
    │
    └── Monitoring
        ├── CloudWatch Alarms + Dashboard
        └── Lambda: 自動スケーリング/修復
```

ただし、このスコープは BLEA 単一ユースケースとしては**大きすぎる**可能性がある。以下のように分割が現実的：

- **Phase 1 (現行案)**: データ分析パターン（S3 AP + Glue + Athena）
- **Phase 1b (追加検討)**: EC2/ECS 共有ストレージパターン（NFS/iSCSI + サーバーレスオペレーション）
- **Phase 2**: サイバーレジリエンス（TPS + ARP/AI）

#### 参考リンク

- [Expedite VMware migration to EC2 and FSx for ONTAP using BlueXP migration advisor](https://aws.amazon.com/blogs/storage/expedite-vmware-migration-to-amazon-ec2-and-amazon-fsx-for-netapp-ontap-using-bluexp-workload-factory-for-aws-migration-advisor/)
- [Seamless migration from VMware to FSx for ONTAP and EC2](https://aws.amazon.com/blogs/storage/seamless-migration-from-any-vmware-environment-to-amazon-fsx-for-netapp-ontap-and-amazon-ec2/)
- [Decoupling compute and data layers with AWS MGN + DataSync + FSx](https://aws.amazon.com/blogs/migration-and-modernization/decoupling-the-compute-and-data-layers-with-aws-mgn-aws-datasync-and-amazon-fsx/)
- [Process files serverlessly using Lambda + S3 AP](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/tutorial-process-files-with-lambda.html)
- [EKS Workshop: FSx for ONTAP as Persistent Volume](https://www.eksworkshop.com/docs/fundamentals/storage/fsx-for-netapp-ontap/)
- [AWS ParallelCluster: FSx for ONTAP shared storage](https://docs.aws.amazon.com/parallelcluster/latest/ug/SharedStorage-v3.html)
- [FSx for ONTAP: Automate monitoring at scale with Lambda](https://aws.amazon.com/blogs/storage/automate-monitoring-at-scale-for-amazon-fsx-for-netapp-ontap-volumes/)
- [How a customer reduced TCO by 28% with FSx for ONTAP (FlexCache + SnapMirror)](https://aws.amazon.com/blogs/storage/how-a-customer-reduced-storage-tco-by-28-with-amazon-fsx-for-netapp-ontap/)
- [Atlassian: 60M repos migrated, 17% latency reduction, $2.1M savings](https://aws.amazon.com/partners/success/atlassian-netapp/)

---

### 10.9 最終推奨: 3段階貢献戦略

```
┌─────────────────────────────────────────────────────┐
│ Phase 1: BLEA 本体                                   │
│ ユースケースA: エンタープライズ NAS + データ分析           │
│ → aws-samples/baseline-environment-on-aws           │
│ → 全 CloudFormation ネイティブ、Custom Resource 不要   │
│ → 地方自治体のデータ活用基盤としても活用可能               │
│ → 実装期間: 2-3週間                                   │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 2: BLEA for FSI                               │
│ ユースケースB: サイバーレジリエンス（FSx for ONTAP強化版）           │
│ → aws-samples/baseline-environment-on-aws-for-      │
│   financial-services-institute                      │
│ → **Tamperproof Snapshot** (管理者でも削除不可)        │
│ → SnapLock Enterprise + ARP/AI                      │
│ → AWS Backup Air-gapped Vault（多層防御）             │
│ → FISC マッピング + 手順書                             │
│ → 金融庁ガイドライン / NISC ガイドライン対応             │
│ → 実装期間: 4-6週間（ドキュメント含む）                  │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 3: 将来拡張                                    │
│ ユースケースC: クロスリージョン DR (SnapMirror)          │
│ ユースケースE: EVS + FSx for ONTAP ストレージ基盤                 │
│ **ユースケースG: 分散拠点ファイルアクセス (FlexCache)**   │
│  → 本庁↔支所の WAN レイテンシ解消                       │
│  → Write-back モードで書き込み負荷にも対応               │
│  → マルチリージョン WorkSpaces 連携                     │
│ → 独立 Guidance または別リポジトリ                      │
└─────────────────────────────────────────────────────┘
```

#### 各フェーズでカバーされる地方自治体ニーズ

| ニーズ | Phase 1 | Phase 2 | Phase 3 |
|--------|---------|---------|---------|
| データ分析・AI 活用 | ✅ | - | - |
| ランサムウェア対策 | - | ✅ (TPS + ARP/AI) | - |
| BCP / DR | (Multi-AZ) | (Air-gapped + TPS) | ✅ (Cross-Region) |
| コスト効率 | ✅ (FabricPool, dedup) | ✅ | ✅ |
| レガシーモダナイゼーション | ✅ (NFS/SMB→S3) | - | - |
| VMware 移行 | - | - | ✅ (EVS) |
| 高可用性 | ✅ (Multi-AZ) | ✅ | ✅ |
| コンプライアンス | - | ✅ (FISC/NISC) | - |
| 分散拠点アクセス | - | - | ✅ (FlexCache) |
| 管理者権限からの保護 | - | ✅ (TPS) | - |
