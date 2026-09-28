/** Explicit FastAPI v1 -> recovered UI presentation mapping; never a demo fallback. */
import { ApiError } from "./errors";
type Obj = Record<string, unknown>;
const fail = (): never => { throw new ApiError("invalid_response"); };
export const record = (v: unknown): Obj => v !== null && typeof v === "object" && !Array.isArray(v) ? v as Obj : fail();
export const list = (v: unknown, max = 500): unknown[] => Array.isArray(v) && v.length <= max ? v : fail();
export const text = (v: unknown): string => typeof v === "string" && v.length <= 4096 ? v : fail();
export const number = (v: unknown): number => typeof v === "number" && Number.isFinite(v) ? v : fail();
export const boolean = (v: unknown): boolean => typeof v === "boolean" ? v : fail();
export const nullableNumber = (v: unknown) => v === null ? null : number(v);
const mode = (v: unknown) => v === "real" || v === "synthetic" ? v : fail();
const envelope = (v: Obj) => ({ schema_version: 1 as const, mode: mode(v.data_mode) });
const noCapabilities = {surface:false,timeseries:false,depth:false,volume:false,vectors:false,current_components:[]};
const capabilities = (value: unknown) => {
  const c = record(value);
  // No implemented model-depth/current HTTP adapter: never infer renderability.
  return {...noCapabilities,surface:boolean(c.surface),timeseries:boolean(c.timeseries)};
};
const variableList = (v: unknown) => Object.entries(record(v)).map(([name,value]) => {
  const info=record(value);
  if(info.source_name!==name) fail();
  return {name,label:typeof info.long_name==="string" ? info.long_name : name,units:text(info.units)};
});
function collection(value: unknown) {
  const v=record(value), c=record(v.capabilities), counts=record(v.counts);
  const source=v.source_id==="argo"?"argo":v.source_id==="ifremer_glider"?"glider":fail();
  return {...envelope(v),collection_id:text(v.collection_id),name:text(v.dataset_id),source,
    variables:variableList(v.variables), sample_count:number(counts.selected_samples),
    profile_count:boolean(c.profiles)?null:0, qc_status:text(v.qc_policy),
    capabilities:{samples:boolean(c.scientific_samples),profiles:boolean(c.profiles),tracks:boolean(c.tracks)},
    provenance:`${text(v.client_processing)}; ${text(v.qc_policy)}; ${list(v.warnings,16).map(text).join("; ")}`};
}
export function adaptBackendResponse(path: string, value: unknown): unknown {
  const v=record(value), route=path.split("?")[0];
  if(route==="/health") return v;
  if(v.schema_version!==1) fail();
  if(route.startsWith("/api/v1/comparisons")) return v;
  if(route==="/ready") {
    if(v.status!=="ready"&&v.status!=="not_ready") fail();
    return {schema_version:1,ready:v.status==="ready",reason:v.reason_code==null?(v.status==="ready"?"configured_surface_products_ready":"configured_surface_products_not_ready"):text(v.reason_code),required_products:list(v.checks,16).map(x=>text(record(x).product_id))};
  }
  if(route==="/api/v1/datasets") {
    const products=list(v.products,640).map(record);
    return {schema_version:1,mode:"real",datasets:list(v.datasets,100).map(item=>{
      const d=record(item), ids=list(d.product_ids,640).map(text);
      const ready=products.filter(q=>q.status==="ready"&&ids.includes(text(q.product_id))&&q.dataset_id===d.dataset_id);
      const p=ready.find(q=>list(q.variables,4).includes("SST")) ?? ready[0];
      if(d.status==="ready"&&!p) fail();
      // Different variable batches may join only with verified matching source
      // checksum/version, real/synthetic mode and exact selected region.
      const compatible=p?ready.filter(q=>q.data_mode===p.data_mode &&
        (q.product_id===p.product_id || (p.region!=null && JSON.stringify(q.region)===JSON.stringify(p.region) &&
        (p.input_md5!=null ? (q.input_md5===p.input_md5 && q.source_version===p.source_version) :
        JSON.stringify(list(q.variables,4).map(text).sort())===JSON.stringify(list(p.variables,4).map(text).sort()))))):[];
      const byTime=new Map<string,string>();
      const byVariable=new Map<string,Map<string,string>>();
      const variableMetadata=new Map<string,ReturnType<typeof variableList>[number]>();
      for(const q of compatible) {
        const names=list(q.variables,4).map(text);
        if(q.variable_metadata!=null) {
          const fields=variableList(q.variable_metadata);
          if(fields.length!==names.length || fields.some(f=>!names.includes(f.name))) fail();
          for(const field of fields) {
            const previous=variableMetadata.get(field.name);
            if(previous && JSON.stringify(previous)!==JSON.stringify(field)) fail();
            variableMetadata.set(field.name,field);
          }
        }
        for(const name of names) {
          const axis=byVariable.get(name) ?? new Map<string,string>();
          for(const time of list(q.times,12).map(text)) if(!axis.has(time)) axis.set(time,text(q.product_id));
          byVariable.set(name,axis);
        }
        // Legacy primary-variable timeline remains available to older consumers.
        if(list(p!.variables,4).every(name=>names.includes(text(name))))
          for(const time of list(q.times,12).map(text)) if(!byTime.has(time)) byTime.set(time,text(q.product_id));
      }
      const times=[...byTime.keys()].sort();
      const order=["SST","SSS","MLD","CHL","DIC","NO3","pCO2_Original","pCO2_Clim","pCO2_Int","Deviant_uncertainty"];
      const fields=[...variableMetadata.values()].sort((a,b)=>(order.indexOf(a.name)<0?99:order.indexOf(a.name))-(order.indexOf(b.name)<0?99:order.indexOf(b.name)) || a.name.localeCompare(b.name));
      return {schema_version:1,mode:p?mode(p.data_mode):"real",dataset_id:text(d.dataset_id),source_name:text(d.source_id),name:text(d.title),
        status:d.status==="ready"?"prepared":text(d.status),product_id:p?text(p.product_id):null,
        variables:fields,time_products:times.map(timestamp=>({timestamp,product_id:byTime.get(timestamp)!})),
        variable_time_products:[...byVariable].map(([variable,axis])=>({variable,times:[...axis.keys()].sort().map(timestamp=>({timestamp,product_id:axis.get(timestamp)!}))})),
        capabilities:p?capabilities(p.capabilities):noCapabilities,
        time_coverage:times.length?{start:times[0],end:times[times.length-1]}:null};
    })};
  }
  if(/^\/api\/v1\/products\/[^/]+$/.test(route)) {
    const lat=list(v.latitude,10000).map(number), lon=list(v.longitude,10000).map(number);
    if(!lat.length||!lon.length) fail();
    return {...envelope(v),product_id:text(v.product_id),dataset_id:text(v.dataset_id),source_name:text(v.source_id),name:text(v.dataset_id),
      variables:variableList(v.variables),capabilities:capabilities(v.capabilities),times:list(v.times,12).map(text),depths:[],depth_units:null,
      bounds:{west:lon[0],east:lon[lon.length-1],south:lat[0],north:lat[lat.length-1]},
      provenance:`${text(v.origin_url)}; version ${text(v.source_version)}; ${text(v.qc_policy)}; ${text(v.temporal_support)}`};
  }
  if(route.endsWith("/frame")) return {...v,...envelope(v),timestamp:text(v.time)};
  if(route.endsWith("/timeseries")) {
    const point=record(v.sample_point);
    return {...v,...envelope(v),timestamps:list(v.times,12).map(text),longitude:number(point.longitude),latitude:number(point.latitude),distance_km:number(v.distance_m)/1000};
  }
  if(route==="/api/v1/acquisitions") return {schema_version:1,mode:"real",acquisitions:list(v.acquisitions,64).map(value=>{
    const a=record(value);
    return {...envelope(a),acquisition_id:text(a.acquisition_id),source_name:text(a.source_id),status:text(a.status),
      provenance:`${text(a.origin_url)}; ${text(a.client_processing)}; acquired input, not a served scientific layer`};
  })};
  if(route==="/api/v1/observations") return {schema_version:1,mode:"real",collections:list(v.collections,32).map(record).filter(c=>c.status==="ready").map(c=>collection(c.metadata))};
  if(/^\/api\/v1\/observations\/[^/]+$/.test(route)) return collection(v);
  if(/^\/api\/v1\/observations\/[^/]+\/samples$/.test(route)) return {...v,...envelope(v),samples:list(v.samples,500).map(value=>{
    const s=record(value), values=record(s.values), pres=record(values.PRES);
    const mapped=Object.fromEntries(Object.entries(values).map(([name,val])=>{
      const q=record(val); const eligible=boolean(q.qc_eligible); const selected=nullableNumber(q.selected_value);
      const kind=text(q.selected_kind);
      if(kind!=="raw"&&kind!=="adjusted") fail();
      if(selected!==q[kind]||q.selected_qc!==q[kind+"_qc"]) fail();
      return [name,eligible?selected:null];
    }));
    const rejected=Object.entries(values).filter(([,q])=>!boolean(record(q).qc_eligible)).map(([name])=>name);
    return {sample_id:text(s.sample_id),profile_id:s.profile_id===null?null:text(s.profile_id),timestamp:text(s.time),longitude:number(s.longitude),latitude:number(s.latitude),depth_m:nullableNumber(s.depth_m),pressure_dbar:number(s.pressure_dbar),
      platform_id:s.platform_id===null?undefined:text(s.platform_id),cycle_id:s.cycle_number===null?undefined:String(number(s.cycle_number)),sequence:number(s.source_sample_index),data_mode:text(pres.selected_kind),
      qc:rejected.length?`QC excluded: ${rejected.join(", ")}`:"Eligible under core flags 1/2 policy (not comparison approval)",values:mapped,
      provenance:JSON.stringify({profile_identity:s.profile_identity_status,time_qc:s.time_qc,position_qc:s.position_qc,values})};
  })};
  return fail();
}
