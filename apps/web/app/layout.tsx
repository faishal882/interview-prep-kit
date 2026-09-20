import type { Metadata } from "next";
import { DM_Sans, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";
import { AuthProvider } from "@/lib/auth";
import { AppShell } from "@/components/app-shell";

const dmSans = DM_Sans({ subsets: ["latin"], variable: "--font-body", display: "swap" });
const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-display", display: "swap" });

export const metadata: Metadata = { title: "Interview Prep Kit" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${dmSans.variable} ${jakarta.variable}`}>
      <body className="kit-body">
        <QueryProvider>
          <AuthProvider>
            <AppShell>{children}</AppShell>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}

export function generateStaticParams() {
  return [];
}
