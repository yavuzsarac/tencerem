export type User = {id:string;email:string};
export type Preferences = {dietary_pattern:string;allergies:string[];liked_ingredients:string[];disliked_ingredients:string[];goals:string[];default_servings:number;default_max_minutes:number|null};
export type RegistryIngredient = {id:string;name:string;preparation_state:string;default_basket_unit:string;allergen_metadata_complete:boolean};
export type SavedPantry = {id:string;ingredient_id:string;name:string;quantity:string|null;unit:string|null;expiration_date:string|null;preparation_state:string};
export async function accountFetch<T>(path:string,init:RequestInit={}):Promise<T> {
  const response=await fetch(`/api/account/${path}`,{...init,headers:{"Content-Type":"application/json","X-Tencerem-CSRF":"1",...init.headers},cache:"no-store",signal:AbortSignal.timeout(12000)});
  if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body.error?.message || "Hesap servisine ulaşılamıyor. Tekrar deneyin.");}
  return response.status===204 ? undefined as T : response.json();
}
export const preparationLabels:Record<string,string>={raw:"Çiğ",dry:"Kuru / pişmemiş",cooked:"Pişmiş / haşlanmış",ready_to_use:"Kullanıma hazır"};
