import { AdvancedLayer } from "./AdvancedLayer";
import type { AdvancedField } from "./advancedModel";
import type { RenderOptions } from "./cesiumAdvanced";
export function DepthSliceLayer(props: {
  field: AdvancedField;
  options: RenderOptions;
}) {
  return <AdvancedLayer {...props} mode="depth-slice" />;
}
