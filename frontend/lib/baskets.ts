export type PantryInput = { ingredient_id: string; quantity: string | null; unit: string | null; presence: true };
export type BasketComponent = {
  unit: string; required_quantity: string; pantry_available_quantity: string | null;
  pantry_allocated_quantity: string; missing_quantity: string; calculation_status: string;
  required_display: string; available_display: string; allocated_display: string; missing_display: string;
  explanation: string; contributions: {selection_index: number; name: string; servings: number; quantity: string; quantity_display: string; unit: string; optional: boolean; notes: string | null}[];
};
export type Basket = {
  mode: "ingredient_preview"; optional_policy: "required_only" | "include_optional";
  items: {ingredient_id: string; name: string; components: BasketComponent[];
    pantry_stock: {quantity:string | null; unit:string | null; display:string}[];
    optional_status: "required" | "optional" | "mixed"; calculation_status: string; warnings: string[]; unknown_pantry_quantity: boolean}[];
  selected_recipes: {name: string; servings: number; selection_index: number}[];
  excluded_optional_contributions: number;
  summary: {unique_ingredients: number; fully_covered: number; partially_covered: number; items_to_buy: number; unresolved_items: number};
  warnings: string[];
};
export const units = [["g", "g"], ["kg", "kg"], ["ml", "ml"], ["l", "l"], ["adet", "adet"], ["tbsp", "yemek kaşığı"], ["dessert_spoon", "tatlı kaşığı"], ["tsp", "çay kaşığı"], ["cup", "su bardağı"]];
