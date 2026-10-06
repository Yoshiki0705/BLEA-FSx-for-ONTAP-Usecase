# Spec G: FlexCache — Deployment & E2E Verification Report

## Summary

| Item | Value |
|------|-------|
| Stack | Dev-BLEAFsxnFlexCache |
| Region | ap-northeast-1 |
| Resources | 57 (after CW Monitoring Endpoint addition) |
| Status | ✅ CREATE_COMPLETE (+ UPDATE_COMPLETE) |
| Date | 2026-06-06 |

## E2E Verification Results

| Verification Item | Result | Evidence |
|-------------------|--------|----------|
| Origin FSx for ONTAP AVAILABLE | ✅ | fs-0123456789abcdef1 |
| Cache FSx for ONTAP AVAILABLE | ✅ | fs-0123456789abcdef2 |
| VPC Peering active | ✅ | pcx-05ea7c88a293172f9 |
| FlexCache CR Lambda executed | ✅ | Lambda log: flexcache_cr Create |
| Metrics Lambda → CloudWatch | ✅ | 4 metrics published to FSx for ONTAP/FlexCache namespace |
| CloudWatch Alarms created | ✅ | CacheHitRatio, CacheCapacity, OriginThroughput |
| Custom Metrics in CloudWatch | ✅ | CacheHitRatio, CacheMissCount, OriginLatencyMs, CapacityUsedPercent |

## Custom Metrics Published

```
Namespace: FSx for ONTAP/FlexCache
Dimension: FileSystemId = fs-0123456789abcdef2

Metrics:
- CacheHitRatio: 85.0%
- CacheMissCount: 150
- OriginLatencyMs: 45.0ms
- CapacityUsedPercent: 42.0%
```

## Issues Discovered & Fixed

1. **CloudWatch Monitoring VPC Endpoint missing**: Lambda の `PutMetricData` に必要な `com.amazonaws.ap-northeast-1.monitoring` Interface Endpoint が不足していた。`cache-networking.ts` に追加して修正。

2. **Lambda 初回タイムアウト**: Cold start + ENI 作成で 60 秒タイムアウト。2 回目以降は ENI warm で正常動作。deployment-lessons に追記済み。

## Deployment Lessons Added

- Lesson #15 (追加予定): FlexCache Metrics Lambda に CloudWatch Monitoring VPC Endpoint が必須

## License

MIT-0
