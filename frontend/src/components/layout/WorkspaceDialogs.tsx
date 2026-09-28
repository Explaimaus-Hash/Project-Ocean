"use client";
import { DemoSettings } from "@/features/data-sources/DataProvider";
import { useRef } from "react";
import { CircleHelp, Settings2, X } from "lucide-react";
import { DisplayPreferences } from "./DisplayPreferences";
export function WorkspaceDialogs() {
  const help = useRef<HTMLDialogElement>(null);
  const settingsDialog = useRef<HTMLDialogElement>(null);
  return (
    <>
      <button
        className="top-icon"
        onClick={() => help.current?.showModal()}
        aria-label="Help"
        title="Help"
      >
        <CircleHelp size={18} />
      </button>
      <button
        className="top-icon"
        onClick={() => settingsDialog.current?.showModal()}
        aria-label="Settings"
        title="Settings"
      >
        <Settings2 size={18} />
      </button>
      <dialog
        ref={help}
        className="workspace-dialog"
        aria-label="Explorer help"
      >
        <button
          className="drawer-close"
          aria-label="Close help"
          onClick={() => help.current?.close()}
        >
          <X size={18} />
        </button>
        <span className="eyebrow">EXPLORER GUIDE</span>
        <h2>Navigate the Earth</h2>
        <dl>
          <dt>Rotate / pan</dt>
          <dd>
            Drag the globe. Use More camera controls for explicit pan and rotate
            buttons.
          </dd>
          <dt>Zoom / tilt</dt>
          <dd>Scroll to zoom. Middle-drag or Ctrl + drag to tilt.</dd>
          <dt>Keyboard</dt>
          <dd>
            Focus the globe. Arrows rotate and tilt; Shift + arrows pan; + / −
            zoom. Home resets the project region.
          </dd>
          <dt>Interrupt a flight</dt>
          <dd>
            Click or scroll on the globe, press Escape while focused on it, or
            use Stop flight.
          </dd>
        </dl>
        <p>
          Coordinates use WGS 84. The ellipsoid is geographic context, not ocean
          bathymetry. Project bounds do not establish dataset coverage.
        </p>
      </dialog>
      <dialog
        ref={settingsDialog}
        className="workspace-dialog settings-drawer"
        aria-label="Display settings"
      >
        <button
          className="drawer-close"
          aria-label="Close settings"
          onClick={() => settingsDialog.current?.close()}
        >
          <X size={18} />
        </button>
        <span className="eyebrow">DISPLAY PREFERENCES</span>
        <h2>Globe settings</h2>
        <DemoSettings />
        <DisplayPreferences />
      </dialog>
    </>
  );
}
