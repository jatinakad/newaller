import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AllerSense — AI-Powered Allergy Prevention',
  description: 'AI-powered patient allergy prevention system with Gemini AI analysis',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  )
}