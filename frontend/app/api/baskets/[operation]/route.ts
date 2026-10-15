import {NextResponse} from "next/server";
import {forwardPreferences} from "../../../../lib/backend-proxy";
export async function POST(request:Request,context:{params:Promise<{operation:string}>}){
 const {operation}=await context.params;
 if(!["price","compare"].includes(operation))return NextResponse.json({error:{message:"İstek bulunamadı."}},{status:404});
 const response=await forwardPreferences(request,`/api/v1/baskets/${operation}`,65536);
 response.headers.set("Cache-Control","no-store");
 return response;
}
