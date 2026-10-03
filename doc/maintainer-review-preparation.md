# BLEA メンテナーレビュー準備

## メンテナー分析

### konokenj (Kenji Kono) — Primary Maintainer

| 項目 | 値 |
|------|-----|
| Role | Senior Solutions Architect @ AWS Japan |
| Location | Nagoya, Japan |
| GitHub Activity | 231 contributions/year, BLEA が唯一の pinned repo |
| Commit Style | Conventional commits (`feat:`, `chore:`, `fix:`, `build:`) |
| 言語 | Issue/PR/コミット: 英語。README_ja.md: 日本語 |
| ツール | release-please, dependabot, Mergify, ESLint v9, Prettier, knip |
| CDK Style | L2 優先、L1 は最小限。npm workspaces。package-lock.json 管理 |

### レビュー傾向（PR 履歴から推測）

1. **コード品質 > 機能量**: ESLint, Prettier, knip (dead code検出) を使用 → コードスタイル厳密
2. **依存パッケージ管理**: dependabot PR に 1 review approval → バージョン管理に注意を払う
3. **Conventional Commits 厳守**: `feat:`, `fix:`, `chore:`, `build:` のプレフィックス必須
4. **テスト**: snapshot test + asset hash 除外パターン
5. **ドキュメント**: bilingual (README_ja.md primary, README.md English)
6. **セキュリティ**: security policy あり、credential 漏洩に敏感

### Approve の条件（PR 履歴からの推定）

| 条件 | 状態 |
|---|---|
| BLEA の既存パターンに厳密に従っている | ✅ |
| ESLint / Prettier が通る | ✅ |
| `cdk synth` が成功する | ✅ |
| テストがパスする | ✅ |
| Conventional commits | ✅ |
| ドキュメントが bilingual | ✅ |
| 不要な依存がない (knip チェック) | ✅ |
| package-lock.json が正しく生成されている | ✅ |
| 新規ユースケース追加の前例がない（メンテナーの判断次第） | ⚠️ |

---

## PR に向けた改善（Kono-san ペルソナレビュー）

### チェックリスト

| # | 項目 | 状態 | 対応 |
|---|------|------|------|
| 1 | ESLint 通過 | ❓ 未確認 | BLEA ルートの eslint.config.mjs に従う |
| 2 | Prettier 通過 | ❓ 未確認 | BLEA ルートの .prettierrc.json に従う |
| 3 | knip (dead code) 通過 | ❓ 未確認 | 不要な export, import がないか |
| 4 | package-lock.json | ❌ 未生成 | npm install で生成必要 |
| 5 | CDK バージョン | ✅ ^2.236.0 | BLEA #1298 PR と一致 |
| 6 | テスト | ✅ 14/14 pass | |
| 7 | Conventional commit | - | PR 提出時に使用 |
| 8 | bilingual docs | ✅ | README_ja.md + README.md |
| 9 | 個人情報なし | ✅ | grep 確認済み |
| 10 | scripts/ 不要ファイル | ⚠️ | deploy-and-verify.sh, generate-test-data.py は PR に含めるか判断 |
| 11 | doc/issue-draft.md | ❌ 不要 | PR には含めない |
| 12 | doc/verification-results/ | ❌ 不要 | PR には含めない（エビデンスは Issue コメントに） |

### PR に含めるべきファイル（最小限）

```
usecases/blea-guest-fsxn-data-analytics-sample/
├── bin/blea-guest-fsxn-data-analytics-sample.ts
├── lib/
│   ├── stack/blea-guest-fsxn-data-analytics-sample-stack.ts
│   └── construct/
│       ├── networking.ts
│       ├── fsxn-storage.ts
│       ├── s3-access-point.ts
│       ├── data-analytics.ts
│       └── monitoring.ts
├── test/
│   ├── snapshot.test.ts
│   └── fsxn-data-analytics.test.ts
├── parameter.ts
├── package.json
├── tsconfig.json
├── cdk.json
├── jest.config.js
└── .gitignore
```

**含めない（開発ツール・エビデンス）:**
- `scripts/` — 検証用スクリプト（BLEA upstream にはこのパターンがない）
- `doc/verification-results/` — エビデンスは Issue コメントに
- `doc/issue-draft.md` — Issue は別途提出済み
- `doc/README_ja.md`, `doc/README.md` — BLEA upstream では `usecases/` 直下にREADMEを置くか、`doc/` に置くかの確認が必要

### PR 文面案（短く）

```
feat: add FSx for NetApp ONTAP data analytics guest system use case

This adds a new guest system use case demonstrating enterprise file storage
with FSx for ONTAP integrated with AWS analytics services via S3 Access Points.

Closes #1303

## Changes
- Add `usecases/blea-guest-fsxn-data-analytics-sample/`
- FSx for ONTAP + S3 AP + Glue + Athena, single stack, 5 constructs
- All CloudFormation native (no custom resources)
- Bilingual documentation
- 14 Jest tests (snapshot + assertion)
- Deployment verified in real AWS account

## Architecture
FSx for ONTAP (NFS/SMB) → S3 Access Point → Glue Crawler → Data Catalog → Athena SQL
```

---

## 次のアクション

1. Fork 内で ESLint / Prettier を通す
2. 不要ファイル削除
3. package-lock.json 生成
4. ブランチ作成 → commit → push → PR
