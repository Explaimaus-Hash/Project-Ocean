import type { ComparisonResult } from "./comparisonModel";
import { validPairs } from "./comparisonModel";
export function ComparisonSummary({ result }: { result?: ComparisonResult }) {
  const state = (v: boolean | undefined) =>
    v === undefined
      ? "Not evaluated"
      : v
        ? result?.mode === "synthetic"
          ? "Illustrative overlap"
          : "Verified overlap"
        : "No overlap";
  return (
    <section className="comparison-summary" aria-label="Overlap summary">
      <h2>Overlap & eligibility</h2>
      <dl>
        <div>
          <dt>Region overlap</dt>
          <dd>{state(result?.regionOverlap)}</dd>
        </div>
        <div>
          <dt>Time overlap</dt>
          <dd>{state(result?.timeOverlap)}</dd>
        </div>
        <div>
          <dt>Depth / pressure support</dt>
          <dd>{state(result?.depthSupport)}</dd>
        </div>
        <div>
          <dt>Compatible quantity</dt>
          <dd>
            {result?.compatible
              ? `${result.quantity} (${result.units}) · ${result.mode === "synthetic" ? "fixture" : "verified"}`
              : "Not evaluated"}
          </dd>
        </div>
        <div>
          <dt>Valid / unmatched</dt>
          <dd>
            {result
              ? `${validPairs(result).length} / ${result.pairs.length - validPairs(result).length}`
              : "Not evaluated"}
          </dd>
        </div>
      </dl>
      {result ? (
        <ul>
          {result.exclusions.map((e) => (
            <li key={e.reason}>
              {e.reason.replaceAll("_", " ")}: {e.count}
            </li>
          ))}
        </ul>
      ) : (
        <p>
          Exclusion reasons and counts require a documented comparison response.
        </p>
      )}
    </section>
  );
}
