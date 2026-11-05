from collections.abc import Sequence

from .core import Action, FinalAnswer, Observation, ToolCall


class DemoPlanner:
    """A deterministic planner used to teach and test the agent loop."""

    def choose_next_action(
        self,
        goal: str,
        observations: Sequence[Observation],
    ) -> Action:
        if not observations:
            query = "human approval" if "approval" in goal.casefold() else "agent"
            return ToolCall("search_documents", {"query": query})

        last = observations[-1]
        if last.error:
            return FinalAnswer("A local tool failed. Inspect the trace before retrying.")

        if last.tool_name == "search_documents":
            results = last.result
            if not isinstance(results, list) or not results:
                return FinalAnswer("No matching local document was found.")
            first = results[0]
            if not isinstance(first, dict) or not isinstance(first.get("path"), str):
                return FinalAnswer("Search returned an unexpected result.")
            arguments = {"path": first["path"]}
            line = first.get("line")
            if isinstance(line, int):
                arguments["line"] = str(line)
            return ToolCall("read_document", arguments)

        if last.tool_name == "read_document" and isinstance(last.result, dict):
            path = last.result.get("path")
            content = last.result.get("content")
            if isinstance(path, str) and isinstance(content, str):
                return FinalAnswer(f"Source: {path}\n{content}")

        return FinalAnswer("Research is complete.")
