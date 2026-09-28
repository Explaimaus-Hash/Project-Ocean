import {test,expect} from "@playwright/test";
import {DataClient} from "../src/lib/dataClient";
import {adaptBackendResponse} from "../src/lib/api/backendAdapter";
import {sourceTimeIndex} from "../src/features/controls/SourceTimeControl";
const product="p_7c8210052d41d41259724e2d", collection="o_c645f248f801845378f0fdaf", comparison="c_0abd2057c5bc5c41fcf49109";
test("UTC time entry requires exact valid dataset membership",()=>{
  const times=["2019-02-28T00:00:00Z","2020-02-29T13:02:03.123Z"];
  expect(sourceTimeIndex(times,"2019-02-28T00:00")).toBe(0);
  expect(sourceTimeIndex(times,"2020-02-29T13:02:03.123")).toBe(1);
  for(const invalid of ["", "2019-02-29T00:00", "2019-02-28T00:01", "2018-02-28T00:00", "2019-02-28T24:00", "2019-02-28T00:00+05:30"])
    expect(sourceTimeIndex(times,invalid)).toBe(-1);
  expect(sourceTimeIndex([],"2019-02-28T00:00")).toBe(-1);
});
test("custom UTC selection loads only an available frame and synchronizes with timeline",async({page})=>{
  await page.goto("/explorer");
  await expect(page.getByText(/Prepared frame loaded/)).toBeVisible({timeout:40000});
  const input=page.locator("#source-time-input");
  await input.fill("2019-02-28T00:00");
  await page.getByRole("button",{name:"Apply time",exact:true}).click();
  await expect(page.locator("#dataset-time")).toHaveValue("2019-02-28T00:00:00Z");
  await expect(page.getByText("Prepared frame loaded · 2019-02-28T00:00:00Z",{exact:true})).toBeVisible();
  await page.locator(".source-time-control").screenshot({path:"test-results/source-time-control.png"});
  await input.fill("2019-02-27T00:00");
  await input.press("Enter");
  await expect(page.locator("#source-time-error")).toContainText("not available");
  await expect(page.locator("#dataset-time")).toHaveValue("2019-02-28T00:00:00Z");
  // Bounded background prefetch may request the next valid frame, but invalid
  // input must never replace the displayed selection.
  await expect(page.locator(".scientific-colorbar")).toHaveAttribute("data-timestamp","2019-02-28T00:00:00Z");
  await input.fill("");await page.getByRole("button",{name:"Apply time",exact:true}).click();
  await expect(input).toHaveAttribute("aria-invalid","true");
  await page.locator("#dataset-time").selectOption("2019-03-30T00:00:00Z");
  await expect(input).toHaveValue("2019-03-30T00:00");
  await page.getByRole("button",{name:"Previous frame",exact:true}).click();
  await expect(input).toHaveValue("2019-02-28T00:00");
  await page.locator("#dataset").selectOption({index:2});
  await expect(input).toBeDisabled();
  await expect(page.getByRole("button",{name:"Apply time",exact:true})).toBeDisabled();
});
test("readiness supports omitted success reason and explicit unavailable state",()=>{
  expect(adaptBackendResponse("/ready",{schema_version:1,status:"ready",checks:[]})).toMatchObject({ready:true});
  expect(adaptBackendResponse("/ready",{schema_version:1,status:"not_ready",reason_code:"not_configured",checks:[]})).toMatchObject({ready:false,reason:"not_configured"});
  expect(()=>adaptBackendResponse("/ready",{schema_version:1,status:"invented",checks:[]})).toThrow();
});
test("rejected QC is not rendered as a valid measurement and provenance is retained",async()=>{
  const response=await fetch(`http://127.0.0.1:8000/api/v1/observations/${collection}/samples`);
  const wire=await response.json();
  wire.samples[0].values.PSAL.qc_eligible=false;
  const mapped=adaptBackendResponse(`/api/v1/observations/${collection}/samples`,wire) as {samples:{values:Record<string,number|null>;provenance:string}[]};
  expect(mapped.samples[0].values.PSAL).toBeNull();
  expect(JSON.parse(mapped.samples[0].provenance).values.PSAL.selected_value).toBe(wire.samples[0].values.PSAL.selected_value);
  wire.samples[0].values.PSAL.selected_value=99999;
  expect(()=>adaptBackendResponse(`/api/v1/observations/${collection}/samples`,wire)).toThrow();
});
test("actual FastAPI responses map without losing units, values or assurance",async()=>{
  const c=new DataClient({baseUrl:"http://127.0.0.1:8000",adapt:adaptBackendResponse});
  expect((await c.getHealth()).status).toBe("ok");
  expect((await c.getReadiness()).ready).toBe(true);
  expect((await c.getDatasets()).datasets.some(d=>d.dataset_id==="incois_bio_roms_v2" && d.product_id)).toBe(true);
  const m=await c.getProduct(product); expect(m.capabilities.depth).toBe(false);expect(m.times).toHaveLength(3);
  const f=await c.getFrame(product,{variable:"SST",time_index:0}); expect(f.mode).toBe("real");expect(f.timestamp).toBe(m.times[0]);expect(f.values).toHaveLength(95);
  const series=await c.getTimeseries(product,{variable:"SST",longitude:75,latitude:0});expect(series.values).toHaveLength(3);
  expect((await c.getAcquisitions()).acquisitions.length).toBeGreaterThan(0);
  expect((await c.getObservationCollections()).collections.some(x=>x.collection_id===collection)).toBe(true);
  const o=await c.getObservationCollection(collection);expect(o.capabilities.profiles).toBe(false);
  const samples=await c.getObservationSamples(collection);expect(samples.total).toBe(14);expect(samples.samples[0].provenance).toContain("adjusted_error");
  expect((await c.getComparisons()).comparisons.some(x=>x.comparison_id===comparison)).toBe(true);
  const metadata=await c.getComparison(comparison);expect(metadata.comparison_ready).toBe(false);expect(metadata.summary.matched_pair_count).toBe(2);
  const page=await c.getComparisonSamples(comparison,0,false);expect(page.total).toBe(12);expect(page.samples.every(x=>x.model_minus_observation===null)).toBe(true);
  c.clear();
});
test("explorer loads real frame, globe and persistent selection",async({page})=>{
  const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
  await page.goto("/explorer");
  await expect(page.locator(".backend-status")).toContainText("Backend connected");
  await expect(page.getByText(/Prepared frame loaded/)).toBeVisible({timeout:40000});
  await expect(page.locator(".cesium-widget canvas")).toBeVisible({timeout:40000});
  await expect(page.locator("#dataset")).toHaveValue("incois_bio_roms_v2");
  await page.locator("#variable").selectOption("SSS");
  await page.getByRole("link",{name:/Analysis/}).click();
  await expect(page.locator(".backend-status")).toContainText("Backend connected");
  await expect(page.locator(".js-plotly-plot")).toBeVisible({timeout:40000});
  await page.getByRole("link",{name:/Explorer/}).click();
  await expect(page).toHaveURL(/\/explorer$/);
  await expect(page.getByRole("heading",{name:"Explorer",exact:true})).toBeVisible();
  await expect(page.locator("#variable")).toHaveValue("SSS");
  await page.screenshot({path:"test-results/live-explorer.png"});
  expect(errors).toEqual([]);
});
test("saved comparison shows real exploratory results and excluded rows",async({page})=>{
  await page.goto("/comparison");
  await expect(page.getByText("2 matched pairs",{exact:true})).toBeVisible();
  await expect(page.getByText("Exploratory assumptions · not independent validation",{exact:true})).toBeVisible();
  await expect(page.getByRole("table",{name:"Comparison samples"}).locator("tbody tr")).toHaveCount(14);
  await page.getByLabel("Comparison row filter").selectOption("excluded");
  await expect(page.getByRole("table",{name:"Comparison samples"}).locator("tbody tr")).toHaveCount(12);
  await page.getByLabel("Comparison row filter").selectOption("matched");
  await expect(page.getByRole("table",{name:"Comparison samples"}).locator("tbody tr")).toHaveCount(2);
  await expect(page.locator(".js-plotly-plot")).toBeVisible();
  await page.screenshot({path:"test-results/live-comparison.png"});
});
test("backend failures do not substitute demo data",async({page})=>{
  await page.route("**/backend/**",route=>route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({schema_version:1,error:{code:"backend_unavailable",message:"Unavailable"}})}));
  await page.goto("/explorer");
  await expect(page.locator(".backend-status")).toContainText("Backend offline");
  await expect(page.locator("#variable")).toBeDisabled();
  await expect(page.getByText("DEMO DATA · SYNTHETIC",{exact:false})).toHaveCount(0);
});
test("profiles and source inventory expose backend provenance",async({page})=>{
  await page.goto("/profiles");
  await expect(page.getByText(/14 source samples loaded/)).toBeVisible();
  await expect(page.getByText(/0 identified profiles/)).toBeVisible();
  await page.getByRole("link",{name:/Data Sources/}).click();
  await expect(page.getByRole("heading",{name:"Data Sources",exact:true})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Acquisitions",exact:true})).toBeVisible();
});

test("archive catalogue exposes 480 dates and browser crosses batch boundaries",async({page})=>{
  test.setTimeout(90000);
  const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
  const client=new DataClient({baseUrl:"http://127.0.0.1:8000",adapt:adaptBackendResponse});
  const dataset=(await client.getDatasets()).datasets.find(d=>d.dataset_id==="incois_bio_roms_v2")!;
  const timeline=dataset.time_products!;
  expect(timeline).toHaveLength(480);
  expect(timeline[0].timestamp).toBe("1980-01-24T00:00:00Z");
  expect(timeline[479].timestamp).toBe("2019-12-25T00:00:00Z");
  await page.goto("/explorer");
  await expect(page.locator("#dataset-time option")).toHaveCount(480);
  for(const index of [0,3,4,240,479]) {
    const entry=timeline[index];
    await page.locator("#source-time-input").fill(entry.timestamp.replace(/:00Z$/,""));
    await page.getByRole("button",{name:"Apply time",exact:true}).click();
    await expect(page.getByText(`Prepared frame loaded · ${entry.timestamp}`,{exact:true})).toBeVisible({timeout:30000});
    await expect(page.locator("#dataset-time")).toHaveValue(entry.timestamp);
  }
  await expect(page.locator(".scientific-colorbar")).toContainText("2019-12-25T00:00:00Z");
  await page.screenshot({path:"test-results/archive-last-date.png"});
  expect(errors).toEqual([]);client.clear();
});

test("archive adapter does not merge incompatible regions, fields or synthetic products",()=>{
  const cap={surface:true,timeseries:true};
  const base={product_id:"p_a",dataset_id:"d",status:"ready",data_mode:"real",variables:["SST"],times:["1980-01-24T00:00:00Z"],capabilities:cap,region:{west:30,east:120,south:-30,north:30}};
  const products=[base,{...base,product_id:"p_b",times:["1980-02-23T00:00:00Z"]},
    {...base,product_id:"p_c",region:{west:40,east:80,south:-10,north:10},times:["1980-03-24T00:00:00Z"]},
    {...base,product_id:"p_d",variables:["SSS"],times:["1980-04-23T00:00:00Z"]},
    {...base,product_id:"p_e",data_mode:"synthetic",times:["1980-05-23T00:00:00Z"]}];
  const result=adaptBackendResponse("/api/v1/datasets",{schema_version:1,products,datasets:[{dataset_id:"d",source_id:"s",title:"Synthetic test",status:"ready",product_ids:products.map(p=>p.product_id)}]}) as {datasets:{time_products:unknown[]}[]};
  expect(result.datasets[0].time_products).toEqual([{timestamp:base.times[0],product_id:"p_a"},{timestamp:"1980-02-23T00:00:00Z",product_id:"p_b"}]);
});

test("batch loading keeps the labelled layer and color scale until replacement is ready",async({page})=>{
  const client=new DataClient({baseUrl:"http://127.0.0.1:8000",adapt:adaptBackendResponse});
  const dates=(await client.getDatasets()).datasets.find(d=>d.dataset_id==="incois_bio_roms_v2")!.time_products!;
  let release!:()=>void;
  const blocked=new Promise<void>(resolve=>{release=resolve;});
  await page.route(`**/backend/api/v1/products/${dates[4].product_id}**`,async route=>{await blocked;await route.continue();});
  await page.goto("/explorer");
  const bar=page.locator(".scientific-colorbar");
  await expect(bar).toHaveAttribute("data-timestamp",dates[0].timestamp);
  const originalMin=await bar.getAttribute("data-min"),originalMax=await bar.getAttribute("data-max");
  for (const width of [1440,760,390]) {
    await page.setViewportSize({width,height:960});
    // Use the timeline itself so the check also works when the source drawer is closed.
    await page.locator("#timeline-time").press("Home");
    for(let step=0;step<3;step++) await page.locator("#timeline-time").press("ArrowRight");
    await expect(bar).toHaveAttribute("data-timestamp",dates[3].timestamp);
    const caption=page.locator(".timeline-caption");
    const before=await caption.boundingBox();
    const controlsBefore=await page.locator(".playback").boundingBox();
    await page.locator("#timeline-time").press("ArrowRight");
    await expect(bar).toHaveAttribute("data-timestamp",dates[3].timestamp);
    await expect(bar).toContainText("previous timestamp retained");
    await expect(caption).toContainText("480 available frames");
    await expect(caption).not.toContainText(/Buffering|Requested:/);
    expect(await caption.boundingBox()).toEqual(before);
    expect(await page.locator(".playback").boundingBox()).toEqual(controlsBefore);
    await page.locator(".bottom-timeline").screenshot({path:`test-results/stable-timeline-${width}.png`});
  }
  release();
  await expect(bar).toHaveAttribute("data-timestamp",dates[4].timestamp);
  await expect(bar).toHaveAttribute("data-min",originalMin!);
  await expect(bar).toHaveAttribute("data-max",originalMax!);
  client.clear();
});

test("timeline still reports a failed batch instead of hiding real errors",async({page})=>{
  const client=new DataClient({baseUrl:"http://127.0.0.1:8000",adapt:adaptBackendResponse});
  const dates=(await client.getDatasets()).datasets.find(d=>d.dataset_id==="incois_bio_roms_v2")!.time_products!;
  await page.goto("/explorer");
  await expect(page.locator(".scientific-colorbar")).toHaveAttribute("data-timestamp",dates[0].timestamp);
  await page.route(`**/backend/api/v1/products/${dates[40].product_id}**`,route=>route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({schema_version:1,error:{code:"backend_unavailable",message:"Unavailable"}})}));
  await page.locator("#dataset-time").selectOption(dates[40].timestamp);
  await expect(page.locator(".bottom-timeline")).toHaveAttribute("data-status","error");
  await expect(page.locator("#timeline-reason")).toContainText("No frame available");
  await expect(page.getByRole("button",{name:"Retry frame",exact:true})).toBeVisible();
  await expect(page.locator(".timeline-caption time")).toHaveText(dates[0].timestamp);
  client.clear();
});

test("source frames crossfade with honest labels and settle after rapid scrubbing",async({page})=>{
  const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
  await page.emulateMedia({reducedMotion:"no-preference"});
  await page.goto("/explorer");
  const bar=page.locator(".scientific-colorbar");
  await expect(bar).toHaveAttribute("data-timestamp","1980-01-24T00:00:00Z");
  const dates=await page.locator("#dataset-time option").evaluateAll(options=>options.map(o=>(o as HTMLOptionElement).value));
  await page.locator("#dataset-time").selectOption(dates[1]);
  await expect(bar).toHaveAttribute("data-transition","blending");
  await expect(bar).toHaveAttribute("data-transition-to",dates[1]);
  await expect(bar).toContainText("display only, not intermediate measurements");
  await expect(bar).toHaveAttribute("data-timestamp",dates[1]);
  await expect(bar).toHaveAttribute("data-transition","idle");
  for(const index of [2,3,4,8,12]) await page.locator("#dataset-time").selectOption(dates[index]);
  await expect(bar).toHaveAttribute("data-timestamp",dates[12]);
  await expect(bar).toHaveAttribute("data-transition","idle");
  await page.locator("#variable").selectOption("SSS");
  await expect(bar).toContainText(/salinity/i);
  await expect(bar).toHaveAttribute("data-transition","idle");
  expect(errors).toEqual([]);
});

test("reduced motion skips source-frame crossfade",async({page})=>{
  await page.emulateMedia({reducedMotion:"reduce"});
  await page.goto("/explorer");
  const bar=page.locator(".scientific-colorbar");
  await expect(bar).toHaveAttribute("data-timestamp","1980-01-24T00:00:00Z");
  await bar.evaluate(element=>{
    element.setAttribute("data-observed-fade","no");
    const observer=new MutationObserver(records=>{
      if(records.some(r=>r.attributeName==="data-transition" && (r.oldValue==="blending" || element.getAttribute("data-transition")==="blending"))) element.setAttribute("data-observed-fade","yes");
    });
    observer.observe(element,{attributes:true,attributeOldValue:true,attributeFilter:["data-transition"]});
  });
  await page.locator("#dataset-time").selectOption({index:1});
  await expect(bar).toHaveAttribute("data-timestamp","1980-02-23T00:00:00Z");
  await expect(bar).toHaveAttribute("data-observed-fade","no");
});

test("all ten BIO-ROMS variables have real globe frames and scientific analysis",async({page})=>{
  test.setTimeout(150000);
  const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
  const client=new DataClient({baseUrl:"http://127.0.0.1:8000",adapt:adaptBackendResponse});
  const dataset=(await client.getDatasets()).datasets.find(d=>d.dataset_id==="incois_bio_roms_v2")!;
  expect(dataset.variables.map(v=>v.name)).toEqual(["SST","SSS","MLD","CHL","DIC","NO3","pCO2_Original","pCO2_Clim","pCO2_Int","Deviant_uncertainty"]);
  await page.goto("/explorer");
  await expect(page.locator("#variable option")).toHaveCount(10);
  for(const variable of dataset.variables) {
    expect(dataset.variable_time_products!.find(v=>v.variable===variable.name)!.times).toHaveLength(480);
    await page.locator("#variable").selectOption(variable.name);
    const bar=page.locator(".scientific-colorbar");
    await expect(bar).toHaveAttribute("data-variable",variable.name);
    await expect(bar.locator("strong")).toContainText(variable.label);
    await expect(bar.locator("strong")).toContainText(variable.units);
    await expect(bar).toHaveAttribute("data-timestamp","1980-01-24T00:00:00Z");
  }
  await page.getByRole("link",{name:/Analysis/}).click();
  for(const variable of dataset.variables) {
    await page.getByLabel("Analysis quantity",{exact:true}).selectOption(variable.name);
    await expect(page.locator(".scientific-plot-shell h2")).toContainText(variable.label);
    await expect(page.locator(".scientific-plot-shell .ytitle")).toHaveText(`${variable.name} (${variable.units})`);
  }
  await page.getByLabel("Analysis quantity",{exact:true}).selectOption("CHL");
  await expect(page.locator(".scientific-plot-shell .ytitle")).toHaveText("CHL (kg/m3)");
  await page.locator(".scientific-plot-shell").screenshot({path:"test-results/bio-roms-chlorophyll.png"});
  await page.getByRole("link",{name:/Explorer/}).click();
  await page.locator("#dataset-time").selectOption("2019-12-25T00:00:00Z");
  await expect(page.locator(".scientific-colorbar")).toHaveAttribute("data-timestamp","2019-12-25T00:00:00Z");
  await page.locator("#variable").selectOption("pCO2_Int");
  await expect(page.locator(".scientific-colorbar")).toHaveAttribute("data-variable","pCO2_Int");
  await expect(page.locator(".scientific-colorbar")).toHaveAttribute("data-timestamp","2019-12-25T00:00:00Z");
  expect(errors).toEqual([]); client.clear();
});

test("variable-specific batch mapping requires the same source checksum and version",()=>{
  const cap={surface:true,timeseries:true};
  const metadata=(name:string,units:string)=>({[name]:{source_name:name,long_name:name,units}});
  const base={product_id:"p_a",dataset_id:"d",status:"ready",data_mode:"real",variables:["SST"],variable_metadata:metadata("SST","deg C"),input_md5:"a".repeat(32),source_version:"v2",times:["1980-01-24T00:00:00Z"],capabilities:cap,region:{west:30,east:120,south:-30,north:30}};
  const products=[base,{...base,product_id:"p_b",variables:["CHL"],variable_metadata:metadata("CHL","kg/m3")},
    {...base,product_id:"p_c",variables:["NO3"],variable_metadata:metadata("NO3","milimole/m3"),input_md5:"b".repeat(32)},
    {...base,product_id:"p_d",variables:["DIC"],variable_metadata:metadata("DIC","milimole/m3"),source_version:"v1"}];
  const adapted=adaptBackendResponse("/api/v1/datasets",{schema_version:1,products,datasets:[{dataset_id:"d",source_id:"s",title:"Fixture",status:"ready",product_ids:products.map(p=>p.product_id)}]}) as {datasets:{variables:{name:string}[];variable_time_products:{variable:string;times:{product_id:string}[]}[]}[]};
  expect(adapted.datasets[0].variables.map(v=>v.name)).toEqual(["SST","CHL"]);
  expect(adapted.datasets[0].variable_time_products.find(v=>v.variable==="CHL")!.times[0].product_id).toBe("p_b");
});

test("analysis metadata and short axis labels fit narrow and wide graph panels",async({page})=>{
  const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
  await page.goto("/analysis");
  const chart=page.locator(".scientific-plot-shell");
  await expect(chart.locator(".js-plotly-plot")).toBeVisible();
  for(const width of [1440,1024,760]) {
    await page.setViewportSize({width,height:1000});
    await expect(chart.locator(".plot-context")).toBeVisible();
    await expect(chart.locator(".ytitle")).toHaveText("SST (deg C)");
    await expect(chart.locator(".gtitle")).toHaveCount(0);
    const context=chart.locator(".plot-context");
    expect(await context.evaluate(e=>e.scrollWidth<=e.clientWidth+1)).toBe(true);
    await chart.scrollIntoViewIfNeeded();
    await chart.screenshot({path:`test-results/analysis-layout-${width}.png`});
  }
  const downloadPromise=page.waitForEvent("download");
  await chart.getByRole("button",{name:"Download PNG",exact:true}).click();
  const download=await downloadPromise;
  expect(await download.failure()).toBeNull();
  await download.saveAs("test-results/analysis-export.png");
  await expect(chart.locator(".gtitle")).toHaveCount(0);
  await expect(chart.getByText("Graph action failed.",{exact:false})).toHaveCount(0);
  expect(errors).toEqual([]);
});
