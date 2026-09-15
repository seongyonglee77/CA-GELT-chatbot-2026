import kitSettings from "../../../prompts/deepgram_kit_code.json";
import kaiSettings from "../../../prompts/deepgram_kai_code.json";

const DEEPGRAM_AGENT_ENDPOINT = "https://agent.deepgram.com/v1/agent/converse";
const TOKEN_ENDPOINT = "https://api.deepgram.com/v1/auth/grant";
const AUDIO_FORMAT = { encoding: "linear16", sample_rate: 24000, container: "none" };
const SETTINGS_BY_PERSONA = { deepgram_kit: kitSettings, deepgram_kai: kaiSettings };

function corsHeaders(request, env) {
  const requestOrigin = request.headers.get("Origin");
  const allowedOrigin = env.ALLOWED_ORIGIN || "*";
  const origin = allowedOrigin === "*" || requestOrigin === allowedOrigin ? allowedOrigin === "*" ? "*" : allowedOrigin : "null";
  return { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Cache-Control": "no-store", Vary: "Origin" };
}

function json(request, env, body, init = {}) {
  return new Response(JSON.stringify(body), { ...init, headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders(request, env), ...(init.headers || {}) } });
}

function fromBase64(value) {
  const raw = atob(value);
  const bytes = new Uint8Array(raw.length);
  for (let index = 0; index < raw.length; index += 1) bytes[index] = raw.charCodeAt(index);
  return bytes;
}

async function toBase64(value) {
  let buffer = value;
  if (value instanceof Blob) buffer = await value.arrayBuffer();
  if (ArrayBuffer.isView(buffer)) {
    buffer = buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength);
  }
  const bytes = new Uint8Array(buffer);
  let result = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    result += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }
  return btoa(result);
}

async function issueToken(request, env) {
  if (!env.DEEPGRAM_API_KEY) return json(request, env, { error: "Worker secret DEEPGRAM_API_KEY is missing" }, { status: 500 });
  const response = await fetch(TOKEN_ENDPOINT, { method: "POST", headers: { Authorization: `Token ${env.DEEPGRAM_API_KEY}`, "Content-Type": "application/json" }, body: JSON.stringify({ ttl_seconds: 30 }) });
  const payload = await response.json().catch(() => null);
  if (!response.ok || typeof payload?.access_token !== "string") return json(request, env, { error: "Deepgram temporary token request failed" }, { status: 502 });
  return json(request, env, { access_token: payload.access_token, expires_in: payload.expires_in });
}

async function relay(request, env) {
  if (request.headers.get("Upgrade")?.toLowerCase() !== "websocket") return new Response("Expected WebSocket", { status: 426 });
  const pair = new WebSocketPair();
  const client = pair[0];
  const browser = pair[1];
  browser.accept();
  let upstream = null;
  let started = false;

  const send = (payload) => { if (browser.readyState === WebSocket.OPEN) browser.send(JSON.stringify(payload)); };
  const close = () => { try { upstream?.close(); } catch {} try { browser.close(); } catch {} };

  browser.addEventListener("message", async (event) => {
    try {
      if (typeof event.data !== "string") return;
      const message = JSON.parse(event.data);
      if (message.type === "start") {
        if (started) return send({ type: "error", message: "Session already started" });
        const personaId = message.persona_id;
        const settings = SETTINGS_BY_PERSONA[personaId];
        if (!settings) return send({ type: "error", message: "Unsupported persona" });
        const response = await fetch(DEEPGRAM_AGENT_ENDPOINT, { headers: { Upgrade: "websocket", Authorization: `Token ${env.DEEPGRAM_API_KEY}` } });
        upstream = response.webSocket;
        if (!upstream) return send({ type: "error", message: "Unable to connect to Deepgram Agent" });
        upstream.accept();
        started = true;
        let upstreamMessageQueue = Promise.resolve();
        upstream.addEventListener("message", (upstreamEvent) => {
          upstreamMessageQueue = upstreamMessageQueue.then(async () => {
            if (typeof upstreamEvent.data !== "string") {
              send({ type: "audio_chunk", data: await toBase64(upstreamEvent.data), audio_format: AUDIO_FORMAT });
              return;
            }
            let provider;
            try { provider = JSON.parse(upstreamEvent.data); } catch { return; }
            switch (provider.type) {
            case "Welcome":
              upstream.send(JSON.stringify(settings));
              break;
            case "SettingsApplied":
            case "SettingsAppliedSuccessfully":
              send({ type: "ready", audio_format: AUDIO_FORMAT });
              send({ type: "settings_applied", audio_format: AUDIO_FORMAT });
              break;
            case "ConversationText":
              send({ type: "transcript", role: provider.role === "user" ? "user" : "assistant", text: String(provider.content || "").slice(0, 4000) });
              break;
            case "UserStartedSpeaking":
            case "AgentStartedSpeaking":
              send({ type: "speaking", role: provider.type.startsWith("User") ? "user" : "agent", speaking: true });
              break;
            case "UserStoppedSpeaking":
            case "AgentStoppedSpeaking":
              send({ type: "speaking", role: provider.type.startsWith("User") ? "user" : "agent", speaking: false });
              break;
            case "AgentAudioDone":
            case "AudioDone":
              send({ type: "audio_done" });
              break;
            case "Error":
            case "AgentError":
              send({ type: "error", message: "Deepgram Agent error" });
              break;
            default:
              send({ type: "status", status: String(provider.type || "provider_event").slice(0, 80) });
            }
          }).catch(() => send({ type: "error", message: "Audio stream processing failed" }));
        });
        upstream.addEventListener("close", () => { if (browser.readyState === WebSocket.OPEN) send({ type: "stopped" }); });
        upstream.addEventListener("error", () => send({ type: "error", message: "Deepgram Agent connection failed" }));
        return;
      }
      if (message.type === "audio") {
        if (upstream?.readyState === WebSocket.OPEN && typeof message.data === "string") upstream.send(fromBase64(message.data));
        return;
      }
      if (message.type === "stop") {
        close();
      }
    } catch {
      send({ type: "error", message: "Session error" });
    }
  });
  browser.addEventListener("close", close);
  return new Response(null, { status: 101, webSocket: client });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(request, env) });
    if (url.pathname === "/api/live-token" && request.method === "GET") return issueToken(request, env);
    if (request.headers.get("Upgrade")?.toLowerCase() === "websocket") return relay(request, env);
    if (env.ASSETS) {
      return env.ASSETS.fetch(request);
    }
    return json(request, env, { error: "Not found" }, { status: 404 });
  }
};
