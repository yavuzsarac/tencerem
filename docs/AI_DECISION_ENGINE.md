# Tencerem decision engine — Phase 4

Ne yiyeceğini düşünme. Tencerem düşünsün.

## Responsibilities and source of truth

AI may interpret Turkish meal intent and choose among a small safe candidate set. It cannot create recipes, mutate preferences, access tools, execute SQL, browse, calculate stock, scale servings or enforce safety. The 24-recipe curated catalog and 37-ingredient registry remain authoritative. Existing scaling, unit, pantry and basket services retain all Decimal arithmetic. No schema migration or decision-history table was added.

## Provider boundary and configuration

`services/ai_provider.py` defines the application `AIProvider` protocol: async `parse_meal_intent(text, previous)` and `choose_candidate(intent, candidates)`. The concrete OpenAI adapter uses httpx and strict JSON Schema Chat Completions; domain services import no vendor SDK. A different adapter can implement the same protocol. Explanations deliberately use trusted templates rather than a third ungrounded prose call. Official contract: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat).

Server-only root `.env` settings:

```dotenv
AI_ENABLED=false
AI_API_KEY=REPLACE_WITH_PRIVATE_API_KEY
AI_MODEL=
AI_TIMEOUT_SECONDS=6
```

To opt in, supply a private key, explicitly select an account-available model supporting strict Structured Outputs, and set AI_ENABLED=true. No model is silently selected. Disabled flag, missing key/model or placeholder key yields the documented offline fallback. Settings can also come from process environment; never use NEXT_PUBLIC_ for secrets. No real provider request was performed during this implementation. No extra package installation is needed in the existing environment; httpx, already locked/installed for tests, is now explicitly a runtime dependency.

The adapter uses a fixed HTTPS provider endpoint, no redirects, no environment proxy inheritance, no tools, no retries, `store=false`, max 1000 completion tokens and a 64 KiB streamed response cap. Each operation has a total wall-clock timeout (0.1–8 seconds; default 6); at most two calls occur per decision. Parsing must precede safe candidate construction, so these calls cannot be combined without giving the model unrestricted candidates. Refusal, truncation, HTTP failure/rate limit, timeout, invalid JSON/schema and disallowed choice all have fallback paths. Live model access/compatibility and output quality remain unverified.

## API and ephemeral state

Both POST endpoints require an allowed Origin plus `X-Tencerem-CSRF: 1`, return no-store JSON and share a bounded process-local decision limit of 15 requests/minute/IP:

- `/api/v1/assistant/recommend`: anonymous; no DB dependency or saved-profile lookup.
- `/api/v1/me/assistant/recommend`: existing session authentication; only that owner's preferences/pantry. Read transaction is released before provider network waits. Missing/invalid authentication never silently falls back to an anonymous account flow.

Example request:

```json
{
  "text": "Evde tavuk var, 30 dakikadan uzun sürmesin ve proteinli olsun.",
  "previous_intent": null,
  "controls": {"servings": 2},
  "pantry": "pirinç, tuz",
  "shown_slugs": [],
  "current_slug": null
}
```

`text` is 2–500 characters. `controls` is the existing typed MealIntent: explicit UI/API choices override inferred values; saved allergy/diet restrictions remain authoritative. `pantry` is optional comma-separated name-only stock. `previous_intent` carries bounded current-meal state: MealIntent, canonical include/exclude/pantry IDs. IDs are revalidated against the registry. No client state confers ownership or bypasses filters. `current_slug` lets “daha hızlı” constrain the next result below the current catalog duration. `shown_slugs` holds up to 24 session exclusions for next-choice requests. None of these values are persisted.

Provider `ParsedIntent` is an untrusted patch: in_scope, optional servings (integer 1–12), max_minutes (integer 5–240), dietary_pattern enum, up to six Goal enums, up to 20 included/excluded/pantry ingredient names each (max 80 characters), and up to five unsupported constraints. Extra properties, invalid enums, noninteger counts and out-of-range values fail validation. Names resolve only through exact canonical IDs/normalized registry aliases. Unknown requested/excluded ingredients block selection with an actionable response; unknown pantry names are reported and not invented.

Response includes validated `intent`, `engine` (`ai_assisted` or `deterministic_fallback`), `notices`, `selected_slug`, grounded `reason`, `matched_needs`, `tradeoffs`, Turkish `understood` summaries and `recommendations`. The latter preserves recipe/scaling/pantry/provenance fields, contains **at most one recipe**, and adds Phase 3 safety warnings/conflicts/applied values. `profile_applied=false` identifies anonymous use. A valid request with a conflict/no compatible recipe returns 200 with an empty recipe list and explanation; invalid request fields return the existing structured 422 envelope. No raw provider exceptions reach the client.

## Deterministic hybrid pipeline

1. Validate request/previous IDs. Run the small offline interpreter as a conservative companion to model parsing.
2. If configured, parse a bounded patch through the provider; schema validation failure uses the local interpreter. Local recognized explicit numbers/diet and negative ingredients cannot be removed by model output.
3. Merge previous ephemeral state and parsed patch, then explicit structured controls. Accumulate exclusions and remove excluded IDs from requested inclusions. “Evde … var” creates only presence signals; it does not overwrite existing saved quantities. Request-only pantry adjustments use the existing overlay service.
4. Filter canonical included/excluded ingredients. Use Phase 3 `compatible` for saved/current diet intersection, known allergies and fail-closed incomplete ingredient metadata, including optional ingredients. Detect impossible requested ingredients. Unsupported conditions or out-of-scope text return no selection.
5. Use existing personalized ranking: hard constraints/time/dislikes first, then pantry usefulness, likes, qualitative goals and existing deterministic score/ties. Phase 3 endpoints retain their original five-result contract; assistant internally requests up to 24 before session exclusion.
6. Remove shown recipes when alternatives exist. If exhausted, explicitly announce restart. Take at most five safe ranked candidates. Send only slug/name/duration/match counts plus ephemeral intent to the chooser; no instructions, stock quantities, account/email, saved allergy list or full recipe documents.
7. Validate chosen slug belongs to that exact allowed set. Invalid/unavailable selection uses its deterministic first candidate. No candidate means no model choice call and no invented recipe.
8. Build explanation from trusted time/pantry/goal/like facts. Model reason codes are bounded but model prose is never rendered. Ingredient quantities come exclusively from `scale_recipe`; later basket requests use the unchanged Phase 2 service.

Allergies always win over likes, goals, pantry, current requests and model output. A saved vegetarian profile plus chicken request produces a conflict. Milk allergy plus cheese request cannot produce a cheese recipe. Unsupported time limits never create a faster fictional recipe. Known/incomplete exclusions do not establish product-label, cross-contact or medical safety; existing Turkish safety disclosures remain visible.

## Follow-up, repetition and fallback limits

The home panel keeps current intent/shown recipes only in React state. “Başka Öner” requests another compatible unseen recipe; exhaustion is announced and resets the local cycle. “Tavuk olmasın” adds a canonical exclusion; “Bunu 4 kişilik yapacağım” changes current servings only; “Daha hızlı olsun” with current_slug tightens catalog time. New Decision, reload, logout/user change clear session state. Legacy structured form and its APIs remain usable; activating either flow clears the other result so the home shows one primary decision.

Offline interpretation is **not AI** or general Turkish understanding. It supports exact aliases with a small suffix list, explicit numeric minutes/servings, ingredient negation, pantry presence, previous-ingredient avoidance, and a few qualitative goal/diet phrases. Examples: “Param az kaldı”, “Proteinli olsun ama makarna istemiyorum”, “Evde tavuk var”, “Dün tavuk yedim”, “Ne yiyeceğimi bilmiyorum”. Users can inspect understood ingredient names and use structured controls when interpretation is insufficient. It does not infer arbitrary allergies from prose; record them separately in profile settings. Mixed clauses/negation have language limits. Equipment requirements (including oven/pot requests) are not reliably encoded in the catalog and therefore block selection transparently. Current exclusions accumulate; use Yeni Karar to clear them. There is no persistent meal history, culinary substitution, clinical nutrition or price inference.

## Privacy, cost and observability

With AI enabled, raw current text and minimal previous ephemeral intent are sent to the configured provider. Do not enter sensitive information unnecessarily; deployment needs a reviewed provider privacy/retention agreement. store=false is not a claim of zero provider retention. Saved pantry amounts, passwords, cookies, tokens, email and stock arithmetic are not sent. No prompts or conversation history are stored by Tencerem. Operation logs include configured model, operation, duration, success/failure category and fallback flag, never raw errors, prompts or key material.

Default disabled configuration incurs no provider cost. Public enablement still requires deployment-grade distributed abuse controls, spend budgets and reviewed logging/privacy. The local IP limit is shared by clients behind the Next proxy, is process-local and is not production-grade cost protection. Provider failure is not a reason to weaken safety filters. No background jobs, autonomous tools, vector infrastructure, web search or agents are present.

## Verification and brand audit

Fake providers and httpx MockTransport cover interpretation, malformed values, refusals/errors, timeouts, allowed-set validation, fail-closed constraints, prompt injection, ephemeral state, pantry isolation, deterministic quantities and logging. `scripts/assistant-smoke.py` exercises HTTP choice/fallback without a key or database. `scripts/assistant-browser-smoke.cjs` checks the live fallback UI. See VERIFICATION.md for actual results and exact commands.

Active package names, API/OpenAPI title, UI, metadata, Compose labels and ingredient/recipe provenance already used Tencerem. Updated browser metadata/tagline and stale home copy. Repository paths in setup commands and documentation now use `G:\tencerem\app`. No imports, migration identifiers, DB names, volumes or Git history were cosmetically renamed.

Real PostgreSQL runtime verification is still blocked by the previously documented missing disposable environment. SQLite account tests/browser checks are isolated evidence only. Phase 5 now adds a separate deterministic demo market-pricing engine; it makes no AI calls or arithmetic requests and does not send the product catalog to the model. Actual PostgreSQL, provider evaluation and deployment/privacy/abuse hardening remain open before public integrations.
