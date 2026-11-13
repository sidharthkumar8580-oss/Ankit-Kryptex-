const json=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
export default async (req)=>{
 if(req.method==='GET'){const hasKey=!!Netlify.env.get('GEMINI_API_KEY');return json({ok:hasKey,provider:hasKey?'Gemini API':'Not configured',error:hasKey?undefined:'Server AI key is not configured.'},hasKey?200:503)}
 if(req.method!=='POST')return json({error:'Method not allowed'},405);
 try{
  const body=await req.json();const message=String(body.message||'').trim();if(!message)return json({error:'Message is required.'},400);if(message.length>12000)return json({error:'Request is too long.'},413);
  const hub=Netlify.env.get('KRYPTEX_HUB_API_URL');
  if(hub){const base=hub.replace(/\\/$/,'');const target=base.endsWith('/chat')?base:base+'/chat';const form=new FormData();form.set('message',message);form.set('history',JSON.stringify(Array.isArray(body.history)?body.history:[]));const upstream=await fetch(target,{method:'POST',body:form,signal:AbortSignal.timeout(55000)});const data=await upstream.json();if(!upstream.ok)return json({error:data.reply||'Kryptex Hub API request failed.'},502);return json(data)}
  const key=Netlify.env.get('GEMINI_API_KEY');if(!key)return json({error:'AI backend is installed, but the server has no GEMINI_API_KEY. Add it to the hosting environment variables.'},503);
  const model=Netlify.env.get('GEMINI_MODEL')||'gemini-2.5-flash';const upstream=await fetch('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent?key='+encodeURIComponent(key),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({systemInstruction:{parts:[{text:'You are Kryptex AI, a clear, safe, helpful assistant. Reply in the language the user uses. Be accurate and concise. For school topics explain concepts simply.'}]},contents:[{role:'user',parts:[{text:message}]}],generationConfig:{temperature:0.7,maxOutputTokens:1800}}),signal:AbortSignal.timeout(55000)});
  const data=await upstream.json();if(!upstream.ok)return json({error:data.error?.message||'Gemini provider request failed.'},502);const reply=data.candidates?.[0]?.content?.parts?.map(p=>p.text||'').join('')||'No response was generated.';return json({reply,provider:model});
 }catch(e){return json({error:e.name==='TimeoutError'?'AI provider timed out. Try again.':e.message||'Unexpected backend error.'},500)}
};
export const config={path:'/api/ai',method:['GET','POST'],rateLimit:{action:'rate_limit',aggregateBy:'ip',windowSize:60,windowLimit:20}};