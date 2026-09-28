"use client";
import { useData } from "@/features/data-sources/DataProvider";
import { useScalar } from "@/features/scalar/ScalarContext";
import { BottomTimeline } from "./BottomTimeline";
export function ConnectedTimeline() {
  const d = useData();
  const s = useScalar();
  return (
    <BottomTimeline
      key={d.dataset?.dataset_id ?? "unavailable"}
      frames={d.times}
      currentIndex={d.timelineIndex}
      displayedTimestamp={
        s.renderInfo?.frame.timestamp ?? d.displayedFrame?.timestamp
      }
      mode={d.product.value?.mode}
      onRetry={d.retry}
      status={
        d.frame.error || d.product.error
          ? "error"
          : d.frame.value &&
              (s.renderInfo?.frame === d.frame.value || !s.settings.visible)
            ? "ready"
            : d.product.value
              ? "buffering"
              : "unavailable"
      }
      onFrameSelect={(i) => {
        const time = d.times[i];
        if (time) d.selectTime(time);
      }}
    />
  );
}
