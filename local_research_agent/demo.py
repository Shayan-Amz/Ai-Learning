from pathlib import Path

from .core import ResearchAgent
from .planner import DemoPlanner
from .tools import build_read_only_tools


def main() -> None:
    knowledge_dir = Path(__file__).with_name("knowledge")
    tools = build_read_only_tools(knowledge_dir)
    agent = ResearchAgent(DemoPlanner(), tools, max_steps=3)
    goal = "Find a local note about human approval."
    result = agent.run(goal)

    print(f"Goal: {goal}")
    print("Answer:")
    print(result.answer)
    print(f"Stop reason: {result.stop_reason}")
    print(f"Tool calls: {len(result.observations)}")
    for observation in result.observations:
        status = "error" if observation.error else "ok"
        print(f"- {observation.tool_name}: {status}")


if __name__ == "__main__":
    main()
