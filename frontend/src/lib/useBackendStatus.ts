"use client";
import { useEffect, useState } from "react";
export function useBackendStatus() {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL;
  const [status, setStatus] = useState(
    base ? "Checking backend" : "Backend not configured",
  );
  useEffect(() => {
    if (!base) return;
    let disposed = false;
    const abort = new AbortController();
    const timeout = window.setTimeout(() => abort.abort(), 5000);
    void fetch(`${base.replace(/\/$/, "")}/health`, {
      signal: abort.signal,
      cache: "no-store",
    })
      .then(async (response) => {
        const data = await response.json();
        if (!disposed)
          setStatus(
            response.ok &&
              data.status === "ok" &&
              data.service === "Project Ocean Backend"
              ? "Backend online"
              : "Backend response invalid",
          );
      })
      .catch(() => {
        if (!disposed) setStatus("Backend unreachable");
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      disposed = true;
      abort.abort();
      window.clearTimeout(timeout);
    };
  }, [base]);
  return status;
}
