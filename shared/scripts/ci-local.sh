#!/bin/bash
set -euo pipefail

# ローカル CI 実行スクリプト
# push 前に実行して CI 失敗を事前検出する
#
# Usage: bash shared/scripts/ci-local.sh

echo "============================================"
echo " Local CI Check"
echo " $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "============================================"

ERRORS=0

# 1. eslint
echo ""
echo "▶ ESLint..."
if npx eslint "usecases/**/*.ts" "shared/**/*.ts" --max-warnings 50 2>/dev/null; then
  echo "  ✅ ESLint passed"
else
  echo "  ❌ ESLint failed"
  ERRORS=$((ERRORS + 1))
fi

# 2. prettier
echo ""
echo "▶ Prettier..."
if npx prettier --check "usecases/**/*.ts" "shared/**/*.ts" 2>/dev/null; then
  echo "  ✅ Prettier passed"
else
  echo "  ❌ Prettier failed (run: npx prettier --write 'usecases/**/*.ts' 'shared/**/*.ts')"
  ERRORS=$((ERRORS + 1))
fi

# 3. Personal info check
echo ""
echo "▶ Personal info check..."
# Generic rules plus .sensitive-patterns.private when present (gitignored)
if python3 tools/check_sensitive.py; then
  echo "  ✅ No personal info"
else
  echo "  ❌ Account ID, IP address, email, or local pattern found (see above)"
  ERRORS=$((ERRORS + 1))
fi

# 4. Tests
echo ""
echo "▶ Tests..."
PASS=0
FAIL=0
for SPEC in usecases/blea-guest-fsxn-data-analytics-sample usecases/guest-fsxn-cyber-resilience-sample usecases/blea-guest-fsxn-flexcache-sample usecases/blea-guest-fsxn-modernization-sample; do
  NAME=$(basename "$SPEC")
  RESULT=$(cd "$SPEC" && npx jest --no-coverage 2>&1 | grep "^Tests:" || echo "FAIL")
  if echo "$RESULT" | grep -q "passed"; then
    PASS=$((PASS + 1))
  else
    echo "  ❌ $NAME: $RESULT"
    FAIL=$((FAIL + 1))
  fi
done
if [ $FAIL -eq 0 ]; then
  echo "  ✅ All $PASS specs passed"
else
  echo "  ❌ $FAIL spec(s) failed"
  ERRORS=$((ERRORS + 1))
fi

# 5. CDK Synth
echo ""
echo "▶ CDK Synth..."
SYNTH_FAIL=0
for SPEC in usecases/blea-guest-fsxn-data-analytics-sample usecases/guest-fsxn-cyber-resilience-sample usecases/blea-guest-fsxn-flexcache-sample usecases/blea-guest-fsxn-modernization-sample; do
  if ! (cd "$SPEC" && npx cdk synth --quiet 2>/dev/null); then
    echo "  ❌ $(basename "$SPEC") synth failed"
    SYNTH_FAIL=$((SYNTH_FAIL + 1))
  fi
done
if [ $SYNTH_FAIL -eq 0 ]; then
  echo "  ✅ All specs synthesize"
else
  ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "============================================"
if [ $ERRORS -eq 0 ]; then
  echo " ✅ All checks passed! Safe to push."
else
  echo " ❌ $ERRORS check(s) failed. Fix before pushing."
fi
echo "============================================"

exit $ERRORS
