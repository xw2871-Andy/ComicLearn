import type { Metadata } from "next";
import { HolacracyWorkspace } from "@/components/holacracy-workspace";

export const metadata: Metadata = {
  title: "Holacracy Executor",
  description:
    "A bilingual circle-based operating workspace for ComicLearn roles, executors, priorities, and teammate stickers."
};

export default function HolacracyPage() {
  return <HolacracyWorkspace />;
}
