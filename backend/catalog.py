from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend.models import Catalog, Program


CATALOG_PATH = Path(__file__).with_name("catalog.json")


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return Catalog.model_validate(raw)


def filter_programs(
    programs: list[Program],
    *,
    query: str | None = None,
    province: str | None = None,
    program_type: str | None = None,
    field: str | None = None,
) -> list[Program]:
    normalized_query = (query or "").strip().casefold()
    normalized_province = (province or "").strip().casefold()
    normalized_type = (program_type or "").strip().casefold()
    normalized_field = (field or "").strip().casefold()
    results: list[Program] = []

    for program in programs:
        searchable = " ".join(
            [
                program.institution,
                program.name,
                program.concentration,
                program.city,
                program.province,
                *program.fields,
                *program.tags,
                *(fact.label for fact in program.facts),
                *(fact.value or "" for fact in program.facts),
            ]
        ).casefold()

        if normalized_query and normalized_query not in searchable:
            continue
        if normalized_province and program.province.casefold() != normalized_province:
            continue
        if normalized_type and program.program_type.casefold() != normalized_type:
            continue
        if normalized_field and normalized_field not in {
            value.casefold() for value in program.fields
        }:
            continue

        results.append(program)

    return results


def unique_sources(programs: list[Program]) -> int:
    source_ids = {
        source.id
        for program in programs
        for source in program.sources
    }
    return len(source_ids)
