"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Globe2,
  ChartNoAxesCombined,
  ChartNoAxesGantt,
  Columns2,
  Database,
  Anchor,
} from "lucide-react";
import { routes } from "@/lib/routes";
const icons = {
  globe: Globe2,
  chart: ChartNoAxesCombined,
  profiles: ChartNoAxesGantt,
  compare: Columns2,
  database: Database,
};
export function NavigationRail() {
  const pathname = usePathname();
  return (
    <nav className="navigation-rail" aria-label="Main navigation">
      {routes.map((route) => {
        const Icon = icons[route.icon];
        return (
          <Link
            key={route.href}
            href={route.href}
            className={pathname === route.href ? "nav-item active" : "nav-item"}
            aria-current={pathname === route.href ? "page" : undefined}
            title={route.label}
          >
            <Icon size={21} aria-hidden="true" />
            <span>{route.label}</span>
          </Link>
        );
      })}
      <div className="rail-footer" aria-hidden="true">
        <Anchor size={20} />
        <span>OCEAN / 01</span>
      </div>
    </nav>
  );
}
