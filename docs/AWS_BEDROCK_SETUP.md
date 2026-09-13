# Amazon Bedrock setup for HomeOps AI

## Purpose

HomeOps uses Amazon Bedrock only as an explanation layer after the deterministic commercial-control engine has already decided whether an invoice is within the approved baseline or must be held. Bedrock cannot overturn the policy decision.

## Recommended model

For the hackathon MVP, use Amazon Nova 2 Lite in `us-east-1`:

```env
BEDROCK_ENABLED=true
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-2-lite-v1:0
```

If your account requires a cross-Region inference profile for this model, use the appropriate profile ID available in your Bedrock account, for example a US geography profile, instead of the direct model ID.

## Credentials

Do not put AWS secret keys in `.env`, source control, screenshots, or the Devpost submission.

Use the standard AWS credential chain. For local Windows development, the simplest options are:

1. AWS CLI profile (`aws configure` or AWS SSO), then optionally set `AWS_PROFILE=<profile-name>` in `.env`.
2. Environment credentials managed outside the repository.
3. An IAM role when deployed on AWS.

## Minimum runtime permission

HomeOps calls the Bedrock Runtime `Converse` API. The underlying inference permission is `bedrock:InvokeModel`.

For a hackathon-only IAM identity using the direct Nova 2 Lite foundation model, start with a narrowly scoped policy such as:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "HomeOpsNova2LiteInference",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-2-lite-v1:0"
    }
  ]
}
```

If you use a cross-Region inference profile, its IAM resource requirements are broader because the request may route to destination Regions. Follow the Bedrock inference-profile IAM documentation rather than guessing resource ARNs.

## Local verification

After credentials are configured, update `.env`:

```env
BEDROCK_ENABLED=true
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-2-lite-v1:0
```

Restart HomeOps, then run:

```powershell
python -m scripts.test_bedrock
```

A successful response contains:

```json
{
  "success": true,
  "source": "bedrock",
  "response_text": "BEDROCK_OK"
}
```

The exact model output can vary slightly; the important evidence is `success: true`, `source: bedrock`, an AWS request ID, and token usage.

You can also open the HomeOps UI and click **Test Bedrock**. The badge changes to **Bedrock live** only after a successful real model invocation.

## Golden demo evidence

Run the normal AC workflow after Bedrock is live. The final invoice review records:

- deterministic decision (`HOLD_FOR_APPROVAL` for the $135 vs $95 case)
- Bedrock-generated explanation
- model ID
- AWS request ID
- latency
- token usage
- fallback error, if Bedrock was unavailable

This creates auditable evidence that AWS was actually used while preserving deterministic commercial controls.
