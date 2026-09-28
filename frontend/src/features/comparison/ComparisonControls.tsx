"use client";
import type { ComparisonSelection } from "./comparisonModel";
export function ComparisonControls({
  value,
  onChange,
  demo,
}: {
  value: ComparisonSelection;
  onChange: (value: ComparisonSelection) => void;
  demo: boolean;
}) {
  const patch = (p: Partial<ComparisonSelection>) =>
    onChange({ ...value, ...p });
  return (
    <section className="comparison-controls" aria-label="Comparison controls">
      <label>
        Model source
        <select
          aria-label="Comparison model source"
          value={value.model}
          onChange={(e) =>
            patch({ model: e.target.value as ComparisonSelection["model"] })
          }
        >
          <option>INCOIS</option>
          <option>Copernicus</option>
        </select>
      </label>
      <label>
        Observation source
        <select
          aria-label="Comparison observation source"
          value={value.observation}
          onChange={(e) =>
            patch({
              observation: e.target.value as ComparisonSelection["observation"],
            })
          }
        >
          <option>Argo</option>
          <option>Glider</option>
        </select>
      </label>
      <label>
        Variable
        <select
          aria-label="Comparison variable"
          disabled={!demo}
          value={value.variable}
          onChange={(e) => patch({ variable: e.target.value })}
        >
          <option value="">Awaiting documented service metadata</option>
          {demo && (
            <option value="TEMP">Temperature (°C) · illustrative</option>
          )}
        </select>
      </label>
      <label>
        Region
        <select
          aria-label="Comparison region"
          value={value.region}
          onChange={(e) => patch({ region: e.target.value })}
        >
          <option value="project">30–120°E / 30°S–30°N (requested)</option>
          <option value="global">Global (requested)</option>
        </select>
      </label>
      <label>
        Time window start
        <input
          aria-label="Comparison start date"
          type="date"
          value={value.start}
          onChange={(e) => patch({ start: e.target.value })}
        />
      </label>
      <label>
        Time window end
        <input
          aria-label="Comparison end date"
          type="date"
          value={value.end}
          onChange={(e) => patch({ end: e.target.value })}
        />
      </label>
      <label>
        Depth / pressure range
        <input
          aria-label="Comparison vertical range"
          value={value.verticalRange}
          onChange={(e) => patch({ verticalRange: e.target.value })}
          placeholder="Awaiting vertical metadata"
        />
      </label>
      <label title="No backend policy is available">
        QC policy
        <select disabled aria-label="Comparison QC policy">
          <option>
            {demo ? "Illustrative flags only" : "Backend policy unavailable"}
          </option>
        </select>
      </label>
      <p className="comparison-policy">
        Matching tolerance:{" "}
        <strong>Not supplied by a documented backend policy</strong>. No
        authoritative tolerance defaults.{" "}
        {demo && "Fixture coordinates and offsets are authored examples only."}
      </p>
    </section>
  );
}
