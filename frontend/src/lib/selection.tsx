"use client";
import {
  createContext,
  useContext,
  useReducer,
  type ReactNode,
  type Dispatch,
} from "react";

export type RegionId = "indian-ocean" | "global";
export interface SelectedObservation {
  collectionId: string;
  sampleId: string;
  profileId: string | null;
  source: "argo" | "glider";
}
export interface Selection {
  analysisPoint: { longitude: number; latitude: number } | null;
  selectedObservation: SelectedObservation | null;
  region: RegionId;
  modelSource: string | null;
  observationSource: string | null;
  variable: string | null;
  timeRange: { start: string; end: string } | null;
  currentTime: string | null;
  depth: { value: number; unit: "m" | "dbar" } | null;
  renderMode: "surface" | "depth-slice" | "volume" | "vectors";
  selectedProfile: string | null;
}
export const initialSelection: Selection = {
  analysisPoint: null,
  selectedObservation: null,
  region: "indian-ocean",
  modelSource: null,
  observationSource: null,
  variable: null,
  timeRange: null,
  currentTime: null,
  depth: null,
  renderMode: "surface",
  selectedProfile: null,
};
export type SelectionAction =
  | { type: "select-region"; region: RegionId }
  | { type: "reset" }
  | { type: "select-render-mode"; value: Selection["renderMode"] }
  | { type: "select-depth"; value: Selection["depth"] }
  | {
      type: "select-analysis-point";
      point: { longitude: number; latitude: number } | null;
    }
  | { type: "select-observation-sample"; value: SelectedObservation | null }
  | { type: "select-dataset"; id: string }
  | { type: "select-variable"; value: string }
  | { type: "select-time"; value: string }
  | { type: "select-observation"; id: string };
export function selectionReducer(
  state: Selection,
  action: SelectionAction,
): Selection {
  switch (action.type) {
    case "select-render-mode":
      return { ...state, renderMode: action.value };
    case "select-depth":
      return { ...state, depth: action.value };
    case "select-observation-sample":
      return {
        ...state,
        selectedObservation: action.value,
        selectedProfile: action.value?.profileId ?? null,
      };
    case "select-analysis-point":
      return { ...state, analysisPoint: action.point };
    case "select-region":
      return { ...state, region: action.region };
    case "select-dataset":
      return {
        ...state,
        modelSource: action.id,
        analysisPoint: null,
        variable: null,
        currentTime: null,
        depth: null,
        renderMode: "surface",
      };
    case "select-variable":
      return {
        ...state,
        variable: action.value,
        renderMode: "surface",
        depth: null,
      };
    case "select-time":
      return {
        ...state,
        currentTime: action.value,
        renderMode: "surface",
        depth: null,
      };
    case "select-observation":
      return {
        ...state,
        observationSource: action.id,
        selectedProfile: null,
        selectedObservation: null,
      };
    case "reset":
      return { ...initialSelection };
  }
}
const SelectionContext = createContext<{
  selection: Selection;
  dispatch: Dispatch<SelectionAction>;
} | null>(null);
export function SelectionProvider({ children }: { children: ReactNode }) {
  const [selection, dispatch] = useReducer(selectionReducer, initialSelection);
  return (
    <SelectionContext.Provider value={{ selection, dispatch }}>
      {children}
    </SelectionContext.Provider>
  );
}
export function useSelection() {
  const context = useContext(SelectionContext);
  if (!context) throw new Error("SelectionProvider is required");
  return context;
}
