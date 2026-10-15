import type {PantryInput} from "./baskets";
export type PricingInput = {
 recipes:{slug:string;servings:number}[];
 optional_policy:"required_only"|"include_optional";
 pantry?:PantryInput[];
};
export type MarketProduct={id:string;name:string;brand:string;package_quantity:string;package_unit:string;price:string;currency:"TRY";source:"curated_demo";observed_at:string};
export type PricedItem={ingredient_id:string;name:string;unit:string;optional_status:"required"|"optional"|"mixed";required_missing_quantity:string;calculation_status:string;status:string;message:string;package_count:number;purchased_quantity:string|null;surplus_quantity:string|null;line_total:string|null;purchases:{product:MarketProduct;package_count:number;purchased_quantity:string;line_total:string}[]};
export type MarketEstimate={retailer:{id:string;name:string;data_source:"curated_demo"};items:PricedItem[];total_required_ingredients:number;fulfilled_count:number;unavailable_count:number;complete:boolean;priced_subtotal:string;basket_total:string|null;warnings:string[]};
export type MarketComparison={mode:"demo_market_comparison";estimates:MarketEstimate[];recommended_retailer_id:string|null;message:string;notice:string};

// Format validated decimal strings directly; no conversion to binary floating point.
export function formatTry(value:string){
 const match=/^(\d+)\.(\d{2})$/.exec(value);
 if(!match)return "Tutar doğrulanamadı";
 return `${match[1].replace(/\B(?=(\d{3})+(?!\d))/g,".")},${match[2]} TL`;
}
export function quantity(value:string|null,unit:string){
 if(value===null)return "Hesaplanamadı";
 const labels:Record<string,string>={tbsp:"yemek kaşığı",tsp:"çay kaşığı",cup:"su bardağı",dessert_spoon:"tatlı kaşığı"};
 return `${value.replace(/(\.\d*?)0+$/,"$1").replace(/\.$/,"").replace(".",",")} ${labels[unit]??unit}`;
}
