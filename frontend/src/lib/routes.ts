export const routes = [
  {
    href: "/explorer",
    label: "Explorer",
    description: "Your ocean workspace",
    icon: "globe",
  },
  {
    href: "/analysis",
    label: "Analysis",
    description: "Explore patterns in the data",
    icon: "chart",
  },
  {
    href: "/profiles",
    label: "Profiles",
    description: "Look beneath the surface",
    icon: "profiles",
  },
  {
    href: "/comparison",
    label: "Comparison",
    description: "Bring models and observations together",
    icon: "compare",
  },
  {
    href: "/data-sources",
    label: "Data Sources",
    description: "Understand the origins of your data",
    icon: "database",
  },
] as const;
export type WorkspaceRoute = (typeof routes)[number];
