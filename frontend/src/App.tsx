import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUpRight,
  Bookmark,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock3,
  ExternalLink,
  FileText,
  GraduationCap,
  MapPin,
  Scale,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  X,
} from "lucide-react";
import type { Fact, OverviewResponse, Program, ProgramListResponse, Source } from "./types";

const SAVED_KEY = "pathfinder:shortlist:v1";
const CHECKLIST_KEY = "pathfinder:checklist:v1";

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

function getFact(program: Program, id: string): Fact | undefined {
  return program.facts.find((fact) => fact.id === id);
}

function displayFact(fact: Fact | undefined): string {
  if (!fact || fact.status === "not_collected" || !fact.value) {
    return "Not captured yet";
  }
  return fact.value;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function getDeadline(program: Program): string {
  const fact = getFact(program, "deadline");
  if (!fact?.value) return "Check official page";
  const dateMatch = fact.value.match(/[A-Za-z]+\s+\d{1,2},\s+\d{4}/);
  return dateMatch ? dateMatch[0] : fact.value;
}

function initials(value: string): string {
  if (value === "U of T") return "UT";
  return value
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function factForCompare(program: Program, factId: string): string {
  if (factId === "duration") return program.duration ?? "Not captured yet";
  if (factId === "delivery") return program.delivery ?? "Not captured yet";
  if (factId === "program_type") {
    return program.program_type === "research" ? "Research master's" : "Professional master's";
  }
  return displayFact(getFact(program, factId));
}

function findEarliestDeadline(programs: Program[]) {
  const deadlines = programs.flatMap((program) => {
    const label = getDeadline(program);
    if (label === "Check official page") return [];
    const date = new Date(`${label} 00:00:00 UTC`);
    if (Number.isNaN(date.getTime())) return [];
    return [{ date }];
  });
  deadlines.sort((left, right) => left.date.getTime() - right.date.getTime());
  const earliest = deadlines[0];
  if (!earliest) return null;
  return {
    month: new Intl.DateTimeFormat("en-US", { month: "short", timeZone: "UTC" })
      .format(earliest.date)
      .toUpperCase(),
    day: new Intl.DateTimeFormat("en-US", { day: "2-digit", timeZone: "UTC" })
      .format(earliest.date),
    count: deadlines.filter((item) => item.date.getTime() === earliest.date.getTime()).length,
  };
}

interface ChecklistTask {
  key: string;
  title: string;
  detail: string;
  sources: Source[];
}

function buildChecklistTasks(program: Program): ChecklistTask[] {
  const definitions: { id: string; title: string; factIds: string[] }[] = [
    { id: "deadline", title: "Confirm the deadline and intended intake", factIds: ["deadline"] },
    {
      id: "academic",
      title: "Review academic requirements and prerequisites",
      factIds: ["academic-standing", "eligibility", "concentration-prerequisites"],
    },
    { id: "references", title: "Confirm referee requirements and submission steps", factIds: ["references"] },
    { id: "duration", title: "Review the expected program length", factIds: ["duration"] },
    { id: "delivery", title: "Confirm the delivery format", factIds: ["delivery"] },
    { id: "admission-option", title: "Review the admission option and thesis details", factIds: ["admission-option"] },
    { id: "tuition", title: "Collect current tuition and fee details", factIds: ["tuition"] },
    { id: "funding", title: "Confirm funding terms and eligibility", factIds: ["funding"] },
  ];

  return definitions.flatMap((definition) => {
    const facts = definition.factIds
      .map((id) => getFact(program, id))
      .filter((fact): fact is Fact => fact !== undefined);
    if (facts.length === 0) return [];

    const detailParts = facts.map((fact) => {
      if (fact.status === "not_collected" || !fact.value) {
        return fact.note ?? `${fact.label} is not captured in this snapshot.`;
      }
      const context = fact.valid_for ? ` (${fact.valid_for})` : "";
      return `${fact.label}: ${fact.value}${context}.`;
    });
    const hasUnknown = facts.some((fact) => fact.status === "not_collected");
    const sourceIds = new Set(
      facts.map((fact) => fact.source_id).filter((id): id is string => id !== null),
    );
    const sources = program.sources.filter((source) => sourceIds.has(source.id));

    return [{
      key: `${program.id}:${program.checked_at}:${definition.id}`,
      title: definition.title,
      detail: `${detailParts.join(" ")} ${hasUnknown ? "Find and verify the current official information." : "Confirm the current official instructions before acting."}`,
      sources,
    }];
  });
}

interface ProgramCardProps {
  program: Program;
  saved: boolean;
  selectedForCompare: boolean;
  onOpen: (program: Program) => void;
  onSave: (programId: string) => void;
  onCompare: (programId: string) => void;
}

function ProgramCard({
  program,
  saved,
  selectedForCompare,
  onOpen,
  onSave,
  onCompare,
}: ProgramCardProps) {
  const deadline = getFact(program, "deadline");
  const deadlineSource = program.sources.find((source) => source.id === deadline?.source_id);
  const durationFact = getFact(program, "duration");
  const durationSource = program.sources.find((source) => source.id === durationFact?.source_id);
  const academic = getFact(program, "academic-standing") ?? getFact(program, "eligibility");

  return (
    <article className="program-card">
      <div className="program-card-topline">
        <div className="institution-lockup">
          <div className={`institution-mark mark-${program.id}`} aria-hidden="true">
            {initials(program.institution_short)}
          </div>
          <div>
            <p className="institution-name">{program.institution_short}</p>
            <p className="institution-location">
              <MapPin size={13} strokeWidth={1.8} />
              {program.city}, {program.province}
            </p>
          </div>
        </div>
        <button
          className={`icon-button save-button ${saved ? "is-saved" : ""}`}
          type="button"
          onClick={() => onSave(program.id)}
          aria-label={saved ? `Remove ${program.name} from shortlist` : `Save ${program.name}`}
          title={saved ? "Remove from shortlist" : "Save to shortlist"}
        >
          <Bookmark size={17} fill={saved ? "currentColor" : "none"} />
        </button>
      </div>

      <div className="program-card-title-row">
        <div>
          <span className={`type-pill type-${program.program_type}`}>
            {program.program_type === "research" ? "Research" : "Professional"}
          </span>
          <span className="credential-pill">{program.credential}</span>
        </div>
        <span className="verified-inline">
          <CheckCircle2 size={14} /> Evidence linked
        </span>
      </div>

      <button className="program-title-button" type="button" onClick={() => onOpen(program)}>
        <h3>{program.name}</h3>
        <span className="program-concentration">{program.concentration}</span>
      </button>
      <p className="program-summary">{program.summary}</p>

      <div className="program-highlights">
        <div className="highlight-cell">
          <span className="highlight-label"><CalendarDays size={14} /> Deadline in snapshot</span>
          <strong>{getDeadline(program)}</strong>
          <span className="highlight-note">{deadline?.valid_for ?? "Confirm intake on source page"}</span>
          {deadlineSource && <a className="highlight-source" href={deadlineSource.url} target="_blank" rel="noreferrer">Official source <ArrowUpRight size={11} /></a>}
        </div>
        <div className="highlight-cell">
          <span className="highlight-label"><Clock3 size={14} /> Program length</span>
          <strong>{program.duration ?? "Not captured"}</strong>
          {durationSource
            ? <a className="highlight-source" href={durationSource.url} target="_blank" rel="noreferrer">Official source <ArrowUpRight size={11} /></a>
            : <span className="highlight-note">Always verify current details</span>}
        </div>
      </div>

      <div className="program-tags">
        {program.fields.slice(0, 3).map((field) => (
          <span className="tag" key={field}>{field}</span>
        ))}
      </div>

      <div className="card-evidence-line">
        <ShieldCheck size={15} />
        <span>{program.sources.length} official page{program.sources.length === 1 ? "" : "s"}</span>
        <span className="evidence-dot">·</span>
        <span>Checked {formatDate(program.checked_at)}</span>
      </div>

      <div className="card-actions">
        <button className="button button-secondary button-detail" type="button" onClick={() => onOpen(program)}>
          <FileText size={15} /> Details & sources
        </button>
        <button
          className={`compare-toggle ${selectedForCompare ? "selected" : ""}`}
          type="button"
          onClick={() => onCompare(program.id)}
          aria-pressed={selectedForCompare}
        >
          {selectedForCompare ? <Check size={15} /> : <Scale size={15} />}
          Compare
        </button>
      </div>

      {academic?.value && (
        <span className="sr-only">Academic requirement: {academic.value}</span>
      )}
    </article>
  );
}

interface ChecklistBoardProps {
  programs: Program[];
  completedKeys: string[];
  onToggle: (taskKey: string) => void;
  onExplore: () => void;
}

function ChecklistBoard({ programs, completedKeys, onToggle, onExplore }: ChecklistBoardProps) {
  const groups = programs
    .map((program) => ({ program, tasks: buildChecklistTasks(program) }))
    .filter((group) => group.tasks.length > 0);
  const allTasks = groups.flatMap((group) => group.tasks);
  const completedCount = allTasks.filter((task) => completedKeys.includes(task.key)).length;
  const progress = allTasks.length === 0 ? 0 : Math.round((completedCount / allTasks.length) * 100);

  if (groups.length === 0) {
    return (
      <div className="empty-state checklist-empty">
        <div className="empty-icon"><CheckCircle2 size={20} /></div>
        <h3>Start with a shortlist</h3>
        <p>Save a program first. Pathfinder will create source-linked reminders from the facts available for that program.</p>
        <button className="button button-secondary" type="button" onClick={onExplore}>Explore programs</button>
      </div>
    );
  }

  return (
    <div className="checklist-board">
      <div className="checklist-overview">
        <div>
          <p className="eyebrow">YOUR NEXT STEPS</p>
          <h3>Application research checklist</h3>
          <p>These are reminders, not automated actions. Open the official source and mark a task complete only after you verify it.</p>
        </div>
        <div className="checklist-progress-card">
          <div><strong>{completedCount}<span> / {allTasks.length}</span></strong><span>tasks complete</span></div>
          <div className="progress-track" role="progressbar" aria-label="Checklist completion" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${progress}%` }} /></div>
        </div>
      </div>
      <div className="checklist-groups">
        {groups.map(({ program, tasks }) => {
          const groupCompleted = tasks.filter((task) => completedKeys.includes(task.key)).length;
          return (
            <article className="checklist-program" key={program.id}>
              <header className="checklist-program-heading">
                <div>
                  <span className="checklist-institution">{program.institution_short} · {program.city}, {program.province}</span>
                  <h4>{program.name}</h4>
                  <span className="checklist-concentration">{program.concentration}</span>
                </div>
                <span className="checklist-group-count">{groupCompleted}/{tasks.length} done</span>
              </header>
              <ul className="checklist-items">
                {tasks.map((task) => {
                  const complete = completedKeys.includes(task.key);
                  return (
                    <li className={`checklist-item ${complete ? "is-complete" : ""}`} key={task.key}>
                      <label className="checklist-task-label">
                        <input type="checkbox" checked={complete} onChange={() => onToggle(task.key)} />
                        <span className="task-checkbox"><Check size={13} /></span>
                        <span className="task-copy">
                          <strong>{task.title}</strong>
                          <span>{task.detail}</span>
                        </span>
                      </label>
                      {task.sources.length > 0 && (
                        <div className="task-source-links">
                          {task.sources.map((source) => (
                            <a href={source.url} target="_blank" rel="noreferrer" key={source.id}>
                              Review {source.title} <ArrowUpRight size={12} />
                            </a>
                          ))}
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            </article>
          );
        })}
      </div>
    </div>
  );
}

interface DetailModalProps {
  program: Program;
  onClose: () => void;
}

function DetailModal({ program, onClose }: DetailModalProps) {
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const sourceById = new Map(program.sources.map((source) => [source.id, source]));

  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="detail-modal" role="dialog" aria-modal="true" aria-labelledby="detail-title">
        <div className="modal-topbar">
          <div className="modal-kicker"><ShieldCheck size={15} /> Source-backed program profile</div>
          <button className="icon-button close-button" type="button" onClick={onClose} aria-label="Close details">
            <X size={19} />
          </button>
        </div>
        <div className="detail-hero">
          <div className={`institution-mark large-mark mark-${program.id}`} aria-hidden="true">
            {initials(program.institution_short)}
          </div>
          <div className="detail-heading-copy">
            <div className="detail-institution">{program.institution} <span>·</span> {program.city}, {program.province}</div>
            <h2 id="detail-title">{program.name}</h2>
            <p>{program.concentration} <span>·</span> {program.credential}</p>
          </div>
        </div>
        <p className="detail-summary">{program.summary}</p>
        <div className="detail-status-row">
          <span className={`type-pill type-${program.program_type}`}>
            {program.program_type === "research" ? "Research master's" : "Professional master's"}
          </span>
          <span className="checked-label"><Clock3 size={14} /> Last checked {formatDate(program.checked_at)}</span>
        </div>

        <div className="modal-section-heading">
          <div>
            <p className="eyebrow">ADMISSIONS SNAPSHOT</p>
            <h3>What the official pages say</h3>
          </div>
          <span className="snapshot-badge"><CheckCircle2 size={14} /> Dated snapshot</span>
        </div>
        <div className="facts-grid">
          {program.facts.map((fact) => {
            const source = fact.source_id ? sourceById.get(fact.source_id) : undefined;
            return (
              <div className={`fact-card ${fact.status === "not_collected" ? "fact-unknown" : ""}`} key={fact.id}>
                <div className="fact-topline">
                  <span className="fact-label">{fact.label}</span>
                  {fact.status === "verified" ? <CheckCircle2 size={15} className="fact-check" /> : <span className="unknown-dot" />}
                </div>
                <p className="fact-value">{fact.value ?? "Not captured in this snapshot"}</p>
                {fact.valid_for && <p className="fact-context">{fact.valid_for}</p>}
                {fact.note && <p className="fact-note">{fact.note}</p>}
                {source && (
                  <a className="fact-source-link" href={source.url} target="_blank" rel="noreferrer">
                    Source: {source.title} <ArrowUpRight size={13} />
                  </a>
                )}
              </div>
            );
          })}
        </div>

        <div className="modal-section-heading source-heading">
          <div>
            <p className="eyebrow">PROVENANCE</p>
            <h3>Official source pages</h3>
          </div>
          <span className="source-count">{program.sources.length} pages</span>
        </div>
        <div className="source-list">
          {program.sources.map((source) => (
            <a className="source-row" href={source.url} target="_blank" rel="noreferrer" key={source.id}>
              <span className="source-icon"><FileText size={17} /></span>
              <span className="source-copy">
                <strong>{source.title}</strong>
                <span>{source.publisher} · Checked {formatDate(source.checked_at)}</span>
              </span>
              <ExternalLink size={16} className="source-external" />
            </a>
          ))}
        </div>
        <div className="modal-disclaimer">
          <ShieldCheck size={16} />
          <p>Use this as a research aid, not an admissions decision. Requirements can change; confirm every important detail on the linked official page.</p>
        </div>
      </section>
    </div>
  );
}

interface CompareModalProps {
  programs: Program[];
  onClose: () => void;
}

function CompareModal({ programs, onClose }: CompareModalProps) {
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const rows = [
    { label: "Program type", id: "program_type" },
    { label: "Next deadline", id: "deadline" },
    { label: "Academic standing", id: "academic-standing" },
    { label: "Academic background", id: "eligibility" },
    { label: "Program-specific prerequisites", id: "concentration-prerequisites" },
    { label: "Admission option", id: "admission-option" },
    { label: "References", id: "references" },
    { label: "Duration", id: "duration" },
    { label: "Delivery format", id: "delivery" },
    { label: "Tuition", id: "tuition" },
    { label: "Funding", id: "funding" },
  ];

  return (
    <div className="modal-backdrop compare-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="compare-modal" role="dialog" aria-modal="true" aria-labelledby="compare-title">
        <div className="modal-topbar">
          <div className="modal-kicker"><Scale size={15} /> Side-by-side research</div>
          <button className="icon-button close-button" type="button" onClick={onClose} aria-label="Close comparison">
            <X size={19} />
          </button>
        </div>
        <div className="compare-heading">
          <div>
            <p className="eyebrow">PROGRAM COMPARISON</p>
            <h2 id="compare-title">Compare the evidence</h2>
            <p>Unknown values stay visible instead of being guessed.</p>
          </div>
          <span className="snapshot-badge"><ShieldCheck size={14} /> Official sources linked</span>
        </div>
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th scope="col">Criteria</th>
                {programs.map((program) => (
                  <th scope="col" key={program.id}>
                    <span className="compare-institution">{program.institution_short}</span>
                    <span className="compare-program-name">{program.credential} · {program.concentration}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Location</th>
                {programs.map((program) => <td key={program.id}>{program.city}, {program.province}</td>)}
              </tr>
              {rows.map((row) => (
                <tr key={row.id}>
                  <th scope="row">{row.label}</th>
                  {programs.map((program) => (
                    <td key={program.id}>
                      {factForCompare(program, row.id)}
                      {getFact(program, row.id)?.source_id && (
                        <a
                          className="table-source-link"
                          href={program.sources.find((source) => source.id === getFact(program, row.id)?.source_id)?.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          View source <ArrowUpRight size={12} />
                        </a>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="compare-footnote">
          <ShieldCheck size={15} /> Dated source snapshot · Review dates appear on each program · Always verify current requirements with the institution.
        </div>
      </section>
    </div>
  );
}

function App() {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [provinces, setProvinces] = useState<string[]>([]);
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [query, setQuery] = useState("");
  const [programType, setProgramType] = useState("all");
  const [province, setProvince] = useState("all");
  const [activeView, setActiveView] = useState<"explore" | "shortlist" | "checklist">("explore");
  const [completedChecklistKeys, setCompletedChecklistKeys] = useState<string[]>(() => {
    try {
      const value: unknown = JSON.parse(localStorage.getItem(CHECKLIST_KEY) ?? "[]");
      return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
    } catch {
      return [];
    }
  });
  const [savedIds, setSavedIds] = useState<string[]>(() => {
    try {
      const value: unknown = JSON.parse(localStorage.getItem(SAVED_KEY) ?? "[]");
      return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
    } catch {
      return [];
    }
  });
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [comparePrograms, setComparePrograms] = useState<Program[] | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState("");
  const [detailProgram, setDetailProgram] = useState<Program | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      getJson<ProgramListResponse>("/api/programs", controller.signal),
      getJson<OverviewResponse>("/api/overview", controller.signal),
    ])
      .then(([catalog, stats]) => {
        if (controller.signal.aborted) return;
        setPrograms(catalog.items);
        setProvinces(catalog.provinces);
        setOverview(stats);
        setLoading(false);
      })
      .catch((error: Error) => {
        if (controller.signal.aborted) return;
        setLoadError(error.message || "The catalog could not be loaded.");
        setLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    localStorage.setItem(SAVED_KEY, JSON.stringify(savedIds));
  }, [savedIds]);

  useEffect(() => {
    localStorage.setItem(CHECKLIST_KEY, JSON.stringify(completedChecklistKeys));
  }, [completedChecklistKeys]);

  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 2800);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const filteredPrograms = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return programs.filter((program) => {
      const searchable = [
        program.institution,
        program.institution_short,
        program.name,
        program.concentration,
        program.city,
        program.province,
        ...program.fields,
        ...program.tags,
        ...program.facts.flatMap((fact) => [fact.label, fact.value ?? ""]),
      ].join(" ").toLowerCase();
      const matchesQuery = !normalized || searchable.includes(normalized);
      const matchesType = programType === "all" || program.program_type === programType;
      const matchesProvince = province === "all" || program.province === province;
      const matchesShortlist = activeView !== "shortlist" || savedIds.includes(program.id);
      return matchesQuery && matchesType && matchesProvince && matchesShortlist;
    });
  }, [programs, query, programType, province, activeView, savedIds]);

  const toggleSave = (programId: string) => {
    const isSaved = savedIds.includes(programId);
    setSavedIds((current) => isSaved
      ? current.filter((id) => id !== programId)
      : [...current, programId]);
    setNotice(isSaved ? "Removed from your shortlist" : "Saved to your shortlist");
  };

  const toggleChecklistTask = (taskKey: string) => {
    setCompletedChecklistKeys((current) => current.includes(taskKey)
      ? current.filter((key) => key !== taskKey)
      : [...current, taskKey]);
  };

  const toggleCompare = (programId: string) => {
    const isSelected = compareIds.includes(programId);
    if (!isSelected && compareIds.length >= 3) {
      setNotice("Compare up to three programs at a time");
      return;
    }
    setCompareIds((current) => isSelected
      ? current.filter((id) => id !== programId)
      : [...current, programId]);
  };

  const openComparison = async () => {
    if (compareIds.length < 2) return;
    setCompareLoading(true);
    setCompareError("");
    try {
      const params = new URLSearchParams({ ids: compareIds.join(",") });
      const result = await getJson<Program[]>(`/api/compare?${params.toString()}`);
      setComparePrograms(result);
    } catch (error) {
      setCompareError(error instanceof Error ? error.message : "Could not compare programs.");
    } finally {
      setCompareLoading(false);
    }
  };

  const clearFilters = () => {
    setQuery("");
    setProgramType("all");
    setProvince("all");
  };

  const uniqueSources = overview?.official_source_count ?? 0;
  const verifiedFacts = overview?.verified_fact_count ?? 0;
  const shownCount = filteredPrograms.length;
  const earliestDeadline = findEarliestDeadline(programs);
  const savedPrograms = programs.filter((program) => savedIds.includes(program.id));
  const checklistTasks = savedPrograms.flatMap(buildChecklistTasks);
  const openChecklistCount = checklistTasks.filter((task) => !completedChecklistKeys.includes(task.key)).length;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Pathfinder home">
          <span className="brand-mark"><Sparkles size={17} /></span>
          <span className="brand-wordmark">PATHFINDER<span>CANADA</span></span>
        </a>
        <nav className="top-nav" aria-label="Primary navigation">
          <a className="nav-link active" href="#explorer">Program explorer</a>
          <a className="nav-link" href="#evidence">Evidence standard</a>
        </nav>
        <div className="topbar-actions">
          <span className="catalog-live"><span /> Curated snapshot</span>
          <a className="api-link" href="/api/docs" target="_blank" rel="noreferrer" title="Open API documentation">
            API <ArrowUpRight size={13} />
          </a>
        </div>
      </header>

      <main id="top">
        <section className="hero-section">
          <div className="hero-copy">
            <div className="hero-kicker"><span className="kicker-line" /> CANADA · GRADUATE STUDY</div>
            <h1>Choose your next<br /><em>academic move</em> with evidence.</h1>
            <p className="hero-subtitle">A calmer way to research graduate programs. Compare official requirements, keep the source close, and leave unknowns honestly unknown.</p>
            <div className="hero-actions">
              <a className="button button-primary" href="#explorer">Explore programs <ArrowUpRight size={16} /></a>
              <div className="hero-assurance"><ShieldCheck size={16} /> Official pages. No guessed facts.</div>
            </div>
          </div>
          <div className="hero-side-card">
            <div className="hero-card-top">
              <div className="hero-card-icon"><CalendarDays size={18} /></div>
              <span className="hero-card-label">Earliest deadline in snapshot</span>
              <span className="hero-card-dots" aria-hidden="true"><i /><i /><i /></span>
            </div>
            {earliestDeadline ? (
              <div className="hero-deadline-date">{earliestDeadline.month} <strong>{earliestDeadline.day}</strong></div>
            ) : (
              <div className="hero-deadline-date no-deadline">No date captured</div>
            )}
            <div className="hero-deadline-meta">
              <span>Check intake details on source</span>
              <span className="deadline-status"><span /> {earliestDeadline?.count ?? 0} program{earliestDeadline?.count === 1 ? "" : "s"}</span>
            </div>
            <div className="hero-card-rule" />
            <div className="hero-card-footer">
              <span>Snapshot reviewed</span>
              <strong>{overview ? formatDate(overview.catalog_checked_at) : "Loading"}</strong>
            </div>
            <div className="deadline-card-watermark" aria-hidden="true">P</div>
          </div>
          <div className="hero-orb hero-orb-one" aria-hidden="true" />
          <div className="hero-orb hero-orb-two" aria-hidden="true" />
        </section>

        <section className="metric-strip" aria-label="Catalog overview">
          <div className="metric-item">
            <span className="metric-icon metric-icon-green"><GraduationCap size={17} /></span>
            <div><strong>{overview?.program_count ?? "—"}</strong><span>Programs tracked</span></div>
          </div>
          <div className="metric-divider" />
          <div className="metric-item">
            <span className="metric-icon metric-icon-blue"><FileText size={16} /></span>
            <div><strong>{uniqueSources}</strong><span>Official source pages</span></div>
          </div>
          <div className="metric-divider" />
          <div className="metric-item">
            <span className="metric-icon metric-icon-gold"><CheckCircle2 size={16} /></span>
            <div><strong>{verifiedFacts}</strong><span>Linked verified facts</span></div>
          </div>
          <div className="metric-note"><ShieldCheck size={15} /> Snapshot reviewed {overview ? formatDate(overview.catalog_checked_at) : "—"}</div>
        </section>

        <section className="explorer-section" id="explorer">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">YOUR RESEARCH WORKSPACE</p>
              <h2>Program explorer</h2>
              <p className="section-subtitle">A focused starter set of Canadian AI and computer science graduate programs.</p>
            </div>
            <div className="view-switch" role="tablist" aria-label="Program view">
              <button className={activeView === "explore" ? "active" : ""} type="button" role="tab" aria-selected={activeView === "explore"} onClick={() => setActiveView("explore")}>
                Explore <span>{programs.length}</span>
              </button>
              <button className={activeView === "shortlist" ? "active" : ""} type="button" role="tab" aria-selected={activeView === "shortlist"} onClick={() => setActiveView("shortlist")}>
                <Bookmark size={14} /> Shortlist <span>{savedIds.length}</span>
              </button>
              <button className={activeView === "checklist" ? "active" : ""} type="button" role="tab" aria-selected={activeView === "checklist"} onClick={() => setActiveView("checklist")}>
                <CheckCircle2 size={14} /> Checklist <span>{openChecklistCount}</span>
              </button>
            </div>
          </div>

          {activeView !== "checklist" && (
            <>
          <div className="filter-panel">
            <label className="search-box">
              <Search size={18} />
              <span className="sr-only">Search programs</span>
              <input
                ref={searchInputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search a school, field, or requirement..."
              />
              {query && <button type="button" aria-label="Clear search" onClick={() => setQuery("")}><X size={15} /></button>}
              <kbd>Ctrl K</kbd>
            </label>
            <div className="filter-control">
              <SlidersHorizontal size={16} />
              <label className="sr-only" htmlFor="program-type">Program type</label>
              <select id="program-type" value={programType} onChange={(event) => setProgramType(event.target.value)}>
                <option value="all">All program types</option>
                <option value="research">Research</option>
                <option value="professional">Professional</option>
              </select>
              <ChevronDown size={14} className="select-chevron" />
            </div>
            <div className="filter-control province-filter">
              <MapPin size={16} />
              <label className="sr-only" htmlFor="province">Province</label>
              <select id="province" value={province} onChange={(event) => setProvince(event.target.value)}>
                <option value="all">All provinces</option>
                {provinces.map((item) => <option value={item} key={item}>{item}</option>)}
              </select>
              <ChevronDown size={14} className="select-chevron" />
            </div>
          </div>

          <div className="results-toolbar">
            <div className="results-count"><strong>{shownCount}</strong> {shownCount === 1 ? "program" : "programs"} <span>·</span> Curated catalog order · not an admissions ranking</div>
            {(query || programType !== "all" || province !== "all") && (
              <button className="clear-filters" type="button" onClick={clearFilters}>Clear filters <X size={13} /></button>
            )}
          </div>

            </>
          )}

          {loading ? (
            <div className="loading-state"><span className="loading-spinner" /> Loading the verified catalog…</div>
          ) : loadError ? (
            <div className="error-state">
              <div className="error-icon"><X size={18} /></div>
              <div><strong>Catalog unavailable</strong><p>{loadError}</p><span>Start the API server, then refresh this page.</span></div>
            </div>
          ) : activeView === "checklist" ? (
            <ChecklistBoard
              programs={savedPrograms}
              completedKeys={completedChecklistKeys}
              onToggle={toggleChecklistTask}
              onExplore={() => setActiveView("explore")}
            />
          ) : filteredPrograms.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><Search size={20} /></div>
              <h3>{activeView === "shortlist" ? "Your shortlist is empty" : "No programs match those filters"}</h3>
              <p>{activeView === "shortlist" ? "Save programs with the bookmark button and they will appear here." : "Try a broader search or clear the filters to see the full starter set."}</p>
              <button className="button button-secondary" type="button" onClick={clearFilters}>Reset search</button>
            </div>
          ) : (
            <div className="program-grid">
              {filteredPrograms.map((program) => (
                <ProgramCard
                  key={program.id}
                  program={program}
                  saved={savedIds.includes(program.id)}
                  selectedForCompare={compareIds.includes(program.id)}
                  onOpen={setDetailProgram}
                  onSave={toggleSave}
                  onCompare={toggleCompare}
                />
              ))}
            </div>
          )}
        </section>

        <section className="evidence-section" id="evidence">
          <div className="evidence-icon"><ShieldCheck size={20} /></div>
          <div className="evidence-copy">
            <p className="eyebrow">BUILT FOR TRACEABILITY</p>
            <h2>Evidence first. Unknowns stay visible.</h2>
            <p>Every verified fact links to an official page and carries a review date. If a value has not been collected, Pathfinder says so instead of filling the gap with a guess.</p>
          </div>
          <div className="evidence-points">
            <span><Check size={14} /> Official university sources</span>
            <span><Check size={14} /> Dated research snapshot</span>
            <span><Check size={14} /> No automated applications</span>
          </div>
        </section>

        <section className="method-note">
          <div className="method-note-icon"><FileText size={17} /></div>
          <div>
            <strong>Research note</strong>
            <p>This starter catalog is a dated snapshot, not a live admissions feed. Deadlines and requirements change. Confirm each decision-critical detail with the institution before acting.</p>
          </div>
          <a href="/api/docs" target="_blank" rel="noreferrer">Explore the API <ArrowUpRight size={14} /></a>
        </section>
      </main>

      <footer className="footer">
        <a className="brand footer-brand" href="#top"><span className="brand-mark"><Sparkles size={15} /></span><span className="brand-wordmark">PATHFINDER<span>CANADA</span></span></a>
        <span>Independent research workspace · Not admissions or immigration advice</span>
        <span className="footer-build">Built for evidence <span>✳</span></span>
      </footer>

      {compareIds.length > 0 && (
        <div className="compare-tray" role="region" aria-label="Program comparison tray">
          <div className="compare-tray-copy">
            <span className="tray-icon"><Scale size={17} /></span>
            <div><strong>{compareIds.length} selected</strong><span>{compareIds.length < 2 ? "Add one more to compare" : "Ready for a side-by-side view"}</span></div>
          </div>
          <div className="compare-tray-selection">
            {compareIds.map((id) => {
              const program = programs.find((item) => item.id === id);
              return program ? <span className="tray-chip" key={id}>{program.institution_short}<button type="button" aria-label={`Remove ${program.institution_short}`} onClick={() => toggleCompare(id)}><X size={12} /></button></span> : null;
            })}
          </div>
          <div className="compare-tray-actions">
            <button className="tray-clear" type="button" onClick={() => setCompareIds([])}>Clear</button>
            <button className="button button-primary compare-open-button" type="button" disabled={compareIds.length < 2 || compareLoading} onClick={openComparison}>
              {compareLoading ? "Loading…" : "Compare programs"} <ArrowUpRight size={15} />
            </button>
          </div>
          {compareError && <span className="tray-error" role="alert">{compareError}</span>}
        </div>
      )}

      {notice && <div className="toast" role="status"><CheckCircle2 size={16} /> {notice}</div>}
      {detailProgram && <DetailModal program={detailProgram} onClose={() => setDetailProgram(null)} />}
      {comparePrograms && <CompareModal programs={comparePrograms} onClose={() => setComparePrograms(null)} />}
    </div>
  );
}

export default App;
