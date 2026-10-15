"use client";
import { useState } from "react";
import type { Basket } from "../lib/baskets";
export default function BasketPreview({ basket }: { basket: Basket }) {
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const summary = basket.summary;
  return <section className="basket-preview" aria-labelledby="basket-heading">
    <span className="eyebrow">MALZEME SEPETİ · YEREL ÖNİZLEME</span><h3 id="basket-heading">Sepetim</h3>
    <p>{basket.selected_recipes.map(r => `${r.name} · ${r.servings} kişilik`).join(" / ")}</p>
    <p className="basket-summary">{summary.unique_ingredients} farklı malzeme · {summary.fully_covered} evde yeterli · {summary.partially_covered} kısmen var · {summary.items_to_buy} malzemede eksik miktar · {summary.unresolved_items} kontrol gerekli</p>
    <p>{basket.optional_policy === "required_only" ? "Yalnızca zorunlu malzemeler" : "İsteğe bağlı malzemeler dahil"}. {basket.excluded_optional_contributions > 0 && `${basket.excluded_optional_contributions} isteğe bağlı tarif katkısı hariç tutuldu.`}</p>
    <div className="result-notes">{basket.warnings.map(w => <p key={w}>{w}</p>)}<p>İşaretler yalnızca bu ekranda tutulur; sayfa yenilenince veya önizleme değişince sıfırlanır. Stoğu değiştirmez.</p></div>
    {basket.items.map(item => <article className="basket-item" key={item.ingredient_id} data-ingredient={item.ingredient_id}>
      <h4>{item.name}{item.optional_status !== "required" && <span className="optional"> · {item.optional_status === "optional" ? "İsteğe bağlı" : "Zorunlu + isteğe bağlı"}</span>}</h4>
      {item.pantry_stock.length > 0 && <p className="stock-record">Girilen stok: {item.pantry_stock.map(s=>s.display).join(" + ")}</p>}
      {item.warnings.map(w => <p className="quantity-warning" key={w}>{w}</p>)}
      {item.components.map(component => {
        const key = `${item.ingredient_id}:${component.unit}`;
        const missing = Number(component.missing_quantity) > 0;
        return <section className="basket-component" key={key}>
          <dl><div><dt>Gerekli</dt><dd>{component.required_display}</dd></div><div><dt>Evde doğrulanan</dt><dd>{component.available_display}</dd></div><div><dt>Evden ayrılan</dt><dd>{component.allocated_display}</dd></div><div><dt>Alınacak / kontrol edilecek</dt><dd>{component.missing_display}</dd></div></dl>
          {!missing && component.calculation_status === "exact" && <p className="covered">Evde yeterli (bu birim için)</p>}
          {missing && <label className="checklist"><input type="checkbox" checked={checked.has(key)} onChange={event => setChecked(previous => {const next = new Set(previous); if(event.target.checked) next.add(key); else next.delete(key); return next;})}/><span>{item.name} — {component.missing_display}{component.calculation_status !== "exact" || item.calculation_status === "incompatible_units" ? " · Miktarı kontrol et" : ""}</span></label>}
          <details><summary>Nasıl hesaplandı?</summary><p>{component.explanation}</p><ul>{component.contributions.map((contribution, index) => <li key={index}>{contribution.name} ({contribution.servings} kişilik; seçim {contribution.selection_index+1}): {contribution.quantity_display}{contribution.optional ? " · İsteğe bağlı" : ""}{contribution.notes ? ` · ${contribution.notes}` : ""}</li>)}</ul></details>
        </section>;
      })}
    </article>)}
  </section>;
}
