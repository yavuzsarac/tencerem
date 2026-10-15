"use client";
import {useAccount} from "./account-provider";
import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";
import type { RecipeMatch } from "../lib/recipes";
import type { Basket, PantryInput } from "../lib/baskets";
import { units } from "../lib/baskets";
import BasketPreview from "./basket-preview";
import MarketPricing from "./market-pricing";
import type {PricingInput} from "../lib/markets";
export default function PantryBasket({ match, pantryIds }: {match: RecipeMatch; pantryIds: string[]}) {
  const {user}=useAccount();
  const [useSaved,setUseSaved]=useState(!!user);
  const [rows, setRows] = useState(() => match.scaled_ingredients.map(i => ({id:i.ingredient_id, has:pantryIds.includes(i.ingredient_id), quantity:"", unit:i.unit})));
  const [includeOptional, setIncludeOptional] = useState(false);
  const [basket, setBasket] = useState<Basket | null>(null);
  const [revision, setRevision] = useState(0);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [pricingInput,setPricingInput] = useState<PricingInput|null>(null);
  function update(id: string, patch: Partial<(typeof rows)[number]>) {
    setRows(previous => previous.map(row => row.id === id ? {...row, ...patch} : row));
    setBasket(null); setError("");
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    const pantry: PantryInput[] = rows.filter(row => row.has).map(row => ({ingredient_id:row.id, quantity:row.quantity === "" ? null : row.quantity, unit:row.quantity === "" ? null : row.unit, presence:true}));
    setPending(true); setBasket(null); setError("");
    const input:PricingInput={recipes:[{slug:match.recipe.slug,servings:match.requested_servings}],...(user&&useSaved?{}:{pantry}),optional_policy:includeOptional?"include_optional":"required_only"};
    try {
      const response = await fetch(user && useSaved ? "/api/account/me/baskets/preview" : "/api/baskets/preview", {method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify(input), signal:AbortSignal.timeout(12000)});
      if (!response.ok) {
        if (response.status === 422) {
          const data = await response.json();
          const message = data.error?.fields?.map((field: {message:string}) => field.message).join(" ");
          throw new Error(message || "Miktar ve birimleri kontrol edin.");
        }
        throw new Error("Sepet servisine ulaşılamıyor. Tekrar deneyin.");
      }
      const data: Basket = await response.json();
      if (data.mode !== "ingredient_preview" || !Array.isArray(data.items)) throw new Error("Beklenmeyen sepet yanıtı.");
      setBasket(data); setRevision(value=>value+1);
      setPricingInput(input);
    } catch(err) {setError(err instanceof Error && err.name !== "TimeoutError" ? err.message : "İstek zaman aşımına uğradı. Tekrar deneyin.");}
    finally {setPending(false);}
  }
  return <section className="pantry-review" aria-labelledby="pantry-review-heading">
    <h3 id="pantry-review-heading">Eksikleri gör · Evdeki miktarları kontrol et</h3>
    <p>“Evde var” tek başına yeterli miktar demek değil. Bildiğin miktarı gir; bilmiyorsan boş bırak. Stok yalnızca bu önizleme için kullanılır.</p>
    <form onSubmit={submit} aria-busy={pending}>
      <fieldset disabled={pending}>
        <label className="checklist"><input type="checkbox" checked={includeOptional} onChange={event=>{setIncludeOptional(event.target.checked);setBasket(null);setError("");}}/>İsteğe bağlı malzemeleri dahil et</label>
        {user && <><label className="checklist"><input type="checkbox" checked={useSaved} onChange={event=>{setUseSaved(event.target.checked);setBasket(null);}}/>Mutfağım’daki kayıtlı stoğu kullan</label><p><Link href="/mutfagim">Mutfağım kayıtlarını düzenle</Link>. Bu önizleme kayıtlı stoğu değiştirmez.</p></>}
        {!(user && useSaved) && match.scaled_ingredients.filter(i=>includeOptional || !i.optional).map(ingredient => {
          const row = rows.find(r=>r.id === ingredient.ingredient_id)!;
          const id = `stock-${row.id}`;
          return <div className="pantry-row" key={row.id}>
            <div><strong>{ingredient.name}</strong><small>Tarif için: {ingredient.display_quantity} {ingredient.unit_label}{ingredient.optional ? " · İsteğe bağlı" : ""}</small>{ingredient.notes && <small>{ingredient.notes}</small>}</div>
            <label className="checklist"><input type="checkbox" checked={row.has} onChange={event=>update(row.id,{has:event.target.checked})}/>Evde var: {ingredient.name}</label>
            {row.has && <div className="stock-controls"><div><label htmlFor={`${id}-quantity`}>Evdeki miktar: {ingredient.name}</label><input id={`${id}-quantity`} type="number" min="0" max="1000000000" step="0.000001" value={row.quantity} onChange={event=>update(row.id,{quantity:event.target.value})} placeholder="Bilinmiyor" aria-describedby={`${id}-help`}/></div><div><label htmlFor={`${id}-unit`}>Birim: {ingredient.name}</label><select id={`${id}-unit`} value={row.unit} disabled={row.quantity === ""} onChange={event=>update(row.id,{unit:event.target.value})}>{units.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></div><small id={`${id}-help`}>Boş miktar stoktan düşülmez. Birimi ve haşlanmış/çiğ gibi hazırlık durumunu kontrol edin.</small></div>}
          </div>;
        })}
        <button type="submit">{pending ? "Sepet hesaplanıyor…" : "Sepete Hazırla"}</button>
      </fieldset>
      <div role="status" aria-live="polite">{pending && <p>İhtiyaçlar birleştiriliyor, evdeki miktarlar karşılaştırılıyor…</p>}{basket && <p>Sepet önizlemesi hazır. {basket.summary.items_to_buy} malzemede eksik miktar var.</p>}</div>
      {error && <p role="alert" className="error">{error}</p>}
    </form>
    {basket && <BasketPreview key={revision} basket={basket}/>}
    {basket && pricingInput && <MarketPricing key={`pricing-${revision}`} input={pricingInput} useSaved={!!user&&useSaved}/>}
  </section>;
}
