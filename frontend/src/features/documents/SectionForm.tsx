import { Button } from "../../shared/ui/button";
import { zDayLogistics, zKnowledgeContent } from "../../shared/api/generated/zod.gen";
import type { Draft, Section } from "./editing";

const verificationLabels = { unverified: "Niezweryfikowane", proposed: "Proponowane", verified: "Zweryfikowane", rejected: "Odrzucone" };
function Verification({ value, onChange }: { value: NonNullable<Section["logistics"]>["verification_status"]; onChange: (value: NonNullable<Section["logistics"]>["verification_status"]) => void }) {
  return <label>Status weryfikacji<select value={value} onChange={(e) => onChange(zDayLogistics.shape.verification_status.parse(e.target.value))}>{Object.entries(verificationLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>;
}
function LogisticsForm({ value, draft, onChange }: { value: NonNullable<Section["logistics"]>; draft: Draft; onChange: (value: NonNullable<Section["logistics"]>) => void }) {
  const textFields = { route_start: "Początek trasy", route_end: "Koniec trasy", time_zone: "Strefa IANA", source: "Źródło pomiaru", organizational_notes: "Notatki organizacyjne", plan_b: "Plan B" } as const;
  const numericFields = { drive_km: "Dystans jazdy (km)", walk_km: "Dystans pieszy (km)", elevation_gain_m: "Przewyższenie (m)", drive_minutes: "Czas jazdy (min)", activity_minutes: "Czas aktywności (min)" } as const;
  return <fieldset><legend>Logistyka dnia</legend>
    <label>Data dnia<input type="date" value={value.date ?? ""} onChange={(e) => onChange({ ...value, date: e.target.value || null })} /></label>
    {Object.entries(textFields).map(([key, label]) => { const name = key as keyof typeof textFields; return <label key={key}>{label}<textarea maxLength={20000} value={value[name]} onChange={(e) => onChange({ ...value, [name]: e.target.value })} /></label>; })}
    {Object.entries(numericFields).map(([key, label]) => { const name = key as keyof typeof numericFields; return <label key={key}>{label}<input type="number" min={0} step={name.endsWith("minutes") ? 1 : "any"} value={value[name] ?? ""} onChange={(e) => onChange({ ...value, [name]: e.target.value === "" ? null : Number(e.target.value) })} /></label>; })}
    <label>Nocleg ze wspólnej logistyki<select value={value.accommodation_entry_id ?? ""} onChange={(e) => onChange({ ...value, accommodation_entry_id: e.target.value || null })}><option value="">Bez wskazanego wpisu</option>{draft.pilot_data?.accommodations?.map((entry) => <option value={entry.entry_id} key={entry.entry_id}>{entry.title}</option>)}</select></label>
    <Verification value={value.verification_status} onChange={(verification_status) => onChange({ ...value, verification_status })} />
    <p>Szacunki nie są pomiarami. Status zweryfikowany wymaga źródła; serwer sprawdza wartości i strefę czasu.</p>
  </fieldset>;
}
function KnowledgeForm({ section, draft, onChange }: { section: Section; draft: Draft; onChange: (value: NonNullable<Section["knowledge"]>) => void }) {
  const value = section.knowledge!;
  const fields = { facts: "Fakty i opisy atrakcji", history: "Historia", geology_nature: "Przyroda i geologia", culture: "Kultura", connection: "Powiązania miejsc", observations: "Obserwacje", stories: "Narracje i historie", pilot_notes: "Notatki pilota" } as const;
  const stops = draft.trip_snapshot?.days?.find((day) => day.day_id === section.day_id)?.stops ?? [];
  return <fieldset><legend>Materiały merytoryczne</legend>
    <p>Wpisuj wyłącznie sprawdzone treści. System nie generuje faktów. Weryfikacja wymaga źródeł i dat.</p>
    <label>Część wiedzy<select value={value.part} disabled={!!section.role} onChange={(e) => onChange({ ...value, part: zKnowledgeContent.shape.part.parse(e.target.value) })}><option value="attractions">Atrakcje</option><option value="context">Kontekst</option><option value="narrative">Narracja</option></select></label>
    <fieldset><legend>Miejsca programu tego dnia</legend>{stops.map((stop) => <label className="editor-check" key={stop.stop_id}><input type="checkbox" checked={value.stop_ids?.includes(stop.stop_id!) ?? false} onChange={(e) => onChange({ ...value, stop_ids: e.target.checked ? [...value.stop_ids ?? [], stop.stop_id!] : value.stop_ids?.filter((id) => id !== stop.stop_id) ?? [] })} />{stop.name}</label>)}</fieldset>
    {Object.entries(fields).map(([key, label]) => { const name = key as keyof typeof fields; return <label key={key}>{label}<textarea maxLength={20000} value={value[name]} onChange={(e) => onChange({ ...value, [name]: e.target.value })} /></label>; })}
    <Verification value={value.verification_status} onChange={(verification_status) => onChange({ ...value, verification_status })} />
    {(value.sources ?? []).map((source, index) => <fieldset key={index}><legend>Źródło {index + 1}</legend><label>Dokładne odniesienie {index + 1}<input maxLength={2000} value={source.reference} onChange={(e) => onChange({ ...value, sources: value.sources?.map((item, i) => i === index ? { ...item, reference: e.target.value } : item) })} /></label>
      <label>Data sprawdzenia {index + 1}<input type="date" value={source.checked_on ?? ""} onChange={(e) => onChange({ ...value, sources: value.sources?.map((item, i) => i === index ? { ...item, checked_on: e.target.value || null } : item) })} /></label>
      <Button variant="outline" onClick={() => onChange({ ...value, sources: value.sources?.filter((_, i) => i !== index) })}>Usuń źródło {index + 1}</Button></fieldset>)}
    <Button variant="outline" disabled={(value.sources?.length ?? 0) >= 100} onClick={() => onChange({ ...value, sources: [...value.sources ?? [], { reference: "", checked_on: null }] })}>Dodaj źródło</Button>
  </fieldset>;
}
function TableForm({ section, onChange }: { section: Section; onChange: (value: Section) => void }) {
  const columns = section.columns ?? [], rows = section.rows ?? [];
  return <fieldset><legend>Komórki tabeli</legend>
    {columns.map((column, i) => <label key={i}>Nagłówek {i + 1}<input maxLength={200} value={column} onChange={(e) => onChange({ ...section, columns: columns.map((c, j) => i === j ? e.target.value : c) })} /><Button variant="outline" disabled={columns.length <= 1} onClick={() => onChange({ ...section, columns: columns.filter((_, j) => i !== j), rows: rows.map((row) => row.filter((_, j) => j !== i)) })}>Usuń kolumnę {i + 1}</Button></label>)}
    <Button variant="outline" disabled={columns.length >= 8} onClick={() => onChange({ ...section, columns: [...columns, "Kolumna"], rows: rows.map((row) => [...row, ""]) })}>Dodaj kolumnę</Button>
    {rows.map((row, i) => <fieldset key={i}><legend>Wiersz {i + 1}</legend>{row.map((cell, j) => <label key={j}>Komórka {i + 1}, {j + 1}<textarea maxLength={20000} value={cell} onChange={(e) => onChange({ ...section, rows: rows.map((r, k) => k === i ? r.map((c, l) => l === j ? e.target.value : c) : r) })} /></label>)}<Button variant="outline" onClick={() => onChange({ ...section, rows: rows.filter((_, j) => j !== i) })}>Usuń wiersz {i + 1}</Button></fieldset>)}
    <Button variant="outline" disabled={!columns.length || rows.length >= 200} onClick={() => onChange({ ...section, rows: [...rows, columns.map(() => "")] })}>Dodaj wiersz</Button>
  </fieldset>;
}

export function SectionForm({ section, draft, required, onChange }: { section: Section; draft: Draft; required: boolean; onChange: (value: Section) => void }) {
  return <div className="section-form">
    <label>Tytuł sekcji<input maxLength={200} required value={section.title} onChange={(e) => onChange({ ...section, title: e.target.value })} /></label>
    <label className="editor-check"><input type="checkbox" checked={section.visible} disabled={required && section.visible} onChange={(e) => onChange({ ...section, visible: e.target.checked })} />Widoczna w dokumencie{required && " (wymagana)"}</label>
    <label>{section.kind === "source" ? "Dodatkowe uwagi sekcji źródłowej" : "Treść sekcji"}<textarea maxLength={20000} value={section.body} onChange={(e) => onChange({ ...section, body: e.target.value })} /></label>
    {section.kind === "source" ? <p>Pola związane z rolą szablonu i migawki pozostają bez zmian. Zaawansowaną treść źródłową edytuj w dotychczasowym Studio.</p> :
      <label>Powiązany dzień<select disabled={!!section.role} value={section.day_id ?? ""} onChange={(e) => onChange({ ...section, day_id: e.target.value || null, ...(section.knowledge ? { knowledge: { ...section.knowledge, stop_ids: [] } } : {}) })}><option value="">Cały dokument</option>{draft.trip_snapshot?.days?.map((day) => <option key={day.day_id} value={day.day_id}>Dzień {day.day_number}: {day.title}</option>)}</select></label>}
    {section.kind === "list" && <fieldset><legend>Punkty listy</legend>{(section.items ?? []).map((item, i) => <label key={i}>Punkt {i + 1}<textarea value={item} maxLength={20000} onChange={(e) => onChange({ ...section, items: section.items?.map((v, j) => i === j ? e.target.value : v) })} /><div className="creation-actions"><Button variant="outline" disabled={i === 0} onClick={() => { const items = [...section.items ?? []]; [items[i - 1], items[i]] = [items[i]!, items[i - 1]!]; onChange({ ...section, items }); }}>Punkt {i + 1} w górę</Button><Button variant="outline" onClick={() => onChange({ ...section, items: section.items?.filter((_, j) => j !== i) })}>Usuń punkt {i + 1}</Button></div></label>)}<Button variant="outline" disabled={(section.items?.length ?? 0) >= 200} onClick={() => onChange({ ...section, items: [...section.items ?? [], ""] })}>Dodaj punkt</Button></fieldset>}
    {section.kind === "table" && <TableForm section={section} onChange={onChange} />}
    {["image", "gallery"].includes(section.kind) && <fieldset><legend>Istniejące zdjęcia</legend><p>Załączniki i kadry są zachowane. Wgrywanie, dobór zdjęć i kadrowanie pozostają w dotychczasowym Studio.</p>{!section.images?.length && <p role="note">Brak zdjęć — podgląd użyje placeholdera.</p>}{section.images?.map((image, i) => <label key={i}>Podpis zdjęcia {i + 1}<textarea maxLength={20000} value={image.caption} onChange={(e) => onChange({ ...section, images: section.images?.map((value, j) => i === j ? { ...value, caption: e.target.value } : value) })} /><span>Zdjęcie: {image.asset_id ?? "placeholder"}; kadr {image.position?.x}/{image.position?.y}; zoom {image.position?.zoom}</span></label>)}</fieldset>}
    {section.logistics && <LogisticsForm value={section.logistics} draft={draft} onChange={(logistics) => onChange({ ...section, logistics })} />}
    {section.knowledge && <KnowledgeForm section={section} draft={draft} onChange={(knowledge) => onChange({ ...section, knowledge })} />}
  </div>;
}
