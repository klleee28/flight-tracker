import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AeroSplit AI - Automated Flight Tracking & Asian Hub Split-Route Calculator",
  description: "Find cheap split-route flights through Asian transit hubs like Kuala Lumpur, Singapore, Tokyo, Taipei, and Manila with dynamic 60-day moving average deal scores.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased dark`}
    >
      <body suppressHydrationWarning className="min-h-full flex flex-col bg-slate-950 text-slate-100 font-sans text-base leading-relaxed">{children}</body>
    </html>
  );
}
