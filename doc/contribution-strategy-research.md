# Contribution Strategy Research

> 調査日: 2026-06-06 (Updated)
> 目的: 各 Spec の PR マージ要件を満たすための調査

## BLEA 本体 (aws-samples/baseline-environment-on-aws)

### リポジトリ概要
- Stars: 272, Forks: 56
- Open PRs: 2 (Draft), Closed: 501
- Primary contributor/maintainer: konokenj (Kenji Kono, Senior SA, Nagoya)
- Co-contributor: ohmurayu
- **Version: 3.1.0**

### 技術スタック（package.json より確認）
- **Node.js >= 22**（重要：我々のプロジェクトは >=20 で設定している）
- **TypeScript ~5.9.3**
- **eslint v9** + `typescript-eslint` v8 + `eslint-config-prettier`
- **prettier v3.6**
- **knip** (未使用コード検出)
- **simple-git-hooks + lint-staged**: pre-commit で `git-secrets --scan` + eslint + prettier
- **workspaces**: `"usecases/*"` — 全 usecase がワークスペース
- **cdk-nag はルート package.json にない**（各 usecase 単位の可能性）

### 重大なギャップ（対応必須）

| 項目 | BLEA 本体 | 我々の現状 | 対応 |
|------|----------|----------|------|
| Node.js | >= 22 | >= 20 | engines フィールド更新 |
| TypeScript | ~5.9.3 | ~5.4.0 | 更新必要 |
| eslint | v9 + flat config | v8 + legacy config | 移行必要 |
| prettier | v3.6 | 未使用 | 追加 |
| knip | あり | なし | 追加検討 |
| git-secrets | pre-commit | gitleaks | 併用 or 切替 |
| AI attribution | 禁止 | — | コミットメッセージ注意 |

### CONTRIBUTING.md 要件
1. Issue を先に作成し、significant work を議論
2. Fork → 変更に集中（全体リフォーマットしない）→ ローカルテスト通過 → PR
3. CI の自動テストに注意
4. コードリフォーマットの混在を避ける

### AI Attribution ポリシー
aws-samples 全体で以下が禁止されている可能性:
- コミットメッセージに `Co-Authored-By: Claude` 等の AI attribution
- PR body に AI 生成の明記
- **対応**: コミットメッセージ・PR body に AI ツールへの言及を含めない

### 既存ユースケース構造パターン
```
usecases/<name>/
├── bin/             # CDK エントリポイント
├── lib/
│   ├── construct/   # 個別リソース Construct
│   └── stack/       # Stack (Construct をまとめる)
├── test/            # Jest テスト
├── parameter.ts     # デプロイ設定
├── cdk.json
├── jest.config.js
├── tsconfig.json
└── package.json
```

### PR マージに必要と推定される要件（更新版）
- [ ] Node.js >= 22 対応
- [ ] TypeScript ~5.9.3
- [ ] eslint v9 flat config 準拠
- [ ] prettier v3 フォーマット通過
- [ ] git-secrets --scan 通過
- [ ] knip（未使用コード）通過
- [ ] cdk synth 成功
- [ ] Jest テスト通過
- [ ] ドキュメント（日英）
- [ ] parameter.ts でカスタマイズ可能
- [ ] 実アカウント情報なし
- [ ] AI attribution なし
- [ ] Issue での事前議論

---

## BLEA for FSI (aws-samples/baseline-environment-on-aws-for-financial-services-institute)

### リポジトリ概要
- Stars: 135, Forks: 7
- PRs: 37, Issues: 1
- Primary contributors: nakajiam, kitaaras, AseiSugiyama, shonansurvivors
- Latest release: v1.6.3 (Dec 2025)
- Language: TypeScript 85%

### 技術スタック（package.json より確認）
- **Node.js >= 14**（緩い）
- **TypeScript ~5.0.4**
- **eslint v8** + `@typescript-eslint/eslint-plugin` v5（旧式）
- **prettier v2.8**
- **cdk-nag ^2.22.33** ← **重要：cdk-nag が必須**
- **standard-version** (リリース管理)
- **simple-git-hooks + lint-staged + git-secrets**
- **workspaces**: `resources/bleafsi-shared-constructs/*`, `usecases/*`, `tools/*`

### BLEA for FSI 特有の要件

| 項目 | BLEA for FSI | 我々の現状 | 対応 |
|------|-------------|----------|------|
| **cdk-nag** | v2.22.33 必須 | 未使用 | **追加必須** |
| eslint | v8 (legacy) | v8 (一致) | OK |
| prettier | v2.8 | 未使用 | 追加 |
| TypeScript | ~5.0.4 | ~5.4.0 | 互換性あり |
| shared-constructs | `resources/bleafsi-shared-constructs/` | 独自 shared/ | 構造合わせ |

### 重大な発見: サイバーレジリエンスは既存ワークロード

（前回調査と同じ — 省略）

### BLEA for FSI のドキュメント3点セット（必須）
1. アーキテクチャ解説 ✅ 作成済み
2. FISC 実務基準対策一覧 ✅ 作成済み
3. CDK サンプルコードデプロイ手順 ✅ 作成済み
4. 手順書（バックアップ/復旧/隔離） ✅ 作成済み

---

## 追加で必要な対応（優先度順）

### P0: ブロッカー（PR 提出前に必須）

#### BLEA 本体 (Spec G, H)
1. [ ] **eslint v9 flat config 移行** — BLEA 本体は eslint v9。我々のコードを eslint v9 で通す
2. [ ] **prettier 適用** — 全 .ts ファイルに prettier v3 実行
3. [ ] **TypeScript ~5.9.3 更新** — tsconfig と依存を更新
4. [ ] **Node.js >= 22 対応確認** — テストが node 22 で通ること確認
5. [ ] **AI attribution 除外** — コミット履歴に AI 関連メッセージがないこと確認

#### BLEA for FSI (Spec B)
1. [ ] **cdk-nag 追加** — `AwsSolutions` パック適用、Nag Suppressions 追記
2. [ ] **prettier v2 適用** — 全ファイルフォーマット
3. [ ] **bleafsi-shared-constructs 構造準拠** — 共有 construct を FSI パターンに合わせる

### P1: 高優先度

4. [ ] Spec A (PR #1304) が BLEA 本体の新しい技術要件を満たしているか確認・更新
5. [ ] 各 usecase の package.json を上流 engines/devDependencies に合わせる
6. [ ] `knip` で未使用 export/import を検出・削除

### P2: 中優先度

7. [ ] cdk-nag を Spec G, H にも追加（BLEA 本体には必須でないが品質向上）
8. [ ] CHANGELOG.md 作成（BLEA for FSI パターン）

---

## レビュアーペルソナ仮説（更新版）

### BLEA 本体 (konokenj)
- **重視**: eslint/prettier 通過、パターン一貫性、独立デプロイ性、セキュリティデフォルト
- **ツール**: knip（未使用コード検出）、git-secrets（シークレット検出）
- **スタイル**: Draft PR で議論 → 正式 PR の 2 段階
- **注意**: cdk.context.json 排除、不要な依存排除、Node.js >= 22

### BLEA for FSI (nakajiam, kitaaras)
- **重視**: cdk-nag 通過、FISC 対応マッピングの正確性、手順書の完全性
- **ツール**: cdk-nag (AwsSolutions pack)、git-secrets
- **スタイル**: リリースバージョン管理（standard-version）、CHANGELOG 必須
- **注意**: ControlTower 環境前提、ガバナンスベースとの統合
