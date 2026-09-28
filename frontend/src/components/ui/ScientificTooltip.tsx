"use client";
import { useId, useState } from "react";
import { Info } from "lucide-react";
export function ScientificTooltip({
  label,
  children,
}: {
  label: string;
  children: string;
}) {
  const id = useId();
  const [dismissed, setDismissed] = useState(false);
  return (
    <span
      className={`tooltip-wrap ${dismissed ? "tooltip-dismissed" : ""}`}
      onMouseEnter={() => setDismissed(false)}
    >
      <button
        className="info-button"
        aria-label={label}
        aria-describedby={id}
        onFocus={() => setDismissed(false)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setDismissed(true);
        }}
      >
        <Info size={14} />
      </button>
      <span id={id} role="tooltip" className="tooltip">
        {children}
      </span>
    </span>
  );
}
