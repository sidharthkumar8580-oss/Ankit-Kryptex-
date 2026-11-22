const AGNES_BASE = (Netlify.env.get("AGNES_BASE_URL") || "https://apihub.agnes-ai.com").replace(/\/$/, "");

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" }
  });
}

async function agnesFetch(path, options = {}) {
  const key = Netlify.env.get("AGNES_API_KEY") || "";
  if (!key) return json({ detail: "Agnes API key Netlify ke Environment variables mein set nahi hai." }, 503);
  const response = await fetch(AGNES_BASE + path, {
    ...options,
    headers: { authorization: `Bearer ${key}`, "content-type": "application/json", ...(options.headers || {}) }
  });
  const raw = await response.text();
  let data;
  try { data = JSON.parse(raw); } catch { data = { detail: raw.slice(0, 1200) }; }
  if (!response.ok) return json({ detail: data.detail || data.message || "Agnes API request failed." }, response.status);
  return data;
}

export default async (request) => {
  const url = new URL(request.url);
  const path = url.pathname;
  const action = url.searchParams.get("action") || "";

  if ((action === "image" || path.endsWith("/api/media/image")) && request.method === "POST") {
    let body;
    try { body = await request.json(); } catch { return json({ detail: "Invalid JSON body." }, 400); }
    if (!body.prompt || typeof body.prompt !== "string" || body.prompt.length > 2000) return json({ detail: "Prompt is required (max 2000 characters)." }, 400);
    if (!["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"].includes(body.ratio || "1:1")) return json({ detail: "Unsupported aspect ratio." }, 400);
    if (!["1K", "2K", "3K", "4K"].includes(body.resolution || "1K")) return json({ detail: "Choose a supported image resolution." }, 400);
    const payload = {
      model: "agnes-image-2.1-flash",
      prompt: body.prompt,
      size: body.resolution || "1K",
      n: 1,
      extra_body: { ratio: body.ratio || "1:1", response_format: "url" }
    };
    if (body.reference_image) payload.extra_body.image = [body.reference_image];
    const data = await agnesFetch("/v1/images/generations", { method: "POST", body: JSON.stringify(payload) });
    if (data instanceof Response) return data;
    const item = (data.data || [{}])[0];
    const resultUrl = item.url || (item.b64_json ? "data:image/png;base64," + item.b64_json : null);
    if (!resultUrl) return json({ detail: "Agnes response mein image URL nahi mila." }, 502);
    return json({ type: "image", url: resultUrl, model: "agnes-image-2.1-flash" });
  }

  if ((action === "video" || path.endsWith("/api/media/video")) && request.method === "POST") {
    let body;
    try { body = await request.json(); } catch { return json({ detail: "Invalid JSON body." }, 400); }
    if (!body.prompt || typeof body.prompt !== "string" || body.prompt.length > 2000) return json({ detail: "Prompt is required (max 2000 characters)." }, 400);
    if (!["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"].includes(body.ratio || "9:16")) return json({ detail: "Unsupported aspect ratio." }, 400);
    const resolution = body.resolution || "720P";
    const model = ["1080P", "1K", "2K"].includes(resolution) ? "agnes-video-2.5" : "agnes-video-2.5-flash";
    const size = model === "agnes-video-2.5" ? resolution : "720P";
    let prompt = body.prompt;
    if (body.mode === "multi") prompt = "Create a coherent multi-shot story with 2 to 5 visually distinct cinematic shots, clear shot transitions, consistent subjects and a beginning, middle and ending. " + prompt;
    const payload = {
      model,
      prompt,
      mode: body.reference_image ? "img2video" : "text",
      seconds: String(Math.max(4, Math.min(12, Number(body.duration) || 5))),
      size,
      aspect_ratio: body.ratio || "9:16"
    };
    if (body.reference_image) payload.first_frame = body.reference_image;
    const data = await agnesFetch("/v1/videos", { method: "POST", body: JSON.stringify(payload) });
    if (data instanceof Response) return data;
    const videoId = data.video_id || data.id || data.task_id;
    if (!videoId) return json({ detail: "Agnes response mein video task ID nahi mila." }, 502);
    return json({ type: "video", video_id: videoId, model, status: data.status || "processing", raw: data });
  }

  const videoMatch = path.match(/\/api\/media\/video\/([^/]+)$/);
  if ((action === "status" || videoMatch) && request.method === "GET") {
    const key = Netlify.env.get("AGNES_API_KEY") || "";
    if (!key) return json({ detail: "Agnes API key Netlify ke Environment variables mein set nahi hai." }, 503);
    const requestedVideoId = url.searchParams.get("video_id") || (videoMatch ? decodeURIComponent(videoMatch[1]) : "");
    if (!requestedVideoId || requestedVideoId.length > 300) return json({ detail: "Invalid video ID." }, 400);
    const model = url.searchParams.get("model_name") || "agnes-video-2.5-flash";
    if (!["agnes-video-2.5", "agnes-video-2.5-flash"].includes(model)) return json({ detail: "Unsupported video model." }, 400);
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
