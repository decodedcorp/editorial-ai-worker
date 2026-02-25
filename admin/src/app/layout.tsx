import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Editorial Admin",
  description: "Editorial AI content management dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen bg-background`}
      >
        <header className="border-b">
          <div className="container mx-auto flex h-14 items-center px-6">
            <h1 className="text-lg font-semibold">Editorial Admin</h1>
          </div>
        </header>
        <main className="container mx-auto px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
