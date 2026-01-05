# Product Roadmap

## Current Release

The current version of the system establishes the core foundation for event-driven orchestration. It includes the complete set of agent roles, including the Director, Builder, Reviewer, and Documentation agents. The tooling layer supports file system operations, git integration, and governed shell execution. The security model enforces allowlists and approval flows, while the audit system captures a full run packet with structured logs.

## Upcoming Features

The next release will focus on resilience and scalability. We plan to introduce durable checkpoints that allow runs to be paused and resumed without data loss. We will also add support for template packs to accelerate the creation of common project types. Furthermore, we intend to enable parallel task execution where it is safe to do so, improving overall throughput.

## Long Term Vision

Our long-term vision includes the development of standardized connectors for external tools and the implementation of fully sandboxed runtime environments for tool execution. We also plan to build a web-based user interface that provides a visual representation of the Kanban board, facilitates approval workflows, and offers a dashboard for reviewing run packets.