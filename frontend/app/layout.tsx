import type { Metadata } from "next";
import "./globals.css";
import {AccountProvider} from "../components/account-provider";
export const metadata: Metadata = { title: "Tencerem | Bugün ne yesem?", description: "Ne yiyeceğini düşünme. Tencerem düşünsün. Katalogdan yemek seç, evdeki malzemelerini değerlendir." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="tr"><body><AccountProvider>{children}</AccountProvider></body></html>;
}
