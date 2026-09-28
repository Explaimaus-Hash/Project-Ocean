"use client";
import { ModelPointSelection } from "@/features/scalar/ModelPointSelection";
import { ConnectedAdvancedLayer } from "@/features/advanced-rendering/ConnectedAdvancedLayer";
import { RenderPerformance } from "@/features/advanced-rendering/RenderPerformance";
import { ObservationGlobeLayer } from "@/features/observations/ObservationGlobeLayer";
import { ScalarGlobeLayer } from "@/features/scalar/ScalarGlobeLayer";
import { useScalar } from "@/features/scalar/ScalarContext";
import {
  LocateFixed,
  Minus,
  Plus,
  Compass,
  Home,
  RotateCcw,
  RotateCw,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  MoveUpRight,
  MoveDownRight,
  Hand,
} from "lucide-react";
import { LoadingOverlay } from "@/components/ui/LoadingOverlay";
import { ErrorState } from "@/components/ui/ErrorState";
import { useCesiumGlobe } from "./useCesiumGlobe";
const controls = [
  ["zoom-in", "Zoom in", Plus],
  ["zoom-out", "Zoom out", Minus],
  ["north", "Reset north", Compass],
  ["project", "Reset to project region", LocateFixed],
  ["home", "Home view", Home],
  ["rotate-left", "Rotate left", RotateCcw],
  ["rotate-right", "Rotate right", RotateCw],
  ["tilt-up", "Tilt up", MoveUpRight],
  ["tilt-down", "Tilt down", MoveDownRight],
  ["pan-left", "Pan left", ArrowLeft],
  ["pan-right", "Pan right", ArrowRight],
  ["pan-up", "Pan up", ArrowUp],
  ["pan-down", "Pan down", ArrowDown],
] as const;
export default function CesiumScene() {
  const globe = useCesiumGlobe();
  const scalar = useScalar();
  const button = ([action, label, Icon]: (typeof controls)[number]) => (
    <button
      key={action}
      disabled={globe.status !== "ready"}
      onClick={() => globe.controller.current?.command(action)}
      aria-label={label}
      title={label}
    >
      <Icon size={17} />
    </button>
  );
  return (
    <section
      ref={globe.surface}
      className="globe-scene"
      aria-label="Ocean geographic workspace"
      data-scene-status={globe.status}
    >
      <div ref={globe.host} className="cesium-host" />
      <ScalarGlobeLayer />
      <ModelPointSelection />
      <ObservationGlobeLayer />
      <ConnectedAdvancedLayer />
      <RenderPerformance />
      {globe.status === "loading" && <LoadingOverlay />}
      {globe.status === "error" && (
        <ErrorState
          message="The globe engine or WebGL could not start, or the graphics context was lost. Check hardware acceleration and retry."
          onRetry={globe.retry}
        />
      )}
      <div className="globe-label">
        <span className="eyebrow">PROJECT WORKING REGION</span>
        <strong>Indian Ocean</strong>
        <span>30°E–120°E · 30°S–30°N</span>
        <small>Selection extent · dataset coverage may differ</small>
      </div>
      <div className="camera-controls" aria-label="Globe camera controls">
        {controls.slice(0, 5).map(button)}
        <details className="camera-more">
          <summary
            aria-label="More camera controls"
            title="Rotate, pan and tilt"
          >
            <Hand size={17} />
          </summary>
          <div className="camera-expanded">{controls.slice(5).map(button)}</div>
        </details>
        <button
          className="stop-flight"
          onClick={() => globe.controller.current?.command("stop")}
        >
          Stop flight
        </button>
      </div>
      {(!scalar.renderInfo || !scalar.settings.visible) && (
        <div className="globe-empty">
          <span className="cyan-dot" />
          <span>
            GEOGRAPHIC EXPLORER{" "}
            <small>
              {scalar.renderInfo
                ? "Scalar layer hidden"
                : "Select a dataset to view a scalar field"}
            </small>
          </span>
        </div>
      )}
      <div className="scene-caption" role="status">
        {globe.imageryState}
      </div>
      <div className="geographic-readout" aria-label="Geographic readout">
        <span ref={globe.coordinates}>Move over Earth for coordinates</span>
        <span ref={globe.altitude}>Altitude —</span>
        <span>WGS 84</span>
      </div>
    </section>
  );
}
