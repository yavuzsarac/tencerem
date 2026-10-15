"use client";
import {useState} from "react";
import type {FormEvent} from "react";
import {useAccount} from "./account-provider";
import RecipeResults from "./recipe-results";
import type {Recommendations} from "../lib/recipes";

type Intent = {meal: Record<string,unknown>; include_ids:string[]; exclude_ids:string[]};
type Result = {intent:Intent; recommendations:Recommendations; engine:"ai_assisted"|"deterministic_fallback"; notices:string[]; selected_slug:string|null; reason:string|null; tradeoffs:string[]; understood:string[]};

export default function MealAssistant({onActive}:{onActive:()=>void}){
 const {user}=useAccount();
 const [result,setResult]=useState<Result|null>(null);
 const [shown,setShown]=useState<string[]>([]);
 const [pending,setPending]=useState(false);
 const [error,setError]=useState("");
 const [text,setText]=useState("");
 async function request(message:string,next=false){
  onActive();
  setPending(true);setError("");
  try{
   const response=await fetch(user?"/api/account/me/assistant/recommend":"/api/assistant/recommend",{method:"POST",headers:{"Content-Type":"application/json","X-Tencerem-CSRF":"1"},
    body:JSON.stringify({text:message,previous_intent:result?.intent??null,shown_slugs:next?shown:[],current_slug:result?.selected_slug??null}),signal:AbortSignal.timeout(24000)});
   if(!response.ok)throw new Error(response.status===429?"Çok hızlı istek gönderildi. Bir dakika sonra tekrar dene.":"Karar servisine ulaşılamıyor. Tekrar dene veya aşağıdaki formu kullan.");
   const data:Result=await response.json();
   if(!data.recommendations||!Array.isArray(data.recommendations.recipes)||!Array.isArray(data.notices)||!data.intent)throw new Error("Yanıt doğrulanamadı. Tekrar dene.");
   setResult(data);
   if(data.selected_slug)setShown(values=>data.notices.some(n=>n.includes("hepsi gösterildi"))?[data.selected_slug!]:[...new Set([...values,data.selected_slug!])].slice(-24));
   setText("");
  }catch(err){setError(err instanceof Error?err.message:"Bağlantı kurulamadı.");}
  finally{setPending(false);}
 }
 function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();void request(text);}
 return <section className="assistant-panel" aria-labelledby="assistant-heading" aria-busy={pending}>
  <span className="eyebrow">NE YİYECEĞİNİ DÜŞÜNME. TENCEREM DÜŞÜNSÜN.</span>
  <h2 id="assistant-heading">Birlikte bugünkü yemeğini seçelim</h2>
  <p>{user?"Kayıtlı tercihlerin ve Mutfağım kullanılır; bugünkü isteklerin kalıcı ayarlarını değiştirmez.":"Üye olmadan deneyebilirsin. Kayıtlı alerji ve tercihler yalnızca giriş yaptığında kullanılır."}</p>
  <form onSubmit={submit}><fieldset disabled={pending}>
   <label htmlFor="meal-message">{result?"İsteğini nasıl değiştirelim?":"Bugün nasıl bir şey yemek istiyorsun?"}</label>
   <textarea id="meal-message" value={text} onChange={event=>setText(event.target.value)} minLength={2} maxLength={500} required rows={2} placeholder={result?"Daha hızlı olsun · Tavuk olmasın · Bunu 4 kişilik yapacağım":"Evde tavuk var, hızlı ve proteinli bir şey istiyorum"}/>
   <button type="submit">{pending?"Yemeğin seçiliyor…":result?"Öneriyi Güncelle":"Tencerem Öner"}</button>
   {result&&<button type="button" className="secondary" onClick={()=>{setResult(null);setShown([]);setText("");setError("");}}>Yeni Karar</button>}
  </fieldset></form>
  <p className="disclosure">Yapay zekâ açıksa isteği yorumlamaya yardımcı olur; kapalıysa sınırlı kurallarla devam ederiz. Tarifler kayıtlı katalogdandır. Miktarlar sepet motoruyla hesaplanır.</p>
  <div role="status" aria-live="polite">{pending&&<p>İsteğin ve uygun tarifler kontrol ediliyor…</p>}</div>
  {error&&<p role="alert" className="error">{error}</p>}
  {result&&<><p className="saved-note">{result.engine==="ai_assisted"?"Yapay zekâ destekli karar · güvenlik filtreleri uygulandı":"Katalog sıralamasıyla öneri · yedek karar yolu"}</p>
   {result.notices.map(n=><p key={n}>{n}</p>)}
   <details><summary>Anlaşılan bugünkü tercihler</summary><p>{String(result.recommendations.requested_servings)} kişilik · {String(result.intent.meal.max_minutes??"Kayıtlı veya 30")} dakika üst sınırı</p>{result.understood.map(n=><p key={n}>{n}</p>)}<small>Kalıcı tercihlerin kaydedilmedi. Özel ekipman koşulları doğrulanamazsa öneri verilmez.</small></details>
   {result.reason&&<p>{result.reason}</p>}
   {result.tradeoffs.map(n=><small key={n}>{n}</small>)}
   <fieldset disabled={pending}><RecipeResults key={JSON.stringify(result)} data={result.recommendations} onNext={()=>void request("Başka bir şey öner",true)}/></fieldset>
  </>}
 </section>;
}
