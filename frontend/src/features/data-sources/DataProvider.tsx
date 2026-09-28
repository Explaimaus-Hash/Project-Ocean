"use client";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useCallback,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { AdvancedField } from "@/features/advanced-rendering/advancedModel";
import type { Bounds, Frame, Product, TimeseriesQuery } from "@/lib/api/types";
import { BoundedFrameLoader } from "@/features/scalar/BoundedFrameLoader";
import { intersect } from "@/features/scalar/ScientificColorScale";
import { DataClient, LatestRequest } from "@/lib/dataClient";
import { adaptBackendResponse } from "@/lib/api/backendAdapter";
import { ApiError, asApiError, errorCopy } from "@/lib/api/errors";
import type { Scenario } from "@/lib/demo/transport";
import { useSelection } from "@/lib/selection";
export function useResource<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
  enabled = true,
) {
  const loader = useRef(load);
  loader.current = load;
  const [result, setResult] = useState<{
    key: string;
    value?: T;
    error?: ApiError;
  }>({ key: "" });
  useEffect(() => {
    if (!enabled) return;
    const gate = new LatestRequest();
    let active = true;
    gate
      .run((signal) => loader.current(signal))
      .then(
        (value) => {
          if (active) setResult({ key, value });
        },
        (error) => {
          if (active) setResult({ key, error: asApiError(error) });
        },
      );
    return () => {
      active = false;
      gate.cancel();
    };
  }, [key, enabled]);
  return enabled && result.key === key ? result : { key };
}
function useDataState() {
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [revision, setRevision] = useState(0);
  const client = useMemo(
    () =>
      new DataClient({
        baseUrl: "/backend",
        adapt: adaptBackendResponse,
      }),
    [scenario, revision],
  );
  useEffect(() => () => client.clear(), [client]);
  const root = `${scenario}:${revision}`;
  const requestTimeseries = useCallback(
    (id: string, query: TimeseriesQuery, signal: AbortSignal) =>
      client.getTimeseries(id, query, signal),
    [client],
  );
  const inspectProduct = useCallback(
    (id: string, signal: AbortSignal) => client.getProduct(id, signal),
    [client],
  );
  const [quality, setQuality] = useState<"preview" | "scientific">("preview");
  const [viewportBounds, setViewportBounds] = useState<Bounds | null>(null);
  const boundedLoader = useMemo(() => new BoundedFrameLoader(client), [client]);
  const { selection, dispatch } = useSelection();
  const health = useResource(`${root}:health`, (s) => client.getHealth(s));
  const readiness = useResource(`${root}:ready`, (s) => client.getReadiness(s));
  const catalogue = useResource(`${root}:datasets`, (s) =>
    client.getDatasets(s),
  );
  const observations = useResource(`${root}:observations`, (s) =>
    client.getObservationCollections(s),
  );
  const acquisitions = useResource(`${root}:acquisitions`, (s) =>
    client.getAcquisitions(s),
  );
  const dataset = catalogue.value?.datasets.find(
    (d) => d.dataset_id === selection.modelSource,
  );
  useEffect(() => {
    if (!selection.modelSource) {
      const first = catalogue.value?.datasets.find(d => d.product_id);
      if (first) dispatch({type:"select-dataset",id:first.dataset_id});
    }
    if (!selection.observationSource) {
      const first = observations.value?.collections[0];
      if (first) dispatch({type:"select-observation",id:first.collection_id});
    }
  }, [catalogue.value,observations.value,selection.modelSource,selection.observationSource,dispatch]);
  const catalogueVariable = dataset?.variables.find(v=>v.name===selection.variable)?.name ?? dataset?.variables[0]?.name;
  const timelineProducts = dataset?.variable_time_products?.find(v=>v.variable===(catalogueVariable ?? selection.variable))?.times ?? dataset?.time_products;
  const mappedTime = timelineProducts?.find(t=>t.timestamp===selection.currentTime) ?? timelineProducts?.[0];
  const selectedProductId = mappedTime?.product_id ?? dataset?.product_id;
  const product = useResource(
    `${root}:product:${selectedProductId}`,
    (s) => client.getProduct(selectedProductId!, s),
    !!selectedProductId,
  );
  const metadata = product.value;
  const [previousMetadata, setPreviousMetadata] = useState<{root:string; value:Product} | null>(null);
  useEffect(() => {
    if (metadata) setPreviousMetadata({root,value:metadata});
  }, [root,metadata]);
  // Retain presentation context only for the same compatible archive group.
  // Requests still require the actual selected product metadata below.
  const displayProduct = metadata ?? (previousMetadata?.root===root && previousMetadata.value.dataset_id===dataset?.dataset_id && mappedTime && (!catalogueVariable || previousMetadata.value.variables.some(v=>v.name===catalogueVariable))
    ? previousMetadata.value : undefined);
  const variable =
    catalogueVariable ?? displayProduct?.variables.find((v) => v.name === selection.variable)?.name ??
    displayProduct?.variables[0]?.name;
  const timestamp = metadata?.times.includes(selection.currentTime ?? "")
    ? selection.currentTime!
    : metadata?.times[0];
  useEffect(() => {
    if (variable && selection.variable !== variable)
      dispatch({ type: "select-variable", value: variable });
    if (timestamp && selection.currentTime !== timestamp)
      dispatch({ type: "select-time", value: timestamp });
  }, [
    variable,
    timestamp,
    selection.variable,
    selection.currentTime,
    dispatch,
  ]);
  const index = timestamp && metadata ? metadata.times.indexOf(timestamp) : 0;
  const variables = dataset?.variables.length ? dataset.variables : displayProduct?.variables ?? [];
  const times = timelineProducts?.length ? timelineProducts.map(t=>t.timestamp) : metadata?.times ?? [];
  const timelineTimestamp = mappedTime?.timestamp ?? timestamp;
  const timelineIndex = timelineTimestamp ? Math.max(0,times.indexOf(timelineTimestamp)) : 0;
  const requestedBounds = viewportBounds ?? {
    west: 30,
    east: 120,
    south: -30,
    north: 30,
  };
  const bounds = displayProduct ? intersect(displayProduct.bounds, requestedBounds) : null;
  const boundsKey = JSON.stringify(bounds);
  const family = `${root}:${dataset?.dataset_id}:${dataset?.product_id}:${variable}:${boundsKey}`;
  const frame = useResource(
    `${family}:${selectedProductId}:${quality}:${index}`,
    async (s) => {
      if (!bounds) throw new ApiError("no_overlap");
      const value = await boundedLoader.load(
        metadata!.product_id,
        { variable: variable!, time_index: index, quality, bounds },
        s,
      );
      if (
        value.variable !== variable || value.product_id !== metadata!.product_id ||
        value.timestamp !== metadata!.times[index] ||
        value.units !==
          metadata!.variables.find((v) => v.name === variable)?.units
      )
        throw new ApiError("invalid_response");
      return value;
    },
    !!metadata && !!variable && !!timestamp && metadata.variables.some(v=>v.name===variable),
  );
  const [previous, setPrevious] = useState<{
    family: string;
    frame: Frame;
  } | null>(null);
  useEffect(() => {
    if (frame.value) setPrevious({ family, frame: frame.value });
  }, [family, frame.value]);
  const displayedFrame =
    frame.value ?? (previous?.family === family ? previous.frame : undefined);
  // Warm at most one next frame (including the next batch) in the existing
  // three-frame/6MiB cache. Cancellation never changes the active selection.
  useEffect(() => {
    if (!frame.value || !metadata || !bounds || !variable) return;
    const nextTime = times[timelineIndex + 1];
    if (!nextTime) return;
    const nextProduct = timelineProducts?.find(t=>t.timestamp===nextTime)?.product_id ?? metadata.product_id;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      void (async () => {
        const next = nextProduct===metadata.product_id ? metadata : await client.getProduct(nextProduct,controller.signal);
        const nextIndex = next.times.indexOf(nextTime);
        if (nextIndex<0 || !next.variables.some(v=>v.name===variable)) return;
        await boundedLoader.load(next.product_id,{variable,time_index:nextIndex,quality,bounds},controller.signal);
      })().catch(()=>undefined); // Prefetch failure must not fail the displayed frame.
    },150);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [frame.value,metadata,variable,quality,boundsKey,timelineIndex,dataset,client,boundedLoader]);
  const collection = observations.value?.collections.find(
    (c) => c.collection_id === selection.observationSource,
  );
  const collectionDetail = useResource(
    `${root}:collection:${collection?.collection_id}`,
    (s) => client.getObservationCollection(collection!.collection_id, s),
    !!collection,
  );
  const [search, setSearch] = useState<{
    collectionId: string;
    offset: number;
    profileId: string;
  }>({ collectionId: "", offset: 0, profileId: "" });
  const query =
    search.collectionId === collection?.collection_id
      ? search
      : {
          collectionId: collection?.collection_id ?? "",
          offset: 0,
          profileId: "",
        };
  const setObservationQuery = (
    patch: Partial<{ offset: number; profileId: string }>,
  ) => {
    dispatch({ type: "select-observation-sample", value: null });
    setSearch({ ...query, ...patch });
  };
  const samples = useResource(
    `${root}:samples:${collection?.collection_id}:${query.offset}:${query.profileId}`,
    (s) =>
      client.getObservationSamples(
        collection!.collection_id,
        {
          offset: query.offset,
          limit: 50,
          profile_id: query.profileId || undefined,
        },
        s,
      ),
    !!collection,
  );
  const selected = selection.selectedObservation;
  const selectedSample =
    selected && selected.collectionId === collection?.collection_id
      ? samples.value?.samples.find(
          (sample) => sample.sample_id === selected.sampleId,
        )
      : undefined;
  const [profilePage, setProfilePage] = useState<{
    id: string;
    offset: number;
  }>({ id: "", offset: 0 });
  const profileKey = `${collection?.collection_id}:${selected?.profileId}`;
  const profileOffset = profilePage.id === profileKey ? profilePage.offset : 0;
  const profile = useResource(
    `${root}:profile:${profileKey}:${profileOffset}`,
    (s) =>
      client.getObservationSamples(
        collection!.collection_id,
        { profile_id: selected!.profileId!, offset: profileOffset, limit: 50 },
        s,
      ),
    !!selectedSample && !!selected?.profileId,
  );
  return {
    // No documented depth/component/volume adapter exists yet. Never infer data from capability flags.
    client,
    advancedField: undefined as AdvancedField | undefined,
    requestTimeseries,
    inspectProduct,
    connectionKey: root,
    observationQuery: query,
    setObservationQuery,
    selectedSample,
    profile,
    profileOffset,
    setProfileOffset: (offset: number) =>
      setProfilePage({ id: profileKey, offset }),
    quality,
    setQuality,
    viewportBounds,
    setViewportBounds,
    bounds,
    displayedFrame,
    family,
    scenario,
    setScenario: (value: Scenario) => {
      dispatch({ type: "reset" });
      setScenario(value);
    },
    health,
    readiness,
    catalogue,
    observations,
    acquisitions,
    dataset,
    product,
    displayProduct,
    variable,
    variables,
    timestamp,
    index,
    times,
    timelineIndex,
    timelineTimestamp,
    frame,
    collectionDetail,
    samples,
    retry: () => setRevision((v) => v + 1),
    selectDataset: (id: string) => dispatch({ type: "select-dataset", id }),
    selectVariable: (value: string) => {
      if (variables.some((v) => v.name === value))
        dispatch({ type: "select-variable", value });
    },
    selectTime: (value: string) => {
      if (times.includes(value))
        dispatch({ type: "select-time", value });
    },
  };
}
const Context = createContext<ReturnType<typeof useDataState> | null>(null);
export function DataProvider({ children }: { children: ReactNode }) {
  const value = useDataState();
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useData() {
  const value = useContext(Context);
  if (!value) throw new Error("DataProvider required");
  return value;
}
export function ApiState({
  error,
  context,
}: {
  error?: ApiError;
  context?: "frame" | "observations";
}) {
  const { retry } = useData();
  if (!error) return null;
  return (
    <div className="api-state" role="status">
      <strong>
        {context === "frame" && error.code === "empty_selection"
          ? "No data at timestamp"
          : context === "frame" && error.code === "no_overlap"
            ? "No data in region"
            : context === "observations" &&
                error.code === "provider_unavailable"
              ? "Observation unavailable"
              : error.code === "timeout"
                ? "Source timed out"
                : errorCopy[error.code][0]}
      </strong>
      <p>{errorCopy[error.code][1]}</p>
      <button className="text-button" onClick={retry}>
        Retry data
      </button>
    </div>
  );
}
export function DemoSettings() {
  return (
    <div className="demo-settings">
      <strong>Live local backend · prepared data</strong>
      <p className="field-note">
        Data is read from your FastAPI backend. No demo fallback or automatic downloads.
        Source availability and scientific readiness remain separate.
      </p>
    </div>
  );
}
