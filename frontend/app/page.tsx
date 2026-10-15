"use client";
import MealAssistant from "../components/meal-assistant";
import SiteHeader from "../components/site-header";
import {useAccount} from "../components/account-provider";
import { useState } from "react";
import type { FormEvent } from "react";

import RecipeResults from "../components/recipe-results";
import type { Recommendations } from "../lib/recipes";
export default function Home() {
  const {user}=useAccount();
  return <MealHome key={user?.id ?? "anonymous"}/>;
}
function MealHome() {
  const {user}=useAccount();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [recommendations, setRecommendations] = useState<Recommendations | null>(null);
  const [assistantRevision,setAssistantRevision] = useState(0);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const values = new FormData(form);
    const craving = String(values.get("craving")).trim() || (user ? "yemek" : "");
    setError(""); setRecommendations(null);
    setAssistantRevision(value=>value+1);
    if (craving.length < 2) { setError("Ne yemek istediğinizi en az 2 karakterle yazın."); return; }
    setPending(true);
    try {
      const response = await fetch(user ? "/api/account/me/recipes/recommend" : "/api/recipes/recommend", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(user ? {craving, ...(values.get("servings") ? {servings:Number(values.get("servings"))}:{}), ...(values.get("time") ? {max_minutes:Number(values.get("time"))}:{}), temporary_tags: values.getAll("temporary_tags"), allow_disliked: values.get("allow_disliked") === "on"} : { craving, servings: Number(values.get("servings")), max_budget_try: values.get("budget"), max_prep_minutes: Number(values.get("time")), dietary_preference: values.get("diet"), pantry: values.get("pantry") }),
        signal: AbortSignal.timeout(12000),
      });
      if (!response.ok) throw new Error(response.status === 422 ? "Bilgileri kontrol edip tekrar deneyin." : "Şu anda bağlantı kurulamıyor. Lütfen tekrar deneyin.");
      const data: Recommendations = await response.json();
      if (data.mode !== "curated" || !Array.isArray(data.recipes) || typeof data.message !== "string") throw new Error("Beklenmeyen sunucu yanıtı.");
      setRecommendations(data);
    } catch (err) {
      setError(err instanceof Error && err.name !== "TimeoutError" ? err.message : "İstek zaman aşımına uğradı. Tekrar deneyin.");
    } finally { setPending(false); }
  }
  return <>
    <a className="skip" href="#preferences">Forma geç</a>
    <SiteHeader/>
    <main>
      <section className="intro" aria-labelledby="heading">
        <span className="eyebrow">DAHA AZ DÜŞÜN, KEYİFLE PİŞİR</span>
        <h1 id="heading">Bugün ne<br/><em>yesem?</em></h1>
        <p>Aklındaki yemeği söyle. Vaktine ve evdeki malzemelerine uygun, yerel kataloğumuzdan tarifler bulalım.</p>
        <div className="illustration" aria-hidden="true"><span className="steam">∿ ∿ ∿</span><div className="lid"/><div className="pot"><span>✳</span></div><span className="herb">✳</span><span className="tomato">●</span></div>
        <div className="note"><span>01 / İLK ADIM</span><p>Güzel bir sofra, sana uygun bir planla başlar.</p></div>
      </section>
      <MealAssistant key={assistantRevision} onActive={()=>setRecommendations(null)}/>
      <section className="card" id="preferences" aria-labelledby="form-heading">
        <div className="card-top"><span className="eyebrow">SENİN MUTFAĞIN, SENİN TERCİHLERİN</span><h2 id="form-heading">Sofranı planlamaya başla</h2><p>Birkaç küçük detayla başlayalım.</p></div>
        <form onSubmit={submit} onChange={() => { setRecommendations(null); setError(""); }} aria-busy={pending}>
          <fieldset disabled={pending}>
            <label htmlFor="craving">Canın ne yemek istiyor?</label>
            <textarea id="craving" name="craving" placeholder="Örneğin: bol sebzeli, hafif bir akşam yemeği" required={!user} minLength={2} maxLength={240} rows={3} aria-describedby="craving-help"/>
            <small id="craving-help">Bir yemek adı ya da aklındaki lezzeti yazabilirsin.</small>
            <div className="grid">
              <div><label htmlFor="servings">Kaç kişilik?</label><input id="servings" name="servings" type="number" min="1" max="12" step="1" defaultValue={user?"":"2"} key={`servings-${!!user}`} placeholder={user?"Kayıtlı kişi sayısı":"2"} required={!user}/></div>
              <div hidden={!!user}><label htmlFor="budget">Bütçe hedefi (₺) · Henüz uygulanmaz</label><input aria-describedby="budget-help" id="budget" name="budget" type="number" min="0.01" max="100000" step="0.01" defaultValue="350" required={!user}/><small id="budget-help">Fiyat verisi yok; bu hedef filtreleme veya sıralamada kullanılmaz.</small></div>
              <div><label htmlFor="time">En fazla toplam süre (dakika)</label><input id="time" name="time" type="number" min="5" max="240" step="1" defaultValue={user?"":"30"} key={`time-${!!user}`} placeholder={user?"Kayıtlı süre veya 30":"30"} required={!user}/></div>
              <div hidden={!!user}><label htmlFor="diet">Beslenme tercihi</label><select id="diet" name="diet" defaultValue="none"><option value="none">Özel tercihim yok</option><option value="vegetarian">Vejetaryen</option><option value="vegan">Vegan</option><option value="gluten_free">Glütensiz</option></select></div>
            </div>
            <div hidden={!!user}><label htmlFor="pantry">Evde olan malzemeler <span className="optional">(isteğe bağlı)</span></label>
            <input id="pantry" name="pantry" maxLength={1000} placeholder="pirinç, yoğurt" aria-describedby="pantry-help"/>
            <small id="pantry-help">Virgülle ayırın. Eşleşmeler miktar yeterliliğini doğrulamaz. Haşlanmış nohut gibi hazırlık durumunu kontrol edin.</small></div>
            {user && <><p className="saved-note">Kayıtlı tercihlerin ve Mutfağım kullanılır. Kişi ve süreyi boş bırakırsan kayıtlı değerler geçerlidir.</p><fieldset><legend>Bugün nasıl bir şey istiyorsun?</legend>{[["quick","Hızlı"],["economical","Ekonomik"],["high_protein","Protein kaynağı"]].map(([value,label])=><label className="checklist" key={value}><input name="temporary_tags" type="checkbox" value={value}/>{label}</label>)}</fieldset><details><summary>Bugüne özel seçenekler</summary><label className="checklist"><input name="allow_disliked" type="checkbox"/>Bugün sevmediğim malzemeler de önerilebilir. Alerji ve beslenme kısıtları korunur.</label></details></>}
            <button className="submit" type="submit">{pending ? "Tarifler aranıyor…" : "Tarifleri bul"}<span aria-hidden="true">↗</span></button>
          </fieldset>
          <div role="status" aria-live="polite">{pending && <p>Tercihlerin sunucuya gönderiliyor…</p>}{recommendations && <p>{recommendations.recipes.length ? "Yemek önerin hazır. İlk önerin formun altında." : recommendations.message}</p>}</div>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
        <p className="disclosure">Bu form mevcut deterministik tarif aramasıdır. Tarifler yerel katalogdan gelir; fiyat hesaplanmaz. Hesapla tercihler ve Mutfağım saklanabilir.</p>
      </section>
      {recommendations && <RecipeResults key={JSON.stringify(recommendations)} data={recommendations}/>}
    </main>
    <footer><span>Özenle planla. Keyifle paylaş.</span><span>Türkiye için tasarlanıyor · ₺ · Metrik ölçüler</span></footer>
  </>;
}
