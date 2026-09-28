"use client";
import { useState } from "react";
import { useData,useResource,ApiState } from "@/features/data-sources/DataProvider";
import { ScientificPlotShell } from "@/features/analysis/ScientificPlotShell";
export function LiveComparisonPanel(){
  const {client,connectionKey}=useData();
  const [selection,setSelection]=useState({id:"",offset:0,filter:"all"});
  const catalogue=useResource(`${connectionKey}:comparisons`,s=>client.getComparisons(s));
  const available=catalogue.value?.comparisons.filter(x=>x.availability==="prepared_snapshot")??[];
  const id=selection.id||available[0]?.comparison_id;
  const matched=selection.filter==="all"?null:selection.filter==="matched";
  const metadata=useResource(`${connectionKey}:comparison:${id}`,s=>client.getComparison(id!,s),!!id);
  const page=useResource(`${connectionKey}:comparison:${id}:${selection.offset}:${selection.filter}`,s=>client.getComparisonSamples(id!,selection.offset,matched,s),!!id);
  const m=metadata.value,summary=m?.summary,rows=page.value?.samples??[],pairs=rows.filter(r=>r.matched);
  return <div className="comparison-workspace">
    <header><span className="eyebrow">PROJECT OCEAN / SAVED COMPARISON</span><h1>Model & observation</h1><p>Copernicus practical salinity vs Argo · read-only prepared results</p></header>
    <div className="demo-notice" role="status"><strong>Exploratory assumptions · not independent validation</strong><p>These saved results use declared time, depth and grid-support assumptions. Strict scientific matching remains blocked. No matching or downloads run in your browser.</p></div>
    <ApiState error={catalogue.error??metadata.error??page.error}/>
    {!catalogue.value&&!catalogue.error&&<p>Loading prepared comparisons…</p>}
    {catalogue.value&&!available.length&&<p>No prepared comparison is available. Preparation is an explicit backend operator task.</p>}
    {catalogue.value?.comparisons.filter(x=>x.availability==="unavailable").map(x=><p key={x.comparison_id}>Unavailable snapshot: {x.comparison_id} · {x.reason_code}</p>)}
    {!!available.length&&<label>Saved snapshot <select aria-label="Saved comparison" value={id} onChange={e=>setSelection({id:e.target.value,offset:0,filter:"all"})}>{available.map(x=><option key={x.comparison_id}>{x.comparison_id}</option>)}</select></label>}
    {m&&summary&&<>
      <p>{m.data_mode} data · {m.status} · {m.quantity_units}<br/>Prepared {m.prepared_at} · historical snapshot, not live source status<br/>{m.model_dataset_id} / {m.model_dataset_version}<br/>Model: {m.model_id} · Observations: {m.collection_id}</p>
      <div className="comparison-metrics" aria-label="Full snapshot metrics"><p><strong>{summary.matched_pair_count} matched pairs</strong> / {summary.total_sample_count} samples · {summary.excluded_sample_count} excluded · {summary.unevaluated_sample_count} unevaluated</p><p>Bias: {summary.bias??"Not available"} · RMSE: {summary.rmse??"Not available"} ({m.quantity_units})</p><p>Full snapshot statistics, not the filtered page. Model minus observation; equal sample weighting; uncertainty not propagated.</p></div>
      <details><summary>Assumptions and strict blockers</summary><pre>{JSON.stringify(m.assumptions,null,2)}</pre><ul>{m.strict_blockers.map(x=><li key={x}>{x}</li>)}</ul></details>
      <label>Rows <select aria-label="Comparison row filter" value={selection.filter} onChange={e=>setSelection({...selection,filter:e.target.value,offset:0})}><option value="all">All samples</option><option value="matched">Matched</option><option value="excluded">Excluded</option></select></label>
      {!page.value&&!page.error&&<p>Loading sample page…</p>}
      {!!pairs.length&&<ScientificPlotShell metadata={{title:"Exploratory model vs observation",source:"Copernicus / Argo",dataset:m.comparison_id,quantity:"Practical salinity",units:m.quantity_units,selection:"Accepted pairs on the current page only",timeRange:pairs.map(r=>r.observation_time).sort().filter((_,i,a)=>i===0||i===a.length-1).join(" → "),note:"Assumption-labelled; not independent validation; no regression fit or inferred correlation",mode:m.data_mode}} traces={[{type:"scatter",mode:"markers",name:"Exploratory pairs",x:pairs.map(r=>r.observation_value),y:pairs.map(r=>r.candidate?.model_value),marker:{color:"#4ed5de",size:10}}]} layout={{xaxis:{title:{text:`Argo (${m.quantity_units})`}},yaxis:{title:{text:`Copernicus (${m.quantity_units})`}},hovermode:"closest"}}/>}
      <div className="comparison-table-scroll" style={{overflowX:"auto"}}><table aria-label="Comparison samples"><thead><tr>{["Observation time","Depth (m)","Argo","Model","Difference","Offset (m)","Result"].map(t=><th key={t}>{t}</th>)}</tr></thead><tbody>{rows.map(r=><tr key={r.sample_id}><td>{r.observation_time}<small>{r.sample_id}</small></td><td>{r.observation_depth_m??"—"}</td><td>{r.observation_value??"—"}</td><td>{r.candidate?.model_value??"—"}</td><td>{r.model_minus_observation??"—"}</td><td>{r.candidate?.horizontal_offset_m??"—"}</td><td>{r.matched?"Exploratory match":r.exclusions.join(", ")}</td></tr>)}</tbody></table></div>
      {page.value&&<div className="observation-paging"><button disabled={!selection.offset} onClick={()=>setSelection({...selection,offset:Math.max(0,selection.offset-100)})}>Previous page</button><span>{page.value.total} filtered rows · page {Math.floor(selection.offset/100)+1}</span><button disabled={page.value.next_offset===null} onClick={()=>setSelection({...selection,offset:page.value!.next_offset!})}>Next page</button></div>}
    </>}
  </div>;
}
