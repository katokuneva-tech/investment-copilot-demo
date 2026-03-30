import type { NextConfig } from "next";

const isExport = process.env.STATIC_EXPORT === "true";

const nextConfig: NextConfig = {
  images: { unoptimized: true },
  ...(isExport
    ? { output: "export" }
    : {
        async rewrites() {
          const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
          return [
            {
              source: "/api/:path*",
              destination: `${backendUrl}/api/:path*`,
            },
          ];
        },
      }),
};

export default nextConfig;
