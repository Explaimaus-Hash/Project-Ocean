"use client";
import { useData } from "@/features/data-sources/DataProvider";
import { useSelection } from "@/lib/selection";
import { useGlobe } from "@/features/globe/GlobeContext";
import { capabilityModes } from "./advancedModel";
import { DepthSliceLayer } from "./DepthSliceLayer";
import { CurrentRenderer } from "./CurrentRenderer";
import { VolumePrototype } from "./VolumePrototype";
export function ConnectedAdvancedLayer() {
  const d = useData(),
    { selection } = useSelection(),
    { settings } = useGlobe();
  const field = d.advancedField;
  const modes = capabilityModes(d.product.value, field, {
    variable: d.variable,
    timestamp: d.timestamp,
  });
  if (
    !field ||
    !modes[selection.renderMode] ||
    selection.renderMode === "surface"
  )
    return null;
  const options = {
    quality: settings.quality,
    exaggeration: settings.exaggeration,
    depthIndex: Math.max(
      0,
      field.depths.indexOf(selection.depth?.value ?? field.depths[0]),
    ),
    density: settings.vectorDensity,
    vectorScale: settings.vectorScale,
    speedColor: settings.speedColor,
  };
  return selection.renderMode === "depth-slice" ? (
    <DepthSliceLayer field={field} options={options} />
  ) : selection.renderMode === "vectors" ? (
    <CurrentRenderer field={field} options={options} />
  ) : (
    <VolumePrototype field={field} options={options} />
  );
}
