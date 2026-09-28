"use client";
import { useEffect, useRef } from "react";
import { useGlobe } from "@/features/globe/GlobeContext";
export function RenderPerformance() {
  const { viewer } = useGlobe();
  const output = useRef<HTMLOutputElement>(null);
  useEffect(() => {
    if (!viewer || viewer.isDestroyed()) return;
    let start = 0,
      total = 0,
      count = 0,
      last = 0;
    const pre = viewer.scene.preRender.addEventListener(() => {
      start = performance.now();
    });
    const post = viewer.scene.postRender.addEventListener(() => {
      last = performance.now();
      total += last - start;
      count++;
    });
    const timer = setInterval(() => {
      if (output.current)
        output.current.textContent = count
          ? `${count} rendered frames / last 1 s · ${(total / count).toFixed(2)} ms mean CPU render submission`
          : last
            ? "Idle · request rendering (no forced frames)"
            : "Awaiting render timing";
      total = 0;
      count = 0;
    }, 1000);
    return () => {
      pre();
      post();
      clearInterval(timer);
    };
  }, [viewer]);
  return (
    <output
      ref={output}
      className="render-performance"
      aria-label="Render performance"
      title="CPU preRender-to-postRender timing, not GPU latency; frames per one-second window, not continuous idle FPS"
    >
      Awaiting render timing
    </output>
  );
}
