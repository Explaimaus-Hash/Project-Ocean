"use client";
import { useMemo, useState } from "react";
import { Calendar, ArrowRight } from "lucide-react";

/**
 * Given the full list of available ISO-8601 source timestamps and a target
 * date string (YYYY-MM-DD), return the index of the timestamp whose date is
 * closest (by absolute millisecond distance) to midnight UTC of that date.
 * Returns -1 when `times` is empty or `targetDate` is unparseable.
 */
function findClosestTimeIndex(times: readonly string[], targetDate: string): number {
  if (!times.length) return -1;
  const target = Date.parse(`${targetDate}T00:00:00.000Z`);
  if (!Number.isFinite(target)) return -1;

  let best = 0;
  let bestDiff = Math.abs(Date.parse(times[0]) - target);

  for (let i = 1; i < times.length; i++) {
    const diff = Math.abs(Date.parse(times[i]) - target);
    if (diff < bestDiff) {
      best = i;
      bestDiff = diff;
    }
  }
  return best;
}

/** Extract YYYY-MM-DD from an ISO timestamp. */
function toDateString(iso: string | undefined): string {
  if (!iso) return "";
  return iso.slice(0, 10);
}

/** Format an ISO timestamp to a human-friendly display string. */
function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    });
  } catch {
    return iso.slice(0, 10);
  }
}

export function SourceTimeControl({ times, timestamp, onSelect }: {
  times: readonly string[];
  timestamp?: string;
  onSelect: (timestamp: string) => void;
}) {
  const available = times.length > 0;

  // Derive min/max date bounds from the available timestamps
  const { minDate, maxDate } = useMemo(() => {
    if (!times.length) return { minDate: "", maxDate: "" };
    return {
      minDate: toDateString(times[0]),
      maxDate: toDateString(times[times.length - 1]),
    };
  }, [times]);

  const [draft, setDraft] = useState(toDateString(timestamp));

  const handleDateChange = (dateValue: string) => {
    setDraft(dateValue);
    if (!dateValue || !available) return;
    const idx = findClosestTimeIndex(times, dateValue);
    if (idx >= 0) onSelect(times[idx]);
  };

  const currentDateStr = toDateString(timestamp);
  const matchedDisplay = timestamp ? formatTimestamp(timestamp) : null;

  return (
    <div className="source-time-control">
      <label htmlFor="source-date-input" className="source-time-label">
        <Calendar size={14} />
        DATE · SOURCE UTC
      </label>
      <div className="source-date-row">
        <input
          id="source-date-input"
          type="date"
          value={draft || currentDateStr}
          min={minDate}
          max={maxDate}
          disabled={!available}
          aria-describedby="source-date-help"
          onChange={(e) => handleDateChange(e.target.value)}
        />
      </div>
      {matchedDisplay && (
        <div className="source-date-matched">
          <ArrowRight size={12} />
          <span className="matched-label">Matched to</span>
          <strong>{matchedDisplay}</strong>
        </div>
      )}
      <p id="source-date-help" className="field-note">
        {available
          ? `Select a date — auto-snaps to nearest available frame from ${times.length} timestamps.`
          : "No timestamps available."}
      </p>
    </div>
  );
}
