import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vagus Graph",
  description: "Closed-loop physiology dashboard for task selection.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
