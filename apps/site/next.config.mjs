import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = dirname(fileURLToPath(import.meta.url));
const rawStudioOrigin =
  process.env.STUDIO_ORIGIN ??
  process.env.NEXT_PUBLIC_STUDIO_URL ??
  "https://whose-attributes-park-twice.trycloudflare.com";
const studioOrigin = rawStudioOrigin.replace(/\/+$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  turbopack: {
    root: projectRoot
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
      { protocol: "https", hostname: "img.shields.io" }
    ]
  },
  async rewrites() {
    return {
      beforeFiles: [
        { source: "/studio", destination: `${studioOrigin}/` },
        { source: "/studio/:path*", destination: `${studioOrigin}/:path*` },
        { source: "/api/:path*", destination: `${studioOrigin}/api/:path*` },
        { source: "/static/:path*", destination: `${studioOrigin}/static/:path*` },
        { source: "/assets/:path*", destination: `${studioOrigin}/assets/:path*` }
      ]
    };
  }
};

export default nextConfig;
