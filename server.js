// olympus-analyzer server (Rung 4). Run: GITHUB_TOKEN=ghp_xxx node server.js
// Endpoint: GET /analyze?repo=owner/name&ref=<sha-or-branch>
// Caches by ref on disk. Sends CORS so the Olympus Console (browser) can call it.
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { analyzeRepo, loadRepoFiles, CONTAINER } = require('./analyze.js');

const PORT = process.env.PORT || 8787;
const TOKEN = process.env.GITHUB_TOKEN || '';
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || '';
const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY || '';
const CACHE = path.join(__dirname, '.cache');
if (!fs.existsSync(CACHE)) fs.mkdirSync(CACHE);

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

async function judge(repo, ref, layer){
  const files = await loadRepoFiles(repo, ref, TOKEN);
  const variant = files.filter(f => inLayer(f.path, layer));
  if(!variant.length) throw new Error('no files matched layer "'+layer+'" (try a path fragment or container kind like "adapters")');
  const variantDirs = new Set(variant.map(f => dirOf(f.path)));
  const variantPaths = new Set(variant.map(f => f.path));
  const aboveDirs = new Set([...variantDirs].map(d => dirOf(d)));
  const above = files.filter(f => !variantPaths.has(f.path) && aboveDirs.has(dirOf(f.path)));

  const prompt =
`You are reviewing the "${layer}" layer of ${repo}@${ref} to assess how hard a NEW feature built on this layer would be.

THE VARIANT LAYER (${variant.length} files, ${variantDirs.size} dirs):
${blob(variant, 12, 12000)}

THE LAYER DIRECTLY ABOVE (${above.length} files):
${blob(above, 8, 8000)}

Answer two BEHAVIOURAL questions a regex scan cannot, citing specific files/symbols and labelling everything as a model judgment, NOT proof:
1. approachWrong: For a feature built on this layer, is the obvious / first implementation approach likely WRONG? Why?
2. invariant: Is there an intermediate-state invariant (count / ordering / lifecycle) a naive implementation would violate while still passing value-equality checks?
For each, give a short verdict (e.g. "likely yes"/"unclear"/"no"), a reason with concrete code citations, and a citations array of "path:symbol" or "path" strings.`;

  const resp = await anthropicMessages({
    model:'claude-opus-4-8',
    max_tokens:4000,
    thinking:{type:'adaptive'},
    output_config:{ format:{ type:'json_schema', schema:JUDGE_SCHEMA } },
    messages:[{ role:'user', content:prompt }],
  });
  const textBlock = (resp.content||[]).find(b => b.type==='text');
  if(!textBlock) throw new Error('no text block in Anthropic response (stop_reason='+resp.stop_reason+')');
  const out = JSON.parse(textBlock.text);
  if(!out.disclaimer) out.disclaimer = 'Model judgment, not proof. No call-graph or runtime analysis was performed.';
  return { repo, ref, layer, variantFiles:variant.length, aboveFiles:above.length, ...out };
}

http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', ALLOWED_ORIGIN || '*');
  if (ALLOWED_ORIGIN) res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
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
    if (!ANTHROPIC_KEY) { res.writeHead(501); return res.end(JSON.stringify({ error: 'ANTHROPIC_API_KEY not set on the server' })); }
    try {
      const result = await judge(repo, ref, layer);
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
