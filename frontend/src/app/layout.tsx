import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PGIS Body Weight",
  description: "Glucose-aware bodyweight training",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
