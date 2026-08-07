import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import { THEME_BOOT_SCRIPT } from "@/lib/theme-store";
import { assetPath } from "@/lib/paths";
import "./globals.css";

const manrope = Manrope({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "NOVARIS Q-SHIELD — Risk Intelligence Console",
  description: "Market stress and cash-hedge workflow evidence console",
  icons: { icon: assetPath("/novaris-mark.png"), apple: assetPath("/novaris-mark.png") },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className={`${manrope.variable} h-full antialiased`}>
      <body className="min-h-full" data-theme="light">
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
        {children}
      </body>
    </html>
  );
}
