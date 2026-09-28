import { record, list, text, number, boolean, nullableNumber } from "./backendAdapter";
export interface ComparisonMetadata {
  schema_version:1; comparison_id:string; prepared_at:string; data_mode:"real"|"synthetic";
  assurance:"exploratory_assumptions"; comparison_ready:false; independent_validation:false;
  status:string; model_id:string; collection_id:string; model_dataset_id:string; model_dataset_version:string;
  quantity_units:string; strict_blockers:string[]; assumptions:Record<string,unknown>;
  summary:{total_sample_count:number;evaluated_sample_count:number;matched_pair_count:number;excluded_sample_count:number;unevaluated_sample_count:number;metrics_available:boolean;bias:number|null;rmse:number|null;exclusion_counts:Record<string,number>};
}
export interface ComparisonSample {
  sample_id:string; matched:boolean; observation_value:number|null; observation_time:string;
  observation_latitude:number; observation_longitude:number; observation_depth_m:number|null;
  exclusions:string[]; model_minus_observation:number|null;
  candidate:null|{model_value:number|null; model_time_label:string; model_depth_m:number; horizontal_offset_m:number; vertical_offset_m:number; midpoint_offset_seconds:number};
}
export interface ComparisonPage {schema_version:1;metadata:ComparisonMetadata;offset:number;limit:number;matched:boolean|null;total:number;next_offset:number|null;samples:ComparisonSample[]}
export interface ComparisonCatalogue {schema_version:1;comparisons:({comparison_id:string;availability:"prepared_snapshot";metadata:ComparisonMetadata}|{comparison_id:string;availability:"unavailable";reason_code:string})[]}
const require = (v: boolean) => { if(!v) throw new Error("Invalid comparison contract"); };
function metadata(value:unknown) {
  const v=record(value), s=record(v.summary);
  require(v.schema_version===1 && /^c_[a-f0-9]{24}$/.test(text(v.comparison_id)));
  require(v.assurance==="exploratory_assumptions"&&v.comparison_ready===false&&v.independent_validation===false);
  require(v.snapshot_semantics==="immutable_result_not_live_source_status"&&v.difference_convention==="model_minus_observation");
  require(v.data_mode==="real"||v.data_mode==="synthetic");
  require(["blocked","evaluated","partially_blocked"].includes(text(v.status)));
  for(const key of ["model_id","collection_id","model_dataset_id","model_dataset_version","quantity_units"]) text(v[key]);
  require(Number.isFinite(Date.parse(text(v.prepared_at))));
  list(v.strict_blockers,64).forEach(text); record(v.assumptions);
  for(const key of ["total_sample_count","evaluated_sample_count","matched_pair_count","excluded_sample_count","unevaluated_sample_count"]){const n=number(s[key]);require(Number.isInteger(n)&&n>=0&&n<=5000);}
  require(s.total_sample_count===number(s.evaluated_sample_count)+number(s.unevaluated_sample_count));
  require(s.evaluated_sample_count===number(s.matched_pair_count)+number(s.excluded_sample_count));
  const bias=nullableNumber(s.bias),rmse=nullableNumber(s.rmse);
  require(boolean(s.metrics_available)===(number(s.matched_pair_count)>0));
  require(number(s.matched_pair_count)>0?bias!==null&&rmse!==null&&rmse>=0:bias===null&&rmse===null);
  Object.values(record(s.exclusion_counts)).forEach(n=>require(Number.isInteger(number(n))&&number(n)>=0));
}
export function isComparisonMetadata(v:unknown): v is ComparisonMetadata {try{metadata(v);return true;}catch{return false;}}
export function isComparisonCatalogue(value:unknown):value is ComparisonCatalogue {
  try {const v=record(value);require(v.schema_version===1);const entries=list(v.comparisons,32);const ids=new Set();for(const item of entries){const e=record(item);const id=text(e.comparison_id);require(/^c_[a-f0-9]{24}$/.test(id)&&!ids.has(id));ids.add(id);if(e.availability==="prepared_snapshot"){metadata(e.metadata);require(record(e.metadata).comparison_id===id);}else{require(e.availability==="unavailable");text(e.reason_code);}}return true;}catch{return false;}
}
export function isComparisonPage(value:unknown):value is ComparisonPage {
  try {const v=record(value);require(v.schema_version===1);metadata(v.metadata);const meta=record(v.metadata),s=record(meta.summary);
    const offset=number(v.offset),limit=number(v.limit),total=number(v.total);
    require(Number.isInteger(offset)&&offset>=0&&offset<=5000&&Number.isInteger(limit)&&limit>=1&&limit<=500);
    require(v.matched===null||typeof v.matched==="boolean");
    require(total===(v.matched===null?s.evaluated_sample_count:v.matched?s.matched_pair_count:s.excluded_sample_count));
    const rows=list(v.samples,500);require(rows.length===Math.min(limit,Math.max(0,total-offset)));
    require(v.next_offset===(offset+rows.length<total?offset+rows.length:null));
    const ids=new Set();for(const value of rows){const r=record(value),id=text(r.sample_id);require(!ids.has(id));ids.add(id);
      const matched=boolean(r.matched);require(v.matched===null||matched===v.matched);require(r.assurance==="exploratory_assumptions"&&r.quantity_units===meta.quantity_units);
      const observation=nullableNumber(r.observation_value),difference=nullableNumber(r.model_minus_observation);list(r.exclusions,64).forEach(text);
      require(Number.isFinite(Date.parse(text(r.observation_time))));number(r.observation_latitude);number(r.observation_longitude);nullableNumber(r.observation_depth_m);
      if(r.candidate!==null){const c=record(r.candidate);nullableNumber(c.model_value);text(c.model_time_label);for(const key of ["model_depth_m","horizontal_offset_m","vertical_offset_m","midpoint_offset_seconds"])number(c[key]);}
      if(matched){const c=record(r.candidate);require(observation!==null&&c.model_value!==null&&difference===number(c.model_value)-number(observation)&&list(r.exclusions).length===0);}else require(difference===null);
    }return true;
  }catch{return false;}
}
