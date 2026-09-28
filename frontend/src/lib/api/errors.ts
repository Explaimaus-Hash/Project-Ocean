export const errorCopy = {
  backend_unavailable: [
    "Backend unavailable",
    "The data service could not be reached. Globe navigation remains available.",
  ],
  not_prepared: [
    "Dataset not prepared",
    "This input has no prepared product. Choose another dataset; preparation is an operator task.",
  ],
  unsupported_selection: [
    "Selection unsupported",
    "Choose a variable, time or region advertised by the selected product.",
  ],
  no_overlap: [
    "No overlap",
    "The requested selection does not overlap this product. Adjust the selection.",
  ],
  request_too_large: [
    "Request too large",
    "Use a smaller region, fewer samples or preview quality before retrying.",
  ],
  busy: [
    "Service busy",
    "The bounded retries are exhausted. Try again when the service has capacity.",
  ],
  provider_unavailable: [
    "Provider unavailable",
    "This source is unavailable. Other sources and the globe remain usable.",
  ],
  empty_selection: [
    "Empty selection",
    "No datasets or collections are available for this selection.",
  ],
  invalid_response: [
    "Response not supported",
    "The response does not match the supported contract. No unvalidated data was applied.",
  ],
  aborted: [
    "Request cancelled",
    "The selection changed or the request was cancelled.",
  ],
  stale_response: ["Selection changed", "An older response was discarded."],
  timeout: [
    "Request timed out",
    "The bounded request deadline was reached. Try again.",
  ],
  not_configured: [
    "Backend not configured",
    "Configure and verify the backend contract before switching to live mode.",
  ],
  http_error: [
    "Data request failed",
    "The requested data could not be loaded. Try another selection.",
  ],
} as const;
export type ApiErrorCode = keyof typeof errorCopy;
export class ApiError extends Error {
  constructor(
    public readonly code: ApiErrorCode,
    public readonly status = 0,
  ) {
    super(errorCopy[code][1]);
    this.name = "ApiError";
  }
}
export function asApiError(error: unknown): ApiError {
  return error instanceof ApiError
    ? error
    : new ApiError("backend_unavailable");
}
export function errorFromResponse(status: number, body: unknown): ApiError {
  const error =
    body && typeof body === "object"
      ? (body as Record<string, unknown>).error
      : undefined;
  const code =
    error && typeof error === "object"
      ? (error as Record<string, unknown>).code
      : undefined;
  if (status === 413) return new ApiError("request_too_large", status);
  if (typeof code === "string" && Object.hasOwn(errorCopy, code))
    return new ApiError(code as ApiErrorCode, status);
  if (status === 422) return new ApiError("unsupported_selection", status);
  if (status === 503) return new ApiError("busy", status);
  return new ApiError("http_error", status);
}
