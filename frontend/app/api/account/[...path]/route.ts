import {NextResponse} from "next/server";
export const dynamic="force-dynamic";
async function proxy(request:Request,context:{params:Promise<{path:string[]}>}){
 const {path}=await context.params;const route=path.join("/");
 const allowed = /^(auth\/(register|login|logout)|me(\/(preferences|pantry|recipes\/recommend|baskets\/preview|assistant\/recommend))?|me\/pantry\/[a-f0-9-]{36}|ingredients)$/.test(route);
 if(!allowed)return NextResponse.json({error:{message:"İstek bulunamadı."}},{status:404});
 const body=["GET","HEAD"].includes(request.method)?undefined:await request.text();
 if(body&&new TextEncoder().encode(body).length>65536)return NextResponse.json({error:{message:"İstek çok büyük."}},{status:413});
 try{
  const upstream=await fetch(`${process.env.BACKEND_URL??"http://127.0.0.1:8000"}/api/v1/${route}`,{method:request.method,body,headers:{"Content-Type":"application/json","Cookie":request.headers.get("cookie")??"","Origin":request.headers.get("origin")??"","X-Tencerem-CSRF":request.headers.get("x-tencerem-csrf")??""},cache:"no-store",redirect:"manual",signal:AbortSignal.timeout(route.endsWith("assistant/recommend")?20000:8000)});
  const response=new NextResponse(upstream.status===204?null:await upstream.text(),{status:upstream.status,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}});
  for(const cookie of upstream.headers.getSetCookie())response.headers.append("Set-Cookie",cookie);
  return response;
 }catch{return NextResponse.json({error:{message:"Hesap servisine ulaşılamıyor. Tekrar deneyin."}},{status:502,headers:{"Cache-Control":"no-store"}});}
}
export {proxy as GET,proxy as POST,proxy as PUT,proxy as PATCH,proxy as DELETE};
