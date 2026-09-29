"use client";
import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Play, Pause, Clock3 } from "lucide-react";
export interface TimelineProps {
  frames?: readonly string[];
  currentIndex?: number;
  status?: "unavailable" | "ready" | "loading" | "buffering" | "error";
  displayedTimestamp?: string;
  onRetry?: () => void;
  mode?: "real" | "synthetic";
  onFrameSelect?: (index: number) => void;
  hidden?: boolean;
}
const EMPTY_FRAMES: readonly string[] = [];
export function BottomTimeline({
  frames = EMPTY_FRAMES,
  currentIndex = 0,
  status = "unavailable",
  onFrameSelect,
  displayedTimestamp,
  onRetry,
  mode = "real",
  hidden = false,
}: TimelineProps) {
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [failed, setFailed] = useState<number[]>([]);
  useEffect(() => {
    if (hidden && playing) {
      setPlaying(false);
    }
  }, [hidden, playing]);
  useEffect(() => {
    if (status === "error") {
      setPlaying(false);
      setFailed((old) =>
        old.includes(currentIndex) ? old : [...old, currentIndex],
      );
    } else if (status === "ready")
      setFailed((old) =>
        old.includes(currentIndex)
          ? old.filter((i) => i !== currentIndex)
          : old,
      );
  }, [status, currentIndex]);
  const available = frames.length > 0 && !!onFrameSelect;
  const ready = available && status === "ready";
  useEffect(() => {
    if (!playing || !ready || !onFrameSelect || frames.length < 2) return;
    const timer = window.setTimeout(
      () => onFrameSelect((currentIndex + 1) % frames.length),
      1000 / speed,
    );
    return () => window.clearTimeout(timer);
  }, [playing, ready, onFrameSelect, frames.length, currentIndex, speed]);
  const timestamp = frames[currentIndex];
  const shown = displayedTimestamp ?? timestamp;
  const markerStride = Math.max(1, Math.ceil(frames.length / 80));
  const message =
    status === "error"
      ? "No frame available at selected timestamp · retry or choose another frame"
      : available
        ? `${frames.length} available frames`
        : status === "loading"
          ? "Loading frame metadata"
          : "Connect a prepared dataset to enable time controls.";
  return (
    <footer
      className={`bottom-timeline ${hidden ? "timeline-collapsed" : ""}`}
      aria-label="Time controls"
      data-status={status}
      data-hidden={hidden ? "true" : "false"}
      aria-hidden={hidden}
    >
      <div className="timeline-caption" aria-busy={status === "loading" || status === "buffering"}>
        <Clock3 size={16} />
        <div>
          <strong>
            {shown ? (
              <time dateTime={shown}>{shown}</time>
            ) : (
              "No timestamp selected"
            )}
          </strong>
          <small id="timeline-reason" role="status">
            {message}
          </small>
        </div>
      </div>
      <div className="playback" aria-describedby="timeline-reason">
        <button
          disabled={!available || currentIndex <= 0}
          onClick={() => onFrameSelect?.(currentIndex - 1)}
          aria-label="Previous frame"
        >
          <ChevronLeft size={16} />
        </button>
        <button
          disabled={!available || frames.length < 2 || status === "error"}
          onClick={() => setPlaying((value) => !value)}
          aria-label={playing ? "Pause timeline" : "Play timeline"}
        >
          {playing ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <button
          disabled={!available || currentIndex >= frames.length - 1}
          onClick={() => onFrameSelect?.(currentIndex + 1)}
          aria-label="Next frame"
        >
          <ChevronRight size={16} />
        </button>
      </div>
      <label className="speed-control">
        SPEED
        <select
          aria-label="Playback speed"
          value={speed}
          onChange={(event) => setSpeed(Number(event.target.value))}
        >
          {[0.25, 0.5, 1, 2, 4].map((value) => (
            <option key={value} value={value}>
              {value}×
            </option>
          ))}
        </select>
      </label>
      <div className="timeline-track">
        <label htmlFor="timeline-time">
          {timestamp ? "Available frames" : "Awaiting dataset metadata"}
        </label>
        <input
          id="timeline-time"
          aria-label="Time frame"
          aria-valuetext={timestamp ?? "No frame available"}
          type="range"
          min="0"
          max={Math.max(0, frames.length - 1)}
          value={timestamp ? currentIndex : 0}
          disabled={!available}
          onChange={(event) => onFrameSelect?.(Number(event.target.value))}
          aria-describedby="timeline-reason"
        />
        {available && (
          <small className="timeline-range" aria-label="Available data range">
            {frames[0]} → {frames.at(-1)}
            {markerStride > 1 ? " · marker subset" : ""}
          </small>
        )}
        {status === "error" && onRetry && (
          <button className="text-button" onClick={onRetry}>
            Retry frame
          </button>
        )}
        <div className="frame-markers" aria-label="Available frame markers">
          {frames.map(
            (frame, index) =>
              (index % markerStride === 0 ||
                index === frames.length - 1 ||
                index === currentIndex) && (
                <button
                  key={`${frame}-${index}`}
                  style={{
                    left: `${frames.length > 1 ? (index * 100) / (frames.length - 1) : 0}%`,
                  }}
                  disabled={!available}
                  onClick={() => onFrameSelect?.(index)}
                  aria-label={`Select frame ${frame}`}
                  title={`${frame}${failed.includes(index) ? " · unavailable" : ""}`}
                  data-missing={failed.includes(index)}
                  aria-current={index === currentIndex ? "true" : undefined}
                />
              ),
          )}
        </div>
      </div>
      <span className="timeline-utc">
        {mode === "synthetic" ? "DEMO UTC" : "UTC"}{" "}
        <span>{timestamp ? "" : "—"}</span>
      </span>
    </footer>
  );
}
