export type Ingredient = {
  ingredient_id: string; name: string; quantity: string; display_quantity: string;
  unit: string; unit_label: string; optional: boolean; notes: string | null;
};
export type RecipeMatch = {
  recipe: { id: string; slug: string; name: string; description: string; category: string;
    prep_minutes: number; cook_minutes: number; total_minutes: number; difficulty: "easy" | "medium";
    base_servings: number; instructions: string[];
    provenance: { kind: "curated_internal"; note: string };
  };
  requested_servings: number; scaled_ingredients: Ingredient[];
  available_ingredients: Ingredient[]; missing_ingredients: Ingredient[]; score: number; reasons: string[];
};
export type Recommendations = {
  mode: "curated"; requested_servings: number; recipes: RecipeMatch[]; message: string;
  normalized_pantry: string[]; recognized_pantry_ids: string[]; unrecognized_pantry: string[];
  budget_applied: false; warnings: string[];
};
