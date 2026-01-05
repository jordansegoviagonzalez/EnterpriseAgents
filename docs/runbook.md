# Operational Runbook

## Local Development Setup

To set up the development environment locally, install the package along with its development dependencies using the standard pip command.

Once installed, you can execute a test run by issuing a command to the enterpriseagents CLI. We recommend enabling the dry-run mode for initial tests, as this allows you to observe the planned actions without making any changes to your file system.

## Troubleshooting

When investigating issues, the primary source of information is the run evidence directory. This location contains comprehensive logs of the entire workflow. The events log provides a timeline of state changes, while the tool calls and results logs offer detailed insight into the specific actions taken by the agents. The approvals log records the decisions made by the policy engine.

## Common Issues and Resolutions

If a command is denied execution, it is likely because it does not match any of the patterns in the policy allowlist. To resolve this, you may need to update the policy configuration to include the necessary command pattern.

Failures during tool execution should be investigated by examining the tool results log, which captures the standard output and error streams from the command. If a task fails the verification stage, the Reviewer agent will emit a specific failure event detailing which acceptance criteria were not met.