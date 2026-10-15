"use client";
import { useState } from "react";
import type { Recommendations, RecipeMatch } from "../lib/recipes";
import PantryBasket from "./pantry-basket";
function MealChoice({ match, pantryIds }: {match:RecipeMatch; pantryIds:string[]}) {
  const [accepted, setAccepted] = useState(false);
  const [showRecipe, setShowRecipe] = useState(false);
  const [review, setReview] = useState(false);
  const required = match.scaled_ingredients.filter(i=>!i.optional);
  const present = required.filter(i=>pantryIds.includes(i.ingredient_id)).length;
  return <article className="recipe-card" aria-labelledby="primary-meal-heading">
    <span className="eyebrow">BUGÜNKÜ ÖNERİN</span><h3 id="primary-meal-heading">Bugün {match.recipe.name} ye.</h3><p>{match.recipe.description}</p>
    <p className="recipe-meta">{match.recipe.total_minutes} dk toplam · {match.recipe.difficulty === "easy" ? "Kolay" : "Orta"} · {match.requested_servings} kişilik</p>
    <p>{required.length} zorunlu malzemeden {present} tanesi evde var olarak eşleşti · {required.length-present} malzeme evde işaretli değil. Miktarlar henüz doğrulanmadı.</p>
    <div className="why"><strong>Neden bu yemek?</strong><ul>{match.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul></div>
    {!accepted ? <button type="button" onClick={()=>{setAccepted(true);setShowRecipe(true);}}>Bunu Yapacağım</button> : <>
      <p className="covered" role="status">Bu yemek seçildi. Önce tarifi incele, sonra evdeki miktarları doğrula.</p>
      <div className="meal-actions"><button type="button" className="secondary" aria-expanded={showRecipe} onClick={()=>setShowRecipe(!showRecipe)}>{showRecipe ? "Tarifi Gizle" : "Tarifi Gör"}</button><button type="button" onClick={()=>setReview(true)}>Eksikleri Gör</button></div>
      {showRecipe && <section className="recipe-detail"><h4>Tarif ve malzemeler</h4><p>{match.recipe.prep_minutes} dk hazırlık + {match.recipe.cook_minutes} dk pişirme. Süre tahminidir, porsiyonla ölçeklenmez.</p><ul>{match.scaled_ingredients.map(i=><li key={i.ingredient_id}>{i.display_quantity} {i.unit_label} {i.name}{i.optional ? " · İsteğe bağlı" : ""}{i.notes && <small>{i.notes}</small>}</li>)}</ul><h4>Nasıl pişirilir?</h4><ol className="instructions">{match.recipe.instructions.map((step,index)=><li key={index}>{step}</li>)}</ol><small>Malzemeler {match.recipe.base_servings} kişilik temel tariften ölçeklendi. Kesirli adetleri bölerek veya tartarak kullanın; miktarlar için bu listeyi izleyin.</small></section>}
      {review && <PantryBasket match={match} pantryIds={pantryIds}/>}
    </>}
    <p className="provenance"><strong>Kaynak: Tencerem yerel geliştirme kataloğu (curated_internal).</strong> {match.recipe.provenance.note}</p>
  </article>;
}
export default function RecipeResults({ data, onNext }: {data: Recommendations; onNext?:()=>void}) {
  const [index, setIndex] = useState(0);
  const match = data.recipes[index];
  return <section className="results" aria-labelledby="results-heading">
    <span className="eyebrow">NE YİYECEĞİNİ DÜŞÜNME. TENCEREM DÜŞÜNSÜN.</span><h2 id="results-heading">{data.recipes.length ? "Bugünkü yemeğin hazır" : "Uygun yemek bulunamadı"}</h2>
    {match ? <><p role="status" aria-live="polite">Öneri {index+1} / {data.recipes.length} · Yerel kürasyonlu katalog</p><MealChoice key={`${index}-${match.recipe.slug}`} match={match} pantryIds={data.recognized_pantry_ids}/><button className="secondary next-meal" type="button" disabled={!onNext && data.recipes.length<2} onClick={()=>onNext ? onNext() : setIndex(value=>(value+1)%data.recipes.length)}>Başka Öner</button><small>Başka öneriye geçince yemek seçimi, stok düzenlemeleri ve yerel sepet sıfırlanır.</small></> : <p>{data.message}</p>}
    <div className="result-notes">{data.warnings.map(w=><p key={w}>{w}</p>)}{data.unrecognized_pantry.length>0 && <p><strong>Eşleştirilemeyen malzemeler:</strong> {data.unrecognized_pantry.join(", ")}. Daha sade bir malzeme adı deneyin.</p>}</div>
  </section>;
}
