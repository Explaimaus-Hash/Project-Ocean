import type { Quality } from "./GlobeContext";
export const PROJECT_REGION = {
  west: 30,
  south: -30,
  east: 120,
  north: 30,
} as const;
export const QUALITY: Record<
  Quality,
  { resolutionScale: number; maximumScreenSpaceError: number }
> = {
  preview: { resolutionScale: 0.75, maximumScreenSpaceError: 4 },
  balanced: { resolutionScale: 1, maximumScreenSpaceError: 2 },
  high: { resolutionScale: 1.5, maximumScreenSpaceError: 1 },
};
export const imageryConfiguration = {
  url: process.env.NEXT_PUBLIC_IMAGERY_URL,
  attribution: process.env.NEXT_PUBLIC_IMAGERY_ATTRIBUTION,
};
