"use client";
import { useData, ApiState, DemoSettings } from "./DataProvider";
export function DataSourcesPanel() {
  const d = useData();
  return (
    <section aria-label="Source families">
      <DemoSettings />
      <ApiState error={d.catalogue.error} />
      {d.catalogue.value?.datasets.map((v) => (
        <div key={v.dataset_id} className="source-row">
          <strong>{v.source_name}</strong>
          <small>
            {v.name} · {v.dataset_id}
          </small>
          <small>
            {v.mode} · {v.status.replaceAll("_", " ")}
          </small>
          <small>
            Variables:{" "}
            {(v.variables.length ? v.variables : d.product.value?.dataset_id === v.dataset_id ? d.product.value.variables : []).map((x) => `${x.name} (${x.units})`).join(", ") || "Select a prepared product to inspect variable metadata"}
          </small>
          <small>
            Capabilities:{" "}
            {Object.entries(v.capabilities)
              .filter(([, x]) => x === true)
              .map(([key]) => key)
              .join(", ") || "None available"}
          </small>
        </div>
      ))}
      <h2>Acquisitions</h2>
      <ApiState error={d.acquisitions.error} />
      {d.acquisitions.value?.acquisitions.map((a) => (
        <p className="field-note" key={a.acquisition_id}>
          {a.source_name} · {a.status.replaceAll("_", " ")}
          <br />
          {a.provenance}
        </p>
      ))}
    </section>
  );
}
