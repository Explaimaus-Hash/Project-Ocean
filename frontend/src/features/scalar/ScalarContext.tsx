"use client";
import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { useGlobe } from "@/features/globe/GlobeContext";
import type { Frame } from "@/lib/api/types";
import { useData } from "@/features/data-sources/DataProvider";
import {
  dataRange,
  defaultPalette,
  logAllowed,
  type Palette,
  type Scale,
} from "./ScientificColorScale";
export interface RenderInfo {
  family: string;
  frame: Frame;
  scale: Scale;
  interpolation: "nearest" | "bilinear";
  milliseconds: number;
  width: number;
  height: number;
}
interface Settings {
  visible: boolean;
  opacity: number;
  palette: Palette;
  manual: boolean;
  min: string;
  max: string;
  log: boolean;
  perFrame: boolean;
  interpolation: "nearest" | "bilinear";
}
function useScalarState() {
  const d = useData();
  const { settings: display } = useGlobe();
  const frame = d.displayedFrame;
  const identity = `${d.dataset?.dataset_id}:${d.dataset?.product_id}:${d.variable}:${display.defaultPalette}`;
  const defaults: Settings = {
    visible: true,
    opacity: 0.78,
    palette:
      display.defaultPalette === "auto"
        ? defaultPalette(d.variable ?? "")
        : display.defaultPalette,
    manual: false,
    min: "",
    max: "",
    log: false,
    perFrame: false,
    interpolation: "bilinear",
  };
  const [saved, setSaved] = useState<{
    identity: string;
    settings: Settings;
  } | null>(null);
  const settings = saved?.identity === identity ? saved.settings : defaults;
  const update = (patch: Partial<Settings>) =>
    setSaved({ identity, settings: { ...settings, ...patch } });
  const range = frame ? dataRange(frame) : null;
  const [base, setBase] = useState<{
    family: string;
    range: [number, number];
  } | null>(null);
  useEffect(() => {
    if (range && base?.family !== d.family)
      setBase({ family: d.family, range });
  }, [d.family, range, base]);
  const stableRange = settings.perFrame
    ? range
    : base?.family === d.family
      ? base.range
      : range;
  const min = settings.manual ? Number(settings.min) : stableRange?.[0];
  const max = settings.manual ? Number(settings.max) : stableRange?.[1];
  const allowed = logAllowed(d.variable ?? "", frame?.units ?? "", range);
  const invalid =
    (settings.manual && (!settings.min.trim() || !settings.max.trim())) ||
    min === undefined ||
    max === undefined ||
    !Number.isFinite(min) ||
    !Number.isFinite(max) ||
    min >= max ||
    (settings.log && (!allowed || min <= 0));
  const scale: Scale | null = invalid
    ? null
    : { min: min!, max: max!, palette: settings.palette, log: settings.log };
  const [renderInfo, setRenderInfo] = useState<RenderInfo | null>(null);
  const [renderError, setRenderError] = useState("");
  return {
    settings,
    update,
    scale,
    allowed,
    range,
    stableRange,
    invalid,
    renderInfo: renderInfo?.family === d.family ? renderInfo : null,
    setRenderInfo,
    renderError,
    setRenderError,
    reset: () => {
      setSaved(null);
      setBase(null);
    },
  };
}
const Context = createContext<ReturnType<typeof useScalarState> | null>(null);
export function ScalarProvider({ children }: { children: ReactNode }) {
  const value = useScalarState();
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useScalar() {
  const value = useContext(Context);
  if (!value) throw new Error("ScalarProvider required");
  return value;
}
