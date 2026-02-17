import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'MedGuard — Medicine Allergy Detection',
  description: 'Prevent allergic reactions by checking prescriptions against patient allergy profiles',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  )
}