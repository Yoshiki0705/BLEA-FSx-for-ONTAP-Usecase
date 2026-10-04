import * as cdk from 'aws-cdk-lib';
import {
  aws_ec2 as ec2,
  aws_iam as iam,
  aws_lambda as lambda,
  aws_lambda_event_sources as eventsources,
  aws_logs as logs,
  aws_sns as sns,
  aws_sqs as sqs,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

export interface ServerlessOpsProps {
  vpc: ec2.IVpc;
  lambdaSecurityGroup: ec2.ISecurityGroup;
  fileSystemId: string;
  alarmTopic: sns.ITopic;
  maxCapacityGiB: number;
}

/**
 * Serverless Operations Automation: CapacityManager.
 *
 * Auto-expands FSx for ONTAP storage when capacity exceeds threshold.
 * Triggered by SNS alarm topic (from CloudWatch StorageCapacityUtilization alarm).
 * Guard: will NOT expand beyond maxCapacityGiB parameter.
 * Cooldown: checks FileSystem status before attempting expansion.
 */
export class ServerlessOps extends Construct {
  public readonly capacityManagerFn: lambda.IFunction;

  constructor(scope: Construct, id: string, props: ServerlessOpsProps) {
    super(scope, id);

    const region = cdk.Stack.of(this).region;

    // DLQ for failed capacity operations
    const dlq = new sqs.Queue(this, 'CapacityManagerDLQ', {
      retentionPeriod: cdk.Duration.days(7),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
    });

    // CapacityManager Lambda
    this.capacityManagerFn = new lambda.Function(this, 'CapacityManager', {
      runtime: lambda.Runtime.NODEJS_22_X,
      handler: 'index.handler',
      code: lambda.Code.fromInline(`
const { FSxClient, DescribeFileSystemsCommand, UpdateFileSystemCommand } = require('@aws-sdk/client-fsx');
const { SNSClient, PublishCommand } = require('@aws-sdk/client-sns');

exports.handler = async (event) => {
  const fsId = process.env.FILE_SYSTEM_ID;
  const maxGiB = parseInt(process.env.MAX_CAPACITY_GIB);
  const topicArn = process.env.ALARM_TOPIC_ARN;
  const region = process.env.AWS_REGION;
  const EXPAND_INCREMENT_GIB = 1024; // 1 TiB per expansion

  const fsx = new FSxClient({ region });
  const sns = new SNSClient({ region });

  // 1. Get current file system state
  const descResp = await fsx.send(new DescribeFileSystemsCommand({ FileSystemIds: [fsId] }));
  const fs = descResp.FileSystems[0];
  const currentGiB = fs.StorageCapacity;
  const lifecycle = fs.Lifecycle;

  console.log(JSON.stringify({
    event: 'capacity_check',
    fileSystemId: fsId,
    currentGiB,
    maxGiB,
    lifecycle,
  }));

  // 2. Cooldown: skip if FSx is already updating (scaling in progress)
  if (lifecycle !== 'AVAILABLE') {
    console.log(JSON.stringify({
      event: 'skipped_not_available',
      lifecycle,
      reason: 'FSx for ONTAP is not in AVAILABLE state (likely scaling in progress)',
    }));
    return { status: 'SKIPPED', reason: 'lifecycle=' + lifecycle, currentGiB };
  }

  // 3. Check if storage scaling is already pending
  const adminActions = fs.AdministrativeActions || [];
  const pendingScale = adminActions.find(
    a => a.AdministrativeActionType === 'FILE_SYSTEM_UPDATE' && a.Status === 'IN_PROGRESS'
  );
  if (pendingScale) {
    console.log(JSON.stringify({
      event: 'skipped_scaling_in_progress',
      targetGiB: pendingScale.TargetFileSystemValues?.StorageCapacity,
    }));
    return { status: 'SKIPPED', reason: 'scaling already in progress', currentGiB };
  }

  // 4. Calculate new capacity
  const newGiB = Math.min(currentGiB + EXPAND_INCREMENT_GIB, maxGiB);

  if (newGiB <= currentGiB) {
    const msg = { fileSystemId: fsId, currentGiB, maxGiB, action: 'BLOCKED - at max capacity' };
    await sns.send(new PublishCommand({
      TopicArn: topicArn,
      Subject: '[WARN] FSx for ONTAP at max capacity - cannot auto-expand',
      Message: JSON.stringify(msg, null, 2),
    }));
    console.log(JSON.stringify({ event: 'at_max_capacity', ...msg }));
    return { status: 'AT_MAX', currentGiB, maxGiB };
  }

  // 5. Expand storage
  await fsx.send(new UpdateFileSystemCommand({
    FileSystemId: fsId,
    StorageCapacity: newGiB,
  }));

  const successMsg = {
    fileSystemId: fsId,
    previousGiB: currentGiB,
    newGiB,
    incrementGiB: EXPAND_INCREMENT_GIB,
    maxGiB,
    remainingHeadroomGiB: maxGiB - newGiB,
    action: 'EXPANDED',
  };

  await sns.send(new PublishCommand({
    TopicArn: topicArn,
    Subject: '[INFO] FSx for ONTAP storage auto-expanded: ' + currentGiB + ' → ' + newGiB + ' GiB',
    Message: JSON.stringify(successMsg, null, 2),
  }));

  console.log(JSON.stringify({ event: 'capacity_expanded', ...successMsg }));
  return { status: 'EXPANDED', previousGiB: currentGiB, newGiB };
};
`),
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      securityGroups: [props.lambdaSecurityGroup],
      timeout: cdk.Duration.seconds(60),
      reservedConcurrentExecutions: 1,
      deadLetterQueue: dlq,
      logGroup: new logs.LogGroup(this, 'CapacityManagerLogs', { retention: logs.RetentionDays.ONE_MONTH }),
      environment: {
        FILE_SYSTEM_ID: props.fileSystemId,
        MAX_CAPACITY_GIB: props.maxCapacityGiB.toString(),
        ALARM_TOPIC_ARN: props.alarmTopic.topicArn,
      },
    });

    // IAM: FSx UpdateFileSystem + Describe (scoped to specific file system)
    this.capacityManagerFn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['fsx:UpdateFileSystem', 'fsx:DescribeFileSystems'],
        resources: [`arn:aws:fsx:${region}:${cdk.Stack.of(this).account}:file-system/${props.fileSystemId}`],
      }),
    );
    props.alarmTopic.grantPublish(this.capacityManagerFn);

    // Trigger: SNS alarm topic → Lambda
    // When StorageCapacityUtilization alarm fires, it publishes to the alarm topic,
    // which triggers this Lambda to auto-expand storage.
    this.capacityManagerFn.addEventSource(new eventsources.SnsEventSource(props.alarmTopic));
  }
}
