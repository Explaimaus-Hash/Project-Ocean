import { DataSourcesPanel } from "@/features/data-sources/DataSourcesPanel";

export const metadata = {
  title: "Data Sources",
  description:
    "Unified registry of numerical ocean models, physical reanalyses, and autonomous in-situ observation platforms.",
};

export default function Page() {
  return (
    <div className="comparison-workspace data-sources-workspace">
      <DataSourcesPanel />
    </div>
  );
}
