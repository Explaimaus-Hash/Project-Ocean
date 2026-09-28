import { AdvancedLayer } from "./AdvancedLayer";
import type { AdvancedField } from "./advancedModel";
import type { RenderOptions } from "./cesiumAdvanced";
export function CurrentRenderer(props: {
  field: AdvancedField;
  options: RenderOptions;
}) {
  return <AdvancedLayer {...props} mode="vectors" />;
}
