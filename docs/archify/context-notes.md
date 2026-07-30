# Context notes

- Target project is `tools/icbm2-knowledge-graph`.
- Current local purpose is dogebi GitHub repository graph visualization, not the original sigco3111 ICBM2 public demo.
- The runtime is static HTML plus D3.js. Python generates embedded graph data before the browser loads the page.
- `data/nodes.json` and `data/links.json` are original ICBM2 data and are not the active dogebi repo graph source.
- Active dogebi graph data is embedded into `dashboard/github-repos.html`, then copied to root `index.html` for `http://127.0.0.1:8020/`.
- Repo-to-repo links are metadata similarity links, not code dependency links.
