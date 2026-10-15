"use client";
import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";

import RecipeResults from "../components/recipe-results";
import type { Recommendations } from "../lib/recipes";
export default function Home() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [recommendations, setRecommendations] = useState<Recommendations | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const values = new FormData(form);
    const craving = String(values.get("craving")).trim();
    setError(""); setRecommendations(null);
    if (craving.length < 2) { setError("Ne yemek istediğinizi en az 2 karakterle yazın."); return; }
    setPending(true);
    try {
      const response = await fetch("/api/recipes/recommend", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ craving, servings: Number(values.get("servings")), max_budget_try: values.get("budget"), max_prep_minutes: Number(values.get("time")), dietary_preference: values.get("diet"), pantry: values.get("pantry") }),
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
    <header className="header"><Link className="brand" href="/" aria-label="Tencerem ana sayfa"><span aria-hidden="true">◒</span> tencerem<span className="dot">.</span></Link><span className="phase">Mutfakta yeni bir başlangıç · Geliştirme sürümü</span></header>
    <main>
      <section className="intro" aria-labelledby="heading">
        <span className="eyebrow">DAHA AZ DÜŞÜN, KEYİFLE PİŞİR</span>
        <h1 id="heading">Bugün ne<br/><em>pişirsek?</em></h1>
        <p>Aklındaki yemeği söyle. Vaktine ve evdeki malzemelerine uygun, yerel kataloğumuzdan tarifler bulalım.</p>
        <div className="illustration" aria-hidden="true"><span className="steam">∿ ∿ ∿</span><div className="lid"/><div className="pot"><span>✳</span></div><span className="herb">✳</span><span className="tomato">●</span></div>
        <div className="note"><span>01 / İLK ADIM</span><p>Güzel bir sofra, sana uygun bir planla başlar.</p></div>
      </section>
      <section className="card" id="preferences" aria-labelledby="form-heading">
        <div className="card-top"><span className="eyebrow">SENİN MUTFAĞIN, SENİN TERCİHLERİN</span><h2 id="form-heading">Sofranı planlamaya başla</h2><p>Birkaç küçük detayla başlayalım.</p></div>
        <form onSubmit={submit} onChange={() => { setRecommendations(null); setError(""); }} aria-busy={pending}>
          <fieldset disabled={pending}>
            <label htmlFor="craving">Canın ne yemek istiyor?</label>
            <textarea id="craving" name="craving" placeholder="Örneğin: bol sebzeli, hafif bir akşam yemeği" required minLength={2} maxLength={240} rows={3} aria-describedby="craving-help"/>
            <small id="craving-help">Bir yemek adı ya da aklındaki lezzeti yazabilirsin.</small>
            <div className="grid">
              <div><label htmlFor="servings">Kaç kişilik?</label><input id="servings" name="servings" type="number" min="1" max="12" step="1" defaultValue="2" required/></div>
              <div><label htmlFor="budget">Bütçe hedefi (₺) · Henüz uygulanmaz</label><input aria-describedby="budget-help" id="budget" name="budget" type="number" min="0.01" max="100000" step="0.01" defaultValue="350" required/><small id="budget-help">Fiyat verisi yok; bu hedef filtreleme veya sıralamada kullanılmaz.</small></div>
              <div><label htmlFor="time">En fazla toplam süre (dakika)</label><input id="time" name="time" type="number" min="5" max="240" step="1" defaultValue="30" required/></div>
              <div><label htmlFor="diet">Beslenme tercihi</label><select id="diet" name="diet" defaultValue="none"><option value="none">Özel tercihim yok</option><option value="vegetarian">Vejetaryen</option><option value="vegan">Vegan</option><option value="gluten_free">Glütensiz</option></select></div>
            </div>
            <label htmlFor="pantry">Evde olan malzemeler <span className="optional">(isteğe bağlı)</span></label>
            <input id="pantry" name="pantry" maxLength={1000} placeholder="pirinç, yoğurt" aria-describedby="pantry-help"/>
            <small id="pantry-help">Virgülle ayırın. Eşleşmeler miktar yeterliliğini doğrulamaz. Haşlanmış nohut gibi hazırlık durumunu kontrol edin.</small>
            <button className="submit" type="submit">{pending ? "Tarifler aranıyor…" : "Tarifleri bul"}<span aria-hidden="true">↗</span></button>
          </fieldset>
          <div role="status" aria-live="polite">{pending && <p>Tercihlerin sunucuya gönderiliyor…</p>}{recommendations && <p>{recommendations.recipes.length ? "Yemek önerin hazır. İlk önerin formun altında." : recommendations.message}</p>}</div>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
        <p className="disclosure">Tarifler kürasyonlu yerel katalogdan gelir. Yapay zekâ kullanılmaz; fiyat ve kayıt özelliği yoktur. Malzeme sepeti yerel önizlemedir.</p>
      </section>
      {recommendations && <RecipeResults key={JSON.stringify(recommendations)} data={recommendations}/>}
    </main>
    <footer><span>Özenle planla. Keyifle paylaş.</span><span>Türkiye için tasarlanıyor · ₺ · Metrik ölçüler</span></footer>
  </>;
}
