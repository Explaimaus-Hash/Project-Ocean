import { WorkspacePanel } from "@/features/WorkspacePanel";
import { routes } from "@/lib/routes";
export const metadata = { title: "Explorer" };
export default function Page() {
  return <WorkspacePanel route={routes[0]} />;
}
