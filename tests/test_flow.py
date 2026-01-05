from enterpriseagents.agents.builder import BuilderAgent
from enterpriseagents.agents.director import DirectorAgent
from enterpriseagents.agents.docs import DocsAgent
from enterpriseagents.agents.reviewer import ReviewerAgent
from enterpriseagents.audit.logger import AuditLogger
from enterpriseagents.core.run import RunCoordinator, RunRequest
from enterpriseagents.policy.policy import PolicyEngine
from enterpriseagents.tools.registry import ToolRegistry


from enterpriseagents.core.router import DynamicRouter
from enterpriseagents.memory.store import MemoryStore

def test_end_to_end_flow(tmp_path, mock_llm):
    """Verify the whole lifecycle works with a fake brain."""
    
    # Setup
    workspace = tmp_path / "workspace"
    runs_dir = tmp_path / "runs"
    
    audit = AuditLogger(runs_dir=runs_dir, run_id="test-run")
    policy = PolicyEngine()
    tools = ToolRegistry.default()
    
    # New dependencies
    memory_path = tmp_path / "memory.db"
    memory = MemoryStore(db_path=memory_path)
    router = DynamicRouter(llm=mock_llm)
    
    # Wired up agents
    director = DirectorAgent(llm=mock_llm)
    builder = BuilderAgent(llm=mock_llm)
    reviewer = ReviewerAgent(tools=tools)
    docs = DocsAgent(llm=mock_llm)
    
    coordinator = RunCoordinator(
        run_id="test-run",
        audit=audit,
        policy=policy,
        tools=tools,
        director=director,
        builder=builder,
        reviewer=reviewer,
        docs=docs,
        router=router,
        memory=memory,
    )
    
    # Execute
    coordinator.execute(RunRequest(
        instruction="Build a mock app", 
        workspace=str(workspace)
    ))
    
    # Assertions
    # 1. Did it create the workspace?
    assert workspace.exists()
    
    # 2. Did Builder write the file mock_llm proposed?
    assert (workspace / "mock.txt").exists()
    assert (workspace / "mock.txt").read_text() == "hi"
    
    # 3. Did Docs write the README?
    assert (workspace / "README.md").exists()
    
    # 4. Did we get audit logs?
    assert (runs_dir / "test-run" / "run_packet.json").exists()
