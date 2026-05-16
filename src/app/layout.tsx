import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "三分钟热度",
  description: "刷到一个爱好，30 秒看它适不适合你",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#0A0A0F",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="bg-bg text-text font-sans">
        <main className="mx-auto max-w-4xl min-h-screen relative">{children}</main>
      </body>
    </html>
  );
}
