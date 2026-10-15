"use client";
import {createContext,useContext,useEffect,useState,useCallback} from "react";
import type {User} from "../lib/account";
import {accountFetch} from "../lib/account";
const Context=createContext<{user:User|null;ready:boolean;refresh:()=>Promise<User|null>}>({user:null,ready:false,refresh:async()=>null});
export function AccountProvider({children}:{children:React.ReactNode}) {
 const [user,setUser]=useState<User|null>(null);const [ready,setReady]=useState(false);
 const refresh=useCallback(async()=>{try{const next=await accountFetch<User>("me");setUser(next);return next;}catch{setUser(null);return null;}finally{setReady(true);}},[]);
 useEffect(()=>{let active=true;accountFetch<User>("me").then(next=>{if(active)setUser(next);}).catch(()=>{if(active)setUser(null);}).finally(()=>{if(active)setReady(true);});return ()=>{active=false;};},[]);
 return <Context.Provider value={{user,ready,refresh}}>{children}</Context.Provider>;
}
export const useAccount=()=>useContext(Context);
