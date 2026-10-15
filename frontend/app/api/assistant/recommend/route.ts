import {NextResponse} from "next/server";
export async function POST(request:Request){
 const body=await request.text();
 if(new TextEncoder().encode(body).length>32768)return NextResponse.json({error:{message:"İstek çok büyük."}},{status:413});
 try{
  const response=await fetch(`${process.env.BACKEND_URL??"http://127.0.0.1:8000"}/api/v1/assistant/recommend`,{method:"POST",body,headers:{"Content-Type":"application/json","Origin":request.headers.get("origin")??"","X-Tencerem-CSRF":request.headers.get("x-tencerem-csrf")??""},cache:"no-store",signal:AbortSignal.timeout(20000)});
  return new NextResponse(await response.text(),{status:response.status,headers:{"Content-Type":"application/json","Cache-Control":"no-store"}});
 }catch{return NextResponse.json({error:{message:"Karar servisine ulaşılamıyor."}},{status:502});}
}
