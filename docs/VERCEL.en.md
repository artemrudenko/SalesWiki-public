# Vercel Preview Deployment

The Knowledge Workbench can be deployed as a static, **synthetic demo** on
Vercel. This is suitable for sharing the interaction model, charts and graph
without giving the browser any access to a real vault, MCP gateway, credentials
or customer data.

## What This Deployment Includes

- the static Workbench interface and synthetic fixture data;
- account graphs, evidence trace, guided assistant and local proposal flow;
- no real user identity, persistence, connector or server-side MCP transport.

The banner and help content must remain visible in this mode: it is a demo, not
a hosted permissioned product.

## Deploy From GitHub

1. Sign in to [Vercel](https://vercel.com) and choose **Add New → Project**.
2. Import `artemrudenko/SalesWiki-public`.
3. Set the **Root Directory** to `prototypes/knowledge-workbench`.
4. Keep the detected build command `npm run build` and output directory
   `dist/client`.
5. Do **not** add `VITE_SALESWIKI_GRAPH_ENDPOINT`; omitting it deliberately
   keeps the published site on safe in-browser fixtures.
6. Deploy and check the deployed URL in a private browser window.

`vercel.json` already provides the correct build output and SPA fallback.

## Before Sharing The URL

Run locally from the Workbench directory:

```bash
npm ci
npm run build
npm test -- --run
```

Then use the live site to check account switching, guided assistant, graph
filters, responsive layout and the visible `Demo` boundary. Never configure a
public Vercel project to call a local or real MCP BFF. A real deployment needs
per-request OAuth/SSO and a hosted server-side gateway first; see
[`DEPLOYMENT.en.md`](DEPLOYMENT.en.md).
