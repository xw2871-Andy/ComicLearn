import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    container: {
      center: true,
      padding: { DEFAULT: "1.25rem", lg: "2rem" },
      screens: { "2xl": "1200px" }
    },
    extend: {
      colors: {
        // Whitepaper palette: cream paper + indigo ink.
        paper:  "#fbfaf6",       // background
        cream:  "#f4f1e8",       // sectioned background
        ink:    "#0f172a",       // primary text (slate-900-ish)
        muted:  "#475569",       // secondary text
        rule:   "#e7e2d3",       // subtle dividers
        indigo: {
          50:  "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",          // primary action
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81"
        },
        accent: "#d97706"        // amber-600 for highlights / underlines
      },
      fontFamily: {
        sans:   ['"Inter"', "ui-sans-serif", "system-ui", "sans-serif"],
        serif:  ['"Source Serif 4"', '"Iowan Old Style"', "Georgia", "serif"],
        mono:   ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"]
      },
      fontSize: {
        // Tighter, paper-like rhythm.
        "display": ["clamp(2.25rem, 1.4rem + 3.6vw, 4.25rem)", { lineHeight: "1.04", letterSpacing: "-0.02em", fontWeight: "600" }],
        "h1":      ["clamp(1.875rem, 1.2rem + 2vw, 2.75rem)",   { lineHeight: "1.1",  letterSpacing: "-0.015em", fontWeight: "600" }],
        "h2":      ["clamp(1.5rem, 1.1rem + 1.2vw, 2rem)",       { lineHeight: "1.15", letterSpacing: "-0.01em",  fontWeight: "600" }],
        "lead":    ["1.125rem", { lineHeight: "1.65" }]
      },
      boxShadow: {
        paper: "0 1px 0 rgba(15,23,42,0.04), 0 12px 32px -16px rgba(15,23,42,0.18)",
        chip:  "0 1px 0 rgba(15,23,42,0.06) inset, 0 1px 1px rgba(15,23,42,0.04)"
      },
      borderRadius: {
        paper: "14px"
      },
      backgroundImage: {
        "rule-dotted":
          "radial-gradient(circle at 1px 1px, rgba(15,23,42,0.18) 1px, transparent 0)"
      },
      maxWidth: {
        prose: "68ch"
      }
    }
  },
  plugins: []
};

export default config;
