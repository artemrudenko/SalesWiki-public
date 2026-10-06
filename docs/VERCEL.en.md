# Deploy the Workbench preview to Vercel

1. Import `artemrudenko/SalesWiki-public` in Vercel.
2. Set **Root Directory** to `prototypes/knowledge-workbench`.
3. Use `npm run build` and output directory `dist/client`.
4. Leave `VITE_SALESWIKI_GRAPH_ENDPOINT` unset. The app then uses its
   synthetic in-browser fixtures.

This deploys only the browser preview. The Python permissioned service and its
local browser-for-frontend are separate processes; this Vercel project does not
deploy them. The public preview has no server-side identity, real CRM data, or
persistent writes. Do not connect it to customer systems.
