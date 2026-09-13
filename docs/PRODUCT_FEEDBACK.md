# Product Feedback Working File

**Rule:** only submit feedback based on tools actually used. Do not invent onboarding experiences or API behaviour.

## Alexa+ / Alexa AI CLI

Status: **Not yet tested in this build environment.**

Once access is available, record:

- task attempted
- exact tool/API used
- what worked well
- what was confusing or blocked
- onboarding quality
- whether we would build with it again
- specific documentation or developer-experience recommendation

## MCP Python SDK

Status: source integration implemented from current official documentation; runtime package installation could not be completed inside the isolated build sandbox because that sandbox has no external package-network access.

Do not attribute the sandbox network restriction to Amazon or the MCP SDK.

After running the repository in a connected environment, capture actual feedback on:

- Streamable HTTP setup
- transport-security configuration
- MCP Inspector workflow
- tool schema generation
- deployment behaviour

## Amazon Bedrock

Status: integration code implemented; live AWS call not executed in this isolated build environment.

Before submission, test with the AWS account intended for the hackathon and record factual feedback on:

- model access setup
- Converse API clarity
- latency
- error messages
- IAM setup
- usefulness for controlled explanation tasks
