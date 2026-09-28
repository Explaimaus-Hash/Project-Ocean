import { ObservationSearch } from "@/features/observations/ObservationSearch";
import type { WorkspaceRoute } from "@/lib/routes";
import { SelectionControls } from "@/features/controls/SelectionControls";

export function WorkspacePanel({ route }: { route: WorkspaceRoute }) {
  return (
    <div className="panel-content">
      <div className="panel-heading">
        <span className="eyebrow">PROJECT OCEAN / WORKSPACE</span>
        <h1>{route.label}</h1>
        <p>{route.description}</p>
      </div>
      {route.href === "/profiles" && <ObservationSearch />}
      <SelectionControls />
      <p className="workspace-guidance">
        {route.href === "/profiles"
          ? "Select a paged observation or a globe marker to inspect its source profile."
          : route.href === "/explorer"
            ? "Select a prepared product. Click its displayed field to inspect a returned grid cell; visual interpolation never changes that value."
            : "Source capabilities determine which scientific controls are available."}
      </p>
    </div>
  );
}
