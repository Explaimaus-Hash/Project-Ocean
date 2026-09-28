"use client";
import { ScalarProvider } from "@/features/scalar/ScalarContext";
import dynamic from "next/dynamic";
import { useState, useRef, type ReactNode, type CSSProperties } from "react";
import { usePathname } from "next/navigation";
import { WorkspacePanel } from "@/features/WorkspacePanel";
import { routes } from "@/lib/routes";
import { SelectionProvider } from "@/lib/selection";
import { ConnectedTimeline } from "./ConnectedTimeline";
import { TopBar } from "./TopBar";
import { NavigationRail } from "./NavigationRail";
import { ContextPanel } from "./ContextPanel";
import { RightInspector } from "./RightInspector";
import { DataProvider } from "@/features/data-sources/DataProvider";
import { LoadingOverlay } from "@/components/ui/LoadingOverlay";
import { GlobeProvider, useGlobe } from "@/features/globe/GlobeContext";
const CesiumScene = dynamic(() => import("@/features/globe/CesiumScene"), {
  ssr: false,
  loading: () => <LoadingOverlay />,
});
export function WorkspaceShell({ children }: { children: ReactNode }) {
  return (
    <SelectionProvider>
      <DataProvider>
        <GlobeProvider>
          <ScalarProvider>
            <Shell>{children}</Shell>
          </ScalarProvider>
        </GlobeProvider>
      </DataProvider>
    </SelectionProvider>
  );
}
function Shell({ children }: { children: ReactNode }) {
  const { status } = useGlobe();
  const pathname = usePathname();
  const analysis = pathname === "/analysis";
  const comparison = pathname === "/comparison";
  const sources = pathname === "/data-sources";
  const [split, setSplit] = useState(45);
  const container = useRef<HTMLElement>(null);
  const dragging = useRef(false);
  const changeSplit = (value: number) =>
    setSplit(Math.max(25, Math.min(65, value)));
  return (
    <>
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <div
        className={`workspace-shell ${analysis ? "analysis-mode" : ""} ${comparison || sources ? "comparison-mode-layout" : ""}`}
        data-launch={status}
        style={{ "--analysis-globe": `${split}%` } as CSSProperties}
      >
        <TopBar />
        <NavigationRail />
        <main id="workspace" tabIndex={-1} ref={container}>
          <ContextPanel>
            {analysis || comparison || sources ? (
              <WorkspacePanel route={routes[comparison ? 3 : 1]} />
            ) : (
              children
            )}
          </ContextPanel>
          <CesiumScene />
          <div
            className="analysis-divider"
            role="separator"
            aria-label="Resize geographic context"
            aria-orientation="vertical"
            aria-valuemin={25}
            aria-valuemax={65}
            aria-valuenow={Math.round(split)}
            tabIndex={analysis ? 0 : -1}
            hidden={!analysis}
            onKeyDown={(event) => {
              if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
                event.preventDefault();
                changeSplit(split + (event.key === "ArrowRight" ? 5 : -5));
              } else if (event.key === "Home") changeSplit(45);
            }}
            onPointerDown={(event) => {
              dragging.current = true;
              event.currentTarget.setPointerCapture(event.pointerId);
            }}
            onPointerMove={(event) => {
              if (!dragging.current || !container.current) return;
              const rect = container.current.getBoundingClientRect();
              changeSplit(((event.clientX - rect.left) / rect.width) * 100);
            }}
            onPointerUp={() => {
              dragging.current = false;
            }}
            onPointerCancel={() => {
              dragging.current = false;
            }}
          />
          <section
            className="analysis-pane"
            hidden={!analysis}
            aria-label="Scientific analysis workspace"
          >
            {analysis && children}
          </section>
          <RightInspector />
          <section
            className="comparison-pane"
            hidden={!comparison && !sources}
            aria-label={
              sources
                ? "Scientific source inventory"
                : "Scientific comparison workspace"
            }
          >
            {(comparison || sources) && children}
          </section>
        </main>
        <ConnectedTimeline />
      </div>
    </>
  );
}
