from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from local_research_agent.core import (
    Action,
    Citation,
    FinalAnswer,
    Observation,
    PlannerError,
    ResearchAgent,
    ToolCall,
    ToolError,
    ToolRegistry,
)
from local_research_agent.tools import build_read_only_tools

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "local_research_agent" / "knowledge"


class FirstActionPlanner:
    def __init__(self, action: Action):
        self.action = action

    def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
        return self.action


def test_agent_refuses_to_finish_without_searching_documents():
    agent = ResearchAgent(FirstActionPlanner(FinalAnswer("Unverified answer")), ToolRegistry({}))

    result = agent.run("What is in my notes?")

    assert result.stop_reason == "no_evidence"
    assert "no research answer" in result.answer.casefold()


def test_agent_requires_search_as_the_first_tool_action():
    class ReadFirst:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            if not observations:
                return ToolCall("read_document", {"path": "safe-tool-use.md"})
            return FinalAnswer("The planner tried to skip search.")

    agent = ResearchAgent(ReadFirst(), build_read_only_tools(KNOWLEDGE_DIR))
    result = agent.run("Read a note directly")

    assert result.stop_reason == "no_evidence"
    assert (
        result.observations[0].error
        == "The first research action must search the approved documents."
    )


def test_agent_requires_read_path_to_come_from_a_prior_search():
    calls: list[str] = []

    def search(arguments: dict[str, object]) -> list[dict[str, object]]:
        return [{"path": "approved.md", "start_line": 1, "end_line": 1}]

    def read(arguments: dict[str, object]) -> dict[str, object]:
        calls.append(str(arguments.get("path")))
        return {"path": "approved.md", "start_line": 1, "end_line": 1, "content": "1: evidence"}

    tools = ToolRegistry({"search_documents": search, "read_document": read})

    class Guesser:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            if not observations:
                return ToolCall("search_documents", {"query": goal})
            if len(observations) == 1:
                return ToolCall("read_document", {"path": "guessed-private.md"})
            return FinalAnswer("I found evidence.")

    result = ResearchAgent(Guesser(), tools, max_steps=3).run("search")

    assert calls == []
    assert result.stop_reason == "no_evidence"
    assert result.observations[1].error == (
        "A document must be returned by a prior search before it can be read."
    )


def test_agent_withholds_answer_when_search_hit_was_not_read():
    class SearchThenFinish:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            if not observations:
                return ToolCall("search_documents", {"query": "human approval"})
            return FinalAnswer("Unsupported synthesis")

    result = ResearchAgent(
        SearchThenFinish(),
        build_read_only_tools(KNOWLEDGE_DIR),
    ).run("Find human approval")

    assert result.stop_reason == "no_evidence"
    assert "was found but not read" in result.answer


def test_agent_requires_valid_citations_after_reading_evidence():
    class ReadThenUncited:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            if not observations:
                return ToolCall("search_documents", {"query": "human approval"})
            if len(observations) == 1:
                hit = observations[0].result[0]
                return ToolCall(
                    "read_document",
                    {
                        "path": hit["path"],
                        "start_line": hit["start_line"],
                        "end_line": hit["end_line"],
                    },
                )
            return FinalAnswer("This response has no verifiable reference.")

    result = ResearchAgent(ReadThenUncited(), build_read_only_tools(KNOWLEDGE_DIR)).run(
        "Find human approval"
    )

    assert result.stop_reason == "citation_error"
    assert result.citations == ()
    assert "withheld" in result.answer


def test_agent_rejects_an_invalid_planner_action():
    result = ResearchAgent(FirstActionPlanner("not-an-action"), ToolRegistry({})).run("Research")

    assert result.stop_reason == "invalid_action"
    assert "invalid action" in result.answer.casefold()


def test_agent_gives_actionable_safe_message_when_local_model_is_unreachable():
    class UnreachableModel:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            raise PlannerError("The configured model could not be reached.")

    result = ResearchAgent(UnreachableModel(), ToolRegistry({})).run("Research")

    assert result.stop_reason == "planner_error"
    assert "make sure it is running" in result.answer
    assert ".env" in result.answer


def test_agent_stops_cleanly_on_a_planner_failure():
    class BrokenPlanner:
        def choose_next_action(self, goal: str, observations: Sequence[Observation]) -> Action:
            raise PlannerError("do not expose provider internals")

    result = ResearchAgent(BrokenPlanner(), ToolRegistry({})).run("Research")

    assert result.stop_reason == "planner_error"
    assert "provider internals" not in result.answer


def test_agent_retries_after_ungrounded_answer_and_forces_another_read(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "nanofluid.md").write_text(
        "Slide title: DLVO\n"
        "DLVO interactions support nanofluid stability by balancing attractive and repulsive forces.\n",
        encoding="utf-8",
    )
    tools = build_read_only_tools(knowledge_dir)

    class RetryPlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            feedback_index = next(
                (
                    index
                    for index, observation in enumerate(observations)
                    if observation.tool_name == "answer_validation"
                ),
                None,
            )
            if not observations:
                return ToolCall("search_documents", {"query": "DLVO"})
            if feedback_index is None:
                if len(observations) == 1:
                    return ToolCall(
                        "read_document",
                        {"path": "nanofluid.md", "start_line": 1, "end_line": 1},
                    )
                return FinalAnswer(
                    "DLVO theory improves electrostatic stabilization [1].",
                    (Citation("nanofluid.md", 1, 1),),
                )

            observations_after_feedback = observations[feedback_index + 1 :]
            if not any(
                item.tool_name == "search_documents" for item in observations_after_feedback
            ):
                return ToolCall(
                    "search_documents",
                    {"query": "DLVO nanofluid stability"},
                )
            return FinalAnswer(
                "DLVO interactions support nanofluid stability by balancing attractive and "
                "repulsive forces [1].",
                (Citation("nanofluid.md", 2, 2),),
            )

    result = ResearchAgent(RetryPlanner(), tools).run("What role does DLVO play?")

    assert result.stop_reason == "finished"
    assert "balancing attractive and repulsive forces" in result.answer
    assert result.citations == (Citation("nanofluid.md", 2, 2),)
    assert [item.tool_name for item in result.observations] == [
        "search_documents",
        "read_document",
        "answer_validation",
        "search_documents",
        "read_document",
    ]


def test_failed_automatic_read_is_not_repeated():
    search_calls = 0
    read_calls = 0

    def search(arguments: dict[str, object]) -> list[dict[str, object]]:
        nonlocal search_calls
        search_calls += 1
        return [
            {
                "path": "nanofluid.md",
                "start_line": 1,
                "end_line": 2,
                "snippet": "DLVO interactions support nanofluid stability.",
            }
        ]

    def read(arguments: dict[str, object]) -> dict[str, object]:
        nonlocal read_calls
        read_calls += 1
        if read_calls > 1:
            raise ToolError("The requested document could not be read.")
        return {
            "path": "nanofluid.md",
            "start_line": 1,
            "end_line": 1,
            "content": "1: Slide title: DLVO",
        }

    tools = ToolRegistry({"search_documents": search, "read_document": read})

    class RetryPlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            feedback_index = next(
                (
                    index
                    for index, observation in enumerate(observations)
                    if observation.tool_name == "answer_validation"
                ),
                None,
            )
            if not observations:
                return ToolCall("search_documents", {"query": "DLVO"})
            if feedback_index is None:
                if len(observations) == 1:
                    return ToolCall(
                        "read_document",
                        {"path": "nanofluid.md", "start_line": 1, "end_line": 1},
                    )
                return FinalAnswer(
                    "DLVO theory improves electrostatic stabilization [1].",
                    (Citation("nanofluid.md", 1, 1),),
                )
            if not any(
                item.tool_name == "search_documents" for item in observations[feedback_index + 1 :]
            ):
                return ToolCall("search_documents", {"query": "DLVO stability"})
            return FinalAnswer(
                "DLVO theory improves electrostatic stabilization [1].",
                (Citation("nanofluid.md", 1, 1),),
            )

    result = ResearchAgent(RetryPlanner(), tools).run("What role does DLVO play?")

    assert result.stop_reason == "ungrounded_answer"
    assert read_calls == 2
    assert search_calls == 2
    assert sum(item.error is not None for item in result.observations) == 1


def test_agent_answers_from_a_bounded_persian_dlvo_section(tmp_path: Path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    lines = [f"Introductory line {line}." for line in range(1, 6)]
    lines.extend(
        [
            "## اسلاید ۱۱: نظریه DLVO",
            "**محتوای اسلاید**",
            "- **V_total = V_vdW + V_EDL**",
            "- **V_vdW:** جاذبه واندروالس (همیشه جاذبه بین ذرات یکسان)",
            "- **V_EDL:** دافعه لایه دوگانه الکتریکی",
            "- **منحنی انرژی:** کمینه اولیه (تجمع برگشت‌ناپذیر)، سد انرژی، کمینه ثانویه (لخته‌شدن ضعیف و برگشت‌پذیر)",
            "- سد انرژی بسیار بلندتر از kT → سوسپانسیون پایدار",
            "**یادداشت گوینده:** DLVO پل ارتباطی بین شیمی آب شور، بار سطحی ذره و پایداری است.",
            "## اسلاید ۱۲: طول دبای",
        ]
    )
    lines.extend(f"Unrelated background line {line}." for line in range(10))
    lines.extend(
        [
            "## واژه‌نامه",
            "| نانوسیال | Nanofluid |",
            "| سوسپانسیون پایدار | Stable suspension |",
        ]
    )
    (knowledge_dir / "nanofluid.md").write_text("\n".join(lines), encoding="utf-8")

    class PersianEvidencePlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            if not observations:
                return ToolCall(
                    "search_documents",
                    {"query": "DLVO"},
                )
            if observations[-1].tool_name == "search_documents":
                hit = observations[-1].result[0]
                return ToolCall(
                    "read_document",
                    {
                        "path": hit["path"],
                        "start_line": hit["start_line"],
                        "end_line": hit["end_line"],
                    },
                )
            return FinalAnswer(
                "V_total = V_vdW + V_EDL [1].\n"
                "V_vdW: جاذبه واندروالس (همیشه جاذبه بین ذرات یکسان) [1].\n"
                "V_EDL: دافعه لایه دوگانه الکتریکی [1].\n"
                "سد انرژی بسیار بلندتر از kT → سوسپانسیون پایدار [1].",
                (Citation("nanofluid.md", 8, 12),),
            )

    result = ResearchAgent(
        PersianEvidencePlanner(),
        build_read_only_tools(knowledge_dir),
    ).run("According to the file, what does DLVO do for nanofluid stability?")

    assert result.stop_reason == "finished"
    assert result.citations == (Citation("nanofluid.md", 8, 12),)
    assert "سوسپانسیون پایدار" in result.answer
