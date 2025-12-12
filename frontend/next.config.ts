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

  // Exclude Three.js and related packages from server-side bundling
  // These packages require browser APIs (WebGL) and cannot be evaluated during SSR
  serverExternalPackages: [
    'three',
    'react-force-graph-3d',
    'react-force-graph-2d',
    '3d-force-graph',
    'three-spritetext',
  ],

  // Custom webpack configuration for Three.js compatibility
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // Ensure Three.js and related packages are in separate chunks
      // that only load when actually needed
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          ...config.optimization?.splitChunks,
          cacheGroups: {
            ...((config.optimization?.splitChunks as any)?.cacheGroups || {}),
            // Put Three.js in its own chunk
            three: {
              test: /[\\/]node_modules[\\/](three|3d-force-graph|three-spritetext|three-forcegraph|three-render-objects)[\\/]/,
              name: 'three-vendor',
              chunks: 'async', // Only load asynchronously
              priority: 20,
            },
            // Put force-graph in its own chunk
            forceGraph: {
              test: /[\\/]node_modules[\\/]react-force-graph/,
              name: 'force-graph-vendor',
              chunks: 'async',
              priority: 20,
            },
          },
        },
      };
    }
    return config;
  },
};

export default nextConfig;
