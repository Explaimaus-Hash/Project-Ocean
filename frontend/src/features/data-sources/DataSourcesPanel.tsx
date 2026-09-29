"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Waves,
  Layers,
  Compass,
  Radio,
  Send,
  MapPin,
  Calendar,
  Clock,
  Sliders,
  Server,
  Search,
  ArrowRight,
  ArrowUpRight,
  Database,
  Globe2,
} from "lucide-react";
import { useData, ApiState } from "./DataProvider";
import {
  REGISTERED_DATA_SOURCES,
  type CatalogDataSource,
  type CatalogVariable,
  getAcquisitionDisplayData,
  KNOWN_ACQUISITIONS,
} from "./dataSourcesCatalog";

export function DataSourcesPanel() {
  const d = useData();
  const [filterRole, setFilterRole] = useState<"all" | "model" | "observation">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Merge live backend data when available
  const enrichedSources = useMemo<CatalogDataSource[]>(() => {
    return REGISTERED_DATA_SOURCES.map((source) => {
      if (source.id === "incois_bio_roms_v2") {
        const liveDataset = d.catalogue.value?.datasets.find(
          (item) => item.dataset_id === "incois_bio_roms_v2",
        );
        const liveVars = liveDataset?.variables;
        if (liveVars && liveVars.length > 0) {
          return {
            ...source,
            variables: liveVars.map(
              (v): CatalogVariable => ({
                name: v.name,
                label: v.label,
                units: v.units,
              }),
            ),
          };
        }
      }

      if (source.id === "argo_gdac") {
        const argoCollection = d.observations.value?.collections.find(
          (c) => c.source === "argo",
        );
        if (argoCollection?.variables && argoCollection.variables.length > 0) {
          return {
            ...source,
            variables: argoCollection.variables.map(
              (v): CatalogVariable => ({
                name: v.name,
                label: v.label,
                units: v.units,
              }),
            ),
          };
        }
      }

      return source;
    });
  }, [d.catalogue.value, d.observations.value]);

  const filteredSources = useMemo(() => {
    return enrichedSources.filter((source) => {
      if (filterRole !== "all" && source.role !== filterRole) {
        return false;
      }
      if (!searchQuery.trim()) {
        return true;
      }
      const q = searchQuery.toLowerCase();
      const matchName = source.name.toLowerCase().includes(q);
      const matchDesc = source.description.toLowerCase().includes(q);
      const matchProvider = source.provider.toLowerCase().includes(q);
      const matchDomain = source.domain.toLowerCase().includes(q);
      const matchVar = source.variables.some(
        (v) =>
          v.name.toLowerCase().includes(q) ||
          (v.label && v.label.toLowerCase().includes(q)) ||
          v.units.toLowerCase().includes(q),
      );
      return matchName || matchDesc || matchProvider || matchDomain || matchVar;
    });
  }, [enrichedSources, filterRole, searchQuery]);

  const getSourceIcon = (family: string) => {
    switch (family) {
      case "incois_bio_roms":
        return <Waves size={22} />;
      case "incois_godas":
        return <Layers size={22} />;
      case "copernicus":
        return <Compass size={22} />;
      case "argo":
        return <Radio size={22} />;
      case "ifremer_glider":
        return <Send size={22} />;
      default:
        return <Database size={22} />;
    }
  };

  return (
    <section aria-label="Source families" className="data-sources-container">
      <header className="data-sources-header">
        <span className="eyebrow">PROJECT OCEAN / DATA REGISTRY</span>
        <h1>Data Sources</h1>
        <p className="data-sources-subtitle">
          Unified registry of numerical models, physical reanalyses, and autonomous in-situ observation platforms across the Indian Ocean basin.
        </p>
      </header>

      {/* System Status Banner */}
      <div className="data-sources-status-banner" role="status">
        <div className="data-sources-status-left">
          <div className="status-dot-pulse" aria-hidden="true" />
          <div>
            <div className="status-text-title">Live Local Backend Connected</div>
            <div className="status-text-desc">
              Data is read from your FastAPI backend. Real source metadata, verified cell coordinates, and authentic observation samples are preserved without demo substitution.
            </div>
          </div>
        </div>
      </div>

      <ApiState error={d.catalogue.error} />

      {/* Overview Stats Ribbon */}
      <div className="data-sources-stats-ribbon">
        <div className="data-source-stat-card">
          <div className="stat-icon-wrapper">
            <Database size={18} />
          </div>
          <div>
            <div className="stat-value">{REGISTERED_DATA_SOURCES.length} Ocean Datasets</div>
            <div className="stat-label">Numerical models & in-situ arrays</div>
          </div>
        </div>

        <div className="data-source-stat-card">
          <div className="stat-icon-wrapper">
            <Globe2 size={18} />
          </div>
          <div>
            <div className="stat-value">30°E–120°E · 30°S–30°N</div>
            <div className="stat-label">Common comparison basin</div>
          </div>
        </div>

        <div className="data-source-stat-card">
          <div className="stat-icon-wrapper">
            <Calendar size={18} />
          </div>
          <div>
            <div className="stat-value">480 Model Timestamps</div>
            <div className="stat-label">1980–2019 surface series</div>
          </div>
        </div>

        <div className="data-source-stat-card">
          <div className="stat-icon-wrapper">
            <Radio size={18} />
          </div>
          <div>
            <div className="stat-value">Autonomous In-Situ</div>
            <div className="stat-label">Argo profiling floats & EGO gliders</div>
          </div>
        </div>
      </div>

      {/* Interactive Controls Bar */}
      <div className="data-sources-controls">
        <div className="filter-pills" role="tablist" aria-label="Filter data sources by category">
          <button
            type="button"
            role="tab"
            aria-selected={filterRole === "all"}
            className={`filter-pill-button ${filterRole === "all" ? "active" : ""}`}
            onClick={() => setFilterRole("all")}
          >
            All Sources ({enrichedSources.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={filterRole === "model"}
            className={`filter-pill-button ${filterRole === "model" ? "active" : ""}`}
            onClick={() => setFilterRole("model")}
          >
            Numerical Models ({enrichedSources.filter((s) => s.role === "model").length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={filterRole === "observation"}
            className={`filter-pill-button ${filterRole === "observation" ? "active" : ""}`}
            onClick={() => setFilterRole("observation")}
          >
            In-Situ Observations ({enrichedSources.filter((s) => s.role === "observation").length})
          </button>
        </div>

        <div className="search-box-wrapper">
          <Search size={15} className="search-box-icon" aria-hidden="true" />
          <input
            type="text"
            placeholder="Filter by variable, source, or provider…"
            aria-label="Filter data sources"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Sources Grid */}
      <div className="data-sources-grid">
        {filteredSources.map((source) => (
          <article key={source.id} className="data-source-card">
            <div className="card-top-row">
              <div className={`card-source-icon ${source.role}`}>
                {getSourceIcon(source.sourceFamily)}
              </div>
              <div className="card-header-body">
                <div className="card-meta-line">
                  <span className={`badge-pill ${source.role}`}>{source.roleLabel}</span>
                  <span className="card-provider-text">{source.provider}</span>
                </div>
                <h3>{source.name}</h3>
              </div>
            </div>

            <p className="card-description">{source.description}</p>

            {/* Key Metrics Grid */}
            <div className="card-metrics-grid">
              <div className="metric-item">
                <span className="metric-key">
                  <MapPin size={11} /> Domain
                </span>
                <span className="metric-val" title={source.domain}>
                  {source.domain}
                </span>
              </div>

              <div className="metric-item">
                <span className="metric-key">
                  <Clock size={11} /> Time Span
                </span>
                <span className="metric-val" title={source.timeCoverage}>
                  {source.timeCoverage}
                </span>
              </div>

              <div className="metric-item">
                <span className="metric-key">
                  <Sliders size={11} /> Resolution
                </span>
                <span className="metric-val" title={source.resolution}>
                  {source.resolution}
                </span>
              </div>

              <div className="metric-item">
                <span className="metric-key">
                  <Server size={11} /> Access
                </span>
                <span className="metric-val" title={source.accessMethod}>
                  {source.accessMethod}
                </span>
              </div>
            </div>

            {/* Variables / Parameters */}
            <div className="card-variables-section">
              <div className="variables-title">
                <span>Key Variables & Parameters</span>
                <span className="variables-count">{source.variables.length} parameters</span>
              </div>
              <div className="variables-chips-wrap">
                {source.variables.map((variable) => (
                  <span
                    key={variable.name}
                    className="var-chip"
                    title={variable.label ? `${variable.label} (${variable.units})` : variable.name}
                  >
                    <span className="var-name">{variable.name}</span>
                    <span className="var-unit">({variable.units})</span>
                  </span>
                ))}
              </div>

              {source.editions && (
                <div style={{ marginTop: "12px" }}>
                  <div className="variables-title">
                    <span>Available Operational Series</span>
                  </div>
                  <div className="editions-chips-wrap">
                    {source.editions.map((ed) => (
                      <span key={ed} className="edition-pill">
                        {ed} Series
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Card Footer Actions */}
            <div className="card-footer-actions">
              {source.actionLink ? (
                <Link href={source.actionLink.href} className="action-link-btn">
                  {source.actionLink.label} <ArrowRight size={13} />
                </Link>
              ) : (
                <span />
              )}
              <a
                href={source.originUrl}
                target="_blank"
                rel="noreferrer"
                className="external-ref-link"
              >
                Documentation <ArrowUpRight size={12} />
              </a>
            </div>
          </article>
        ))}
      </div>

      {/* Acquisitions Section */}
      <section className="acquisitions-section" aria-label="Acquisitions">
        <h2>Acquisitions</h2>
        <p className="acquisitions-subtitle">
          Preserved local inputs and operator ingestion pipelines for models, profiling floats, and underwater gliders.
        </p>

        <ApiState error={d.acquisitions.error} />

        <div className="acquisitions-grid">
          {(d.acquisitions.value?.acquisitions && d.acquisitions.value.acquisitions.length > 0
            ? d.acquisitions.value.acquisitions.map((raw) => getAcquisitionDisplayData(raw))
            : Object.values(KNOWN_ACQUISITIONS)
          ).map((acq) => (
            <article key={acq.acquisitionId} className="acquisition-card">
              <div className="acquisition-top">
                <div className="acquisition-title-group">
                  <span className="acquisition-category-tag">{acq.category}</span>
                  <h3 className="acquisition-source-name">{acq.displayName}</h3>
                </div>
                <span
                  className="acquisition-id-pill"
                  title={`Preserved Acquisition ID: ${acq.acquisitionId}`}
                >
                  {acq.acquisitionId}
                </span>
              </div>

              <p className="acquisition-summary">{acq.summary}</p>

              <div className="acquisition-meta-grid">
                <div className="acquisition-meta-item">
                  <span className="acquisition-meta-label">Scope &amp; Coverage</span>
                  <span className="acquisition-meta-val">{acq.scope}</span>
                </div>
                <div className="acquisition-meta-item">
                  <span className="acquisition-meta-label">Ingestion Pipeline</span>
                  <span className="acquisition-meta-val">{acq.pipeline}</span>
                </div>
                <div className="acquisition-meta-item">
                  <span className="acquisition-meta-label">Preserved Format</span>
                  <span className="acquisition-meta-val">{acq.format}</span>
                </div>
                <div className="acquisition-meta-item">
                  <span className="acquisition-meta-label">Origin Reference</span>
                  <a
                    href={acq.originUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="acquisition-meta-link"
                  >
                    <span>{acq.originDomain}</span>
                    <ArrowUpRight size={11} />
                  </a>
                </div>
              </div>

              {acq.variables.length > 0 && (
                <div className="acquisition-tags-row">
                  <span className="acquisition-tags-label">Preserved Fields:</span>
                  <div className="acquisition-tags">
                    {acq.variables.map((tag) => (
                      <span key={tag} className="acquisition-tag">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
