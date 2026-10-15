"use client";
import Link from "next/link";
import {useRouter} from "next/navigation";
import {useState} from "react";
import {useAccount} from "./account-provider";
import {accountFetch} from "../lib/account";
export default function SiteHeader(){
 const router=useRouter();
 const {user,refresh}=useAccount();const [error,setError]=useState("");
 async function logout(){try{await accountFetch("auth/logout",{method:"POST"});await refresh();router.push("/");router.refresh();}catch(e){setError(e instanceof Error?e.message:"Çıkış yapılamadı.");}}
 return <header className="header"><Link className="brand" href="/" aria-label="Tencerem ana sayfa"><span aria-hidden="true">◒</span> tencerem<span className="dot">.</span></Link><nav aria-label="Hesap">{user?<><Link href="/mutfagim">Mutfağım</Link><Link href="/tercihlerim">Tercihlerim</Link><button className="nav-button" onClick={logout}>Çıkış Yap</button></>:<><Link href="/giris">Giriş Yap</Link><Link href="/kayit">Kayıt Ol</Link></>}{error&&<p role="alert">{error}</p>}</nav></header>;
}
