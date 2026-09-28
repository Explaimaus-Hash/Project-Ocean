"use client";
import { useMemo, useState } from "react";
import { ComparisonControls } from "./ComparisonControls";
import { ComparisonSummary } from "./ComparisonSummary";
import { ComparisonMetrics } from "./ComparisonMetrics";
import { MatchedPairTable } from "./MatchedPairTable";
import { ProfileComparisonPlot } from "./ProfileComparisonPlot";
import { ScatterComparisonPlot } from "./ScatterComparisonPlot";
import { ResidualPlot } from "./ResidualPlot";
import { PairedSeriesPlot } from "./PairedSeriesPlot";
import { createComparisonFixture } from "./demoComparison";
import {
  initialComparison,
  unavailableMessage,
  validPairs,
  type ComparisonSelection,
} from "./comparisonModel";
const demoEnabled =
  process.env.NODE_ENV === "development" &&
  process.env.NEXT_PUBLIC_ENABLE_DEMO_COMPARISON === "true";
export function ComparisonPanel() {
  const [mode, setMode] = useState<"real" | "demo">("real");
  const [selection, setSelection] =
    useState<ComparisonSelection>(initialComparison);
  const [selectedId, setSelectedId] = useState("");
  const demo = demoEnabled && mode === "demo";
  const fixture = useMemo(
    () => (demo ? createComparisonFixture() : undefined),
    [demo],
  );
  const matches =
    demo &&
    selection.model === "INCOIS" &&
    selection.observation === "Argo" &&
    selection.variable === "TEMP" &&
    selection.region === "project" &&
    selection.start === "2020-01-01" &&
    selection.end === "2020-01-03" &&
    selection.verticalRange === "0–150 dbar";
  const result = matches ? fixture : undefined;
  const pairs = validPairs(result);
  const selected = pairs.find((p) => p.id === selectedId) ?? pairs[0];
  return (
    <div className="comparison-workspace">
      <header>
        <span className="eyebrow">PROJECT OCEAN / COMPARISON</span>
        <h1>Model & observation</h1>
        <p>Inspect compatibility before interpreting agreement.</p>
      </header>
      <div className="comparison-mode">
        <button
          aria-pressed={!demo}
          onClick={() => {
            setMode("real");
            setSelection(initialComparison);
            setSelectedId("");
          }}
        >
          Real mode
        </button>
        <button
          disabled={!demoEnabled}
          title={
            demoEnabled
              ? "Authored development fixture"
              : "Requires development server and NEXT_PUBLIC_ENABLE_DEMO_COMPARISON=true"
          }
          aria-pressed={demo}
          onClick={() => {
            setMode("demo");
            setSelection({
              ...initialComparison,
              variable: "TEMP",
              start: "2020-01-01",
              end: "2020-01-03",
              verticalRange: "0–150 dbar",
            });
            setSelectedId("");
          }}
        >
          Illustrative demo mode
        </button>
      </div>
      {demo ? (
        <div className="demo-notice" role="status">
          <strong>Illustrative / Demo data</strong>
          <p>
            Not operational data, model validation or an authoritative policy.
            One fixed INCOIS/Argo illustrative scenario; changing its scope
            withholds results.
          </p>
        </div>
      ) : (
        <div className="api-state" role="status">
          <strong>{unavailableMessage}</strong>
          <p>
            No documented comparison HTTP route is connected. No matching
            requests or metrics are invented.
          </p>
        </div>
      )}
      <ComparisonControls
        value={selection}
        demo={demo}
        onChange={(v) => {
          setSelection(v);
          setSelectedId("");
        }}
      />
      {demo && !result && (
        <p role="status">
          No illustrative fixture for this selection. Re-select Illustrative
          demo mode to restore its exact scope.
        </p>
      )}
      <ComparisonSummary result={result} />
      <ComparisonMetrics result={result} />
      {result && selected ? (
        <>
          <label className="comparison-pair-picker">
            Synchronized pair
            <select
              aria-label="Synchronized pair"
              value={selected.id}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              {pairs.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id} · {p.modelTime} · {p.observationDepth} {p.verticalUnit}
                </option>
              ))}
            </select>
          </label>
          <div className="comparison-graphs">
            <ProfileComparisonPlot result={result} selected={selected} />
            <ScatterComparisonPlot result={result} selected={selected} />
            <ResidualPlot result={result} selected={selected} />
            <PairedSeriesPlot result={result} selected={selected} />
          </div>
        </>
      ) : (
        <div className="comparison-graphs">
          {[
            "Model vs Observation Profile",
            "Model vs Observation Scatter Plot",
            "Residual · Model - Observation",
            "Paired Time Series",
          ].map((title) => (
            <section className="comparison-placeholder" key={title}>
              <h2>{title}</h2>
              <p>{unavailableMessage}</p>
              <small>
                Quantity, units, matched support and policy must be verified
                before plotting.
              </small>
            </section>
          ))}
        </div>
      )}
      <MatchedPairTable
        key={result ? "fixture" : "unavailable"}
        result={result}
        selectedId={selected?.id}
        onSelect={(p) => setSelectedId(p.id)}
      />
    </div>
  );
}
