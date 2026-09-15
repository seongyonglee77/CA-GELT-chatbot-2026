const DEEPGRAM_TOKEN_ENDPOINT = "https://api.deepgram.com/v1/auth/grant";

function corsHeaders(request, env) {
  const requestOrigin = request.headers.get("Origin");
  const allowedOrigin = env.ALLOWED_ORIGIN || "*";
  const origin =
    allowedOrigin === "*"
      ? "*"
      : requestOrigin === allowedOrigin
        ? allowedOrigin
        : "null";

  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Cache-Control": "no-store",
    Vary: "Origin"
  };
}

function json(request, env, body, init = {}) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...corsHeaders(request, env),
      ...(init.headers || {})
    }
  });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(request, env)
      });
    }

    const url = new URL(request.url);
    if (url.pathname !== "/api/live-token" || request.method !== "GET") {
      return json(request, env, { error: "Not found" }, { status: 404 });
    }

    if (!env.DEEPGRAM_API_KEY) {
      return json(
        request,
        env,
        { error: "Worker secret DEEPGRAM_API_KEY is missing" },
        { status: 500 }
      );
    }

    const tokenResponse = await fetch(DEEPGRAM_TOKEN_ENDPOINT, {
      method: "POST",
      headers: {
        "Authorization": "Token " + env.DEEPGRAM_API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ ttl_seconds: 30 })
    });

    const payload = await tokenResponse.json().catch(() => null);
    if (!tokenResponse.ok || typeof payload?.access_token !== "string") {
      console.error("Deepgram temporary token request failed", {
        status: tokenResponse.status,
        payload
      });

      return json(
        request,
        env,
        {
          error: "Deepgram temporary token request failed",
          upstream_status: tokenResponse.status,
          upstream_message:
            typeof payload?.err_msg === "string"
              ? payload.err_msg
              : typeof payload?.error?.message === "string"
                ? payload.error.message
                : "Deepgram did not return an access token."
        },
        { status: 502 }
      );
    }

    return json(request, env, {
      access_token: payload.access_token,
      expires_in: payload.expires_in
    });
  }
};
