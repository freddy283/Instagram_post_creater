'use client'
import './globals.css'
import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/lib/theme'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [qc] = useState(() => new QueryClient({
    defaultOptions: { queries: { retry: 1, staleTime: 30000 } },
  }))
  return (
    <html lang="en" data-theme="dark">
      <head>
        <title>Aureus — Daily Video Automation</title>
        <meta name="description" content="Generate beautiful daily motivational videos and post to Instagram automatically." />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet" />
      </head>
      <body>
        <ThemeProvider>
          <QueryClientProvider client={qc}>{children}</QueryClientProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
