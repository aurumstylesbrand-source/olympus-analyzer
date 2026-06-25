# Claude Code prompts — olympus-analyzer

Run Claude Code **inside this folder**. Do the prompts in order. Each is copy-paste ready.
(You don't strictly need Claude Code to start it — `node server.js` works — but these handle setup, hardening, and deploy cleanly.)

---

## 1 — Run & verify locally
```
This folder is a dependency-free Node service (server.js + analyze.js) that scans a GitHub repo's source at a pinned commit. Check Node 18+ is installed, then start the server on port 8787. If I give you a GitHub token, start it with GITHUB_TOKEN set. Verify it works by curling http://localhost:8787/analyze?repo=tidwall/gjson&ref=master and show me the JSON. If it errors, debug and fix server.js — but do NOT change the analysis logic in analyze.js unless there is a real bug, and explain any change.
```

## 2 — Make it deployment-ready
```
Add deployment scaffolding without adding any npm dependencies and without breaking the existing /analyze endpoint:
- .gitignore that ignores node_modules and .cache
- .env.example listing GITHUB_TOKEN, PORT, and (for later) ANTHROPIC_API_KEY
- a Dockerfile based on node:20-alpine that copies the files, exposes 8787, and runs `node server.js`
- a GET /health endpoint in server.js that returns {"ok":true}
Then start the server and confirm both /health and /analyze still respond. Show me the output.
```

## 3 — Tighten CORS & input
```
In server.js, add an optional ALLOWED_ORIGIN env var: when set, send Access-Control-Allow-Origin with exactly that origin instead of *; when unset, keep *. Reject any repo query param that is not the shape owner/name with 400. Keep everything dependency-free. Verify /analyze still works from a browser-style fetch (you can simulate with curl -H "Origin: http://localhost") and show me the response headers.
```

## 4 — Deploy to a public HTTPS URL
```
Initialize a git repo in this folder, commit everything, and help me deploy this service to Railway (or Render or Fly.io — recommend the simplest for a single-file Node service). Walk me through, step by step: creating the project, setting the GITHUB_TOKEN environment variable on the host, and getting the public HTTPS URL. After it's live, curl https://<my-url>/health and https://<my-url>/analyze?repo=typeorm/typeorm&ref=master to confirm it works. Give me the final URL to paste into the Olympus Console settings.
```

## 5 — (Optional, Rung 3) Add the Claude judgment pass
```
Add a second endpoint GET /judge?repo=owner/name&ref=sha&layer=<path-or-kind> that answers the two BEHAVIOURAL questions the regex scan can't. Reuse the tarball-download + extract code from analyze.js to pull the variant layer and the layer directly above it. Then call the Anthropic API (key from ANTHROPIC_API_KEY env, the messages endpoint, a current Claude model) passing those files, and ask it to answer, WITH code citations and as a clearly-labelled model judgment (not proof):
  1. For a feature built on this layer, is the obvious/first implementation approach likely WRONG? Why?
  2. Is there an intermediate-state invariant (count / ordering / lifecycle) a naive implementation would violate while still passing value checks?
Return structured JSON: {approachWrong:{verdict,reason,citations[]}, invariant:{verdict,reason,citations[]}, disclaimer}. Do NOT change /analyze. Add ANTHROPIC_API_KEY to .env.example. Show me a sample call against typeorm/typeorm.
```

---

## After it's running — link it to the console (manual, ~30 seconds)
1. Open the **downloaded** `olympus_console.html` in your browser — NOT the claude.ai preview (the preview blocks outbound calls).
2. Settings → **GitHub access token** → paste a fine-grained read-only token → Save (lets the console read repos live).
3. Settings → **Analyzer backend URL** → paste `http://localhost:8787` (local) or your deployed `https://…` URL → Save.
4. Analyze any repo, then click **Read source (measured)** in the difficulty screen. It now calls your backend (full-repo scan, per-variant breakdown, cached).

Mixed-content note: a local `file://` console can call `http://localhost`. A console hosted over **https** must call an **https** backend.
