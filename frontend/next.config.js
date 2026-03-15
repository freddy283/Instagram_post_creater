/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  eslint: {
    ignoreDuringBuilds: true,   // don't fail build on ESLint warnings
  },
  typescript: {
    ignoreBuildErrors: true,    // don't fail build on TS type errors
  },
  output: 'standalone',        // optimised for containerised deployment
}

module.exports = nextConfig