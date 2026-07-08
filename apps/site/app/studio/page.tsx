import type { Metadata } from "next";
import { StudioClient } from "./studio-client";

export const metadata: Metadata = {
  title: "Studio | 创作工作台",
  description:
    "ComicLearn Studio with editable bilingual lesson setup, Claude + Gemini API settings, comic preview, video workflow, and export actions."
};

export default function StudioPage() {
  return <StudioClient />;
}
