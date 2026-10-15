import { forwardPreferences } from "../../../lib/backend-proxy";
export async function POST(request: Request) {
  return forwardPreferences(request, "/api/v1/meal-preferences");
}
