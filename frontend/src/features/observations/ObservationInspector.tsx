"use client";
import { useEffect, useRef, useState } from "react";
import { useData, ApiState } from "@/features/data-sources/DataProvider";
import { useSelection } from "@/lib/selection";
import { profileVariableAllowed } from "./observationModel";
import { ProfilePlot } from "./ProfilePlot";
export function ObservationInspector() {
  const d = useData();
  const { selection, dispatch } = useSelection();
  const selected = d.selectedSample,
    collection = d.collectionDetail.value;
  const close = useRef<HTMLButtonElement>(null);
  const [parameter, setParameter] = useState("TEMP");
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    close.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape")
        dispatch({ type: "select-observation-sample", value: null });
    };
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("keydown", escape);
      if (previous?.isConnected) previous.focus();
    };
  }, [dispatch, selection.selectedObservation?.sampleId]);
  const variables = collection?.variables.filter(profileVariableAllowed) ?? [];
  const variable = variables.find((v) => v.name === parameter) ?? variables[0];
  const samples = selected?.profile_id
    ? d.profile.value?.samples
    : selected
      ? [selected]
      : undefined;
  const vertical = selected?.depth_m != null ? "depth_m" : "pressure_dbar";
  const hasVertical = samples?.some((sample) => sample[vertical] !== null);
  return (
    <aside
      className="right-inspector observation-inspector"
      aria-label="Observation profile inspector"
    >
      <button
        ref={close}
        className="text-button"
        onClick={() =>
          dispatch({ type: "select-observation-sample", value: null })
        }
      >
        Close observation
      </button>
      <span className="eyebrow">
        {collection?.source.toUpperCase()} · {collection?.mode}
      </span>
      <h2>{selected?.profile_id ? "Observation profile" : "Observation sample"}</h2>
      {!selected ? (
        <p>No sample loaded on this page.</p>
      ) : (
        <>
          <p className="field-note">
            {selected.platform_id ?? "Platform not provided"} ·{" "}
            {selected.profile_id ?? "No profile ID"}
            <br />
            {selected.timestamp}
            <br />
            QC: {selected.qc} / {selected.data_mode ?? "Mode not provided"}
          </p>
          <details>
            <summary>Platform, position & provenance</summary>
            <dl>
              <dt>Platform</dt>
              <dd>{selected.platform_id ?? "Not provided"}</dd>
              <dt>Profile / cycle</dt>
              <dd>
                {selected.profile_id ?? "Not provided"} /{" "}
                {selected.cycle_id ?? "Not provided"}
              </dd>
              <dt>Deployment</dt>
              <dd>{selected.deployment_id ?? "Not provided"}</dd>
              <dt>Timestamp</dt>
              <dd>{selected.timestamp}</dd>
              <dt>Latitude / longitude</dt>
              <dd>
                {selected.latitude.toFixed(4)}° /{" "}
                {selected.longitude.toFixed(4)}°
              </dd>
              <dt>Source</dt>
              <dd>{collection?.name}</dd>
              <dt>QC / data mode</dt>
              <dd>
                {selected.qc} / {selected.data_mode ?? "Not provided"}
              </dd>
              <dt>Available parameters</dt>
              <dd>
                {collection?.variables
                  .map((v) => `${v.label} (${v.units})`)
                  .join(", ")}
              </dd>
            </dl>
          </details>
          {selected.provenance && <details><summary>Original QC, values and adjusted errors</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{JSON.stringify(JSON.parse(selected.provenance),null,2)}</pre></details>}
          {!selected.profile_id && <p className="field-note">This source does not establish a separate profile identity. The plot shows only the selected sample, not a reconstructed profile.</p>}
          <label htmlFor="profile-parameter">PROFILE PARAMETER</label>
          <select
            id="profile-parameter"
            value={variable?.name ?? ""}
            disabled={!variables.length}
            onChange={(e) => setParameter(e.target.value)}
          >
            {variables.map((v) => (
              <option key={v.name} value={v.name}>
                {v.label} ({v.units})
              </option>
            ))}
          </select>
          <p className="field-note">
            {variables.some((v) => v.interpretation === "chlorophyll")
              ? "BGC uses advertised normalized chlorophyll; no fluorescence conversion."
              : "BGC/chlorophyll is unavailable: no interpreted, normalized BGC parameter is advertised."}
          </p>
          <ApiState error={d.profile.error} />
          {samples && !hasVertical ? (
            <p role="status">
              No vertical coordinates supplied for this profile page.
            </p>
          ) : samples && variable ? (
            <ProfilePlot
              samples={samples}
              variable={variable}
              vertical={vertical}
            />
          ) : (
            !d.profile.error && (
              <p role="status">Loading bounded profile page…</p>
            )
          )}
          {d.profile.value && (
            <div className="observation-paging">
              <button
                disabled={d.profileOffset === 0}
                onClick={() =>
                  d.setProfileOffset(Math.max(0, d.profileOffset - 50))
                }
              >
                Previous profile page
              </button>
              <span>
                {d.profileOffset + 1}–
                {d.profileOffset + d.profile.value.samples.length} of{" "}
                {d.profile.value.total}
              </span>
              <button
                disabled={d.profileOffset + 50 >= d.profile.value.total}
                onClick={() => d.setProfileOffset(d.profileOffset + 50)}
              >
                Next profile page
              </button>
            </div>
          )}
          <p className="inspector-note">
            {collection?.provenance}
            <br />
            Discrete observations only. A connected trajectory is not continuous
            measured coverage.
          </p>
        </>
      )}
    </aside>
  );
}
