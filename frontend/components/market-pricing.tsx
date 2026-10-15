"use client";
import {useState} from "react";
import {formatTry,quantity} from "../lib/markets";
import type {MarketComparison,PricingInput} from "../lib/markets";

export default function MarketPricing({input,useSaved}:{input:PricingInput;useSaved:boolean}){
 const [result,setResult]=useState<MarketComparison|null>(null);
 const [selected,setSelected]=useState("");
 const [pending,setPending]=useState(false);
 const [error,setError]=useState("");
 async function compare(){
  setPending(true);setError("");setResult(null);
  try{
   const response=await fetch(useSaved?"/api/account/me/baskets/compare":"/api/baskets/compare",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(input),signal:AbortSignal.timeout(12000)});
   if(!response.ok)throw new Error("Demo fiyat hesabı tamamlanamadı. Tekrar deneyin; miktar ve kayıtlı tercihlerinizi kontrol edin.");
   const data:MarketComparison=await response.json();
   if(data.mode!=="demo_market_comparison"||!Array.isArray(data.estimates))throw new Error("Beklenmeyen fiyat yanıtı.");
   setResult(data);setSelected(data.recommended_retailer_id??data.estimates[0]?.retailer.id??"");
  }catch(err){setError(err instanceof Error&&err.name!=="TimeoutError"?err.message:"Hesap zaman aşımına uğradı. Tekrar deneyin.");}
  finally{setPending(false);}
 }
 const estimate=result?.estimates.find(e=>e.retailer.id===selected);
 return <section className="market-pricing" aria-labelledby="market-heading" aria-busy={pending}>
  <span className="eyebrow">DEMO FİYATLAR · CANLI FİYAT DEĞİLDİR</span>
  <h3 id="market-heading">Tahmini Market Sepeti</h3>
  <p>Geliştirme amaçlı ürün kataloğu. Eksik miktarlar için paket alımını karşılaştırır; gerçek market bağlantısı, sipariş veya fiyat garantisi içermez.</p>
  <button type="button" onClick={()=>void compare()} disabled={pending}>{pending?"Demo sepetler hesaplanıyor…":"Marketleri Karşılaştır"}</button>
  <div role="status" aria-live="polite">{pending&&<p>Paket seçenekleri ve karşılanabilen malzemeler kontrol ediliyor…</p>}</div>
  {error&&<p role="alert" className="error">{error}</p>}
  {result&&<><p className="saved-note" role="status">{result.message}</p><p className="disclosure">{result.notice}</p>
   <label htmlFor="market-select">Demo Market Seç</label>
   <select id="market-select" value={selected} onChange={event=>setSelected(event.target.value)}>{result.estimates.map(e=><option key={e.retailer.id} value={e.retailer.id}>{e.retailer.name}{e.retailer.id===result.recommended_retailer_id?" · En uygun tam sepet":""}</option>)}</select>
   <details className="market-alternatives"><summary>Diğer demo marketleri gör</summary><ul>{result.estimates.map(e=><li key={e.retailer.id}><strong>{e.retailer.name}</strong>: {e.fulfilled_count}/{e.total_required_ingredients} malzeme karşılanıyor · {e.complete&&e.basket_total!==null?`Tam demo sepet: ${formatTry(e.basket_total)}`:"Kısmi sepet — tam fiyat karşılaştırılamaz"}</li>)}</ul></details>
   {estimate&&<article className="market-estimate" data-retailer={estimate.retailer.id}>
    <h4>{estimate.retailer.name}</h4>
    <p>{estimate.fulfilled_count}/{estimate.total_required_ingredients} eksik malzeme karşılanıyor · {estimate.unavailable_count} karşılanamayan malzeme</p>
    <p className={estimate.complete?"basket-summary":"quantity-warning"}>{estimate.complete&&estimate.basket_total!==null?`Demo sepet toplamı: ${formatTry(estimate.basket_total)}`:`Tam sepet hesaplanamadı. Yalnızca fiyatlanan kısmın ara toplamı: ${formatTry(estimate.priced_subtotal)}`}</p>
    {estimate.items.length===0&&<p>Evde yeterli; alınacak ürün yok.</p>}
    {estimate.items.map(item=><section className="market-line" key={`${item.ingredient_id}-${item.unit}`} data-market-ingredient={item.ingredient_id}>
     <h5>{item.name}{item.optional_status!=="required"?` · ${item.optional_status==="optional"?"İsteğe bağlı":"Zorunlu + isteğe bağlı"}`:""}</h5>
     <p>Eksik miktar: {quantity(item.required_missing_quantity,item.unit)}</p>
     {item.status==="fulfilled"?<><ul>{item.purchases.map(p=><li key={p.product.id}><strong>{p.product.name}</strong><br/>{p.package_count} paket × {formatTry(p.product.price)} = {formatTry(p.line_total)}<small>Kaynak: geliştirme verisi (curated_demo) · Sabit veri tarihi: {p.product.observed_at.slice(0,10)}. Canlı gözlem değildir.</small></li>)}</ul>
      <dl><div><dt>Paket sayısı</dt><dd>{item.package_count}</dd></div><div><dt>Alınacak miktar</dt><dd>{quantity(item.purchased_quantity,item.unit)}</dd></div><div><dt>Artacak miktar</dt><dd>{quantity(item.surplus_quantity,item.unit)}</dd></div><div><dt>Demo satır toplamı</dt><dd>{item.line_total===null?"Hesaplanamadı":formatTry(item.line_total)}</dd></div></dl>
      {item.calculation_status!=="exact"&&<p className="quantity-warning">Stok miktarı veya birimler kontrol gerektiriyor. Demo hesap yalnızca bu birimdeki ihtiyacı karşılar; evdeki bilinmeyen miktar düşülmedi.</p>}
     </>:<p className="quantity-warning">{item.message} Bu satıra fiyat atanmadı.</p>}
    </section>)}
   </article>}
  </>}
 </section>;
}
