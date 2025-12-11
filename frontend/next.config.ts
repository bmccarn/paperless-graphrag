import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable static export for Docker deployment
  output: "export",

  // Disable image optimization (not supported in static export)
  images: {
    unoptimized: true,
  },

  // Trailing slashes for better nginx compatibility
  trailingSlash: true,
};

export default nextConfig;
