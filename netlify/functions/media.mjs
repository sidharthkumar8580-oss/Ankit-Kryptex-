const AGNES_BASE = (Netlify.env.get("AGNES_BASE_URL") || "https://apihub.agnes-ai.com").replace(/\/$/, "");

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" }
  });
}

function agnesKeys() {
  return [...new Set([
    Netlify.env.get("AGNES_API_KEY"),
    Netlify.env.get("AGNES_API_KEY1"),
    Netlify.env.get("AGNES_API_KEY2"),
    Netlify.env.get("AGNES_API_KEY3"),
    Netlify.env.get("AGNES_KEY1"),
    Netlify.env.get("AGNES_KEY2"),
    Netlify.env.get("AGNES_VIDEO_KEY")
  ].filter(Boolean))];
}

async function agnesFetch(path, options = {}) {
  const keys = agnesKeys();
  if (!keys.length) return json({ detail: "Agnes API key Netlify ke Environment variables mein set nahi hai." }, 503);
  const retryable = new Set([401, 402, 403, 408, 429, 500, 502, 503, 504]);
  let lastResponse = null;
  for (let index = 0; index < keys.length; index++) {
    try {
      const response = await fetch(AGNES_BASE + path, {
        ...options,
        headers: { authorization: "Bearer " + keys[index], "content-type": "application/json", ...(options.headers || {}) }
      });
      const raw = await response.text().catch(() => "");
      let data = {};
      try { data = raw.trim() ? JSON.parse(raw) : {}; } catch { data = { detail: raw.slice(0, 500) }; }
      // Some Agnes endpoints return model/quota errors inside HTTP 200 JSON.
      const embeddedError = Boolean(data.error || data.code || data.success === false || data.status === "failed");
      if (response.ok && !embeddedError) {
        if (!raw.trim()) return json({ detail: "Agnes API ne empty response diya.", code: "empty_upstream_response" }, 502);
        return data;
      }
      const errorObject = data.error || {};
      const status = response.ok ? (Number(data.status_code || errorObject.status || 400) || 400) : response.status;
      lastResponse = json({
        detail: data.detail || data.message || errorObject.message || errorObject.detail || ("Agnes API HTTP " + status),
        code: data.code || errorObject.code || null,
        request_id: data.request_id || errorObject.request_id || null
      }, status);
      if (index === keys.length - 1) return lastResponse;
      if (![400, 401, 402, 403, 408, 409, 429, 500, 502, 503, 504].includes(status) || index === keys.length - 1) return lastResponse;
    } catch (error) {
      lastResponse = json({ detail: "Agnes server se connection nahi ho paya: " + (error?.message || "network error") }, 502);
      if (index === keys.length - 1) return lastResponse;
    }
  }
  return lastResponse || json({ detail: "Agnes API request failed." }, 502);
}

async function withModelFallback(path, payload, candidates) {
  let lastResponse = null;
  for (const model of candidates) {
    const result = await agnesFetch(path, { method: "POST", body: JSON.stringify({ ...payload, model }) });
    if (!(result instanceof Response)) return { data: result, model };
    lastResponse = result;
    const detail = await result.clone().json().catch(() => ({}));
    const message = String(detail.detail || detail.message || detail.error?.message || detail.code || detail.error?.code || "").toLowerCase();
    const code = String(detail.code || detail.error?.code || "").toLowerCase();
    const modelUnavailable = [400, 404, 410, 422].includes(result.status) &&
      (message.includes("model") || message.includes("not found") || message.includes("unsupported") || message.includes("invalid") || message.includes("not available") || code.includes("model"));
    const capacityIssue = [429, 503].includes(result.status) &&
      (message.includes("queue") || message.includes("busy") || message.includes("rate") || message.includes("limit") || message.includes("capacity") || message.includes("temporar"));
    const temporaryServerIssue = [500, 502, 504].includes(result.status);
    // Never rotate models to hide exhausted quota or invalid credentials.
    if (!modelUnavailable && !capacityIssue && !temporaryServerIssue) return result;
  }
  return lastResponse || json({ detail: "No compatible Agnes model is currently available." }, 503);
}

function hfToken() { return Netlify.env.get("HUGGINGFACE_VIDEOANDIMAGE_API_KEY") || Netlify.env.get("HF_TOKEN") || ""; }

async function hfImageFallback(prompt, ratio) {
  const token = hfToken();
  if (!token) return null;
  const models = ["stabilityai/stable-diffusion-xl-base-1.0", "black-forest-labs/FLUX.1-dev"];
  let last = "Hugging Face image fallback unavailable.";
  for (const model of models) {
    try {
      const response = await fetch("https://router.huggingface.co/hf-inference/models/" + model, {
        method: "POST", headers: { authorization: "Bearer " + token, "content-type": "application/json", accept: "image/*" },
        body: JSON.stringify({ inputs: prompt + " . Aspect ratio: " + (ratio || "1:1") })
      });
      if (!response.ok) { last = "HF " + model + " returned HTTP " + response.status + ": " + (await response.text()).slice(0, 250); continue; }
      const type = response.headers.get("content-type") || "image/png";
      if (!type.startsWith("image/")) { last = "HF image endpoint did not return an image."; continue; }
      const bytes = new Uint8Array(await response.arrayBuffer());
      let binary = ""; for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      return { type: "image", url: "data:" + type + ";base64," + btoa(binary), model: "huggingface:" + model };
    } catch (error) { last = error?.message || String(error); }
  }
  throw new Error(last);
}

const HF_VIDEO_SPACES = [
  { id: "Wan-AI/Wan2.1-T2V-1.3B", seconds: false },
  { id: "genmo/mochi-1-preview", seconds: false },
  { id: "Lightricks/LTX-Video", seconds: true },
  { id: "THUDM/CogVideoX-5b", seconds: false },
  { id: "Tencent/HunyuanVideo", seconds: false },
  { id: "Wan-AI/Wan2.2-T2V-A14B", seconds: false },
  { id: "Skywork/SkyReels-V2", seconds: true }
];

async function submitHfVideo(prompt, requestedDuration) {
  const token = hfToken(); if (!token) throw new Error("Hugging Face token is not configured.");
  const duration = Math.max(4, Math.min(15, Number(requestedDuration) || 5));
  const errors = [];
  for (const item of HF_VIDEO_SPACES) {
    try {
      const endpoint = "https://" + item.id.replace("/", "-") + ".hf.space/gradio_api/call/generate";
      const data = item.seconds ? [prompt, duration] : [prompt];
      let response = await fetch(endpoint, { method: "POST", headers: { authorization: "Bearer " + token, "content-type": "application/json" }, body: JSON.stringify({ data }) });
      if (!response.ok) { errors.push(item.id + " HTTP " + response.status); continue; }
      const accepted = await response.json();
      if (!accepted.event_id) { errors.push(item.id + " did not return an event id"); continue; }
      return { type: "video", video_id: "hf:" + encodeURIComponent(item.id) + ":" + encodeURIComponent(accepted.event_id), model: "huggingface:" + item.id, status: "processing", provider: "huggingface" };
    } catch (error) { errors.push(item.id + ": " + (error?.message || "request failed")); }
  }
  throw new Error("Hugging Face Spaces fallback failed: " + errors.slice(0, 3).join("; "));
}

async function pollHfVideo(videoId) {
  const token = hfToken();
  const parts = String(videoId).split(":");
  if (parts.length < 3 || !token) return json({ detail: "Invalid Hugging Face video task." }, 400);
  const space = decodeURIComponent(parts[1]); const eventId = decodeURIComponent(parts.slice(2).join(":"));
  const endpoint = "https://" + space.replace("/", "-") + ".hf.space/gradio_api/call/generate/" + encodeURIComponent(eventId);
  try {
    const response = await fetch(endpoint, { headers: { authorization: "Bearer " + token }, signal: AbortSignal.timeout(12000) });
    if (!response.ok) return json({ status: "processing", detail: "Hugging Face Space is still processing (HTTP " + response.status + ")." });
    const raw = await response.text();
    const lines = raw.split(/\\r?\\n/);
    let event = "", payload = null;
    for (const line of lines) { if (line.startsWith("event:")) event = line.slice(6).trim(); if (line.startsWith("data:")) { try { payload = JSON.parse(line.slice(5).trim()); } catch {} } }
    if (event === "complete" && payload) {
      const walk = (value) => { if (!value) return null; if (typeof value === "string" && /^https?:\\/\\//.test(value) && /\\.(mp4|webm|mov)(\\?|$)/i.test(value)) return value; if (Array.isArray(value)) { for (const v of value) { const found = walk(v); if (found) return found; } } if (typeof value === "object") { for (const k of ["url", "video", "path", "name"]) { const found = walk(value[k]); if (found) return found; } for (const v of Object.values(value)) { const found = walk(v); if (found) return found; } } return null; };
      const videoUrl = walk(payload);
      return json(videoUrl ? { status: "completed", url: videoUrl, model: "huggingface:" + space } : { status: "failed", error: "Space completed but did not return a public video URL." });
    }
    if (event === "error") return json({ status: "failed", error: typeof payload === "string" ? payload : "Hugging Face generation failed." });
    return json({ status: "processing", progress: null, detail: "Hugging Face is generating your video…" });
  } catch (error) { return json({ status: "processing", detail: "Hugging Face generation is still running." }); }
}

export default async (request) => {
  const url = new URL(request.url);
  const path = url.pathname;
  const action = url.searchParams.get("action") || "";

  if ((action === "chat" || path.endsWith("/api/media/chat")) && request.method === "POST") {
    let body;
    try { body = await request.json(); } catch { return json({ detail: "Invalid JSON body." }, 400); }
    if (!Array.isArray(body.messages) || !body.messages.length) return json({ detail: "Chat messages are required." }, 400);
    const models = ["agnes-1.5-flash","agnes-2.0-flash","agnes-2.5-flash","agnes-3.0-flash"];
    const selected = models.includes(body.model) ? body.model : "agnes-2.5-flash";
    const candidates = [selected, ...models.filter(m => m !== selected)];
    const result = await withModelFallback("/v1/chat/completions", {
      messages: body.messages.slice(-30), temperature: 0.7, max_tokens: 2048, stream: false
    }, candidates);
    if (result instanceof Response) return result;
    const choice = result.data?.choices?.[0]?.message;
    const reply = choice?.content || choice?.reasoning_content;
    if (!reply || (typeof reply === "string" && !reply.trim())) {
      return json({ detail: "Agnes model ne reply return nahi kiya. Fallback models bhi try kiye gaye; thodi der baad dobara try karein.", code: "empty_chat_completion", model: result.model }, 502);
    }
    return json({ reply, model: result.model });
  }

  if ((action === "image" || path.endsWith("/api/media/image")) && request.method === "POST") {
    let body;
    try { body = await request.json(); } catch { return json({ detail: "Invalid JSON body." }, 400); }
    if (!body.prompt || typeof body.prompt !== "string" || body.prompt.length > 2000) return json({ detail: "Prompt is required (max 2000 characters)." }, 400);
    if (!["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"].includes(body.ratio || "1:1")) return json({ detail: "Unsupported aspect ratio." }, 400);
    
    const payload = {
      model: body.model || "agnes-image-2.0-flash",
      prompt: body.prompt,
      size: ({ "1K": "1024x1024", "2K": "2048x2048", "3K": "3072x3072", "4K": "4096x4096" })[body.resolution || "1K"] || "1024x1024",
      n: 1,
      extra_body: { response_format: "url" }
    };
    if (body.reference_image) payload.extra_body.image = [body.reference_image];
    const imageModels = ["agnes-image-2.0-flash","agnes-image-2.1-flash","agnes-image-2.5-flash","agnes-image-2.0"];
    const selectedImageModel = imageModels.includes(payload.model) ? payload.model : imageModels[0];
    const imageResult = await withModelFallback("/v1/images/generations", payload, [selectedImageModel, ...imageModels.filter(m=>m!==selectedImageModel)]);
    if (imageResult instanceof Response) {
      const fallback = await hfImageFallback(body.prompt, body.ratio).catch(() => null);
      if (fallback) return json(fallback);
      return imageResult;
    }
    const data = imageResult.data;
    if (data.error || data.code) return json({ detail: data.error?.message || data.message || data.code || "Agnes image generation failed.", code: data.code || null }, 502);
    const item = (data.data || [{}])[0];
    const resultUrl = item.url || (item.b64_json ? "data:image/png;base64," + item.b64_json : null);
    if (!resultUrl) return json({ detail: "Agnes response mein image URL nahi mila." }, 502);
    return json({ type: "image", url: resultUrl, model: imageResult.model });
  }

  if ((action === "video" || path.endsWith("/api/media/video")) && request.method === "POST") {
    let body; try { body = await request.json(); } catch { return json({ detail: "Invalid JSON body." }, 400); }
    if (!body.prompt || typeof body.prompt !== "string" || body.prompt.length > 2000) return json({ detail: "Prompt is required (max 2000 characters)." }, 400);
    if (!["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"].includes(body.ratio || "9:16")) return json({ detail: "Unsupported aspect ratio." }, 400);
    try {
      const hfTask = await submitHfVideo(body.prompt, body.duration);
      return json(hfTask);
    } catch (hfError) {
      const selectedVideoModel = "agnes-video-2.5-flash";
      let prompt = body.prompt;
      if (body.mode === "multi") prompt = "Create a coherent multi-shot story with 2 to 5 visually distinct cinematic shots, clear shot transitions, consistent subjects and a beginning, middle and ending. " + prompt;
      const payload = { model: selectedVideoModel, prompt, mode: body.reference_image ? "img2video" : "text", seconds: String(Math.max(4, Math.min(12, Number(body.duration) || 5))), size: "720P", aspect_ratio: body.ratio || "9:16" };
      if (body.reference_image) payload.first_frame = body.reference_image;
      const videoResult = await agnesFetch("/v1/videos", { method: "POST", body: JSON.stringify(payload) });
      if (videoResult instanceof Response) return json({ detail: "Hugging Face fallback unavailable (" + hfError.message + "). Agnes fallback: " + (await videoResult.clone().json().catch(() => ({}))).detail }, videoResult.status);
      const videoId = videoResult.video_id || videoResult.id || videoResult.task_id;
      if (!videoId) return json({ detail: "Neither Hugging Face nor Agnes returned a video task ID." }, 502);
      return json({ type: "video", video_id: videoId, model: selectedVideoModel, status: videoResult.status || "processing", provider: "agnes", fallback_reason: hfError.message });
    }
  }
  const videoMatch = path.match(/\/api\/media\/video\/([^/]+)$/);
  if ((action === "status" || videoMatch) && request.method === "GET") {
    const requestedVideoId = url.searchParams.get("video_id") || (videoMatch ? decodeURIComponent(videoMatch[1]) : "");
    if (requestedVideoId.startsWith("hf:")) return await pollHfVideo(requestedVideoId);
    const keys = agnesKeys();
    if (!keys.length) return json({ detail: "Agnes API key Netlify ke Environment variables mein set nahi hai." }, 503);
    if (!requestedVideoId || requestedVideoId.length > 300) return json({ detail: "Invalid video ID." }, 400);
    const model = url.searchParams.get("model_name") || "agnes-video-2.5-flash";
    if (!["agnes-video-2.5", "agnes-video-2.5-flash", "agnes-video-v2.0", "agnes-video-h3-moe"].includes(model)) return json({ detail: "Unsupported video model." }, 400);
    const upstream = new URL(AGNES_BASE + "/agnesapi");
    upstream.searchParams.set("video_id", requestedVideoId);
    upstream.searchParams.set("model_name", model);
    let response;
    for (const key of keys) {
      response = await fetch(upstream, { headers: { authorization: `Bearer ${key}` } });
      if (response.status !== 401 && response.status !== 403) break;
    }
    const raw = await response.text();
    let data;
    try { data = JSON.parse(raw); } catch { data = { detail: raw.slice(0, 1200) }; }
    return json(response.ok ? data : { detail: data.detail || data.message || "Agnes status check failed." }, response.status);
  }

  if ((action === "download" || path.endsWith("/api/media/download")) && request.method === "GET") {
    const target = url.searchParams.get("url");
    try {
      const parsed = new URL(target);
      if (parsed.protocol !== "https:") return json({ detail: "Only HTTPS media URLs are supported." }, 400);
      return Response.redirect(parsed.toString(), 302);
    } catch { return json({ detail: "Invalid media URL." }, 400); }
  }

  return json({ detail: "Not found." }, 404);
};
