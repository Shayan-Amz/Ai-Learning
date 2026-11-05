from datetime import date
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, model_validator


ProgramType = Literal["professional", "research"]
FactStatus = Literal["verified", "not_collected"]
SourceKind = Literal["program_page", "department_page", "eligibility_page"]


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    publisher: str
    url: AnyHttpUrl
    checked_at: date
    kind: SourceKind


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    value: str | None = None
    status: FactStatus
    source_id: str | None = None
    valid_for: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def verified_fact_has_source(self):
        if self.status == "verified" and (not self.value or not self.source_id):
            raise ValueError("Verified facts require both a value and a source_id")
        if self.status == "not_collected" and self.value is not None:
            raise ValueError("not_collected facts must not invent a value")
        return self


class Program(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    institution: str
    institution_short: str
    name: str
    concentration: str
    credential: str
    program_type: ProgramType
    city: str
    province: str
    duration: str | None = None
    delivery: str | None = None
    summary: str
    fields: list[str]
    tags: list[str]
    checked_at: date
    facts: list[Fact]
    sources: list[Source]

    @model_validator(mode="after")
    def facts_reference_known_sources(self):
        source_ids = {source.id for source in self.sources}
        for fact in self.facts:
            if fact.source_id is not None and fact.source_id not in source_ids:
                raise ValueError(
                    f"Fact '{fact.id}' references unknown source '{fact.source_id}'"
                )
        if len(source_ids) != len(self.sources):
            raise ValueError(f"Program '{self.id}' contains duplicate source IDs")
        fact_ids = [fact.id for fact in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError(f"Program '{self.id}' contains duplicate fact IDs")
        return self

    @model_validator(mode="after")
    def program_metadata_has_verified_facts(self):
        for attribute in ("duration", "delivery"):
            value = getattr(self, attribute)
            if value is None:
                continue
            fact = next((item for item in self.facts if item.id == attribute), None)
            if fact is None or fact.status != "verified" or fact.value != value:
                raise ValueError(
                    f"Program '{self.id}' {attribute} must match a verified fact"
                )
        return self


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_checked_at: date
    programs: list[Program]

    @model_validator(mode="after")
    def program_ids_are_unique(self):
        ids = [program.id for program in self.programs]
        if len(ids) != len(set(ids)):
            raise ValueError("Catalog contains duplicate program IDs")
        return self


class ProgramListResponse(BaseModel):
    total: int
    matched: int
    items: list[Program]
    provinces: list[str]
    program_types: list[str]


class OverviewResponse(BaseModel):
    program_count: int
    official_source_count: int
    verified_fact_count: int
    catalog_checked_at: date
