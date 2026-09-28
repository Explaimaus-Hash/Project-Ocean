import type * as T from "./api/types";
import { validators, validBounds, type Guard } from "./api/validation";
import { ApiError, errorFromResponse } from "./api/errors";
import {isComparisonCatalogue,isComparisonMetadata,isComparisonPage,type ComparisonMetadata,type ComparisonPage} from "./api/comparisons";
export { ApiError } from "./api/errors";
export type Transport = (url: string, init: RequestInit) => Promise<Response>;
interface Entry {
  value: unknown;
  expires: number;
  bytes: number;
}
class BoundedCache {
  private entries = new Map<string, Entry>();
  constructor(
    private count: number,
    private byteLimit: number,
  ) {}
  get(key: string) {
    const item = this.entries.get(key);
    if (!item) return;
    this.entries.delete(key);
    if (item.expires < Date.now()) return;
    this.entries.set(key, item);
    return structuredClone(item.value);
  }
  set(key: string, value: unknown, bytes: number) {
    if (bytes > this.byteLimit) return;
    this.entries.delete(key);
    this.entries.set(key, {
      value: structuredClone(value),
      bytes,
      expires: Date.now() + 60000,
    });
    while (
      this.entries.size > this.count ||
      [...this.entries.values()].reduce((sum, item) => sum + item.bytes, 0) >
        this.byteLimit
    )
      this.entries.delete(this.entries.keys().next().value!);
  }
  clear() {
    this.entries.clear();
  }
  get size() {
    return this.entries.size;
  }
}
interface Flight {
  promise: Promise<unknown>;
  controller: AbortController;
  consumers: number;
}
export interface ClientOptions {
  baseUrl?: string;
  transport?: Transport;
  deadlineMs?: number;
  retryDelayMs?: number;
  adapt?: (path: string, value: unknown) => unknown;
}
export function abortableDelay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new ApiError("aborted"));
      return;
    }
    const abort = () => {
      clearTimeout(timer);
      reject(new ApiError("aborted"));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, ms);
    signal.addEventListener("abort", abort, { once: true });
  });
}
/** An independent gate for effects/searches: only the latest selection may commit. */
export class LatestRequest {
  private revision = 0;
  private active?: AbortController;
  async run<T>(task: (signal: AbortSignal) => Promise<T>): Promise<T> {
    this.active?.abort();
    const revision = ++this.revision;
    const controller = new AbortController();
    this.active = controller;
    try {
      const result = await task(controller.signal);
      if (revision !== this.revision) throw new ApiError("stale_response");
      return result;
    } catch (error) {
      if (revision !== this.revision) throw new ApiError("stale_response");
      throw error;
    }
  }
  cancel() {
    this.revision++;
    this.active?.abort();
  }
}
/** Bounded GET client. Live responses use the explicit FastAPI presentation adapter. */
export class DataClient {
  private metadata = new BoundedCache(32, 2 * 1024 * 1024);
  private frames = new BoundedCache(3, 6 * 1024 * 1024);
  private flights = new Map<string, Flight>();
  private transport: Transport;
  private generation = 0;
  constructor(private options: ClientOptions = {}) {
    this.transport = options.transport ?? ((url, init) => fetch(url, init));
  }
  clear() {
    this.generation++;
    this.metadata.clear();
    this.frames.clear();
    for (const flight of this.flights.values()) flight.controller.abort();
    this.flights.clear();
  }
  diagnostics() {
    return {
      metadataEntries: this.metadata.size,
      frameEntries: this.frames.size,
      pending: this.flights.size,
    };
  }
  private async body(
    response: Response,
  ): Promise<{ value: unknown; bytes: number }> {
    const max = 2 * 1024 * 1024;
    if (Number(response.headers.get("content-length")) > max)
      throw new ApiError("request_too_large", 413);
    if (!response.body) throw new ApiError("invalid_response");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let bytes = 0;
    let text = "";
    try {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        bytes += chunk.value.byteLength;
        if (bytes > max) {
          await reader.cancel();
          throw new ApiError("request_too_large", 413);
        }
        text += decoder.decode(chunk.value, { stream: true });
      }
      text += decoder.decode();
      try {
        return { value: JSON.parse(text) as unknown, bytes };
      } catch {
        throw new ApiError("invalid_response", response.status);
      }
    } finally {
      reader.releaseLock();
    }
  }
  private request<T>(
    path: string,
    guard: Guard<T>,
    signal?: AbortSignal,
    cacheKind: "metadata" | "frame" | "none" = "metadata",
    acceptReadiness = false,
  ): Promise<T> {
    if (signal?.aborted) return Promise.reject(new ApiError("aborted"));
    if (!this.options.baseUrl)
      return Promise.reject(new ApiError("not_configured"));
    const cache = cacheKind === "frame" ? this.frames : this.metadata;
    const cached = cacheKind !== "none" ? cache.get(path) : undefined;
    if (cached !== undefined && guard(cached)) return Promise.resolve(cached);
    let flight = this.flights.get(path);
    if (!flight) {
      if (this.flights.size >= 8)
        return Promise.reject(new ApiError("busy", 503));
      const controller = new AbortController();
      const generation = this.generation;
      const task = {
        controller,
        consumers: 0,
        promise: Promise.resolve(undefined) as Promise<unknown>,
      };
      task.promise = (async () => {
        let timedOut = false;
        const timer = setTimeout(() => {
          timedOut = true;
          controller.abort();
        }, this.options.deadlineMs ?? 8000);
        try {
          for (let attempt = 0; attempt < 3; attempt++) {
            const response = await this.transport(
              `${this.options.baseUrl!.replace(/\/$/, "")}${path}`,
              {
                method: "GET",
                signal: controller.signal,
                cache: "no-store",
                headers: { Accept: "application/json" },
              },
            );
            let parsed: { value: unknown; bytes: number };
            try {
              parsed = await this.body(response);
            } catch (error) {
              if (
                error instanceof ApiError &&
                error.code === "request_too_large"
              )
                throw error;
              if (response.ok || (acceptReadiness && response.status === 503))
                throw error;
              parsed = { value: null, bytes: 0 };
            }
            if (this.options.adapt && (response.ok || (acceptReadiness && response.status === 503)))
              parsed.value = this.options.adapt(path, parsed.value);
            if (
              !response.ok &&
              !(
                acceptReadiness &&
                response.status === 503 &&
                guard(parsed.value)
              )
            ) {
              const error = errorFromResponse(response.status, parsed.value);
              if (
                response.status === 503 &&
                error.code === "busy" &&
                attempt < 2
              ) {
                await abortableDelay(
                  (this.options.retryDelayMs ?? 200) * 2 ** attempt,
                  controller.signal,
                );
                continue;
              }
              throw error;
            }
            if (!guard(parsed.value))
              throw new ApiError("invalid_response", response.status);
            if (
              acceptReadiness &&
              (parsed.value as T.Readiness).ready !== response.ok
            )
              throw new ApiError("invalid_response", response.status);
            if (controller.signal.aborted)
              throw new ApiError(timedOut ? "timeout" : "aborted");
            if (generation !== this.generation)
              throw new ApiError("stale_response");
            if (cacheKind !== "none")
              cache.set(path, parsed.value, parsed.bytes);
            return parsed.value;
          }
          throw new ApiError("busy", 503);
        } catch (error) {
          if (controller.signal.aborted)
            throw new ApiError(timedOut ? "timeout" : "aborted");
          if (error instanceof ApiError) throw error;
          throw new ApiError("backend_unavailable");
        } finally {
          clearTimeout(timer);
          if (this.flights.get(path) === task) this.flights.delete(path);
        }
      })();
      flight = task;
      this.flights.set(path, task);
    }
    const shared = flight;
    shared.consumers++;
    return new Promise<T>((resolve, reject) => {
      let settled = false;
      const release = () => {
        if (settled) return false;
        settled = true;
        signal?.removeEventListener("abort", abort);
        shared.consumers--;
        if (!shared.consumers && this.flights.get(path) === shared) {
          this.flights.delete(path);
          shared.controller.abort();
        }
        return true;
      };
      const abort = () => {
        if (release()) reject(new ApiError("aborted"));
      };
      signal?.addEventListener("abort", abort, { once: true });
      shared.promise.then(
        (value) => {
          if (release()) resolve(structuredClone(value) as T);
        },
        (error) => {
          if (release()) reject(error);
        },
      );
      if (signal?.aborted) abort();
    });
  }
  getHealth(signal?: AbortSignal) {
    return this.request("/health", validators.health, signal, "none");
  }
  getComparisons(signal?: AbortSignal) { return this.request("/api/v1/comparisons",isComparisonCatalogue,signal,"none"); }
  getComparison(id:string, signal?:AbortSignal) { return this.request(`/api/v1/comparisons/${encodeURIComponent(id)}`,(v):v is ComparisonMetadata=>isComparisonMetadata(v)&&v.comparison_id===id,signal,"none"); }
  getComparisonSamples(id:string,offset:number,matched:boolean|null,signal?:AbortSignal) {
    const params=new URLSearchParams({offset:String(offset),limit:"100"});if(matched!==null)params.set("matched",String(matched));
    return this.request(`/api/v1/comparisons/${encodeURIComponent(id)}/samples?${params}`,(v):v is ComparisonPage=>isComparisonPage(v)&&v.metadata.comparison_id===id&&v.offset===offset&&v.limit===100&&v.matched===matched,signal,"none");
  }
  getReadiness(signal?: AbortSignal) {
    return this.request("/ready", validators.readiness, signal, "none", true);
  }
  getDatasets(signal?: AbortSignal) {
    return this.request("/api/v1/datasets", validators.datasets, signal);
  }
  getProduct(id: string, signal?: AbortSignal) {
    return this.request(
      `/api/v1/products/${encodeURIComponent(id)}`,
      (v): v is T.Product => validators.product(v) && v.product_id === id,
      signal,
    );
  }
  getFrame(id: string, query: T.FrameQuery, signal?: AbortSignal) {
    if (
      !Number.isInteger(query.time_index) ||
      query.time_index < 0 ||
      !query.variable ||
      (query.bounds && !validBounds(query.bounds))
    )
      return Promise.reject(new ApiError("unsupported_selection", 422));
    const params = new URLSearchParams({
      variable: query.variable,
      time_index: String(query.time_index),
      quality: query.quality ?? "preview",
    });
    if (query.bounds)
      for (const [key, value] of Object.entries(query.bounds))
        params.set(key, String(value));
    params.sort();
    return this.request(
      `/api/v1/products/${encodeURIComponent(id)}/frame?${params}`,
      (v): v is T.Frame =>
        validators.frame(v) &&
        v.product_id === id &&
        v.variable === query.variable &&
        v.time_index === query.time_index &&
        v.display_only === (query.quality !== "scientific"),
      signal,
      "frame",
    );
  }
  getTimeseries(id: string, query: T.TimeseriesQuery, signal?: AbortSignal) {
    if (
      !Number.isFinite(query.longitude) ||
      !Number.isFinite(query.latitude) ||
      Math.abs(query.longitude) > 180 ||
      Math.abs(query.latitude) > 90
    )
      return Promise.reject(new ApiError("unsupported_selection", 422));
    const params = new URLSearchParams({
      variable: query.variable,
      longitude: String(query.longitude),
      latitude: String(query.latitude),
    });
    params.sort();
    return this.request(
      `/api/v1/products/${encodeURIComponent(id)}/timeseries?${params}`,
      (v): v is T.Timeseries =>
        validators.timeseries(v) &&
        v.product_id === id &&
        v.variable === query.variable,
      signal,
      "none",
    );
  }
  getAcquisitions(signal?: AbortSignal) {
    return this.request(
      "/api/v1/acquisitions",
      validators.acquisitions,
      signal,
    );
  }
  getObservationCollections(signal?: AbortSignal) {
    return this.request("/api/v1/observations", validators.collections, signal);
  }
  getObservationCollection(id: string, signal?: AbortSignal) {
    return this.request(
      `/api/v1/observations/${encodeURIComponent(id)}`,
      (v): v is T.ObservationCollection =>
        validators.collection(v) && v.collection_id === id,
      signal,
    );
  }
  getObservationSamples(
    id: string,
    query: T.SampleQuery = {},
    signal?: AbortSignal,
  ) {
    const { offset = 0, limit = 50, profile_id } = query;
    if (!Number.isInteger(limit) || limit > 500)
      return Promise.reject(new ApiError("request_too_large", 413));
    if (limit < 1 || !Number.isInteger(offset) || offset < 0)
      return Promise.reject(new ApiError("unsupported_selection", 422));
    const params = new URLSearchParams({
      offset: String(offset),
      limit: String(limit),
    });
    if (profile_id) params.set("profile_id", profile_id);
    params.sort();
    return this.request(
      `/api/v1/observations/${encodeURIComponent(id)}/samples?${params}`,
      (v): v is T.ObservationSamples =>
        validators.samples(v) &&
        v.collection_id === id &&
        v.offset === offset &&
        v.limit === limit &&
        (!profile_id ||
          v.samples.every((sample) => sample.profile_id === profile_id)),
      signal,
      "none",
    );
  }
  prefetchNearbyFrames(
    product: T.Product,
    variable: string,
    index: number,
    signal?: AbortSignal,
  ) {
    return Promise.allSettled(
      [index - 1, index + 1]
        .filter((i) => i >= 0 && i < product.times.length)
        .map((time_index) =>
          this.getFrame(product.product_id, { variable, time_index }, signal),
        ),
    );
  }
}
