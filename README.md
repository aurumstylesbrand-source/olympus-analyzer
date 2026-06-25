# olympus-analyzer (Rung 4)

A tiny, dependency-free backend that reads a repo's **actual source** at a pinned commit and returns structured findings the browser console can't compute (full-repo scale, no CSP, no API rate-limit pain, cached by commit).

## What it really does (honest scope)
**Computes for real (full-repo regex scan):**
- total public/exported **surface** symbol count + barrel re-export count
- total **method** signatures and **concrete** method count
- the **variant kinds** present (adapters/drivers/dialects/providers/…) with a **per-variant breakdown** (files, symbols, methods each)
- a **free-helper signal** (concrete methods in base/abstract files, or high concrete-method density across variants)

**Does NOT do (do not claim it does):**
- tree-sitter / AST parsing or a language server — it's regex, so it misses edge cases
- call-graph analysis or proof that a helper is genuinely free for a *specific* feature (`freeHelperSignal` is a heuristic, not proof)
- the two behavioural screen questions — "is the obvious approach wrong" and "does a naive impl fail an invariant" are reasoning tasks; run an LLM pass for those (extension point below)

## Run
```bash
cd olympus-analyzer
GITHUB_TOKEN=ghp_your_readonly_token node server.js   # token optional but lifts rate limits
# GET http://localhost:8787/analyze?repo=typeorm/typeorm&ref=<commit-sha>
```
Results cache to `.cache/` by `repo@ref`. Delete the folder to bust.

## Wire it to the console
Open the console → Settings → **Analyzer backend URL** → `http://localhost:8787` (or your deployed URL). When set, the console calls the backend instead of the browser scan and shows the richer per-variant findings.
The server already sends `Access-Control-Allow-Origin: *` so the browser can call it. For production put it behind HTTPS and lock the origin down.

## Extension points (the deeper rungs, deliberately not implemented)
1. Swap `scanSymbols` for **tree-sitter** WASM/native grammars → accurate signatures, struct fields, mutability.
2. Add a **call-graph** pass (language server / semgrep) to upgrade `freeHelperSignal` from heuristic to proof for a named layer.
3. Add an **LLM pass**: feed the variant layer + parent layer to a model and have it answer "obvious approach wrong?" / "invariant a naive impl fails?" with code citations. This is the only thing that makes those two screen answers measured rather than judged.

## Deploy
Any Node host (Fly.io, Railway, Render, a VPS). One file, no deps. Set `GITHUB_TOKEN`. It is stateless apart from the on-disk cache.
