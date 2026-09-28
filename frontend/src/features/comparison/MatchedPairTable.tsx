"use client";
import { useState } from "react";
import {
  residual,
  type ComparisonResult,
  type MatchedPair,
} from "./comparisonModel";
export function MatchedPairTable({
  result,
  selectedId,
  onSelect,
}: {
  result?: ComparisonResult;
  selectedId?: string;
  onSelect: (pair: MatchedPair) => void;
}) {
  const [page, setPage] = useState(0);
  const rows = result?.pairs ?? [];
  const index = Math.min(page, Math.max(0, Math.ceil(rows.length / 8) - 1));
  const number = (n: number | null) =>
    n === null ? "Missing" : Number(n.toFixed(3));
  return (
    <section className="matched-table" aria-label="Matched pairs">
      <h2>Match table</h2>
      <p>
        {result
          ? "Illustrative / Demo data · select a valid pair to synchronize profile time, series depth and scatter highlight."
          : "No documented matched pairs available."}
      </p>
      <div
        className="matched-scroll"
        tabIndex={0}
        aria-label="Scrollable match table"
      >
        <table>
          <thead>
            <tr>
              {[
                "Pair",
                "Model source",
                "Observation source",
                "Variable / units",
                "Model value",
                "Observation value",
                "Model - Observation",
                "Model time",
                "Observation time",
                "Time offset (s)",
                "Horizontal offset (km)",
                "Model depth / pressure",
                "Observation depth / pressure",
                "Vertical offset",
                "QC",
                "Match status",
              ].map((v) => (
                <th key={v} scope="col">
                  {v}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(index * 8, index * 8 + 8).map((p) => (
              <tr key={p.id} aria-selected={p.id === selectedId}>
                <td>
                  <button
                    aria-label={`Inspect pair ${p.id}`}
                    disabled={p.status !== "valid"}
                    onClick={() => onSelect(p)}
                  >
                    {p.id}
                  </button>
                </td>
                <td>{p.modelSource}</td>
                <td>{p.observationSource}</td>
                <td>
                  {p.variable} ({p.units})
                </td>
                <td>{number(p.model)}</td>
                <td>{number(p.observation)}</td>
                <td>
                  {p.status === "valid" ? number(residual(p)) : "Not evaluated"}
                </td>
                <td>{p.modelTime}</td>
                <td>{p.observationTime}</td>
                <td>{number(p.timeOffsetSeconds)}</td>
                <td>{number(p.horizontalOffsetKm)}</td>
                <td>
                  {number(p.modelDepth)} {p.verticalUnit}
                </td>
                <td>
                  {number(p.observationDepth)} {p.verticalUnit}
                </td>
                <td>
                  {number(p.depthOffset)} {p.verticalUnit}
                </td>
                <td>{p.qc}</td>
                <td>{p.status.replaceAll("_", " ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="observation-paging">
        <button disabled={!index} onClick={() => setPage(index - 1)}>
          Previous pairs
        </button>
        <span>
          {rows.length ? index * 8 + 1 : 0}–
          {Math.min(rows.length, index * 8 + 8)} of {rows.length}
        </span>
        <button
          disabled={(index + 1) * 8 >= rows.length}
          onClick={() => setPage(index + 1)}
        >
          Next pairs
        </button>
      </div>
    </section>
  );
}
