import type { Dataset } from "@/lib/api/types";
import type { ApiErrorCode } from "@/lib/api/errors";
export const inventoryStatuses = {
  available: [
    "Available",
    "A prepared product or observation collection is advertised; selection-specific access can still fail.",
  ],
  cached: [
    "Cached",
    "Only use when persistent cache status is explicitly reported. Browser metadata caching is not product readiness.",
  ],
  acquired_not_prepared: [
    "Acquired but not prepared",
    "Downloaded input does not establish a visualization-ready product.",
  ],
  not_configured: [
    "Not configured",
    "The service explicitly reports missing configuration.",
  ],
  not_prepared: ["Not prepared", "No prepared product is advertised."],
  no_data: [
    "No data in selection",
    "The requested bounds/time have no data or overlap.",
  ],
  timeout: [
    "Timed out",
    "The bounded request deadline elapsed; readiness is unknown.",
  ],
  unsupported: [
    "Unsupported",
    "The advertised contract cannot serve this selection.",
  ],
  blocked: [
    "Scientifically blocked",
    "A required scientific service or matching policy is not verified.",
  ],
  backend_unavailable: [
    "Backend unavailable",
    "Connectivity failed; source readiness is unknown.",
  ],
  provider_unavailable: [
    "Provider unavailable",
    "This provider failed independently of other sources.",
  ],
  busy: ["Busy", "Bounded retries were exhausted."],
  unknown: [
    "Not reported",
    "No authoritative metadata was returned for this field.",
  ],
} as const;
export type InventoryStatus = keyof typeof inventoryStatuses;
export function datasetStatus(d: Dataset): InventoryStatus {
  return d.status === "prepared" ? "available" : d.status;
}
export function requestStatus(code?: ApiErrorCode): InventoryStatus {
  if (code === "no_overlap" || code === "empty_selection") return "no_data";
  if (code === "unsupported_selection" || code === "invalid_response")
    return "unsupported";
  if (
    code === "backend_unavailable" ||
    code === "timeout" ||
    code === "not_configured" ||
    code === "not_prepared" ||
    code === "provider_unavailable" ||
    code === "busy"
  )
    return code;
  return "unknown";
}
/** Public inventory never renders arbitrary paths, credential strings or signed URLs. */
export function publicText(text?: string | null): string {
  if (!text) return "Not reported";
  if (
    /(?:[a-z]:[\\/]|\\\\|(?:^|\s)\/\S+|password|username|secret|token|credential|api[_-]?key|https?:\/\/\S*[?@])/i.test(
      text,
    )
  )
    return "Withheld: metadata requires public-safe review";
  return text.length > 1200 ? text.slice(0, 1200) + "…" : text;
}
export const sourceFamilies = [
  {
    id: "bioroms",
    name: "INCOIS BIO-ROMS",
    role: "Model",
    note: "BIO-ROMS V2 is surface-only. No water-column volume or vertical current capability is implied.",
  },
  {
    id: "godas",
    name: "INCOIS GODAS",
    role: "Model",
    note: "Depth and variable support must be established by the configured product metadata.",
  },
  {
    id: "copernicus",
    name: "Copernicus Marine",
    role: "Model",
    note: "Product identity and model variables appear only when reported. No configured identity is inferred from this family name.",
  },
  {
    id: "argo",
    name: "Argo GDAC",
    role: "Observation",
    note: "GDAC/service is the data source. Argopy is a client, not the data owner. Profiles are discrete observations, not continuous coverage.",
  },
  {
    id: "glider",
    name: "IFREMER Gliders",
    role: "Observation",
    note: "Repository and deployment must be reported by the source. An Antarctic Bella sample is not Indian Ocean operational comparison data.",
  },
  {
    id: "local",
    name: "Local / registered products",
    role: "Model",
    note: "Other catalogue records are retained here without assigning an unreported provider or claiming a local filesystem location.",
  },
] as const;
export function familyFor(source: string) {
  return /bio.?roms/i.test(source)
    ? "bioroms"
    : /godas/i.test(source)
      ? "godas"
      : /copernicus/i.test(source)
        ? "copernicus"
        : "local";
}
