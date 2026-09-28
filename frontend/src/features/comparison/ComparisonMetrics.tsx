import { trustedMetrics, type ComparisonResult } from "./comparisonModel";
export function ComparisonMetrics({ result }: { result?: ComparisonResult }) {
  const metrics = trustedMetrics(result);
  return (
    <section className="comparison-metrics" aria-label="Comparison metrics">
      {[
        ["Valid pairs", metrics?.validPairs],
        [
          `Mean Bias (${result?.units ?? "units unavailable"})`,
          metrics?.meanBias,
        ],
        [`RMSE (${result?.units ?? "units unavailable"})`, metrics?.rmse],
        ["Correlation", metrics?.correlation],
      ].map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>
            {typeof value === "number"
              ? value.toLocaleString("en-US", { maximumFractionDigits: 4 })
              : "Not available"}
          </strong>
        </div>
      ))}
      <p>
        {metrics
          ? result?.mode === "synthetic"
            ? "Illustrative / Demo data · fixed fixture metrics, not operational validation."
            : "Metrics supplied by verified backend matching."
          : "Metrics withheld: no verified eligible matched pairs."}{" "}
        Bias = Model - Observation. No metrics are calculated from display
        fields.
      </p>
    </section>
  );
}
