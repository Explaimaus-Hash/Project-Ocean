"use client";
import { useState } from "react";

/** UTC wall-clock input, never local timezone, nearest-date snapping or interpolation. */
export function sourceTimeIndex(times: readonly string[], draft: string): number {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?$/.exec(draft);
  if (!match) return -1;
  const canonical = `${match[1]}T${match[2]}:${match[3] ?? "00"}.${(match[4] ?? "").padEnd(3, "0")}Z`;
  const milliseconds = Date.parse(canonical);
  if (!Number.isFinite(milliseconds) || new Date(milliseconds).toISOString() !== canonical) return -1;
  return times.findIndex((time) => Date.parse(time) === milliseconds);
}

export function SourceTimeControl({ times, timestamp, onSelect }: {
  times: readonly string[];
  timestamp?: string;
  onSelect: (timestamp: string) => void;
}) {
  const [draft, setDraft] = useState(timestamp?.replace(/Z$/, "") ?? "");
  const [error, setError] = useState("");
  const available = times.length > 0;
  const apply = () => {
    const index = sourceTimeIndex(times, draft);
    if (index < 0) {
      setError("This time is not available in the selected prepared dataset. Choose an available source time below. Current selection is unchanged.");
      return;
    }
    setError("");
    onSelect(times[index]);
  };
  return (
    <div className="source-time-control">
      <label htmlFor="source-time-input">TIME · SOURCE UTC</label>
      <input
        id="source-time-input"
        type="datetime-local"
        step="0.001"
        value={draft}
        disabled={!available}
        aria-describedby="source-time-help source-time-error"
        aria-invalid={!!error}
        onChange={(event) => { setDraft(event.target.value); setError(""); }}
        onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); apply(); } }}
      />
      <button type="button" disabled={!available} onClick={apply}>Apply time</button>
      <p id="source-time-help" className="field-note">
        Enter date/time in UTC, not local time. Only exact source timestamps are accepted; no automatic nearest-time selection.
        {available ? ` ${times.length} timestamps currently prepared.` : " No timestamps available."}
      </p>
      <p id="source-time-error" role="alert" className="field-note">{error}</p>
      <label htmlFor="dataset-time">AVAILABLE SOURCE TIMES · UTC</label>
      <select id="dataset-time" value={timestamp ?? ""} disabled={!available}
        onChange={(event) => { setDraft(event.target.value.replace(/Z$/, "")); setError(""); onSelect(event.target.value); }}>
        {!available && <option value="">No timestamps available</option>}
        {times.map((time) => <option key={time}>{time}</option>)}
      </select>
    </div>
  );
}
