export type ProgramType = "professional" | "research";
export type FactStatus = "verified" | "not_collected";

export interface Source {
  id: string;
  title: string;
  publisher: string;
  url: string;
  checked_at: string;
  kind: string;
}

export interface Fact {
  id: string;
  label: string;
  value: string | null;
  status: FactStatus;
  source_id: string | null;
  valid_for: string | null;
  note: string | null;
}

export interface Program {
  id: string;
  institution: string;
  institution_short: string;
  name: string;
  concentration: string;
  credential: string;
  program_type: ProgramType;
  city: string;
  province: string;
  duration: string | null;
  delivery: string | null;
  summary: string;
  fields: string[];
  tags: string[];
  checked_at: string;
  facts: Fact[];
  sources: Source[];
}

export interface ProgramListResponse {
  total: number;
  matched: number;
  items: Program[];
  provinces: string[];
  program_types: ProgramType[];
}

export interface OverviewResponse {
  program_count: number;
  official_source_count: number;
  verified_fact_count: number;
  catalog_checked_at: string;
}
