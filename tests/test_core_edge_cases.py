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


def test_agent_retries_after_ungrounded_answer_with_new_evidence(tmp_path: Path):
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
            if not any(item.tool_name == "read_document" for item in observations_after_feedback):
                return ToolCall(
                    "read_document",
                    {"path": "nanofluid.md", "start_line": 2, "end_line": 2},
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


def test_agent_corrects_mixed_language_claim_from_already_read_source_text():
    search_calls = 0
    read_calls = 0
    source_line = "DLVO پل ارتباطی بین شیمی آب شور، بار سطحی ذره و پایداری است."

    def search(arguments: dict[str, object]) -> list[dict[str, object]]:
        nonlocal search_calls
        search_calls += 1
        return [{"path": "nanofluid.md", "start_line": 1, "end_line": 1}]

    def read(arguments: dict[str, object]) -> dict[str, object]:
        nonlocal read_calls
        read_calls += 1
        return {
            "path": "nanofluid.md",
            "start_line": 1,
            "end_line": 1,
            "content": f"1: {source_line}",
        }

    rejected_answer = FinalAnswer(
        "According to the file, DLVO (دینامیک لایه دوگانه الکتریکی واندروالس) plays a role "
        "in nanofluid stability as a theoretical framework linking salt-water chemistry, "
        "particle surface charge, and stability [1].",
        (Citation("nanofluid.md", 1, 1),),
    )
    corrected_answer = FinalAnswer(
        f"{source_line} [1].",
        (Citation("nanofluid.md", 1, 1),),
    )

    class MixedLanguagePlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            if not observations:
                return ToolCall("search_documents", {"query": goal})
            if observations[-1].tool_name == "search_documents":
                return ToolCall(
                    "read_document",
                    {"path": "nanofluid.md", "start_line": 1, "end_line": 1},
                )
            if any(item.tool_name == "answer_validation" for item in observations):
                return corrected_answer
            return rejected_answer

    result = ResearchAgent(
        MixedLanguagePlanner(),
        ToolRegistry({"search_documents": search, "read_document": read}),
    ).run("According to the file, what role does DLVO play in nanofluid stability?")

    assert result.stop_reason == "finished"
    assert result.answer == f"{source_line} [1]."
    assert result.citations == (Citation("nanofluid.md", 1, 1),)
    assert search_calls == 1
    assert read_calls == 1
    assert [item.tool_name for item in result.observations] == [
        "search_documents",
        "read_document",
        "answer_validation",
    ]
    feedback = result.observations[-1]
    assert isinstance(feedback.result, str)
    assert "دینامیک لایه دوگانه الکتریکی واندروالس" in feedback.result


def test_duplicate_read_uses_exact_source_fallback_before_planner_loops():
    search_calls = 0
    read_calls = 0
    path = "nanofluid.md"
    source_line = "**یادداشت گوینده:** DLVO پل ارتباطی بین شیمی آب شور، بار سطحی ذره و پایداری است."
    source_content = "\n".join(
        (
            "180: - **V_total = V_vdW + V_EDL**",
            "181: - **V_vdW:** جاذبه واندروالس (همیشه جاذبه بین ذرات یکسان)",
            "182: - **V_EDL:** دافعه لایه دوگانه الکتریکی",
            "183: - **منحنی انرژی:** کمینه اولیه (تجمع برگشت‌ناپذیر)، سد انرژی، کمینه ثانویه (لخته‌شدن ضعیف و برگشت‌پذیر)",
            "184: - سد انرژی بسیار بلندتر از kT → سوسپانسیون پایدار",
            "185: ",
            f"186: {source_line}",
        )
    )

    def search(arguments: dict[str, object]) -> list[dict[str, object]]:
        nonlocal search_calls
        search_calls += 1
        return [{"path": path, "start_line": 177, "end_line": 191}]

    def read(arguments: dict[str, object]) -> dict[str, object]:
        nonlocal read_calls
        read_calls += 1
        return {
            "path": path,
            "start_line": 177,
            "end_line": 191,
            "content": source_content,
        }

    class DuplicateReadPlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            if not observations:
                return ToolCall("search_documents", {"query": goal})
            return ToolCall(
                "read_document",
                {"path": path, "start_line": 177, "end_line": 191},
            )

    result = ResearchAgent(
        DuplicateReadPlanner(),
        ToolRegistry({"search_documents": search, "read_document": read}),
    ).run("According to the file, what role does DLVO play in stability of nanofluids?")

    assert result.stop_reason == "finished"
    assert search_calls == 1
    assert read_calls == 1
    assert source_line[:-1] in result.answer
    assert "V_total = V_vdW + V_EDL" in result.answer
    assert "دافعه لایه دوگانه الکتریکی" in result.answer
    assert "سد انرژی بسیار بلندتر از kT" in result.answer
    assert result.citations == (Citation(path, 180, 186),)
    assert result.observations[-1].error == (
        "This line range was already read. Use the existing evidence or choose a different "
        "unread range; do not repeat this read."
    )


def test_extractive_fallback_keeps_single_sentence_without_adjacent_bullets():
    path = "nanofluid.md"
    source_line = "DLVO پل ارتباطی بین شیمی آب شور، بار سطحی ذره و پایداری است."
    observations = (
        Observation(
            tool_name="search_documents",
            result=[{"path": path, "start_line": 1, "end_line": 1}],
        ),
        Observation(
            tool_name="read_document",
            result={
                "path": path,
                "start_line": 1,
                "end_line": 1,
                "content": f"1: {source_line}",
            },
        ),
    )

    answer = ResearchAgent._extractive_fallback(
        "According to the file, what role does DLVO play in nanofluid stability?",
        observations,
    )

    assert answer is not None
    assert answer.text == f"{source_line[:-1]} [1]."
    assert answer.citations == (Citation(path, 1, 1),)


def test_repeated_duplicate_reads_stop_safely_when_no_relevant_quote_exists():
    search_calls = 0
    read_calls = 0
    path = "notes.md"

    def search(arguments: dict[str, object]) -> list[dict[str, object]]:
        nonlocal search_calls
        search_calls += 1
        return [{"path": path, "start_line": 1, "end_line": 1}]

    def read(arguments: dict[str, object]) -> dict[str, object]:
        nonlocal read_calls
        read_calls += 1
        return {"path": path, "start_line": 1, "end_line": 1, "content": "1: General note."}

    class EndlessReader:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            if not observations:
                return ToolCall("search_documents", {"query": goal})
            return ToolCall("read_document", {"path": path, "start_line": 1, "end_line": 1})

    result = ResearchAgent(
        EndlessReader(),
        ToolRegistry({"search_documents": search, "read_document": read}),
    ).run("What is in this note?")

    assert result.stop_reason == "repeated_read"
    assert "repeatedly requested an already-read" in result.answer
    assert search_calls == 1
    assert read_calls == 1
    assert sum(item.error is not None for item in result.observations) == 2


def test_repeated_mixed_language_failure_falls_back_to_exact_relevant_source_line():
    search_calls = 0
    read_ranges: list[tuple[int, int]] = []
    path = "nanofluid.md"
    direct_quote = "**یادداشت گوینده:** DLVO پل ارتباطی بین شیمی آب شور، بار سطحی ذره و پایداری است"
    lines = {
        37: "",
        38: "**محتوای اسلاید**",
        39: "- A: چرا ازدیاد برداشت؟",
        40: "- B: نانوسیال چیست؟",
        41: "- C: پایداری (DLVO، طول دبای)",
        42: "- D: سازوکارهای اثر",
        177: "## اسلاید ۱۱: نظریه DLVO",
        179: "**محتوای اسلاید**",
        180: "- **V_total = V_vdW + V_EDL**",
        181: "- **V_vdW:** جاذبه واندروالس",
        182: "- **V_EDL:** دافعه لایه دوگانه الکتریکی",
        183: "- **منحنی انرژی:** کمینه اولیه، سد انرژی و کمینه ثانویه",
        184: "- سد انرژی بسیار بلندتر از kT → سوسپانسیون پایدار",
        186: f"{direct_quote}.",
        188: "**پیشنهاد تصویر:** نمودار انرژی در برابر فاصله.",
    }

    def search(arguments: dict[str, object]) -> list[dict[str, object]]:
        nonlocal search_calls
        search_calls += 1
        return [
            {"path": path, "start_line": 177, "end_line": 191, "snippet": "DLVO stability"},
            {"path": path, "start_line": 37, "end_line": 42, "snippet": "DLVO outline"},
        ]

    def read(arguments: dict[str, object]) -> dict[str, object]:
        start = int(arguments["start_line"])
        end = int(arguments["end_line"])
        read_ranges.append((start, end))
        content = "\n".join(
            f"{line_number}: {lines.get(line_number, '')}" for line_number in range(start, end + 1)
        )
        return {"path": path, "start_line": start, "end_line": end, "content": content}

    bad_answer = FinalAnswer(
        "According to the file, DLVO (دینامیک لایه دوگانه الکتریکی واندروالس) plays a role "
        "in nanofluid stability as a theoretical framework linking colloid chemistry, surface "
        "charge of particles, and stability [1].",
        (Citation(path, 177, 191),),
    )

    class RepeatsAndMisreadsPlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            feedback_index = next(
                (
                    index
                    for index, item in enumerate(observations)
                    if item.tool_name == "answer_validation"
                ),
                None,
            )
            if not observations:
                return ToolCall("search_documents", {"query": goal})
            if feedback_index is None:
                successful_reads = [
                    item
                    for item in observations
                    if item.tool_name == "read_document" and not item.error
                ]
                if not successful_reads:
                    return ToolCall(
                        "read_document",
                        {"path": path, "start_line": 177, "end_line": 191},
                    )
                return bad_answer

            retry_observations = observations[feedback_index + 1 :]
            if not any(item.tool_name == "search_documents" for item in retry_observations):
                return ToolCall("search_documents", {"query": "DLVO پایداری"})
            if not any(item.tool_name == "read_document" for item in retry_observations):
                return ToolCall(
                    "read_document",
                    {"path": path, "start_line": 37, "end_line": 42},
                )
            return FinalAnswer(
                "DLVO acts as a framework for stability [1].",
                (Citation(path, 37, 42),),
            )

    result = ResearchAgent(
        RepeatsAndMisreadsPlanner(),
        ToolRegistry({"search_documents": search, "read_document": read}),
    ).run("According to the file, what role does DLVO play in stability of nanofluids?")

    assert result.stop_reason == "finished"
    assert search_calls == 2
    assert read_ranges == [(177, 191), (37, 42)]
    assert direct_quote in result.answer
    assert "V_total = V_vdW + V_EDL" in result.answer
    assert "سد انرژی بسیار بلندتر از kT" in result.answer
    assert result.citations == (Citation(path, 180, 186),)
    assert result.observations[2].tool_name == "answer_validation"
    assert "colloid chemistry" in str(result.observations[2].result)


def test_grounding_retry_reports_the_rejected_claim_and_never_repeats_a_read():
    search_calls = 0
    read_ranges: list[tuple[int, int]] = []

    def search(arguments: dict[str, object]) -> list[dict[str, object]]:
        nonlocal search_calls
        search_calls += 1
        return [{"path": "nanofluid.md", "start_line": 1, "end_line": 2}]

    def read(arguments: dict[str, object]) -> dict[str, object]:
        start = int(arguments["start_line"])
        end = int(arguments["end_line"])
        read_ranges.append((start, end))
        return {
            "path": "nanofluid.md",
            "start_line": start,
            "end_line": end,
            "content": "1: Slide title: DLVO\n2: Colloidal interactions are discussed.",
        }

    tools = ToolRegistry({"search_documents": search, "read_document": read})
    rejected_answer = FinalAnswer(
        "DLVO improves electrostatic stabilization [1].",
        (Citation("nanofluid.md", 1, 2),),
    )

    class RepeatsReadPlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            feedback_index = next(
                (
                    index
                    for index, item in enumerate(observations)
                    if item.tool_name == "answer_validation"
                ),
                None,
            )
            if not observations:
                return ToolCall("search_documents", {"query": goal})
            if feedback_index is None:
                if observations[-1].tool_name == "search_documents":
                    return ToolCall(
                        "read_document",
                        {"path": "nanofluid.md", "start_line": 1, "end_line": 2},
                    )
                return rejected_answer
            retry_observations = observations[feedback_index + 1 :]
            if any(item.error for item in retry_observations):
                return rejected_answer
            return ToolCall(
                "read_document",
                {"path": "nanofluid.md", "start_line": 1, "end_line": 2},
            )

    result = ResearchAgent(RepeatsReadPlanner(), tools).run("What role does DLVO play?")

    assert result.stop_reason == "ungrounded_answer"
    assert read_ranges == [(1, 2)]
    assert search_calls == 1
    feedback = next(item for item in result.observations if item.tool_name == "answer_validation")
    assert isinstance(feedback.result, str)
    assert "Rejected draft claim" in feedback.result
    assert "DLVO improves electrostatic stabilization" in feedback.result
    assert [item.tool_name for item in result.observations] == [
        "search_documents",
        "read_document",
        "answer_validation",
        "read_document",
    ]
    assert result.observations[-1].error == (
        "This line range was already read. Use the existing evidence or choose a different "
        "unread range; do not repeat this read."
    )


def test_grounding_retry_trims_overlapping_reads_to_unread_lines():
    read_ranges: list[tuple[int, int]] = []

    def search(arguments: dict[str, object]) -> list[dict[str, object]]:
        return [{"path": "nanofluid.md", "start_line": 1, "end_line": 3}]

    def read(arguments: dict[str, object]) -> dict[str, object]:
        start = int(arguments["start_line"])
        end = int(arguments["end_line"])
        read_ranges.append((start, end))
        lines = {
            1: "Slide title: DLVO",
            2: "The source discusses colloidal interactions.",
            3: "DLVO interactions support nanofluid stability directly.",
        }
        return {
            "path": "nanofluid.md",
            "start_line": start,
            "end_line": end,
            "content": "\n".join(f"{number}: {lines[number]}" for number in range(start, end + 1)),
        }

    class PartialOverlapPlanner:
        def choose_next_action(
            self,
            goal: str,
            observations: Sequence[Observation],
        ) -> Action:
            feedback_index = next(
                (
                    index
                    for index, item in enumerate(observations)
                    if item.tool_name == "answer_validation"
                ),
                None,
            )
            if not observations:
                return ToolCall("search_documents", {"query": goal})
            if feedback_index is None:
                if observations[-1].tool_name == "search_documents":
                    return ToolCall(
                        "read_document",
                        {"path": "nanofluid.md", "start_line": 1, "end_line": 2},
                    )
                return FinalAnswer(
                    "DLVO improves electrostatic stabilization [1].",
                    (Citation("nanofluid.md", 1, 2),),
                )
            has_retry_read = any(
                item.tool_name == "read_document" and not item.error
                for item in observations[feedback_index + 1 :]
            )
            if not has_retry_read:
                return ToolCall(
                    "read_document",
                    {"path": "nanofluid.md", "start_line": 1, "end_line": 3},
                )
            return FinalAnswer(
                "DLVO interactions support nanofluid stability directly [1].",
                (Citation("nanofluid.md", 3, 3),),
            )

    result = ResearchAgent(
        PartialOverlapPlanner(),
        ToolRegistry({"search_documents": search, "read_document": read}),
    ).run("What role does DLVO play?")

    assert result.stop_reason == "finished"
    assert read_ranges == [(1, 2), (3, 3)]
    assert result.citations == (Citation("nanofluid.md", 3, 3),)


def test_failed_retry_read_does_not_ground_the_answer():
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
            retry_observations = observations[feedback_index + 1 :]
            if not any(item.tool_name == "search_documents" for item in retry_observations):
                return ToolCall("search_documents", {"query": "DLVO stability"})
            if not any(item.tool_name == "read_document" for item in retry_observations):
                return ToolCall(
                    "read_document",
                    {"path": "nanofluid.md", "start_line": 2, "end_line": 2},
                )
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
