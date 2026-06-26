// olympus-analyzer server (Rung 4). Run: GITHUB_TOKEN=ghp_xxx node server.js
// Endpoint: GET /analyze?repo=owner/name&ref=<sha-or-branch>
// Caches by ref on disk. Sends CORS so the Olympus Console (browser) can call it.
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { analyzeRepo, loadRepoFiles, CONTAINER } = require('./analyze.js');

// Minimal .env loader (dependency-free): populate process.env from a local .env if present, so
// `node server.js` works locally without exporting vars. Real host env vars always take precedence.
try { fs.readFileSync(path.join(__dirname, '.env'), 'utf8').split('\n').forEach(l => {
  const m = l.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
  if (m && !process.env[m[1]]) { let v = m[2]; if ((v.startsWith('"')&&v.endsWith('"'))||(v.startsWith("'")&&v.endsWith("'"))) v = v.slice(1,-1); process.env[m[1]] = v; }
}); } catch {}

const PORT = process.env.PORT || 8787;
const TOKEN = process.env.GITHUB_TOKEN || '';
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || '';
const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY || '';
// Optional FREE model path: any OpenAI-compatible endpoint (Google AI Studio / Gemini, Zhipu GLM,
// Groq, DeepSeek, OpenRouter, NVIDIA NIM, ...). Used only when ANTHROPIC_API_KEY is not set.
// Two modes:
//   1. Single model  — set JUDGE_API_KEY (+ JUDGE_BASE_URL, JUDGE_MODEL).
//   2. ENSEMBLE      — set JUDGE_A_KEY/_BASE_URL/_MODEL and JUDGE_B_KEY/_BASE_URL/_MODEL.
//      Both models run IN PARALLEL on the same prompt; their answers are fused into one
//      centralized verdict (a synthesis model reconciles them) with an agreement/confidence
//      signal. Agreement = high confidence; disagreement is flagged, never hidden.
const JUDGE_API_KEY = process.env.JUDGE_API_KEY || '';
const JUDGE_BASE_URL = (process.env.JUDGE_BASE_URL || 'https://generativelanguage.googleapis.com/v1beta/openai').replace(/\/$/, '');
const JUDGE_MODEL = process.env.JUDGE_MODEL || 'gemini-flash-lite-latest';
const GEMINI_BASE = 'https://generativelanguage.googleapis.com/v1beta/openai';
function mkProvider(label, key, base, model, small){
  if(!key) return null;
  const baseUrl = (base || GEMINI_BASE).replace(/\/$/, '');
  // Providers with tight free token-per-minute limits (Groq, Cerebras) get a TRIMMED prompt so
  // they stay under the cap instead of 429-ing out of the ensemble. Auto-detected, or force via env.
  const isSmall = small===true || /^(1|true|yes)$/i.test(String(small||'')) || /groq\.com|cerebras\.ai/i.test(baseUrl);
  // Zhipu GLM models reason by default, which consumes the token budget and can blank the answer.
  // Disable it so tokens go to the JSON (clean output, faster). Harmless on providers that ignore it.
  const extra = (/bigmodel\.cn/i.test(baseUrl) || /^glm/i.test(model||'')) ? { thinking:{ type:'disabled' } } : {};
  return { label: label || model || 'model', key, baseUrl, model: model || 'gemini-flash-lite-latest', small: isSmall, extra };
}
// Provider roster: explicit A/B/C/D slots, PLUS the legacy single-provider config as an extra
// member, so existing deployments keep working AND extra free models can be added alongside them.
const PROVIDERS = [];
['A','B','C','D'].forEach(s => { const p = mkProvider(process.env['JUDGE_'+s+'_LABEL'], process.env['JUDGE_'+s+'_KEY'], process.env['JUDGE_'+s+'_BASE_URL'], process.env['JUDGE_'+s+'_MODEL'], process.env['JUDGE_'+s+'_SMALL']); if(p) PROVIDERS.push(p); });
if (JUDGE_API_KEY) { const leg = mkProvider(process.env.JUDGE_LABEL || JUDGE_MODEL, JUDGE_API_KEY, JUDGE_BASE_URL, JUDGE_MODEL); if (leg && !PROVIDERS.some(p => p.key===leg.key && p.model===leg.model)) PROVIDERS.push(leg); }
const SYNTH = (process.env.JUDGE_SYNTH || 'on').toLowerCase(); // 'on' | 'off' | a provider label that does the reconciliation
const CACHE = path.join(__dirname, '.cache');
if (!fs.existsSync(CACHE)) fs.mkdirSync(CACHE);

// General, repo-agnostic judging rubric (loaded once; embedded verbatim into every /judge prompt).
const JUDGE_RUBRIC = (() => { try { return fs.readFileSync(path.join(__dirname, 'judge_rubric.md'), 'utf8').trim(); } catch { return ''; } })();

function cacheKey(repo, ref){ return repo.replace(/[^a-z0-9]/gi,'_') + '@' + ref.replace(/[^a-z0-9]/gi,'_') + '.json'; }

// POST a Messages API request to Anthropic over raw HTTPS (keeps the service dependency-free).
function anthropicMessages(payload){
  return new Promise((resolve, reject)=>{
    const body = JSON.stringify(payload);
    const req = https.request('https://api.anthropic.com/v1/messages', {
      method:'POST',
      headers:{
        'content-type':'application/json',
        'x-api-key':ANTHROPIC_KEY,
        'anthropic-version':'2023-06-01',
        'content-length':Buffer.byteLength(body),
      },
    }, res=>{
      const chunks=[]; res.on('data',c=>chunks.push(c));
      res.on('end',()=>{
        const txt=Buffer.concat(chunks).toString('utf8');
        if(res.statusCode!==200) return reject(new Error('Anthropic HTTP '+res.statusCode+': '+txt.slice(0,400)));
        try { resolve(JSON.parse(txt)); } catch(e){ reject(new Error('bad JSON from Anthropic: '+txt.slice(0,200))); }
      });
    });
    req.on('error', reject);
    req.write(body); req.end();
  });
}

const dirOf = p => p.includes('/') ? p.slice(0, p.lastIndexOf('/')) : '';
// Does this file belong to the requested variant layer? `layer` is a path fragment or a container kind.
function inLayer(p, layer){
  const low = p.toLowerCase(), l = layer.toLowerCase();
  if(l.includes('/')) return low.includes(l);
  const seg = low.split('/').some(s => s === l || s === l+'s' || s+'s' === l);
  const m = p.match(CONTAINER);
  return seg || (m && m[2].toLowerCase() === l);
}
// Compact a file list into a prompt blob, bounded by file count and per-file size.
function blob(files, maxFiles, perFile){
  return files.slice(0, maxFiles)
    .map(f => '=== '+f.path+' ===\n'+f.text.slice(0, perFile))
    .join('\n\n');
}

const JUDGE_SCHEMA = {
  type:'object', additionalProperties:false,
  required:['approachWrong','invariant','disclaimer'],
  properties:{
    approachWrong:{ type:'object', additionalProperties:false, required:['verdict','reason','citations'],
      properties:{ verdict:{type:'string'}, reason:{type:'string'}, citations:{type:'array', items:{type:'string'}} } },
    invariant:{ type:'object', additionalProperties:false, required:['verdict','reason','citations'],
      properties:{ verdict:{type:'string'}, reason:{type:'string'}, citations:{type:'array', items:{type:'string'}} } },
    disclaimer:{type:'string'},
  },
};

function judgeKey(repo, ref, layer){ return 'judge_' + (repo+'@'+ref+'__'+layer).replace(/[^a-z0-9]/gi,'_') + '.json'; }

// The exact instruction a Claude judgment must follow — shared by the API path and the manual paste path.
const JUDGE_TASK =
`Answer two BEHAVIOURAL questions a regex scan cannot, citing specific files/symbols and labelling everything as a model judgment, NOT proof:
1. approachWrong: For a feature built on this layer, is the obvious / first implementation approach likely WRONG? Why?
2. invariant: Is there an intermediate-state invariant (count / ordering / lifecycle) a naive implementation would violate while still passing value-equality checks?
Reply with ONLY a JSON object of this exact shape (no prose, no markdown fence):
{"approachWrong":{"verdict":"likely yes|unclear|no","reason":"... with code citations","citations":["path:symbol"]},"invariant":{"verdict":"...","reason":"...","citations":["path"]},"disclaimer":"Model judgment, not proof."}`;

// Assemble the paste-ready prompt at a given size profile (so small-context providers get less).
function assembleJudgePrompt(repo, ref, layer, variant, above, variantDirs, sz){
  return `You are reviewing the "${layer}" layer of ${repo}@${ref} to assess how hard a NEW feature built on this layer would be.

THE VARIANT LAYER (${variant.length} files, ${variantDirs.size} dirs):
${blob(variant, sz.mv, sz.mvc)}

THE LAYER DIRECTLY ABOVE (${above.length} files):
${blob(above, sz.ma, sz.mac)}
${JUDGE_RUBRIC ? `
Ground your judgment in this general, language-agnostic rubric of code signals (applies to ANY repo). Map what you see in the code above to these signals, then apply the verdict-calibration lines:

${JUDGE_RUBRIC}
` : ''}
${JUDGE_TASK}`;
}
const PROMPT_FULL = { mv:12, mvc:12000, ma:8, mac:8000 };   // big-context models (Gemini/GLM/Claude)
const PROMPT_SMALL = { mv:4, mvc:5000, ma:3, mac:4000 };     // tight free TPM (Groq/Cerebras) ~6-8k tokens
// Download the repo, isolate the variant layer + the layer above, and assemble both prompt sizes.
async function buildJudgeContext(repo, ref, layer){
  const files = await loadRepoFiles(repo, ref, TOKEN);
  const variant = files.filter(f => inLayer(f.path, layer));
  if(!variant.length) throw new Error('no files matched layer "'+layer+'" (try a path fragment or container kind like "adapters")');
  const variantDirs = new Set(variant.map(f => dirOf(f.path)));
  const variantPaths = new Set(variant.map(f => f.path));
  const aboveDirs = new Set([...variantDirs].map(d => dirOf(d)));
  const above = files.filter(f => !variantPaths.has(f.path) && aboveDirs.has(dirOf(f.path)));
  const prompt = assembleJudgePrompt(repo, ref, layer, variant, above, variantDirs, PROMPT_FULL);
  const promptSmall = assembleJudgePrompt(repo, ref, layer, variant, above, variantDirs, PROMPT_SMALL);
  return { prompt, promptSmall, variantFiles:variant.length, aboveFiles:above.length };
}

// Normalize any judgment object (from the API or pasted by a human) into the response shape.
function shapeJudgment(repo, ref, layer, ctx, raw, source){
  const out = { repo, ref, layer, variantFiles:ctx&&ctx.variantFiles, aboveFiles:ctx&&ctx.aboveFiles, source,
    approachWrong: raw.approachWrong || {}, invariant: raw.invariant || {},
    disclaimer: raw.disclaimer || 'Model judgment, not proof. No call-graph or runtime analysis was performed.' };
  return out;
}

async function judgeViaApi(repo, ref, layer){
  const ctx = await buildJudgeContext(repo, ref, layer);
  const resp = await anthropicMessages({
    model:'claude-opus-4-8',
    max_tokens:4000,
    thinking:{type:'adaptive'},
    output_config:{ format:{ type:'json_schema', schema:JUDGE_SCHEMA } },
    messages:[{ role:'user', content:ctx.prompt }],
  });
  const textBlock = (resp.content||[]).find(b => b.type==='text');
  if(!textBlock) throw new Error('no text block in Anthropic response (stop_reason='+resp.stop_reason+')');
  return shapeJudgment(repo, ref, layer, ctx, JSON.parse(textBlock.text), 'api');
}

// POST to ONE OpenAI-compatible /chat/completions endpoint (Gemini / GLM / Groq / DeepSeek / OpenRouter).
function openaiChat(provider, payload){
  return new Promise((resolve, reject)=>{
    const body = JSON.stringify(payload);
    const req = https.request(provider.baseUrl + '/chat/completions', {
      method:'POST',
      headers:{ 'content-type':'application/json', 'authorization':'Bearer '+provider.key, 'content-length':Buffer.byteLength(body) },
      timeout: 40000,
    }, res=>{
      const chunks=[]; res.on('data',c=>chunks.push(c));
      res.on('end',()=>{
        const txt=Buffer.concat(chunks).toString('utf8');
        if(res.statusCode!==200) return reject(new Error(provider.label+' HTTP '+res.statusCode+': '+txt.slice(0,200)));
        try { resolve(JSON.parse(txt)); } catch(e){ reject(new Error('bad JSON from '+provider.label+': '+txt.slice(0,160))); }
      });
    });
    req.on('timeout', () => req.destroy(new Error(provider.label+' request timeout (40s)')));
    req.on('error', reject); req.write(body); req.end();
  });
}
// Defensive parse: strip ```json fences / prose, keep the first {...} object.
function parseModelJson(content){
  if(!content) throw new Error('empty model content');
  content = String(content).replace(/```json/gi,'').replace(/```/g,'').trim();
  const m = content.match(/\{[\s\S]*\}/); if(m) content = m[0];
  return JSON.parse(content);
}
function contentOf(resp){ return resp && resp.choices && resp.choices[0] && resp.choices[0].message && resp.choices[0].message.content; }
const sleep = ms => new Promise(r => setTimeout(r, ms));
// Transient upstream conditions worth a retry (rate limit, overload, gateway/timeout, reset).
function isTransient(msg){ const st = parseInt((String(msg).match(/HTTP (\d{3})/)||[])[1], 10);
  return [408,425,429,500,502,503,504,529].includes(st) || /timeout|socket hang up|ECONNRESET|ECONNREFUSED|EAI_AGAIN|network/i.test(String(msg)); }
async function withRetry(fn, tries){
  tries = tries || 3; let lastErr;
  for(let i=0;i<tries;i++){
    try { return await fn(); }
    catch(e){ lastErr = e; if(i<tries-1 && isTransient(e&&e.message)){ await sleep(500*(i+1)); continue; } throw e; }
  }
  throw lastErr;
}
// Hard cap on a single async op so one slow/hung provider can never block the whole ensemble.
const withDeadline = (promise, ms, label) => Promise.race([ promise,
  new Promise((_, rej) => setTimeout(() => rej(new Error((label||'op') + ' deadline ' + ms + 'ms exceeded')), ms)) ]);
// Ask ONE provider the judge question; return its per-model verdict object.
async function judgeOneModel(provider, prompt){
  const resp = await withRetry(() => openaiChat(provider, Object.assign({ model: provider.model, messages:[{ role:'user', content: prompt }], max_tokens: 1500 }, provider.extra||{})));
  const raw = parseModelJson(contentOf(resp));
  return { label: provider.label, model: provider.model, approachWrong: raw.approachWrong || {}, invariant: raw.invariant || {} };
}
// Normalize any verdict phrasing to one of yes|no|unclear.
function normVerdict(v){ const z = String(v||'').toLowerCase().trim();
  if(/^(likely\s*yes|yes\b|probably|definitely)/.test(z)) return 'yes';
  if(/^(likely\s*no|no\b|unlikely|none)/.test(z)) return 'no';
  return 'unclear'; }
// Deterministically fuse one dimension across members: centralized verdict + agreement + merged cites.
function fuseDimension(members, dim){
  const items = members.map(m => ({ label:m.label, v:(m[dim]&&m[dim].verdict)||'?', n:normVerdict(m[dim]&&m[dim].verdict),
    reason:(m[dim]&&m[dim].reason)||'', cites:(m[dim]&&m[dim].citations)||[] }));
  const counts = { yes:0, no:0, unclear:0 }; items.forEach(i => counts[i.n]++);
  const distinct = new Set(items.map(i => i.n));
  const agreement = distinct.size===1 ? 'full' : (counts.yes && counts.no ? 'split' : 'partial');
  let cn; // centralized normalized verdict
  if(distinct.size===1) cn = items[0].n;
  else if(counts.yes && counts.no) cn = 'unclear';            // hard disagreement -> conservative
  else cn = counts.yes >= counts.no ? (counts.yes>=counts.unclear?'yes':'unclear') : (counts.no>=counts.unclear?'no':'unclear');
  const disp = { yes:'likely yes', no:'no', unclear:'unclear' }[cn];
  const cites = [...new Set(items.flatMap(i => i.cites))];
  const reason = (agreement==='full' ? 'All models agree. ' : agreement==='split' ? 'Models DISAGREE -> centralized to unclear. ' : 'Models partially agree. ')
    + items.map(i => i.label+' ('+i.v+'): '+i.reason).join('  |  ');
  return { verdict:disp, reason, citations:cites, agreement, members: items.map(i => ({ label:i.label, verdict:i.v })) };
}
// Optional synthesis: one model reads both verdicts and writes a reconciled, centralized reason.
async function judgeSynthesize(provider, repo, layer, members){
  const prompt = `Two independent models judged the "${layer}" layer of ${repo}. Reconcile them into ONE centralized judgment.

`+members.map(m => `MODEL ${m.label}:\n`+JSON.stringify({ approachWrong:m.approachWrong, invariant:m.invariant })).join('\n\n')+`

Questions: (1) approachWrong - is the obvious/first implementation of a NEW feature on this layer likely WRONG? (2) invariant - is there an intermediate-state invariant (count/ordering/lifecycle) a naive implementation would violate while still passing value-equality checks?
Where the models agree, give the strongest shared reasoning. Where they disagree, weigh the cited evidence, pick the better-supported verdict, and say they disagreed. Cite specific files/symbols. Reply with ONLY JSON (no prose, no fence):
{"approachWrong":{"verdict":"likely yes|unclear|no","reason":"...","citations":["path:symbol"]},"invariant":{"verdict":"...","reason":"...","citations":["path"]},"disclaimer":"Centralized from 2 models; not proof."}`;
  const resp = await withRetry(() => openaiChat(provider, Object.assign({ model: provider.model, messages:[{ role:'user', content: prompt }], max_tokens: 1300 }, provider.extra||{})));
  return parseModelJson(contentOf(resp));
}
// FREE ensemble judge: run every configured provider in parallel, fuse into one centralized verdict.
async function judgeViaEnsemble(repo, ref, layer){
  const ctx = await buildJudgeContext(repo, ref, layer);
  const settled = await Promise.allSettled(PROVIDERS.map(p => withDeadline(judgeOneModel(p, p.small ? ctx.promptSmall : ctx.prompt), 55000, p.label)));
  const members = []; const errors = [];
  settled.forEach((s,i) => s.status==='fulfilled' ? members.push(s.value) : errors.push(PROVIDERS[i].label+': '+String(s.reason&&s.reason.message||s.reason)));
  if(!members.length) throw new Error('all judge providers failed -> '+errors.join(' | '));
  // Single model available (one configured, or the other failed): return it directly.
  if(members.length===1){
    const m = members[0];
    const out = shapeJudgment(repo, ref, layer, ctx, { approachWrong:m.approachWrong, invariant:m.invariant,
      disclaimer:'Single model ('+m.label+'). Not proof.'+(errors.length?' (other provider failed: '+errors.join('; ')+')':'') }, 'llm:'+m.model);
    if(errors.length) out.providerErrors = errors;
    return out;
  }
  // >=2 members: deterministic fusion + optional synthesis pass.
  const fa = fuseDimension(members,'approachWrong'), fi = fuseDimension(members,'invariant');
  let aw = { verdict:fa.verdict, reason:fa.reason, citations:fa.citations };
  let iv = { verdict:fi.verdict, reason:fi.reason, citations:fi.citations };
  let synthesized = false;
  if(SYNTH !== 'off'){
    try {
      const synthProvider = PROVIDERS.find(p => p.label.toLowerCase()===SYNTH) || members[0] && PROVIDERS.find(p=>p.label===members[0].label) || PROVIDERS[0];
      const s = await withDeadline(judgeSynthesize(synthProvider, repo, layer, members), 35000, 'synthesis');
      // Synthesis writes the centralized reason+verdict, BUT a hard split is never papered over: force unclear.
      if(s.approachWrong) aw = { verdict: fa.agreement==='split' ? 'unclear' : (s.approachWrong.verdict||fa.verdict),
        reason: (fa.agreement==='split'?'[models disagreed] ':'')+(s.approachWrong.reason||fa.reason),
        citations: [...new Set([...(s.approachWrong.citations||[]), ...fa.citations])] };
      if(s.invariant) iv = { verdict: fi.agreement==='split' ? 'unclear' : (s.invariant.verdict||fi.verdict),
        reason: (fi.agreement==='split'?'[models disagreed] ':'')+(s.invariant.reason||fi.reason),
        citations: [...new Set([...(s.invariant.citations||[]), ...fi.citations])] };
      synthesized = true;
    } catch(e){ /* keep deterministic fusion */ }
  }
  const labels = members.map(m => m.label).join('+');
  const out = shapeJudgment(repo, ref, layer, ctx, { approachWrong:aw, invariant:iv,
    disclaimer:'Centralized from '+members.length+' models ('+labels+')'+(synthesized?' + synthesis reconciliation':'')
      +'. Agreement: approach='+fa.agreement+', invariant='+fi.agreement+'. A model consensus, not proof.' }, 'ensemble:'+labels);
  out.members = members.map(m => ({ label:m.label, model:m.model, approachWrong:m.approachWrong, invariant:m.invariant }));
  out.agreement = { approachWrong:fa.agreement, invariant:fi.agreement };
  out.synthesized = synthesized;
  if(errors.length) out.providerErrors = errors;
  return out;
}

// FREE, model-free judge: scan the variant + above layers for the rubric's signals and emit
// approach/invariant verdicts with citations. Honest: a heuristic regex scan, NOT a model judgment.
const APPROACH_SIGNALS = [
  ['shared base class with concrete helpers', /\b(abstract\s+class|class\s+\w*Base\w*|extends\s+\w*Base|super\.\w+\()/i],
  ['hidden dispatch / registry', /\b(registry|factory|dispatch|handlers?\s*[:=]|switch\s*\(|new\s+Map\(|Record<\s*string)/i],
  ['lazy / deferred initialization', /\b(\.connect\(|setup\(|initialize\(|\.acquire\(|lazy|bootstrap\()/i],
  ['internal caching / memoization', /\b(cache|memo|lru|WeakMap|WeakRef|useMemo)/i],
  ['implicit ordering contract', /\b(middleware|\.use\(|pipeline|priority|ordered|chain)/i],
  ['interface with non-obvious required methods', /\b(interface\s+\w|implements\s+\w|abstract\s+\w+\s*\()/i],
  ['builder / fluent order-dependent state', /\b(Builder\b|\.build\(|\.where\(|\.select\(|\.from\()/i],
];
const INVARIANT_SIGNALS = [
  ['paired lifecycle hooks', /\b(open\(|close\(|begin\(|commit\(|acquire\(|release\(|subscribe\(|unsubscribe\(|disconnect\()/i],
  ['query / operation count', /\b(queries|batch|N\+1|EXPLAIN|\.stats\(|queryCount)/i],
  ['insertion ordering', /\b(ORDER\s+BY|\.sort\(|ordered|LinkedHashMap|insertionOrder)/i],
  ['reference counting / pooling', /\b(Rc<|Arc<|refcount|\bpool\b|checkout|checkin|semaphore)/i],
  ['derived values after filtering', /\b(\.count\b|\bsum\b|aggregate|subtree|reduce\()/i],
  ['transactional visibility', /\b(transaction|BEGIN\b|COMMIT\b|@Transactional|rollback)/i],
  ['idempotency under retry', /\b(IF\s+NOT\s+EXISTS|ON\s+CONFLICT|idempoten|dedup|upsert)/i],
  ['concurrency ordering', /\b(Mutex|\bLock\b|sync\.|tokio::|goroutine|select\s*\{)/i],
  ['cleanup-on-error path', /\b(defer\s|finally\b|impl\s+Drop|dispose\()/i],
];
function scanSignals(files, signals){
  const hits = [];
  for(const [name, re] of signals){ const f = files.find(f => re.test(f.text)); if(f) hits.push({ name, file:f.path }); }
  return hits;
}
async function judgeHeuristic(repo, ref, layer){
  const files = await loadRepoFiles(repo, ref, TOKEN);
  const variant = files.filter(f => inLayer(f.path, layer));
  if(!variant.length) throw new Error('no files matched layer "'+layer+'" (try a path fragment or container kind like "adapters")');
  const variantDirs = new Set(variant.map(f => dirOf(f.path)));
  const variantPaths = new Set(variant.map(f => f.path));
  const aboveDirs = new Set([...variantDirs].map(d => dirOf(d)));
  const above = files.filter(f => !variantPaths.has(f.path) && aboveDirs.has(dirOf(f.path)));
  const scope = variant.concat(above);
  const aHits = scanSignals(scope, APPROACH_SIGNALS);
  const iHits = scanSignals(scope, INVARIANT_SIGNALS);
  if(new Set(variant.map(f => f.path.split('/')[0])).size >= 3) aHits.push({ name:'cross-package / cross-module wiring', file:'(3+ top-level dirs)' });
  const cite = h => h.map(x => x.file + ' [' + x.name + ']');
  const reason = (h, kind) => h.length ? ('matched ' + h.length + ' ' + kind + ' signals from the rubric: ' + h.map(x => x.name).join('; ')) : 'no ' + kind + ' signals detected by the rubric scan';
  return {
    repo, ref, layer, source:'heuristic', variantFiles:variant.length, aboveFiles:above.length,
    approachWrong:{ verdict: aHits.length>=3 ? 'likely yes' : aHits.length>=1 ? 'unclear' : 'no', reason: reason(aHits,'approach-wrong'), citations: cite(aHits) },
    invariant:{ verdict: iHits.length>=2 ? 'likely yes' : iHits.length>=1 ? 'unclear' : 'no', reason: reason(iHits,'invariant'), citations: cite(iHits) },
    disclaimer: 'Heuristic rubric-signal scan (regex over the layer) — NOT a model judgment and NOT proof. For a deeper read, use the paste-a-Claude-chat mode (mode=prompt). Always confirm in-editor.',
  };
}

// Read and JSON-parse a request body (bounded to 1 MB).
function readJsonBody(req){
  return new Promise((resolve, reject)=>{
    const chunks=[]; let size=0;
    req.on('data', c=>{ size+=c.length; if(size>1e6){ reject(new Error('body too large')); req.destroy(); } else chunks.push(c); });
    req.on('end', ()=>{ try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')||'{}')); } catch(e){ reject(new Error('body is not valid JSON')); } });
    req.on('error', reject);
  });
}

// Curate the next batch of candidate repos via the Anthropic API (server-side: the browser
// can't call Anthropic directly — no CORS, and the key must not ship to the client).
// The prompt is built server-side from {tier, used} so this can't be used as a general proxy.
const TIER_PLAN = { olympus:{gold:3,test:2}, mars:{gold:4,test:3} };
async function generateRepos(tier, used){
  const plan = TIER_PLAN[tier]; const need = plan.gold + plan.test;
  const guide = tier==='olympus'
    ? 'OLYMPUS: prefer repos with 5+ adapters/dialects/backends each a DIFFERENT pattern AND a discovery-gap sibling code path, OR deep concurrency/type systems. Must support 700+ agent LOC across 6+ existing files.'
    : 'MARS: clean public API, 5-15 files, clear behavioural contracts. Challenging but more solvable.';
  const sys = `You curate GitHub repos for the ${tier} tier of an AI coding-challenge pipeline. Return ONLY a raw JSON array, no prose/fences. Exactly ${need} objects: ${plan.gold} "kind":"gold" and ${plan.test} "kind":"test". Constraints: PRIMARY language Go or TypeScript only (never JS-primary); permissive licence (MIT/Apache-2.0/BSD); 500+ stars; commit within 12 months; production-grade. Pass-rate targets are now STRICTER: Olympus <=20%, Mars <=30%. "Verify Flakiness" is a MANDATORY platform check, so strongly prefer repos with deterministic, non-flaky test suites (no time/network/order-dependent tests, no WASM-heap flakiness). ${guide} NEVER include any repo in this exclusion list: ${(used||[]).join(', ')}. Keys per object: fullName, url, lang, license, stars (e.g. "~12k"), kind, why (<=22 words)${tier==='olympus'?', path ("A"/"B"/"A+B")':''}.`;
  const resp = await anthropicMessages({
    model:'claude-sonnet-4-6', max_tokens:1200,
    system: sys,
    messages:[{ role:'user', content:`Generate the next ${tier} batch as a JSON array of ${need} repos.` }],
  });
  const textBlock = (resp.content||[]).find(b => b.type==='text');
  if(!textBlock) throw new Error('no text block in Anthropic response (stop_reason='+resp.stop_reason+')');
  const txt = textBlock.text.replace(/```json/gi,'').replace(/```/g,'').trim();
  const arr = JSON.parse(txt);
  if(!Array.isArray(arr)) throw new Error('model did not return a JSON array');
  return { tier, repos: arr };
}

http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', ALLOWED_ORIGIN || '*');
  if (ALLOWED_ORIGIN) res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'content-type');
  res.setHeader('Content-Type', 'application/json');
  if (req.method === 'OPTIONS') { res.writeHead(204); return res.end(); }

  const u = new URL(req.url, 'http://localhost');
  if (u.pathname === '/health') { res.writeHead(200); return res.end(JSON.stringify({ ok: true })); }

  if (u.pathname === '/judge') {
    const repo = u.searchParams.get('repo');
    const ref = u.searchParams.get('ref') || 'HEAD';
    const layer = u.searchParams.get('layer');
    if (!repo || !/^[\w.-]+\/[\w.-]+$/.test(repo)) { res.writeHead(400); return res.end(JSON.stringify({ error: 'bad repo (want owner/name)' })); }
    if (!layer) { res.writeHead(400); return res.end(JSON.stringify({ error: 'missing layer (path fragment or container kind, e.g. adapters)' })); }
    const jf = path.join(CACHE, judgeKey(repo, ref, layer));

    // POST: accept a human-pasted judgment (from a Claude chat) and cache it for the console to read.
    if (req.method === 'POST') {
      try {
        const body = await readJsonBody(req);
        if (!body || (!body.approachWrong && !body.invariant)) {
          res.writeHead(400); return res.end(JSON.stringify({ error: 'expected JSON with approachWrong and/or invariant keys' }));
        }
        const result = shapeJudgment(repo, ref, layer, null, body, 'manual');
        result.savedAt = new Date().toISOString();
        fs.writeFileSync(jf, JSON.stringify(result));
        res.writeHead(200); return res.end(JSON.stringify({ ok: true, saved: result }));
      } catch (e) {
        res.writeHead(400); return res.end(JSON.stringify({ error: String(e.message || e) }));
      }
    }

    // GET precedence: ?mode=prompt always rebuilds the paste prompt; else a cached judgment
    // wins; else a model API call when a key is set; else a FREE heuristic rubric-signal scan.
    try {
      const wantPrompt = u.searchParams.get('mode') === 'prompt';
      if (!wantPrompt && fs.existsSync(jf)) { const b = JSON.parse(fs.readFileSync(jf,'utf8')); b.cached = true; res.writeHead(200); return res.end(JSON.stringify(b)); }
      if (wantPrompt) {
        const ctx = await buildJudgeContext(repo, ref, layer);
        res.writeHead(200); return res.end(JSON.stringify({
          needsJudgment: true, repo, ref, layer, variantFiles: ctx.variantFiles, aboveFiles: ctx.aboveFiles,
          prompt: ctx.prompt,
          howto: 'Paste `prompt` into any Claude chat, then POST Claude\'s JSON back to this same /judge URL to cache it.',
        }));
      }
      let result;
      if (ANTHROPIC_KEY) result = await judgeViaApi(repo, ref, layer);
      else if (PROVIDERS.length) {
        try { result = await judgeViaEnsemble(repo, ref, layer); }
        catch (e) { result = await judgeHeuristic(repo, ref, layer); result.ensembleError = String(e.message || e); }
      } else result = await judgeHeuristic(repo, ref, layer);
      fs.writeFileSync(jf, JSON.stringify(result));
      res.writeHead(200); return res.end(JSON.stringify(result));
    } catch (e) {
      res.writeHead(502); return res.end(JSON.stringify({ error: String(e.message || e) }));
    }
  }

  if (u.pathname === '/generate') {
    const tier = (req.method === 'POST') ? null : u.searchParams.get('tier');
    if (!ANTHROPIC_KEY) { res.writeHead(501); return res.end(JSON.stringify({ error: 'ANTHROPIC_API_KEY not set on the server (needed to curate batches)' })); }
    try {
      const body = (req.method === 'POST') ? await readJsonBody(req) : {};
      const t = (body.tier || tier || '').toLowerCase();
      if (t !== 'olympus' && t !== 'mars') { res.writeHead(400); return res.end(JSON.stringify({ error: 'tier must be "olympus" or "mars"' })); }
      const result = await generateRepos(t, body.used || []);
      res.writeHead(200); return res.end(JSON.stringify(result));
    } catch (e) {
      res.writeHead(502); return res.end(JSON.stringify({ error: String(e.message || e) }));
    }
  }

  if (u.pathname !== '/analyze') { res.writeHead(404); return res.end(JSON.stringify({ error: 'use /analyze?repo=owner/name&ref=sha' })); }

  const repo = u.searchParams.get('repo');
  const ref = u.searchParams.get('ref') || 'HEAD';
  if (!repo || !/^[\w.-]+\/[\w.-]+$/.test(repo)) { res.writeHead(400); return res.end(JSON.stringify({ error: 'bad repo (want owner/name)' })); }

  const cf = path.join(CACHE, cacheKey(repo, ref));
  if (fs.existsSync(cf)) { const b=JSON.parse(fs.readFileSync(cf,'utf8')); b.cached=true; res.writeHead(200); return res.end(JSON.stringify(b)); }

  try {
    const result = await analyzeRepo(repo, ref, TOKEN);
    fs.writeFileSync(cf, JSON.stringify(result));
    res.writeHead(200); res.end(JSON.stringify({ ...result, cached: false }));
  } catch (e) {
    res.writeHead(502); res.end(JSON.stringify({ error: String(e.message || e) }));
  }
}).listen(PORT, () => console.log('olympus-analyzer on :' + PORT + (TOKEN ? ' (token set)' : ' (NO token — 60 req/hr)')));
