import type { ReactNode } from "react";

import { SearchStoreProvider } from "../components/search-store";
import { Shell } from "../components/shell";
import "./globals.css";

export const metadata = {
  title: "LetterOps Console",
  description: "Dashboard, review, and graph views for evidence-first retrieval."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <SearchStoreProvider>
          <Shell>{children}</Shell>
        </SearchStoreProvider>
      </body>
    </html>
  );
}
