"use client";
import { Waves } from "lucide-react";
import { useSelection } from "@/lib/selection";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useData } from "@/features/data-sources/DataProvider";
import { WorkspaceDialogs } from "./WorkspaceDialogs";
export function TopBar() {
  const { selection } = useSelection();
  const data = useData();
  const backend = data.health.value
    ? "Backend connected"
    : data.health.error
      ? "Backend offline"
      : "Connecting backend";
  return (
    <header className="top-bar">
      <div className="brand">
        <Waves aria-hidden="true" />
        <div>
          PROJECT <strong>OCEAN</strong>
          <small>OCEAN INTELLIGENCE WORKSPACE</small>
        </div>
      </div>
      <div className="top-context">
        <span className="top-divider" />
        <span>
          {selection.region === "indian-ocean"
            ? "Indian Ocean"
            : "Global ocean"}
        </span>
        <span className="muted">/</span>
        <span className="muted">
          Source: {data.dataset?.source_name ?? "not selected"}
          <small className="dataset-context">
            Dataset: {data.dataset?.name ?? "not selected"}
          </small>
        </span>
      </div>
      <div className="top-status">
        <span
          title="Backend connectivity is separate from dataset readiness"
          className="backend-status"
        >
          <StatusBadge tone={!!data.health.value ? "success" : "neutral"}>
            {backend}
          </StatusBadge>
        </span>
        <StatusBadge tone="neutral">Local prepared data</StatusBadge>
        <span title={data.readiness.value?.reason}>
          <StatusBadge>
            Readiness:{" "}
            {data.readiness.value
              ? data.readiness.value.ready ? "surface ready" : "not ready"
              : data.readiness.error
                ? "unavailable"
                : "checking"}
          </StatusBadge>
        </span>
        <WorkspaceDialogs />
      </div>
    </header>
  );
}
