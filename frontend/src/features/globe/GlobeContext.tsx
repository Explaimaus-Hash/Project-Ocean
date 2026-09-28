"use client";
import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import type { Viewer } from "cesium";
export type GlobeStatus = "loading" | "ready" | "error";
export type Quality = "preview" | "balanced" | "high";
export interface GlobeSettings {
  animationSpeed: number;
  atmosphere: boolean;
  earthRotation: boolean;
  keepCentered: boolean;
  reducedAnimation: boolean;
  defaultPalette:
    "auto" | "temperature" | "salinity" | "chlorophyll" | "speed" | "anomaly";
  exaggeration: number;
  vectorDensity: number;
  vectorScale: number;
  speedColor: boolean;
  quality: Quality;
  lighting: boolean;
  basemapVisible: boolean;
  basemapOpacity: number;
}
const defaults: GlobeSettings = {
  animationSpeed: 1,
  atmosphere: true,
  earthRotation: false,
  keepCentered: false,
  reducedAnimation: false,
  defaultPalette: "auto",
  exaggeration: 1,
  vectorDensity: 0.5,
  vectorScale: 5000,
  speedColor: false,
  quality: "balanced",
  lighting: false,
  basemapVisible: true,
  basemapOpacity: 1,
};
const GlobeContext = createContext<{
  viewer: Viewer | null;
  setViewer: (viewer: Viewer | null) => void;
  status: GlobeStatus;
  setStatus: (status: GlobeStatus) => void;
  settings: GlobeSettings;
  updateSettings: (patch: Partial<GlobeSettings>) => void;
} | null>(null);
export const SETTINGS_KEY = "project-ocean-display-v1";
export function validateSettings(raw: unknown): GlobeSettings {
  const result = { ...defaults };
  if (!raw || typeof raw !== "object") return result;
  const v = raw as Record<string, unknown>;
  for (const key of [
    "lighting",
    "basemapVisible",
    "speedColor",
    "atmosphere",
    "earthRotation",
    "keepCentered",
    "reducedAnimation",
  ] as const)
    if (typeof v[key] === "boolean") result[key] = v[key];
  for (const [key, min, max] of [
    ["exaggeration", 1, 10],
    ["vectorDensity", 0.1, 1],
    ["vectorScale", 100, 20000],
    ["basemapOpacity", 0, 1],
    ["animationSpeed", 0.25, 4],
  ] as const)
    if (
      typeof v[key] === "number" &&
      Number.isFinite(v[key]) &&
      v[key] >= min &&
      v[key] <= max
    )
      result[key] = v[key];
  if (["preview", "balanced", "high"].includes(String(v.quality)))
    result.quality = v.quality as Quality;
  if (
    [
      "auto",
      "temperature",
      "salinity",
      "chlorophyll",
      "speed",
      "anomaly",
    ].includes(String(v.defaultPalette))
  )
    result.defaultPalette = v.defaultPalette as GlobeSettings["defaultPalette"];
  return result;
}
export function GlobeProvider({ children }: { children: ReactNode }) {
  const [viewer, setViewer] = useState<Viewer | null>(null);
  const [status, setStatus] = useState<GlobeStatus>("loading");
  const [settings, setSettings] = useState(defaults);
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    try {
      setSettings(
        validateSettings(
          JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? "null"),
        ),
      );
    } catch {
      /* Storage unavailable or corrupt: safe defaults. */
    }
    setHydrated(true);
  }, []);
  useEffect(() => {
    if (hydrated) {
      try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
      } catch {
        /* Display settings still work in memory. */
      }
    }
  }, [settings, hydrated]);
  return (
    <GlobeContext.Provider
      value={{
        viewer,
        setViewer,
        status,
        setStatus,
        settings,
        updateSettings: (patch) => setSettings((old) => ({ ...old, ...patch })),
      }}
    >
      {children}
    </GlobeContext.Provider>
  );
}
export function useGlobe() {
  const value = useContext(GlobeContext);
  if (!value) throw new Error("GlobeProvider is required");
  return value;
}
