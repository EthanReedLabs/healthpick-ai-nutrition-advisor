import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HealthPick · 营养知识助手",
  description: "基于指定资料、可追溯引用的营养知识问答工作台",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
