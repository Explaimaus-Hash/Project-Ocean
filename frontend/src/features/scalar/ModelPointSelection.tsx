"use client";
import { usePathname } from "next/navigation";
import { useSelection } from "@/lib/selection";
import { useScalar } from "./ScalarContext";
import { useGeographicSelection } from "@/features/analysis/useGeographicSelection";
import { modelCell } from "./modelPoint";
export function ModelPointSelection() {
  const path = usePathname();
  const { selection, dispatch } = useSelection();
  const s = useScalar();
  const enabled =
    path === "/explorer" &&
    selection.renderMode === "surface" &&
    s.settings.visible &&
    !!s.renderInfo;
  const frame = s.renderInfo?.frame,
    point = selection.analysisPoint;
  const cell = enabled && frame && point ? modelCell(frame, point) : null;
  useGeographicSelection({
    mode: enabled ? "point" : "none",
    requested: enabled && point ? point : undefined,
    actual: cell ?? undefined,
    onPoint: (p) => {
      dispatch({ type: "select-observation-sample", value: null });
      dispatch({ type: "select-analysis-point", point: p });
    },
  });
  return null;
}
