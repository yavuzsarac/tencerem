import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Tencerem | Bugün ne pişirsek?", description: "Sofranıza, vaktinize ve bütçenize uygun yemek planlamanın ilk adımı." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="tr"><body>{children}</body></html>;
}
