from fastapi import FastAPI, HTTPException, Query

from backend.catalog import filter_programs, load_catalog, unique_sources
from backend.models import (
    OverviewResponse,
    Program,
    ProgramListResponse,
)


app = FastAPI(
    title="Pathfinder Canada API",
    version="0.1.0",
    description=(
        "A source-first graduate program explorer. Facts are a dated snapshot, "
        "not admissions advice."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
def health() -> dict[str, str | int]:
    catalog = load_catalog()
    return {
        "status": "ok",
        "program_count": len(catalog.programs),
        "catalog_checked_at": catalog.catalog_checked_at.isoformat(),
    }


@app.get("/api/overview", response_model=OverviewResponse)
def overview() -> OverviewResponse:
    catalog = load_catalog()
    verified_fact_count = sum(
        fact.status == "verified"
        for program in catalog.programs
        for fact in program.facts
    )
    return OverviewResponse(
        program_count=len(catalog.programs),
        official_source_count=unique_sources(catalog.programs),
        verified_fact_count=verified_fact_count,
        catalog_checked_at=catalog.catalog_checked_at,
    )


@app.get("/api/programs", response_model=ProgramListResponse)
def list_programs(
    q: str | None = Query(default=None, max_length=120),
    province: str | None = None,
    program_type: str | None = None,
    field: str | None = None,
) -> ProgramListResponse:
    catalog = load_catalog()
    items = filter_programs(
        catalog.programs,
        query=q,
        province=province,
        program_type=program_type,
        field=field,
    )
    return ProgramListResponse(
        total=len(catalog.programs),
        matched=len(items),
        items=items,
        provinces=sorted({program.province for program in catalog.programs}),
        program_types=sorted({program.program_type for program in catalog.programs}),
    )


@app.get("/api/programs/{program_id}", response_model=Program)
def get_program(program_id: str) -> Program:
    for program in load_catalog().programs:
        if program.id == program_id:
            return program
    raise HTTPException(status_code=404, detail="Program not found")


@app.get("/api/compare", response_model=list[Program])
def compare_programs(
    ids: str = Query(..., description="Comma-separated program IDs; choose 2 or 3")
) -> list[Program]:
    requested = list(dict.fromkeys(item.strip() for item in ids.split(",") if item.strip()))
    if not 2 <= len(requested) <= 3:
        raise HTTPException(
            status_code=422,
            detail="Choose between two and three distinct programs to compare",
        )

    programs_by_id = {program.id: program for program in load_catalog().programs}
    unknown = [program_id for program_id in requested if program_id not in programs_by_id]
    if unknown:
        raise HTTPException(status_code=404, detail=f"Unknown program IDs: {', '.join(unknown)}")

    return [programs_by_id[program_id] for program_id in requested]
