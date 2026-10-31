import { z } from "zod";
import { zDocumentSectionOutput as zDocumentSection, zDraftUpdate } from "../../shared/api/generated/zod.gen";
import { readDraft, saveDraft } from "../../shared/api/adapters/studio";
import { ApiError } from "../../shared/api/client/errors";

export type Draft = Awaited<ReturnType<typeof readDraft>>;
export type Section = z.output<typeof zDocumentSection>;
export type Update = z.input<typeof zDraftUpdate>;
export const editableKeys = ["title", "date_label", "editorial_notes", "day_overrides", "sections"] as const;
export type Form = Pick<Draft, typeof editableKeys[number]>;
export function formFrom(draft: Draft): Form {
  return structuredClone({ title: draft.title, date_label: draft.date_label, editorial_notes: draft.editorial_notes,
    day_overrides: draft.day_overrides, sections: draft.sections });
}
export function freeze<T>(value: T): T {
  if (value && typeof value === "object") { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).filter(([, v]) => v !== undefined).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, canonical(v)]));
  return value;
}
export const equal = (a: unknown, b: unknown) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
export function savePayload(baseline: Draft, form: Form): Update {
  // Required title/revision plus changed groups only: never leak optional schema
  // defaults into exclude_unset or overwrite advanced objects/status/snapshots.
  const result: Update = { revision: baseline.revision, title: form.title.trim() };
  if (!equal(form.date_label, baseline.date_label)) result.date_label = form.date_label;
  if (!equal(form.editorial_notes, baseline.editorial_notes)) result.editorial_notes = form.editorial_notes;
  if (!equal(form.day_overrides, baseline.day_overrides)) result.day_overrides = form.day_overrides;
  if (!equal(form.sections, baseline.sections)) result.sections = form.sections?.map((s) => ({ ...s, title: s.title.trim(), columns: s.columns?.map((c) => c.trim()),
    ...(s.knowledge ? { knowledge: { ...s.knowledge, sources: s.knowledge.sources?.map((source) => ({ ...source, reference: source.reference.trim() })) } } : {}) })) ?? form.sections;
  zDraftUpdate.parse(result);
  return result;
}
export type SaveIntent = Readonly<{ baseline: Draft; payload: Update }>;
export function saveIntent(baseline: Draft, form: Form): SaveIntent {
  return freeze(structuredClone({ baseline, payload: savePayload(baseline, form) }));
}
const serverKeys = new Set(["revision", "updated_at", "updated_by", "last_library_operation"]);
function content(draft: object) { return Object.fromEntries(Object.entries(draft).filter(([key]) => !serverKeys.has(key))); }
export function matchesSave(draft: Draft, intent: SaveIntent): boolean {
  const expected = { ...intent.baseline, ...intent.payload };
  return draft.revision === intent.baseline.revision + 1 && equal(content(draft), content(expected));
}
export type SaveOutcome = { kind: "saved"; draft: Draft } | { kind: "conflict" | "not-saved"; draft: Draft } | { kind: "uncertain" };
export async function inspectSave(intent: SaveIntent, signal?: AbortSignal): Promise<SaveOutcome> {
  try {
    const draft = await readDraft(intent.baseline.document_id!, signal);
    if (draft.document_id !== intent.baseline.document_id || draft.template_id !== intent.baseline.template_id || draft.confidentiality !== intent.baseline.confidentiality) return { kind: "uncertain" };
    if (matchesSave(draft, intent)) return { kind: "saved", draft };
    if (draft.revision === intent.baseline.revision && equal(draft, intent.baseline)) return { kind: "not-saved", draft };
    return { kind: "conflict", draft };
  } catch (error) {
    if (error instanceof ApiError && ["unauthenticated", "forbidden"].includes(error.kind)) throw error;
    return { kind: "uncertain" };
  }
}
export async function submitSave(intent: SaveIntent, signal?: AbortSignal): Promise<SaveOutcome> {
  try {
    const result = await saveDraft(intent.baseline.document_id!, intent.payload, signal);
    if (!matchesSave(result, intent)) return { kind: "uncertain" };
  } catch (error) {
    if (error instanceof ApiError && error.status && error.status < 500) throw error;
    return { kind: "uncertain" };
  }
  return inspectSave(intent, signal);
}

export const sectionKinds = { text: "Tekst", list: "Lista", image: "Zdjęcie", gallery: "Galeria", table: "Tabela", callout: "Wyróżnienie", day: "Dzień", logistics: "Logistyka", knowledge: "Wiedza", source: "Dane szablonu" };
export function customSection(kind: Section["kind"], order: number, dayId?: string): Section {
  if (kind === "source") throw new ApiError("validation");
  return zDocumentSection.parse({ section_id: crypto.randomUUID().replaceAll("-", ""), role: null, kind, title: sectionKinds[kind],
    order, visible: true, day_id: dayId ?? null, body: "", items: [], images: [], columns: kind === "table" ? ["Nazwa", "Opis"] : [], rows: [],
    logistics: kind === "logistics" ? { date: null, drive_km: null, walk_km: null, elevation_gain_m: null, drive_minutes: null, activity_minutes: null, accommodation_entry_id: null } : null,
    knowledge: kind === "knowledge" ? { part: "narrative", sources: [], stop_ids: [] } : null });
}
export function validationMessages(baseline: Draft, form: Form): string[] {
  const issues: string[] = [];
  const result = zDraftUpdate.safeParse({ revision: baseline.revision, ...form, title: form.title.trim() });
  if (!result.success) issues.push("Sprawdź wymagane pola i limity długości/liczby elementów.");
  for (const section of form.sections ?? []) {
    if (!section.title.trim() || section.columns?.some((c) => !c.trim())) issues.push("Tytuł sekcji i nagłówki tabeli nie mogą być puste.");
    if ((section.knowledge || section.logistics) && !baseline.trip_snapshot?.days?.some((day) => day.day_id === section.day_id)) issues.push("Wiedza i logistyka wymagają dnia z zapisanej migawki.");
    if (section.kind === "table" && (!section.columns?.length || section.rows?.some((row) => row.length !== section.columns?.length))) issues.push("Tabela wymaga nagłówków i zgodnej liczby komórek w każdym wierszu.");
    if (section.logistics) {
      const l = section.logistics;
      if (l.time_zone) { try { new Intl.DateTimeFormat("pl", { timeZone: l.time_zone }); } catch { issues.push("Podaj prawidłową strefę IANA."); } }
      if (l.verification_status === "verified" && !l.source.trim()) issues.push("Zweryfikowane metryki wymagają źródła pomiaru.");
    }
    if (section.knowledge?.verification_status === "verified" && (!section.knowledge.sources?.length || section.knowledge.sources.some((s) => !s.reference.trim() || !s.checked_on))) issues.push("Zweryfikowana wiedza wymaga źródeł i dat sprawdzenia.");
  }
  return [...new Set(issues)];
}
