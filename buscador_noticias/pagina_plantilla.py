"""Plantilla HTML de la página móvil (réplica ligera de la interfaz de Streamlit)."""

PLANTILLA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0f172a">
<title>Amenazas híbridas</title>
<style>
*{box-sizing:border-box}
body{margin:0;font:15px/1.45 "Source Sans Pro",system-ui,sans-serif;background:#fff;color:#0f172a}
header{background:#0f172a;color:#fff;padding:14px 14px 12px;border-left:6px solid #dc2626}
header h1{margin:0;font-size:19px;font-weight:900;letter-spacing:.3px}
header small{color:#7dd3fc;font-weight:700}
#filtros{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px 12px;background:#f8fafc;border-bottom:1px solid #e2e8f0}
#filtros label{font-size:12px;color:#475569;display:block}
#filtros input,#filtros select{width:100%;padding:9px;border:1px solid #e2e8f0;border-radius:8px;background:#f0f2f6;font-size:15px}
#filtros .w{grid-column:1/-1}
#chips{display:flex;gap:6px;overflow-x:auto;padding:8px 12px;background:#e2e8f0}
.chip{flex:none;border:0;border-radius:16px;padding:7px 12px;background:#fff;font-size:14px;cursor:pointer}
.chip.on{background:#ff4b4b;color:#fff}
.pager{display:flex;gap:6px;align-items:center;justify-content:center;padding:8px 12px}
.pager button{flex:1;max-width:80px;padding:9px;border:1px solid #cbd5e1;border-radius:8px;background:#fff;font-size:16px}
.pager button:disabled{opacity:.35}.pager span{font-size:13px;color:#475569;white-space:nowrap}
main{padding:4px 12px 20px}
article{border:1px solid #e2e8f0;border-left:8px solid #0f172a;border-radius:8px;padding:10px 12px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.m{font-size:12px;color:#64748b;margin-bottom:6px}
.b{display:inline-block;border-radius:4px;padding:1px 6px;font-size:11px;font-weight:800;margin-right:4px}
h2{font-size:17px;font-weight:850;margin:4px 0 8px}
.bar{display:flex;gap:12px;margin-bottom:8px}.bar>div{flex:1}
.bar b{font-size:11px;color:#334155}.bar i{display:block;background:#e2e8f0;border-radius:4px;height:8px}.bar u{display:block;height:8px;border-radius:4px}
.cu{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:8px 12px;font-size:13.5px;margin-bottom:8px;white-space:pre-wrap}
.ctx{background:#f0f9ff;border-left:4px solid #0284c7;padding:8px 12px;color:#0c4a6e;font-size:13px;margin-bottom:8px}
.tr{background:#ecfdf5;border-left:4px solid #059669;padding:8px 12px;color:#064e3b;font-size:13.5px;margin-top:8px}
.acc{display:flex;gap:8px;flex-wrap:wrap}
.acc a,.acc button{border:0;border-radius:6px;padding:9px 12px;font-size:13px;font-weight:800;text-decoration:none;cursor:pointer;background:#0f172a;color:#fff}
.acc button{background:#fff;color:#0f172a;border:1px solid #cbd5e1}
.vacio{text-align:center;color:#64748b;padding:30px}
</style></head><body>
<header><h1>🛡️ BUSCADOR DE AMENAZAS HÍBRIDAS</h1><small>Actualizado: __ACTUALIZADO__ · <span id="n"></span></small></header>
<div id="filtros">
<div class="w"><label>🔍 Buscar (admite "frase", OR, AND y -excluir)</label><input id="q" type="search" autocomplete="off"></div>
<div><label>🎯 Precisión</label><select id="m"><option value="e">Exacto</option><option value="b" selected>Equilibrado</option><option value="a">Amplio</option></select></div>
<div><label>📅 Ventana temporal</label><select id="v"><option value="24">Últimas 24 horas</option><option value="48">Últimas 48 horas</option><option value="168">Última semana</option><option value="0">Histórico</option></select></div>
<div><label>⭐ Priorizar</label><select id="o"><option value="c">Actualidad + cobertura</option><option value="r">Más recientes</option></select></div>
<div><label>Canal</label><select id="ca"><option value="">Todos</option></select></div>
<div><label>📄 Por página</label><select id="pp"><option>10</option><option>20</option><option>50</option><option value="0">Todas</option></select></div>
</div>
<div id="chips"></div>
<div class="pager" id="p1"></div><main id="lista"></main><div class="pager" id="p2"></div>
<script>
const D=__DATOS__;const SEC=__SECCIONES__;
const COL={ESPANA:"#dc2626",AGENCIAS:"#4f46e5",EMPRESA:"#d97706",GLOBAL:"#0f172a",CRIPTO:"#7c3aed",SANCIONES:"#b45309",DETENCION:"#be123c",CHINA:"#1e3a8a",CRIMENES:"#991b1b",DRONES:"#0284c7",INJERENCIA:"#7c3aed",OTAN:"#0369a1",ASESINATOS:"#991b1b",TELEGRAM:"#0284c7",REDES:"#059669"};
let sec="",pag=1;const AHORA=Date.now()/1000;
const $=i=>document.getElementById(i);
const norm=s=>(s||"").toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g,"");
const mk=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
[...new Set(D.map(a=>a.c))].sort().forEach(c=>{const o=mk("option","",c);o.value=c;$("ca").append(o)});
const SIN=__SINONIMOS__;
const VACIAS=new Set("de del la las el los en y a un una por con para al the of and in to on for".split(" "));
const ESC=s=>s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
const SINESP=/[\u0600-\u06FF\u3040-\u30ff\u4e00-\u9fff]/,CIR=/[\u0400-\u04FF]/,L="(?<![\\p{L}\\p{N}_])",R="(?![\\p{L}\\p{N}_])";
const cache={};
function patron(t,m){const k=m+"|"+t;if(cache[k])return cache[k];let r,e=ESC(t);
 if(SINESP.test(t))r=e;else if(CIR.test(t)&&t.length>=5)r=L+ESC(t.slice(0,-1));
 else if(m==="e")r=L+e+R;else if(m==="a"&&t.length>=5)r=L+e;else if(t.length>=4)r=L+e+"(?:s|es)?"+R;else r=L+e+R;
 return cache[k]=new RegExp(r,"u")}
function expande(p,m){const r=new Set([p]);if(m==="e")return[...r];
 for(const k in SIN){const ns=SIN[k];if(p===k||ns.includes(p)||(m==="a"&&p.length>=5&&k.length>=5&&p.startsWith(k.slice(0,5))))ns.forEach(x=>r.add(x))}return[...r]}
const casa=(w,h,m)=>expande(w,m).some(v=>patron(v,m).test(h));
function ramas(q){return q.split(/\bOR\b/i).map(s=>s.trim()).filter(Boolean).map(r=>{
 r=r.replace(/^\(|\)$/g,"");const neg=[];
 const pos=r.replace(/(?:NOT\s+|(?:^|\s)-)(?:"([^"]+)"|(\S+))/gi,(_,f,w)=>{neg.push(norm(f||w));return" "});
 const fr=[...pos.matchAll(/"([^"]+)"/g)].map(x=>norm(x[1]).trim());
 const pa=pos.replace(/"[^"]+"/g," ").split(/\bAND\b|\s+/i).map(norm).filter(w=>w&&!VACIAS.has(w));
 return{neg,fr,pa}})}
function cumple(h,rs,m){if(!rs.length)return true;
 for(const{neg,fr,pa}of rs){
  if(neg.some(n=>casa(n,h,m)))continue;
  if(fr.some(f=>!new RegExp(L+ESC(f)+R,"u").test(h)))continue;
  if(!pa.length)return true;
  const ok=pa.filter(w=>casa(w,h,m)).length;
  if(ok>=(m==="a"?Math.ceil(pa.length*.6):pa.length))return true}
 return false}
function filtra(){
 const rs=ramas($("q").value),m=$("m").value,v=+$("v").value,ca=$("ca").value;
 let L=D.filter(a=>{if(sec&&a.s!==sec)return 0;if(ca&&a.c!==ca)return 0;if(v&&AHORA-a.e>v*3600)return 0;return cumple(a.h,rs,m)});
 if($("o").value==="c")L.sort((x,y)=>Math.floor(y.e/21600)-Math.floor(x.e/21600)||y.n-x.n||y.e-x.e);else L.sort((x,y)=>y.e-x.e);
 return L}
function chips(){const c=$("chips");c.innerHTML="";
 [["","Todo"],...SEC].forEach(([k,n])=>{const b=mk("button","chip"+(k===sec?" on":""),n);b.onclick=()=>{sec=k;pag=1;chips();pinta()};c.append(b)})}
function pager(id,tot,pp){const d=$(id);d.innerHTML="";if(!pp||tot<=1)return;
 const bt=(t,p,off)=>{const b=mk("button","",t);b.disabled=off;b.onclick=()=>{pag=p;pinta();scrollTo(0,0)};return b};
 d.append(bt("⏮",1,pag<=1),bt("◀",pag-1,pag<=1),mk("span","","Pág. "+pag+" / "+tot),bt("▶",pag+1,pag>=tot),bt("⏭",tot,pag>=tot))}
async function traduce(a,box,btn){btn.disabled=true;btn.textContent="Traduciendo…";
 const t=async x=>{const r=await fetch("https://api.mymemory.translated.net/get?q="+encodeURIComponent(x.slice(0,480))+"&langpair=Autodetect|es");const j=await r.json();if(!j.responseData)throw 0;return j.responseData.translatedText};
 try{const x=mk("div","tr");const tt=mk("b","",await t(a.t));x.append(mk("div","","🌐 Traducción automática:"),tt);
  if(a.b){x.append(mk("br"),document.createTextNode(await t(a.b)))}box.append(x);btn.remove()}
 catch(e){btn.disabled=false;btn.textContent="🌐 Traducir (servicio saturado, reintenta)"}}
function tarjeta(a){
 const e=mk("article");e.style.borderLeftColor=COL[a.k]||"#0f172a";
 const m=mk("div","m");const h=(AHORA-a.e)/3600;
 const add=(t,bg,fg)=>{const s=mk("span","b",t);s.style.background=bg;s.style.color=fg;m.append(s)};
 if(h<=6)add("⚡ ÚLTIMAS 6 H","#fee2e2","#991b1b");else if(h<=24)add("⚡ 24H","#fee2e2","#991b1b");else if(h<=48)add("🔥 48H","#fef08a","#854d0e");
 if(a.n>1)add("📰 "+a.n+" FUENTES","#dbeafe","#1e40af");
 m.append(document.createTextNode(" 📅 "+a.f+" | 📢 "+a.c));e.append(m,mk("h2","",a.t));
 if(a.fi!==undefined){const bar=mk("div","bar");
  [["🧭 Fiabilidad",a.fi,a.fi>=66?"#16a34a":a.fi>=40?"#d97706":"#dc2626"],["⚠️ Peligro",a.pe,a.pe>=66?"#dc2626":a.pe>=40?"#d97706":"#16a34a"]].forEach(([n,v,c])=>{
   const d=mk("div"),i=mk("i"),u=mk("u");u.style.width=v+"%";u.style.background=c;i.append(u);d.append(mk("b","",n+": "+v+"%"),i);bar.append(d)});e.append(bar)}
 if(a.b)e.append(mk("div","cu",a.b));
 if(a.x)e.append(mk("div","ctx",a.x));
 const acc=mk("div","acc");
 if(a.u){const l=mk("a","","🔗 ABRIR FUENTE ORIGINAL");l.href=a.u;l.target="_blank";l.rel="noopener noreferrer";acc.append(l)}
 const bt=mk("button","","🌐 Traducir al español");bt.onclick=()=>traduce(a,e,bt);acc.append(bt);e.append(acc);return e}
function pinta(){
 const L=filtra(),pp=+$("pp").value,tot=pp?Math.max(1,Math.ceil(L.length/pp)):1;if(pag>tot)pag=tot;
 $("n").textContent=L.length+" noticias";const m=$("lista");m.innerHTML="";
 (pp?L.slice((pag-1)*pp,pag*pp):L).forEach(a=>m.append(tarjeta(a)));
 if(!L.length)m.append(mk("div","vacio","Sin resultados con estos filtros."));
 pager("p1",tot,pp);pager("p2",tot,pp)}
["q","m","v","o","ca","pp"].forEach(i=>$(i).addEventListener(i==="q"?"input":"change",()=>{pag=1;pinta()}));
chips();pinta();
</script></body></html>"""
