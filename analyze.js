// olympus-analyzer — core analysis (Rung 4). No external dependencies.
// Downloads the repo tarball at an exact ref, extracts in memory, scans EVERY source file,
// and returns structured findings: full-repo surface, per-variant breakdown, free-helper signal.
const https = require('https');
const zlib = require('zlib');

function fetchBuf(url, token, redirects=0){
  return new Promise((resolve, reject)=>{
    const headers={'User-Agent':'olympus-analyzer'};
    if(token) headers['Authorization']='Bearer '+token;
    https.get(url, {headers}, res=>{
      if([301,302,307].includes(res.statusCode) && res.headers.location && redirects<5){
        res.resume(); return resolve(fetchBuf(res.headers.location, token, redirects+1));
      }
      if(res.statusCode!==200){ res.resume(); return reject(new Error('HTTP '+res.statusCode+' for '+url)); }
      const chunks=[]; res.on('data',c=>chunks.push(c)); res.on('end',()=>resolve(Buffer.concat(chunks)));
    }).on('error', reject);
  });
}

// minimal tar reader (USTAR): yields {name, data} for regular files
function* untar(buf){
  let off=0;
  while(off+512<=buf.length){
    const block=buf.slice(off, off+512);
    if(block.every(b=>b===0)) break;
    let name=block.toString('utf8',0,100).replace(/\0.*$/,'');
    const prefix=block.toString('utf8',345,500).replace(/\0.*$/,'');
    if(prefix) name=prefix+'/'+name;
    const size=parseInt(block.toString('utf8',124,136).replace(/\0.*$/,'').trim()||'0',8);
    const type=block.toString('utf8',156,157);
    const start=off+512;
    if(type==='0'||type===''||type==='\0') yield {name, data:buf.slice(start, start+size)};
    off = start + Math.ceil(size/512)*512;
  }
}

function langOf(path){if(/\.[cm]?tsx?$/.test(path))return 'ts';if(/\.[cm]?jsx?$/.test(path))return 'js';if(/\.go$/.test(path))return 'go';if(/\.rs$/.test(path))return 'rust';if(/\.py$/.test(path))return 'py';return 'other';}
function scanSymbols(text,path){
  const L=langOf(path),lines=text.split('\n'),sym=new Set();let methods=0,barrel=0,concrete=0;
  const add=n=>{if(n&&n.length>1&&n!=='from'&&n!=='type')sym.add(n);};
  if(L==='ts'||L==='js'){
    lines.forEach(ln=>{let m;
      if(m=ln.match(/^export\s+(?:async\s+)?function\s+([A-Za-z0-9_$]+)/))add(m[1]);
      else if(m=ln.match(/^export\s+(abstract\s+)?class\s+([A-Za-z0-9_$]+)/))add(m[2]);
      else if(m=ln.match(/^export\s+(?:declare\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)/))add(m[1]);
      else if(m=ln.match(/^export\s+interface\s+([A-Za-z0-9_$]+)/))add(m[1]);
      else if(m=ln.match(/^export\s+(?:default\s+)?enum\s+([A-Za-z0-9_$]+)/))add(m[1]);
      else if(m=ln.match(/^export\s+(?:type\s+)?\{([^}]*)\}/))m[1].split(',').forEach(p=>{const nm=p.trim().split(/\s+as\s+/).pop().trim();if(nm&&nm!=='type')add(nm);});
      else if(/^export\s+(?:type\s+)?\*\s+from/.test(ln))barrel++;
      else if(m=ln.match(/^(?:module\.)?exports\.([A-Za-z0-9_$]+)\s*=/))add(m[1]); // CommonJS named export
      if(/^(?:\t+| {2,})(?:public\s+|async\s+|abstract\s+)?[A-Za-z_][A-Za-z0-9_]*\s*\(.*\)\s*[:{]/.test(ln)&&!/^\s*\/\//.test(ln)&&!/\b(if|for|while|switch|return|catch|constructor)\b/.test(ln)){methods++;if(!/abstract\s/.test(ln)&&/\{/.test(ln))concrete++;}
    });
  } else if(L==='go'){
    lines.forEach(ln=>{let m;
      if(m=ln.match(/^func\s+(?:\([^)]*\)\s+)?([A-Z][A-Za-z0-9_]*)\s*\(/)){add(m[1]);if(/^func\s+\(/.test(ln)){methods++;concrete++;}}
      else if(m=ln.match(/^type\s+([A-Z][A-Za-z0-9_]*)\s+(?:struct|interface)/))add(m[1]);});
  } else if(L==='rust'){lines.forEach(ln=>{let m;if(m=ln.match(/^\s*pub\s+(?:async\s+)?fn\s+([A-Za-z0-9_]+)/)){add(m[1]);methods++;concrete++;}else if(m=ln.match(/^\s*pub\s+(?:struct|trait|enum)\s+([A-Za-z0-9_]+)/))add(m[1]);});}
  else if(L==='py'){lines.forEach(ln=>{let m;if(m=ln.match(/^def\s+([A-Za-z0-9_]+)/))add(m[1]);else if(m=ln.match(/^class\s+([A-Za-z0-9_]+)/))add(m[1]);else if(m=ln.match(/^\s{4}def\s+([A-Za-z0-9_]+)/)){methods++;concrete++;}});}
  return {lang:L,symbols:[...sym],count:sym.size,methods,barrel,concrete};
}

const CONTAINER=/(^|\/)(adapters?|drivers?|dialects?|providers?|backends?|handlers?|transports?|protocols?|plugins?|modules?|exporters?|connectors?|codecs?|stores?|engines?|strategies|policies|parsers?|serializers?|formatters?|balancers?|resolvers?)(\/|$)/i;

async function analyzeRepo(repo, ref, token){
  const url='https://codeload.github.com/'+repo+'/tar.gz/'+ref;
  const gz=await fetchBuf(url, token);
  const tar=zlib.gunzipSync(gz);
  const surface=new Set(); let methods=0,barrel=0,concrete=0,files=0;
  const variants={}; const baseHelpers={}; // dir -> concrete methods (free-helper signal)
  for(const f of untar(tar)){
    const rel=f.name.replace(/^[^/]+\//,''); // strip the top tarball dir
    if(!/\.(ts|tsx|js|jsx|mjs|cjs|mts|cts|go|rs|py)$/.test(rel)) continue;
    if(/\.(test|spec|d)\.|__tests__|\/test\/|\/tests\//.test(rel)) continue;
    if(f.data.length>400000) continue; // skip huge generated files
    const txt=f.data.toString('utf8'); const r=scanSymbols(txt, rel);
    r.symbols.forEach(s=>surface.add(s)); methods+=r.methods; barrel+=r.barrel; concrete+=r.concrete; files++;
    const mm=rel.match(CONTAINER);
    if(mm){
      const kind=mm[2].toLowerCase();
      variants[kind]=variants[kind]||{files:0,symbols:0,methods:0};
      variants[kind].files++; variants[kind].symbols+=r.count; variants[kind].methods+=r.methods;
    } else if(/abstract|base/i.test(rel)) {
      baseHelpers[rel]=r.concrete; // base/abstract files with concrete methods = likely free helpers
    }
  }
  const freeHelperConcrete=Object.values(baseHelpers).reduce((a,b)=>a+b,0);
  const vk=Object.keys(variants);
  return {
    repo, ref, filesScanned: files,
    surface: surface.size, barrelReExports: barrel, methods, concreteMethods: concrete,
    variantKinds: vk, variants,
    freeHelperSignal: vk.length>0 && (freeHelperConcrete>=8 || concrete>=vk.length*10),
    freeHelperConcreteMethods: freeHelperConcrete,
    note: 'Surface/method/variant counts are real (full-repo regex scan). freeHelperSignal is a HEURISTIC, not proof — it does not do call-graph analysis or prove a helper is free for a SPECIFIC feature. Approach-wrong and invariant-fails are NOT computed here (behavioural reasoning; use an LLM pass).'
  };
}
// Download + extract a repo tarball at an exact ref and return source files as
// { path, text } (top tarball dir stripped, tests/huge files skipped). Reused by /judge.
async function loadRepoFiles(repo, ref, token){
  const url='https://codeload.github.com/'+repo+'/tar.gz/'+ref;
  const gz=await fetchBuf(url, token);
  const tar=zlib.gunzipSync(gz);
  const out=[];
  for(const f of untar(tar)){
    const rel=f.name.replace(/^[^/]+\//,'');
    if(!/\.(ts|tsx|js|jsx|mjs|cjs|mts|cts|go|rs|py)$/.test(rel)) continue;
    if(/\.(test|spec|d)\.|__tests__|\/test\/|\/tests\//.test(rel)) continue;
    if(f.data.length>400000) continue;
    out.push({path:rel, text:f.data.toString('utf8')});
  }
  return out;
}

module.exports={analyzeRepo, scanSymbols, loadRepoFiles, CONTAINER};
