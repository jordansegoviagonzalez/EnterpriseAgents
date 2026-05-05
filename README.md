![alt text](enterpriseagents_logo_v3.gif)
# Enterprise Agents

Enterprise Agents is an orchestration layer designed to transform Large Language Models into capable delivery engines. By connecting intelligent models such as OpenAI, DeepSeek, or Ollama to a structured environment, this system enables the reliable execution of complex software engineering tasks.

The core philosophy of this project is to turn a single instruction into a verified artifact bundle, complete with a full audit trail.

## Why the Verified Run System Matters

Large Language Models excel at reasoning and drafting content but often struggle with the rigorous demands of completing multi-step engineering projects. Common challenges include drifting from the original plan, executing unsafe commands, and failing to provide objective proof of completion.

Our **Verified Run System** introduces a necessary enterprise governance layer to solve these issues. It employs an event-driven Kanban board to manage workflow state and enforces strict policy gates on all tool executions. Every action is subject to deterministic quality checks and is recorded in an immutable audit log, ensuring that the final output is both correct and reproducible.

## Sprint 1: Local Verified Run

For Sprint 1, you can test the orchestration logic completely locally without any paid APIs using the deterministic local scaffold.

To begin working with the system, first create an isolated Python environment and install the package with development dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run a deterministic local execution:
```bash
enterpriseagents run "Scaffold a tiny Python CLI app with tests and a README" --workspace ./workspace --local
```

### Expected Output Folder Structure

After running, the system guarantees the generation of both the workspace artifacts and the comprehensive run proof:

```text
workspace/
├── app.py
├── test_app.py
└── README.md

runs/<run_id>/
├── metadata.json
├── plan.json
├── task_graph.json
├── tool_calls.jsonl
├── policy_decisions.jsonl
├── test_results.txt
├── events.jsonl
├── tool_results.jsonl
└── evidence_packet.md
```

## System Architecture

The framework is composed of specialized agents that collaborate to achieve the user's goal.

- **Director Agent:** Analyzes the instruction and decomposes it into tasks with specific acceptance criteria.
- **Builder Agent:** Proposes concrete actions such as writing files or executing shell commands.
- **Reviewer Agent:** Runs verified checks against the work produced to ensure it meets the acceptance criteria.
- **Documentation Agent:** Generates comprehensive guides and usage instructions based on the actual artifacts produced.

All operations are governed by a central Policy Engine that evaluates every proposed tool call against a strict set of rules. This ensures that no unsafe or unauthorized actions are taken during the execution of the workflow.

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

## What is Not Implemented Yet

- **Web Dashboard:** The React/TypeScript/Vite dashboard is planned but not started.
- **SQLite Storage:** Audit logs are currently written to local files, not SQLite.
- **Full Human-in-the-Loop:** Policy decisions are mocked to allow execution; interactive approval gates are pending.
- **Extensive Model Support:** Full LLM routing (Anthropic, Ollama, etc.) is structurally supported but not deeply integrated.

## Licensing

This project is released under the MIT License. Please refer to the license file for full terms and conditions.