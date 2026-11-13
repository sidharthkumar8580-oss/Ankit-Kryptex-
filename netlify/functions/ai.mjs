const cors = {
  'Access-Control-Allow-Origin': 'https://sidharthkumar8580-oss.github.io',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Cache-Control': 'no-store'
};
const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { ...cors, 'Content-Type': 'application/json' }
});
export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
  if (req.method === 'GET') {
    const hasHub = !!Netlify.env.get('KRYPTEX_HUB_API_URL');
    const hasGroq = !!Netlify.env.get('GROQ_API_KEY');
    const hasGemini = !!Netlify.env.get('GEMINI_API_KEY');
    const provider = hasHub ? 'Kryptex Hub API' : hasGroq ? 'Groq AI' : hasGemini ? 'Gemini AI' : 'Not configured';
    const ok = hasHub || hasGroq || hasGemini;
    return json({ ok, provider, error: ok ? undefined : 'Add GROQ_API_KEY to Netlify environment variables.' }, ok ? 200 : 503);
  }
  if (req.method !== 'POST') return json({ error: 'Method not allowed' }, 405);
  try {
    const body = await req.json();
    const message = String(body.message || '').trim();
    if (!message) return json({ error: 'Message is required.' }, 400);
    if (message.length > 12000) return json({ error: 'Request is too long.' }, 413);
    const hub = Netlify.env.get('KRYPTEX_HUB_API_URL');
    if (hub) {
      const base = hub.replace(/\/$/, '');
      const target = base.endsWith('/chat') ? base : base + '/chat';
      const form = new FormData();
      form.set('message', message);
      form.set('history', JSON.stringify(Array.isArray(body.history) ? body.history : []));
      const upstream = await fetch(target, { method: 'POST', body: form, signal: AbortSignal.timeout(55000) });
      const data = await upstream.json();
      if (!upstream.ok) return json({ error: data.reply || 'Kryptex Hub API request failed.' }, 502);
      return json(data);
    }
    const system = 'You are Kryptex AI, a helpful assistant for students and everyday creators. Reply in the language the user uses (Hindi, Hinglish or English). Explain school topics simply and accurately. For educational work, teach the method and do not fabricate facts. For writing tasks, produce useful, original drafts.';
    const history = Array.isArray(body.history) ? body.history.slice(-10).filter(x =>
      x && ['user', 'assistant'].includes(x.role) && typeof x.text === 'string'
    ).map(x => ({ role: x.role, content: x.text.slice(0, 4000) })) : [];
    const messages = [{ role: 'system', content: system }, ...history, { role: 'user', content: message }];
    const groqKey = Netlify.env.get('GROQ_API_KEY');
    if (groqKey) {
      const model = Netlify.env.get('GROQ_MODEL') || 'llama-3.3-70b-versatile';
      const upstream = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + groqKey, 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, messages, temperature: 0.7, max_completion_tokens: 1800 }),
        signal: AbortSignal.timeout(55000)
      });
      const data = await upstream.json();
      if (!upstream.ok) return json({ error: data.error?.message || 'Groq API request failed.' }, 502);
      return json({ reply: data.choices?.[0]?.message?.content || 'No response was generated.', provider: model });
    }
    const geminiKey = Netlify.env.get('GEMINI_API_KEY');
    if (!geminiKey) return json({ error: 'AI backend is installed, but GROQ_API_KEY is not configured on the server.' }, 503);
    const model = Netlify.env.get('GEMINI_MODEL') || 'gemini-2.5-flash';
    const upstream = await fetch('https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent?key=' + encodeURIComponent(geminiKey), {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: system }] },
        contents: [...history.map(x => ({ role: x.role === 'assistant' ? 'model' : 'user', parts: [{ text: x.content }] })), { role: 'user', parts: [{ text: message }] }],
        generationConfig: { temperature: 0.7, maxOutputTokens: 1800 }
      }),
      signal: AbortSignal.timeout(55000)
    });
    const data = await upstream.json();
    if (!upstream.ok) return json({ error: data.error?.message || 'Gemini provider request failed.' }, 502);
    return json({ reply: data.candidates?.[0]?.content?.parts?.map(p => p.text || '').join('') || 'No response was generated.', provider: model });
  } catch (e) {
    return json({ error: e.name === 'TimeoutError' ? 'AI provider timed out. Try again.' : e.message || 'Unexpected backend error.' }, 500);
  }
};
export const config = { path: '/api/ai', method: ['GET', 'POST', 'OPTIONS'], rateLimit: { action: 'rate_limit', aggregateBy: 'ip', windowSize: 60, windowLimit: 20 } };
