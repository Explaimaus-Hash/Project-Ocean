import { DataClient, ApiError } from "@/lib/dataClient";
import type { FrameQuery } from "@/lib/api/types";
/** Remember rejected scientific extents so animation never repeats a known oversized request. */
export class BoundedFrameLoader {
  private previewOnly = new Set<string>();
  constructor(private client: DataClient) {}
  async load(id: string, query: FrameQuery, signal: AbortSignal) {
    const key = JSON.stringify([id, query.variable, query.bounds]);
    const preview = () =>
      this.client.getFrame(id, { ...query, quality: "preview" }, signal);
    if (query.quality === "scientific" && this.previewOnly.has(key))
      return preview();
    try {
      return await this.client.getFrame(id, query, signal);
    } catch (error) {
      if (
        query.quality !== "scientific" ||
        !(error instanceof ApiError) ||
        error.code !== "request_too_large"
      )
        throw error;
      this.previewOnly.add(key);
      if (this.previewOnly.size > 32)
        this.previewOnly.delete(this.previewOnly.values().next().value!);
      return preview();
    }
  }
}
