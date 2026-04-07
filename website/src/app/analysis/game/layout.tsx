import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Game Analysis — ChessNext.ai",
  description:
    "Analyze your chess games with root-cause analysis. Discover not just where you went wrong, but why. Powered by Leela Chess Zero concepts.",
  openGraph: {
    title: "Game Analysis — ChessNext.ai",
    description:
      "Analyze your chess games with root-cause analysis. Discover not just where you went wrong, but why.",
  },
};

export default function GameAnalysisLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
