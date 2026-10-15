import { NextResponse } from "next/server";
export async function forwardPreferences(request: Request, path: string, maxBytes = 8192) {
  if (Number(request.headers.get("content-length")) > maxBytes) return NextResponse.json({ error: { code: "payload_too_large" } }, { status: 413 });
  const body = await request.text();
  if (new TextEncoder().encode(body).length > maxBytes) return NextResponse.json({ error: { code: "payload_too_large" } }, { status: 413 });
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://127.0.0.1:8000"}${path}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body, cache: "no-store", signal: AbortSignal.timeout(8000),
    });
    if (response.status === 422) return NextResponse.json(await response.json(), { status: 422 });
    if (!response.ok) throw new Error("Backend unavailable");
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: { code: "backend_unavailable", message: "Tarif servisine ulaşılamıyor." } }, { status: 502 });
  }
}
