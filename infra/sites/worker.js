const securityHeaders = {
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY"
};

function withSecurityHeaders(response) {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(securityHeaders)) {
    headers.set(name, value);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/contact") {
      return Response.json(
        { message: "The contact form is unavailable in this private design preview." },
        { status: 503, headers: securityHeaders }
      );
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", { status: 405, headers: securityHeaders });
    }

    const assetUrl = new URL(url);
    if (assetUrl.pathname === "/") {
      assetUrl.pathname = "/index.html";
    } else if (assetUrl.pathname.endsWith("/")) {
      assetUrl.pathname += "index.html";
    } else if (!assetUrl.pathname.split("/").pop().includes(".")) {
      assetUrl.pathname += "/index.html";
    }

    const assetResponse = await env.ASSETS.fetch(new Request(assetUrl, request));
    if (assetResponse.status !== 404) {
      return withSecurityHeaders(assetResponse);
    }

    const notFoundUrl = new URL("/404.html", url);
    const notFound = await env.ASSETS.fetch(new Request(notFoundUrl, request));
    return withSecurityHeaders(new Response(notFound.body, {
      status: 404,
      headers: notFound.headers
    }));
  }
};
