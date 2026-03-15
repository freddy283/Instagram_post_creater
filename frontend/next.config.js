/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,   // removes the "N" dev toolbar button
}

module.exports = nextConfig

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
}

module.exports = nextConfig
```

**2. Missing environment variable during build** — add to Vercel env vars:
```
NEXT_PUBLIC_API_URL=https://instagram-post-creater.onrender.com