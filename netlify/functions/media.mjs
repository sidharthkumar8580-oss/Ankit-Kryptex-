const AGNES_BASE = (Netlify.env.get("AGNES_BASE_URL") || "https://apihub.agnes-ai.com").replace(/\/$/, "");

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" }
  });
}

async function agnesFetch(path, options = {}) {
  const key = Netlify.env.get("AGNES_API_KEY") || Netlify.env.get("AGNES_VIDEO_KEY") || "";
  if (!key) return json({ detail: "Agnes API key Netlify ke Environment variables mein set nahi hai." }, 503);
  const response = await fetch(AGNES_BASE + path, {
    ...options,
    headers: { authorization: `Bearer ${key}`, "content-type": "application/json", ...(options.headers || {}) }
  });
  const raw = await response.text();
  let data;
  try { data = JSON.parse(raw); } catch { data = { detail: raw.slice(0, 1200) }; }
  if (!response.ok) return json({ detail: data.detail || data.message || "Agnes API request failed.", code: data.code || null, request_id: data.request_id || null }, response.status);
  return data;
}

async function withModelFallback(path, payload, candidates) {
  let lastResponse = null;
  for (const model of candidates) {
    const result = await agnesFetch(path, { method: "POST", body: JSON.stringify({ ...payload, model }) });
    if (!(result instanceof Response)) return { data: result, model };
    lastResponse = result;
    const detail = await result.clone().json().catch(() => ({}));
    const message = String(detail.detail || detail.message || detail.code || "").toLowerCase();
    const modelUnavailable = [400, 404, 422].includes(result.status) &&
      (message.includes("model") || message.includes("not found") || message.includes("unsupported") || message.includes("invalid"));
    if (!modelUnavailable) return result;
  }
  return lastResponse || json({ detail: "No compatible Agnes model is currently available." }, 503);
}

export default async (request) => {
  const url = new URL(request.url);
  const path = url.pathname;
  const action = url.searchParams.get("action") || "";

  if ((action === "chat" || path.endsWith("/api/media/chat")) && request.method === "POST") {
    let body;
    try { body = await request.json(); } catch { return json({ detail: "Invalid JSON body." }, 400); }
    if (!Array.isArray(body.messages) || !body.messages.length) return json({ detail: "Chat messages are required." }, 400);
    const models = ["agnes-1.5-flash","agnes-2.0-flash","agnes-2.5-flash","agnes-2.5-pro-alpha","agnes-3.0-flash"];
    const selected = models.includes(body.model) ? body.model : "agnes-2.5-flash";
    const candidates = [selected, ...models.filter(m => m !== selected).reverse()];
    const result = await withModelFallback("/v1/chat/completions", {
      messages: body.messages.slice(-30), temperature: 0.7, max_tokens: 2048
    }, candidates);
    if (result instanceof Response) return result;
    const choice = result.data.choices?.[0]?.message;
    return json({ reply: choice?.content || choice?.reasoning_content || "Agnes ne empty response diya.", model: result.model });
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
    if (imageResult instanceof Response) return imageResult;
    const data = imageResult.data;
    if (data.error || data.code) return json({ detail: data.error?.message || data.message || data.code || "Agnes image generation failed.", code: data.code || null }, 502);
    const item = (data.data || [{}])[0];
    const resultUrl = item.url || (item.b64_json ? "data:image/png;base64," + item.b64_json : null);
    if (!resultUrl) return json({ detail: "Agnes response mein image URL nahi mila." }, 502);
    return json({ type: "image", url: resultUrl, model: imageResult.model });
  }

  if ((action === "video" || path.endsWith("/api/media/video")) && request.method === "POST") {
    let body;
    try { body = await request.json(); } catch { return json({ detail: "Invalid JSON body." }, 400); }
    if (!body.prompt || typeof body.prompt !== "string" || body.prompt.length > 2000) return json({ detail: "Prompt is required (max 2000 characters)." }, 400);
    if (!["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"].includes(body.ratio || "9:16")) return json({ detail: "Unsupported aspect ratio." }, 400);
    const resolution = body.resolution || "720P";
    const videoModels = ["agnes-video-2.5-flash","agnes-video-2.5","agnes-video-v2.0","agnes-video-h3-moe"];
    const selectedVideoModel = videoModels.includes(body.model) ? body.model : (["1080P","1K","2K"].includes(resolution) ? "agnes-video-2.5" : "agnes-video-2.5-flash");
    const size = selectedVideoModel === "agnes-video-2.5" ? resolution : "720P";
    let prompt = body.prompt;
    if (body.mode === "multi") prompt = "Create a coherent multi-shot story with 2 to 5 visually distinct cinematic shots, clear shot transitions, consistent subjects and a beginning, middle and ending. " + prompt;
    const payload = {
      model: selectedVideoModel,
      prompt,
      mode: body.reference_image ? "img2video" : "text",
      seconds: String(Math.max(4, Math.min(12, Number(body.duration) || 5))),
      size,
      aspect_ratio: body.ratio || "9:16"
    };
    if (body.reference_image) payload.first_frame = body.reference_image;
    const videoResult = await withModelFallback("/v1/videos", payload, [selectedVideoModel, ...videoModels.filter(m=>m!==selectedVideoModel)]);
    if (videoResult instanceof Response) return videoResult;
    const data = videoResult.data;
    const model = videoResult.model;
    const videoId = data.video_id || data.id || data.task_id;
    if (!videoId) return json({ detail: "Agnes response mein video task ID nahi mila." }, 502);
    return json({ type: "video", video_id: videoId, model, status: data.status || "processing", raw: data });
  }

  const videoMatch = path.match(/\/api\/media\/video\/([^/]+)$/);
  if ((action === "status" || videoMatch) && request.method === "GET") {
    const key = Netlify.env.get("AGNES_API_KEY") || Netlify.env.get("AGNES_VIDEO_KEY") || "";
    if (!key) return json({ detail: "Agnes API key Netlify ke Environment variables mein set nahi hai." }, 503);
    const requestedVideoId = url.searchParams.get("video_id") || (videoMatch ? decodeURIComponent(videoMatch[1]) : "");
    if (!requestedVideoId || requestedVideoId.length > 300) return json({ detail: "Invalid video ID." }, 400);
    const model = url.searchParams.get("model_name") || "agnes-video-2.5-flash";
    if (!["agnes-video-2.5", "agnes-video-2.5-flash", "agnes-video-v2.0", "agnes-video-h3-moe"].includes(model)) return json({ detail: "Unsupported video model." }, 400);
    const upstream = new URL(AGNES_BASE + "/agnesapi");
    upstream.searchParams.set("video_id", requestedVideoId);
    upstream.searchParams.set("model_name", model);
    const response = await fetch(upstream, { headers: { authorization: `Bearer ${key}` } });
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
