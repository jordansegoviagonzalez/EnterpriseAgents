# Enterprise Agents

Enterprise Agents is an orchestration layer designed to transform Large Language Models into capable delivery engines. By connecting intelligent models such as OpenAI, DeepSeek, or Ollama to a structured environment, this system enables the reliable execution of complex software engineering tasks.

The core philosophy of this project is to turn a single instruction into a verified artifact bundle, complete with a full audit trail.

## The Problem and Solution

Large Language Models excel at reasoning and drafting content but often struggle with the rigorous demands of completing multi-step engineering projects. Common challenges include drifting from the original plan, executing unsafe commands, and failing to provide objective proof of completion.

This framework introduces a necessary enterprise governance layer to solve these issues. It employs an event-driven Kanban board to manage workflow state and enforces strict policy gates on all tool executions. Every action is subject to deterministic quality checks and is recorded in an immutable audit log, ensuring that the final output is both correct and reproducible.

## Quick Start Guide

To begin working with the system, first create an isolated Python environment and install the package with development dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Next, configure your preferred language model. The system supports OpenAI by default but is fully compatible with DeepSeek and local Ollama instances. You will need to export your API key as an environment variable.

```bash
export EA_OPENAI_API_KEY="sk-..."
```

Once configured, you can initiate a workflow by providing a natural language instruction.

```bash
enterpriseagents run "Scaffold a tiny Python CLI app with tests and a README" --workspace ./workspace
```

The system includes a dry-run capability that allows you to preview proposed actions without executing them. This is useful for verifying the plan before committing to any changes.

## System Architecture

The framework is composed of specialized agents that collaborate to achieve the user's goal.

The Director Agent is responsible for analyzing the initial instruction and decomposing it into a logical plan of tasks, each with specific acceptance criteria.

The Builder Agent functions as the primary engineer, proposing concrete actions such as writing files or executing shell commands to complete the assigned tasks.

The Reviewer Agent acts as a quality assurance gate, running verified checks against the work produced to ensure it meets the acceptance criteria.

The Documentation Agent ensures that the final deliverable is properly documented, generating comprehensive guides and usage instructions based on the actual artifacts produced.

All operations are governed by a central Policy Engine that evaluates every proposed tool call against a strict set of rules. This ensures that no unsafe or unauthorized actions are taken during the execution of the workflow.

## Audit and Compliance

A key feature of Enterprise Agents is its commitment to transparency and auditability. Every run produces a comprehensive evidence packet located in the runs directory. This packet includes a complete timeline of events, a record of all tool calls and their results, and a log of all policy decisions and approvals. This data provides an objective proof of work and allows for detailed post-run analysis.

## Development and Testing

The project includes a comprehensive test suite that utilizes a mock language model. This allows developers to verify the internal logic and orchestration flow without incurring costs or requiring network access to external APIs.

To run the full test suite, execute the following command:

```bash
pytest
```

We adhere to strict code quality standards. You can verify compliance by running the linting and type-checking tools.

```bash
ruff check .
mypy enterpriseagents
```

## Licensing

This project is released under the MIT License. Please refer to the license file for full terms and conditions.