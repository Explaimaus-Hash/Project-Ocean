import type { Metadata } from "next";
import "cesium/Build/Cesium/Widgets/widgets.css";
import "./tokens.css";
import "./globals.css";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
export const metadata: Metadata = {
  title: { default: "Project Ocean", template: "%s · Project Ocean" },
  description:
    "A scientific ocean workspace. Part 1: geographic context and shared selection.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <WorkspaceShell>{children}</WorkspaceShell>
      </body>
    </html>
  );
}
