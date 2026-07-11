import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Personal Learning OS",
  description:
    "Личная система глубокого обучения: материалы, карта концепций, повторение и AI-наставник.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
