import { ImageResponse } from "next/og";
import { site } from "@/lib/site";

export const runtime = "edge";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#fbfaf6",
          padding: "80px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          fontFamily: "Georgia, serif"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 44,
              height: 44,
              background: "#0f172a",
              color: "#fbfaf6",
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 20,
              fontWeight: 700,
              letterSpacing: 1
            }}
          >
            CT
          </div>
          <span style={{ fontSize: 28, fontWeight: 600, color: "#0f172a" }}>
            {site.name}
          </span>
        </div>

        <div>
          <p
            style={{
              fontSize: 22,
              color: "#475569",
              textTransform: "uppercase",
              letterSpacing: 4,
              margin: 0
            }}
          >
            Open-source AI agent for teachers
          </p>
          <h1
            style={{
              fontSize: 96,
              lineHeight: 1.02,
              color: "#0f172a",
              margin: "16px 0 0",
              fontWeight: 600,
              letterSpacing: -2
            }}
          >
            Turn your lessons
            <br />
            into <span style={{ background: "linear-gradient(180deg, transparent 65%, #d97706 65%)" }}>Manga</span>.
          </h1>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            color: "#475569",
            fontSize: 22
          }}
        >
          <span>{site.domain}</span>
          <span>MIT · Self-host in 60s</span>
        </div>
      </div>
    ),
    size
  );
}
