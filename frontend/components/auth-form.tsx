"use client";
import Link from "next/link";
import {useState} from "react";
import type {FormEvent} from "react";
import {useRouter} from "next/navigation";
import SiteHeader from "./site-header";
import {useAccount} from "./account-provider";
import {accountFetch} from "../lib/account";
export default function AuthForm({register=false}:{register?:boolean}){
 const [pending,setPending]=useState(false);const [error,setError]=useState("");const {refresh}=useAccount();const router=useRouter();
 async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();const form=event.currentTarget;const data=new FormData(form);setPending(true);setError("");try{await accountFetch(`auth/${register?"register":"login"}`,{method:"POST",body:JSON.stringify({email:data.get("email"),password:data.get("password")})});form.reset();await refresh();router.push(register?"/tercihlerim?onboarding=1":"/");}catch(e){setError(e instanceof Error?e.message:"İşlem tamamlanamadı.");}finally{setPending(false);}}
 return <><SiteHeader/><main className="account-main"><section className="card"><span className="eyebrow">SOFRANA ÖZEL BİR BAŞLANGIÇ</span><h1 className="account-title">{register?"Kayıt Ol":"Giriş Yap"}</h1><p>Tercihlerin ve Mutfağım kayıtların sonraki ziyaretinde seni beklesin.</p><form onSubmit={submit}><fieldset disabled={pending}><label htmlFor="email">E-posta</label><input id="email" name="email" type="email" autoComplete="email" required maxLength={254}/><label htmlFor="password">Parola</label><input id="password" name="password" type="password" autoComplete={register?"new-password":"current-password"} required minLength={12} maxLength={128}/><small>12–128 karakter. Parolanı başka hesaplarda kullanma.</small><button className="submit" type="submit">{pending?"İşlem sürüyor…":register?"Hesabımı Oluştur":"Giriş Yap"}</button></fieldset>{error&&<p className="error" role="alert">{error}</p>}</form><p><Link href={register?"/giris":"/kayit"}>{register?"Zaten hesabım var":"Hesap oluştur"}</Link> · <Link href="/">Misafir olarak devam et</Link></p><small>E-posta, güvenli parola özeti, tercihlerin ve stok kayıtların saklanır. E-posta doğrulama ve parola kurtarma henüz yoktur.</small></section></main></>;
}
