# Issue Draft: aws-samples/baseline-environment-on-aws

> 提出先: https://github.com/aws-samples/baseline-environment-on-aws/issues
> ステータス: レビュー済み（全ペルソナ PASS）、提出可能

---

## Title

`[Feature Request] Add FSx for NetApp ONTAP data analytics guest system use case`

## Body

### Summary

I would like to propose a new guest system use case that demonstrates enterprise file storage with Amazon FSx for NetApp ONTAP, integrated with AWS analytics services via S3 Access Points.

### Business Problem

Enterprise organizations store critical business data on file servers (NFS/SMB), but this data remains siloed and inaccessible to analytics tools. Traditional approaches require copying file data to S3 and building ETL pipelines — adding cost, latency, and operational complexity.

This use case removes the copy step: file data on FSx for ONTAP is queried via SQL through S3 Access Points, the Glue Data Catalog, and Amazon Athena, with no ETL pipeline.

### Motivation

BLEA currently provides guest system samples for ECS web apps, EC2 web apps, and Serverless APIs. However, there is no sample covering:
- Enterprise file storage provisioning with CDK
- Data analytics without data duplication
- Integration between storage and analytics services

Amazon FSx for NetApp ONTAP launched S3 Access Points in December 2025, making this integration possible natively via CloudFormation (`AWS::FSx::S3AccessPointAttachment`).

### Proposed Architecture

![Architecture](doc/images/architecture.png)

```
[BLEA Governance Base]
    │
[FSx for ONTAP Data Analytics Guest System]
    ├── VPC (Multi-AZ, Private Subnets, VPC Endpoints, No Internet)
    ├── Amazon FSx for NetApp ONTAP (Multi-AZ, KMS encrypted)
    │   ├── Storage Virtual Machine (UNIX)
    │   ├── Volume (NFS, dedup + compression, FabricPool AUTO)
    │   └── S3 Access Point (Internet-origin, UNIX identity)
    ├── AWS Glue (Database + Crawler → auto-catalog via S3 AP)
    ├── Amazon Athena (Workgroup, enforced config, KMS results)
    └── Monitoring (CloudWatch Alarms + SNS + Chatbot)
```

### Key Design Decisions

- **Single stack** (like blea-guest-serverless-api-sample)
- **5 constructs**: Networking, FsxnStorage, S3AccessPoint, DataAnalytics, Monitoring
- **All CloudFormation native** — no Custom Resources needed
- **Lake Formation integration** via `CfnPrincipalPermissions` for Glue Crawler
- **parameter.ts** with dev (SINGLE_AZ_1, $500/mo) and prod (MULTI_AZ_1, $1500/mo)

### Implementation Status

| Item | Status |
|---|---|
| CDK code complete (TypeScript strict, aws-cdk-lib ^2.219.0) | ✅ |
| 14 Jest tests passing (snapshot + assertion) | ✅ |
| Real AWS deployment verified (ap-northeast-1, end-to-end data flow confirmed) | ✅ |
| Bilingual documentation (Japanese primary + English) | ✅ |
| Cost estimates included | ✅ |

### Verified End-to-End Data Flow

| Step | Result | Status |
|---|---|---|
| NFS write → FSx for ONTAP Volume | written | ✅ |
| S3 AP ListObjects | file data visible | ✅ |
| Glue Crawler | table auto-detected (300K rows, 45s) | ✅ |
| Athena SQL query | results returned (14.5MB, 2.1s) | ✅ |
| CloudWatch Alarms | monitoring active | ✅ |

### Checklist

- [x] TypeScript CDK v2 (aws-cdk-lib)
- [x] Single stack, independently deployable
- [x] parameter.ts for configuration
- [x] Monitoring with CloudWatch + SNS + Chatbot
- [x] Snapshot tests + assertion tests
- [x] Bilingual documentation (Japanese + English)
- [x] MIT-0 license compatible
- [x] No real account IDs or secrets in code
- [x] Deployment verified in real AWS account

### Related Resources

- [S3 Access Points for FSx for ONTAP (Dec 2025)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-fsx-netapp-ontap-s3-access/)
- [AWS::FSx::S3AccessPointAttachment](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-fsx-s3accesspointattachment.html)
- [Using access points with AWS services](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/using-access-points-with-aws-services.html)

### Next Steps

If maintainers are interested, I will:
1. Fork the repository
2. Add the use case to `usecases/blea-guest-fsxn-data-analytics-sample/`
3. Submit a PR with full code, tests, and documentation

I'm happy to discuss the design and adjust based on feedback.
