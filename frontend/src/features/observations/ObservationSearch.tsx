"use client";
import { useState } from "react";
import { useData, ApiState } from "@/features/data-sources/DataProvider";
import { useSelection } from "@/lib/selection";
import { markerSamples } from "./observationModel";
export function ObservationSearch() {
  const d = useData();
  const { selection, dispatch } = useSelection();
  const [source, setSource] = useState("all");
  const [profile, setProfile] = useState("");
  const collections =
    d.observations.value?.collections.filter(
      (c) => source === "all" || c.source === source,
    ) ?? [];
  const collection = d.collectionDetail.value;
  const samples = d.samples.value;
  const rows =
    collection && samples
      ? markerSamples(samples.samples, collection.source)
      : [];
  const reason =
    "This filter is not supported by the current observation query contract. No samples are filtered scientifically in the browser.";
  return (
    <section className="observation-search" aria-label="Observation search">
      <h2>Observation search</h2>
      <p className="field-note">
        {collection?.mode ?? "Loading"} catalogue · server-paged samples. Argo rows
        group profiles on this page only.
      </p>
      <label htmlFor="observation-type">SOURCE TYPE</label>
      <select
        id="observation-type"
        value={source}
        onChange={(e) => {
          setSource(e.target.value);
          dispatch({ type: "select-observation", id: "" });
        }}
      >
        <option value="all">Argo + Glider</option>
        <option value="argo">Argo</option>
        <option value="glider">Glider</option>
      </select>
      <label htmlFor="observation-collection">COLLECTION</label>
      <select
        id="observation-collection"
        value={selection.observationSource ?? ""}
        onChange={(e) =>
          dispatch({ type: "select-observation", id: e.target.value })
        }
      >
        <option value="">Select an observation collection</option>
        {collections.map((c) => (
          <option key={c.collection_id} value={c.collection_id}>
            {c.name}
          </option>
        ))}
      </select>
      <ApiState
        error={
          d.observations.error ?? d.collectionDetail.error ?? d.samples.error
        }
      />
      {d.observationQuery.profileId && (
        <p className="field-note">
          Applied profile: {d.observationQuery.profileId}
        </p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          d.setObservationQuery({ profileId: profile.trim(), offset: 0 });
        }}
      >
        <label htmlFor="profile-search">EXACT PROFILE ID</label>
        <input
          id="profile-search"
          value={profile}
          maxLength={128}
          placeholder="Backend-provided profile ID (r_...)"
          onChange={(e) => setProfile(e.target.value)}
        />
        <button disabled={!collection} type="submit">
          Search profile
        </button>
        <button
          type="button"
          onClick={() => {
            setProfile("");
            d.setObservationQuery({ profileId: "", offset: 0 });
          }}
        >
          Clear profile search
        </button>
      </form>
      <details>
        <summary>Additional search filters</summary>
        <p className="field-note" id="unsupported-observation-filters">
          {reason}
        </p>
        {[
          "Platform / float",
          "Cycle",
          "Deployment",
          "Date from",
          "Date to",
          "Region",
          "Parameter",
        ].map((label) => (
          <label key={label} title={reason}>
            {label}
            <input
              aria-label={label}
              aria-describedby="unsupported-observation-filters"
              disabled
              type={label.startsWith("Date") ? "date" : "text"}
              placeholder="Not supported by current API"
            />
          </label>
        ))}
      </details>
      {samples && (
        <>
          <div className="observation-paging">
            <button
              disabled={samples.offset === 0}
              onClick={() =>
                d.setObservationQuery({
                  offset: Math.max(0, samples.offset - 50),
                })
              }
            >
              Previous samples
            </button>
            <span>
              {samples.samples.length ? samples.offset + 1 : 0}–
              {samples.offset + samples.samples.length} of {samples.total}
            </span>
            <button
              disabled={samples.offset + samples.limit >= samples.total}
              onClick={() =>
                d.setObservationQuery({
                  offset: samples.offset + samples.limit,
                })
              }
            >
              Next samples
            </button>
          </div>
          <p className="field-note">
            {samples.samples.length} normalized samples on this page.{" "}
            {collection?.qc_status}
          </p>
          <ul className="observation-results">
            {rows.map((sample) => (
              <li key={sample.sample_id}>
                <button
                  onClick={() =>
                    dispatch({
                      type: "select-observation-sample",
                      value: {
                        collectionId: collection!.collection_id,
                        sampleId: sample.sample_id,
                        profileId: sample.profile_id,
                        source: collection!.source,
                      },
                    })
                  }
                  aria-label={`Inspect ${sample.sample_id}`}
                >
                  <strong>{sample.profile_id ?? sample.sample_id}</strong>
                  <small>
                    {sample.platform_id ?? "Platform not provided"} ·{" "}
                    {sample.timestamp}
                  </small>
                </button>
              </li>
            ))}
          </ul>
          {!rows.length && (
            <p role="status">No observations match this server query.</p>
          )}
        </>
      )}
    </section>
  );
}
