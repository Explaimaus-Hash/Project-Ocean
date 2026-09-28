import type { ReactNode } from "react";
export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  return (
    <span className={`badge badge-${tone}`}>
      <span aria-hidden="true">●</span>
      {children}
    </span>
  );
}
