export interface CatalogVariable {
  name: string;
  label?: string;
  units: string;
}

export interface CatalogDataSource {
  id: string;
  sourceFamily: "incois_bio_roms" | "incois_godas" | "copernicus" | "argo" | "ifremer_glider";
  name: string;
  role: "model" | "observation";
  roleLabel: string;
  provider: string;
  originUrl: string;
  domain: string;
  timeCoverage: string;
  resolution: string;
  accessMethod: string;
  description: string;
  variables: CatalogVariable[];
  editions?: string[];
  actionLink?: {
    href: string;
    label: string;
  };
}

export const REGISTERED_DATA_SOURCES: CatalogDataSource[] = [
  {
    id: "incois_bio_roms_v2",
    sourceFamily: "incois_bio_roms",
    name: "INCOIS BIO-ROMS V2",
    role: "model",
    roleLabel: "Surface Model",
    provider: "INCOIS (Indian National Centre for Ocean Information Services)",
    originUrl: "https://zenodo.org/records/14614739",
    domain: "30°E–120°E · 30°S–30°N",
    timeCoverage: "1980–2019 · 480 timestamps",
    resolution: "1/12° (~9 km) · Surface",
    accessMethod: "Local NetCDF4 Archive",
    description:
      "High-resolution biogeochemical and physical numerical simulation of the Indian Ocean, providing monthly surface carbon, nutrient, and hydrographic fields with verified cell-centre coordinates.",
    variables: [
      { name: "SST", label: "Sea Surface Temperature", units: "deg C" },
      { name: "SSS", label: "Sea Surface Salinity", units: "PSU" },
      { name: "MLD", label: "Mixed Layer Depth", units: "m" },
      { name: "CHL", label: "Chlorophyll-a", units: "mg/m³" },
      { name: "DIC", label: "Dissolved Inorganic Carbon", units: "mmol/m³" },
      { name: "NO3", label: "Nitrate Concentration", units: "mmol/m³" },
      { name: "pCO2_Original", label: "Surface Ocean pCO₂", units: "µatm" },
      { name: "pCO2_Clim", label: "Climatological pCO₂", units: "µatm" },
      { name: "pCO2_Int", label: "Interpolated pCO₂", units: "µatm" },
      { name: "Deviant_uncertainty", label: "Surface Uncertainty", units: "µatm" },
    ],
    actionLink: {
      href: "/explorer",
      label: "Explore Globe",
    },
  },
  {
    id: "incois_godas",
    sourceFamily: "incois_godas",
    name: "INCOIS GODAS Reanalysis",
    role: "model",
    roleLabel: "Ocean Reanalysis",
    provider: "INCOIS / MoES (Ministry of Earth Sciences, India)",
    originUrl: "https://las.incois.gov.in/thredds/catalog.html",
    domain: "Tropical Indian Ocean & Global",
    timeCoverage: "2022–2025 Multi-Year Series",
    resolution: "Multi-Level · 1/4° to 1/2° Grid",
    accessMethod: "OPeNDAP / THREDDS LAS",
    description:
      "Operational Global Ocean Data Assimilation System reanalysis assimilating temperature and salinity profiles to provide 3D thermohaline structure, horizontal velocity, and dynamic sea surface height.",
    editions: ["2025", "2024", "2023", "2022"],
    variables: [
      { name: "temp", label: "Potential Ocean Temperature", units: "°C" },
      { name: "salt", label: "Practical Salinity", units: "PSU" },
      { name: "u / v", label: "Zonal & Meridional Currents", units: "m/s" },
      { name: "ssh", label: "Sea Surface Height", units: "m" },
    ],
  },
  {
    id: "copernicus_global_multiyear_phy",
    sourceFamily: "copernicus",
    name: "Copernicus GLOBAL_MULTIYEAR_PHY_001_030",
    role: "model",
    roleLabel: "Physical Model",
    provider: "Copernicus Marine Service (Mercator Ocean International)",
    originUrl:
      "https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/description",
    domain: "30°E–120°E · 30°S–30°N",
    timeCoverage: "1993–Present · Physics Archive",
    resolution: "1/12° (~9 km) Tri-Polar Grid",
    accessMethod: "Copernicus Marine Toolbox",
    description:
      "High-resolution numerical physical ocean reanalysis providing potential temperature, practical salinity, and velocity fields utilized in Project Ocean exploratory model–observation comparison.",
    variables: [
      { name: "thetao", label: "Sea Water Potential Temperature", units: "°C" },
      { name: "so", label: "Sea Water Practical Salinity", units: "PSU" },
      { name: "uo / vo", label: "Horizontal Ocean Currents", units: "m/s" },
      { name: "zos", label: "Sea Surface Height Above Geoid", units: "m" },
      { name: "mlotst", label: "Ocean Mixed Layer Thickness", units: "m" },
    ],
    actionLink: {
      href: "/comparison",
      label: "View Comparison",
    },
  },
  {
    id: "argo_gdac",
    sourceFamily: "argo",
    name: "Official Argo GDAC Float Observations",
    role: "observation",
    roleLabel: "Profiling Floats",
    provider: "Argo Global Data Assembly Centre (GDAC) / Ifremer",
    originUrl: "https://argo.ucsd.edu",
    domain: "30°E–120°E · 30°S–30°N",
    timeCoverage: "10-day Profiling Cycles",
    resolution: "0–2000 dbar Point Profiles",
    accessMethod: "Argopy Client / GDAC FTP",
    description:
      "Worldwide fleet of autonomous robotic profiling floats collecting temperature and salinity profiles down to 2,000 dbar, with rigorous real-time and delayed-mode quality control flags.",
    variables: [
      { name: "PRES", label: "Sea Pressure (raw & adjusted)", units: "dbar" },
      { name: "TEMP", label: "In-Situ Temperature (ITS-90)", units: "°C" },
      { name: "PSAL", label: "Practical Salinity (PSS-78)", units: "PSU" },
    ],
    actionLink: {
      href: "/profiles",
      label: "View Profiles",
    },
  },
  {
    id: "ifremer_glider_v2",
    sourceFamily: "ifremer_glider",
    name: "IFREMER EGO Autonomous Ocean Gliders",
    role: "observation",
    roleLabel: "Ocean Gliders",
    provider: "IFREMER / European Gliding Observatories (EGO)",
    originUrl: "https://www.ego-network.org",
    domain: "Indian Ocean / Mission Transects",
    timeCoverage: "Mission-Specific Deployments",
    resolution: "0–1000 m Saw-Tooth Transects",
    accessMethod: "EGO Glider FTP / NetCDF4",
    description:
      "Buoyancy-driven autonomous underwater gliders measuring high-resolution vertical sections of temperature and salinity along complex oceanographic transects with GPS trajectory tracking.",
    variables: [
      { name: "TEMP", label: "High-Resolution Temperature", units: "°C" },
      { name: "PSAL", label: "High-Resolution Practical Salinity", units: "PSU" },
      { name: "PRES", label: "Sensor Depth & Pressure", units: "dbar" },
      { name: "GPS", label: "Coordinates & Timestamps", units: "deg / UTC" },
    ],
  },
];

export interface CatalogAcquisition {
  acquisitionId: string;
  sourceFamily: "copernicus" | "argo" | "ifremer_glider" | "incois_godas" | "incois_bio_roms" | "other";
  displayName: string;
  category: string;
  role: string;
  summary: string;
  scope: string;
  pipeline: string;
  format: string;
  variables: string[];
  originDomain: string;
  originUrl: string;
}

export const KNOWN_ACQUISITIONS: Record<string, CatalogAcquisition> = {
  a_9e918d43555ffc26d3659e08: {
    acquisitionId: "a_9e918d43555ffc26d3659e08",
    sourceFamily: "copernicus",
    displayName: "Copernicus Marine PHY",
    category: "Physical Ocean Model",
    role: "Model Comparison Subset",
    summary:
      "Physical ocean model selection (thetao, so, uo, vo) acquired via official Copernicus Marine Toolbox for exploratory model–observation comparison across the equatorial Indian Ocean.",
    scope: "65°E–66°E, 1°S–0°N · Daily 2019-01-29",
    pipeline: "Copernicus Marine Toolbox API (v2.4.1)",
    format: "NetCDF-4 · 54.8 KB",
    variables: ["thetao", "so", "uo", "vo"],
    originDomain: "data.marine.copernicus.eu",
    originUrl:
      "https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/description",
  },
  a_d30181bd8998aca81bb33be1: {
    acquisitionId: "a_d30181bd8998aca81bb33be1",
    sourceFamily: "argo",
    displayName: "Argo Global GDAC",
    category: "Profiling Floats (GDAC)",
    role: "In-Situ Observation Samples",
    summary:
      "Official in-situ float observations accessed through Argopy; 14 preserved local Indian Ocean point samples with dual raw and adjusted QC flags evaluated for exploratory comparison.",
    scope: "14 point samples · 65°–75°E, 5°S–5°N",
    pipeline: "Argopy pipeline via IFREMER ERDDAP",
    format: "NetCDF-4 · 62.6 KB",
    variables: ["PRES", "TEMP", "PSAL"],
    originDomain: "ftp.ifremer.fr/ifremer/argo",
    originUrl: "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats",
  },
  a_9cbe844e66f3fbb520b0d235: {
    acquisitionId: "a_9cbe844e66f3fbb520b0d235",
    sourceFamily: "ifremer_glider",
    displayName: "IFREMER Gliders (EGO)",
    category: "Ocean Glider Mission",
    role: "Preserved Mission NetCDF",
    summary:
      "Bella autonomous underwater glider mission transect dataset preserved from European Gliding Observatories archive. Preserved local input pending sensor time/QC reconciliation.",
    scope: "Bella mission transect (Bella_626_R.nc)",
    pipeline: "EGO Glider FTP (Python standard client)",
    format: "NetCDF-4 · 45.3 MB",
    variables: ["Trajectory", "Sensor CTD", "NetCDF-4"],
    originDomain: "ftp.ifremer.fr/ifremer/glider",
    originUrl: "ftp://ftp.ifremer.fr/ifremer/glider/v2/",
  },
};

export function getAcquisitionDisplayData(acq: {
  acquisition_id: string;
  source_name: string;
  provenance?: string;
  status?: string;
}): CatalogAcquisition {
  const known = KNOWN_ACQUISITIONS[acq.acquisition_id];
  if (known) return known;

  // Fallback for any unknown / dynamic acquisition
  const src = (acq.source_name || "").toLowerCase();
  let family: CatalogAcquisition["sourceFamily"] = "other";
  if (src.includes("copernicus")) family = "copernicus";
  else if (src.includes("argo")) family = "argo";
  else if (src.includes("glider")) family = "ifremer_glider";
  else if (src.includes("godas")) family = "incois_godas";
  else if (src.includes("bio_roms")) family = "incois_bio_roms";

  let summary = "Preserved local source input acquired for Project Ocean exploration.";
  let originDomain = "Local Archive";
  let originUrl = "#";

  if (acq.provenance) {
    const parts = acq.provenance
      .split(";")
      .map((p) => p.trim())
      .filter(Boolean);
    const urlPart = parts.find(
      (p) =>
        p.startsWith("http://") ||
        p.startsWith("https://") ||
        p.startsWith("ftp://"),
    );
    if (urlPart) {
      originUrl = urlPart;
      try {
        const u = new URL(urlPart);
        originDomain = u.hostname;
      } catch {
        originDomain =
          urlPart.replace(/^(https?|ftp):\/\//, "").split("/")[0] ||
          "Remote Provider";
      }
    }

    const descParts = parts.filter(
      (p) =>
        !p.startsWith("http") &&
        !p.startsWith("ftp") &&
        !p.includes("parallel=") &&
        !p.includes("errors=") &&
        !p.includes("Argopy renames") &&
        !p.includes("VLEN strings") &&
        !p.includes("acquired input, not a served") &&
        !p.includes("acquired_not_prepared") &&
        !p.includes("not_prepared"),
    );
    if (descParts.length > 0) {
      summary = descParts.join(". ");
    }
  }

  return {
    acquisitionId: acq.acquisition_id,
    sourceFamily: family,
    displayName: (acq.source_name || "Preserved Source").toUpperCase().replace(/_/g, " "),
    category: "Preserved Acquisition",
    role: "Local Source Input",
    summary,
    scope: "Preserved Local Input",
    pipeline: "Standard Acquisition Pipeline",
    format: "NetCDF Archive",
    variables: [],
    originDomain,
    originUrl,
  };
}
