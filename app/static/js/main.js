const $ = (s, r) => (r || document).querySelector(s), $$ = (s, r) => [...(r || document).querySelectorAll(s)];
const io = new IntersectionObserver(es => es.forEach(e => e.isIntersecting && (e.target.classList.add("in"), io.unobserve(e.target))), {threshold: .12});
$$(".bgrid .bcard,.cgrid .ctile").forEach((el,i)=>{el.classList.add("reveal");el.style.transitionDelay=(i%6)*80+"ms";setTimeout(()=>el.style.transitionDelay="",2500)});
$$(".reveal,.rails,.finale").forEach(el => io.observe(el));
// carrosséis: setas, arraste nativo e rolagem automática pausável
$$(".rails").forEach(sec => {
  const r = $(".rail", sec), step = () => r.clientWidth * .8;
  $(".prev", sec).onclick = () => r.scrollBy({left: -step(), behavior: "smooth"});
  $(".next", sec).onclick = () => r.scrollBy({left: step(), behavior: "smooth"});
  if (r.hasAttribute("data-auto") && !matchMedia("(prefers-reduced-motion:reduce)").matches) {
    let pos = 0, paused = false, vis = false, t;
    const hold = () => { paused = true; clearTimeout(t); }, go = d => { clearTimeout(t); t = setTimeout(() => { pos = r.scrollLeft; paused = false; }, d); };
    r.addEventListener("pointerenter", e => e.pointerType === "mouse" && hold()); r.addEventListener("pointerleave", e => e.pointerType === "mouse" && go(200));
    r.addEventListener("touchstart", hold, {passive: true}); r.addEventListener("touchend", () => go(2500));
    sec.addEventListener("click", e => e.target.closest("button") && (hold(), go(3000)));
    new IntersectionObserver(e => vis = e[0].isIntersecting).observe(r);
    (function tick() { if (!paused && vis) { pos += .45; r.scrollLeft = pos; if (r.scrollLeft < pos - 2) pos = 0; } requestAnimationFrame(tick); })();
  }
});
// catálogo: busca, filtros inteligentes, favoritos
const ls = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) || d; } catch (e) { return d; } }, lset = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
let sel = ls("luft_sel", []), fav = ls("luft_fav", []), cat = "all";
const grid = $("#grid"), cards = grid ? $$(".card", grid) : [], val = id => ($("#" + id) || {}).value || "";
const catMatch = c => c.dataset.cat === cat || c.dataset.cat.startsWith(cat + "-");
function refill() {
  const vis = cards.filter(c => cat === "all" || cat === "fav" || catMatch(c));
  [["team", "Todos os times", "team"], ["size", "Todos os tamanhos", "sizes"], ["color", "Todas as cores", "colors"]].forEach(([id, lab, k]) => {
    const el = $("#" + id); if (!el) return; const set = new Set(); vis.forEach(c => (c.dataset[k] || "").split("|").filter(Boolean).forEach(v => set.add(v)));
    const cur = el.value; el.innerHTML = `<option value="">${lab}</option>` + [...set].sort((a, b) => a.localeCompare(b, "pt", {numeric: true})).map(v => `<option>${v}</option>`).join(""); el.value = set.has(cur) ? cur : ""; el.hidden = !set.size; });
}
let lim = 12;
function apply(keep) {
  if (keep !== true) lim = 12;
  const q = val("q").toLowerCase().trim(), b = val("brand"), [lo, hi] = val("price") ? val("price").split("-").map(Number) : [0, 1e9], promo = $("#promo") && $("#promo").checked, sort = val("sort");
  const has = (c, k, v) => !v || (c.dataset[k] || "").split("|").includes(v);
  const ok = cards.filter(c => { const p = +c.dataset.price, id = c.querySelector(".fav").dataset.id;
    const show = (cat === "all" || (cat === "fav" ? fav.includes(id) : catMatch(c))) && (!b || c.dataset.brand === b) && p >= lo && p <= hi && (!promo || c.dataset.promo === "1")
      && (!val("team") || c.dataset.team === val("team")) && has(c, "sizes", val("size")) && has(c, "colors", val("color")) && c.dataset.name.includes(q) && (!$("#avail") || !$("#avail").checked || c.dataset.avail === "1");
    return show; });
  ok.sort((x, y) => sort === "asc" ? x.dataset.price - y.dataset.price : sort === "desc" ? y.dataset.price - x.dataset.price : y.dataset.ts - x.dataset.ts).forEach(c => grid.append(c));
  cards.forEach(c => c.hidden = true); ok.forEach((c, i) => c.hidden = i >= lim);
  const mb = $("#morebtn"); if (mb) mb.hidden = ok.length <= lim; const ct = $("#count"); if (ct) ct.textContent = cards.length ? `${ok.length} produto${ok.length === 1 ? "" : "s"}` : "";
  const none = $("#none"); if (none) none.hidden = ok.length > 0 || !cards.length;
}
const setCat = f => { cat = f; $$(".chip").forEach(y => y.classList.toggle("on", y.dataset.f === f)); refill(); apply(); };
["q", "brand", "price", "sort", "promo", "avail", "team", "size", "color"].forEach(id => $("#" + id) && $("#" + id).addEventListener("input", apply));
$$(".chip").forEach(x => x.onclick = () => setCat(x.dataset.f));
$$(".ctile").forEach(x => x.onclick = () => { setCat(x.dataset.f); $("#catalogo").scrollIntoView({behavior: "smooth"}); });
$$(".bcard").forEach(x => x.onclick = () => { $("#brand").value = x.dataset.b; apply(); $("#catalogo").scrollIntoView({behavior: "smooth"}); });
refill(); apply();
const mbtn = $("#morebtn"); if (mbtn) mbtn.onclick = () => { lim += 12; apply(true); };
const q = $("#q"), sug = $("#sug");
if (q && sug) {
  q.addEventListener("input", () => { const t = q.value.toLowerCase().trim(); if (t.length < 2) return sug.hidden = true;
    const cs = $$(".chip").filter(c => !["all", "fav"].includes(c.dataset.f) && c.textContent.toLowerCase().includes(t)).slice(0, 3);
    const ps = cards.filter(c => c.dataset.name.includes(t)).slice(0, 4);
    sug.innerHTML = cs.map(c => `<button data-c="${c.dataset.f}">${c.textContent}<small>categoria</small></button>`).join("") + ps.map(c => { const im = c.querySelector(".thumb img");
      return `<a href="${c.querySelector("a.thumb").href}">${im ? `<img src="${im.src}" alt="">` : "<i></i>"}<span>${c.querySelector("h3").textContent}</span><b>${c.querySelector(".price strong").textContent}</b></a>`; }).join("");
    sug.hidden = !sug.innerHTML; });
  sug.onclick = e => { const b = e.target.closest("button"); if (b) { setCat(b.dataset.c); sug.hidden = true; $("#catalogo").scrollIntoView({behavior: "smooth"}); } };
  document.addEventListener("click", e => { if (!e.target.closest(".sw")) sug.hidden = true; });
}
// nav + parallax
const nav = $(".nav"), mark = $(".showcase"), calm = matchMedia("(prefers-reduced-motion:reduce)").matches; let tk = false;
addEventListener("scroll", () => { if (tk) return; tk = true; requestAnimationFrame(() => { const y = scrollY; nav.classList.toggle("scrolled", y > 40); if (mark && !calm && y < innerHeight) mark.style.setProperty("--py", y * .07 + "px"); tk = false; }); }, {passive: true});
// seleção, favoritos, WhatsApp
const wanum = document.body.dataset.wa, beacon = (k, id, m) => navigator.sendBeacon && navigator.sendBeacon(`/t/${k}/${id}` + (m ? `?m=${encodeURIComponent(m)}` : ""));
function toast(t, err) { const d = document.createElement("div"); d.className = "toast" + (err ? " err" : ""); d.textContent = t; document.body.append(d); setTimeout(() => d.classList.add("out"), 2000); setTimeout(() => d.remove(), 2600); }
const esc = t => String(t).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const brl = v => "R$ " + (+v).toLocaleString("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const stockOf = (it, d) => { // estoque real da combinação escolhida (Infinity = sem controle)
  if (!d) return Infinity; const vs = d.variants || [];
  if (vs.length) return vs.filter(v => (!it.color || v.c.toLowerCase() === it.color.toLowerCase()) && (!it.size || v.s.toLowerCase() === it.size.toLowerCase())).reduce((a, v) => a + v.q, 0);
  return d.stock == null ? Infinity : d.stock; };
function draw() {
  const n = sel.reduce((a, x) => a + x.qty, 0); $("#selcount").textContent = n; $("#selbtn").classList.toggle("has", n > 0);
  $(".dh b").textContent = n ? `${n} ${n > 1 ? "itens" : "item"} na sua seleção` : "Minha seleção";
  $("#dlist").innerHTML = sel.length ? sel.map((x, i) => `<div class="di">${x.img ? `<img src="${x.img}" alt="">` : "<i></i>"}<div><b>${esc(x.name)}</b><small>${esc([x.size && "Tamanho " + x.size, x.color && "Cor " + x.color].filter(Boolean).join(" · ") || "Sem opções")}</small><small>${x.val != null ? `${x.qty} × ${brl(x.val)} = <b>${brl(x.qty * x.val)}</b>` : esc(x.price || "")}</small>
    ${x.out ? '<small class="bad">Indisponível no momento — remova para enviar</small>' : `<div class="stp"><button data-a="dec" data-i="${i}" ${x.qty <= 1 ? "disabled" : ""} aria-label="Menos">−</button><span>${x.qty}</span><button data-a="inc" data-i="${i}" ${x.max != null && x.qty >= x.max ? "disabled" : ""} aria-label="Mais">+</button></div>${x.max != null && x.qty >= x.max ? `<small>Máximo em estoque: ${x.max}</small>` : ""}`}</div><button data-i="${i}" aria-label="Remover">×</button></div>`).join("") : '<p class="dempty">Sua seleção está vazia. Escolha produtos e toque em adicionar.</p>';
  const tot = sel.filter(x => !x.out).reduce((a, x) => a + (x.val || 0) * x.qty, 0); $("#dtotal").innerHTML = sel.length && tot ? `<span>Total estimado</span><b>${brl(tot)}</b>` : "";
  $$(".fav").forEach(b => b.classList.toggle("on", fav.includes(b.dataset.id))); $$("#pfav").forEach(b => b.classList.toggle("on", fav.includes(b.dataset.id)));
  const fn = $("#favn"); if (fn) fn.textContent = fav.length ? `(${fav.length})` : "";
}
function add(it) { const ex = sel.find(x => x.id == it.id && x.size == it.size && x.color == it.color), have = ex ? ex.qty : 0, cap = it.max == null ? 99 : it.max;
  if (have + it.qty > cap) { if (have >= cap) return toast(cap ? `Você já tem ${have} na seleção. Limite de estoque: ${cap}.` : "Produto esgotado.", 1); it.qty = cap - have; toast(`Só há ${cap} unidade${cap > 1 ? "s" : ""} em estoque. Ajustamos a quantidade.`, 1); }
  if (ex) { ex.qty += it.qty; ex.max = it.max; } else sel.push(it);
  lset("luft_sel", sel); draw(); beacon("sel", it.id, it.size);
  const tot = sel.reduce((a, x) => a + x.qty, 0); toast(`✓ ${tot} ${tot > 1 ? "itens" : "item"} na sua seleção`); const b = $("#selbtn"); b.classList.remove("bump"); void b.offsetWidth; b.classList.add("bump"); }
const buildMsg = () => { const d = $("#drawer").dataset, tot = sel.reduce((a, x) => a + (x.val || 0) * x.qty, 0);
  const lines = sel.map((x, i) => `${i + 1}. ${x.name}` + (x.size ? `\n   Tamanho: ${x.size}` : "") + (x.color ? `\n   Cor: ${x.color}` : "") + (x.val != null ? `\n   ${x.qty} × ${brl(x.val)} = ${brl(x.qty * x.val)}` : `\n   Quantidade: ${x.qty}`));
  return "Olá! 👋\n\n" + d.intro.replace(/^Olá!\s*/, "") + "\n\n" + lines.join("\n\n") + (tot ? `\n\nTotal estimado: ${brl(tot)}` : "") + "\n\n" + d.outro; };
const drawer = o => document.body.classList.toggle("dopen", o);
$("#selbtn").onclick = () => drawer(true); $("#dclose").onclick = $("#dback").onclick = () => drawer(false);
addEventListener("keydown", e => { if (e.key !== "Escape") return; if (document.body.classList.contains("dopen")) drawer(false); else if (xc) closeProduct(); });
let cf = 0; $("#dclear").onclick = e => { if (!sel.length) return; const bt = e.currentTarget;
  if (!cf) { bt.textContent = "Toque de novo para confirmar"; cf = setTimeout(() => { cf = 0; bt.textContent = "Limpar seleção"; }, 3000); return; }
  clearTimeout(cf); cf = 0; bt.textContent = "Limpar seleção"; sel = []; lset("luft_sel", sel); draw(); toast("✓ Seleção limpa"); };
$("#dlist").onclick = e => { const b = e.target.closest("button"); if (!b) return; const i = +b.dataset.i, x = sel[i]; if (!x) return;
  if (b.dataset.a === "inc") { if (x.max != null && x.qty >= x.max) return toast(`Limite de estoque: ${x.max} unidade${x.max > 1 ? "s" : ""}.`, 1); x.qty++; }
  else if (b.dataset.a === "dec") { if (x.qty <= 1) return; x.qty--; } else { sel.splice(i, 1); toast("✓ Produto removido"); }
  lset("luft_sel", sel); draw(); };
$("#dsend").onclick = async () => { if (!sel.length) return toast("Adicione produtos primeiro", 1); const bt = $("#dsend"), win = open("about:blank", "_blank");
  bt.classList.add("loading"); try { await sync(); } catch (e) {} bt.classList.remove("loading");
  if (sel.some(x => x.out)) { win && win.close(); return toast("Remova os itens indisponíveis antes de enviar.", 1); }
  if (!sel.length) { win && win.close(); return; } const url = `https://wa.me/${wanum}?text=${encodeURIComponent(buildMsg())}`; win ? (win.location.href = url) : (location.href = url); toast("✓ Mensagem preparada"); };
$("#dcopy").onclick = () => { if (!sel.length) return toast("Adicione produtos primeiro", 1);
  (navigator.clipboard ? navigator.clipboard.writeText(buildMsg()) : Promise.reject()).then(() => toast("✓ Lista copiada"), () => toast("Não foi possível copiar", 1)); };
const toggleFav = id => { fav = fav.includes(id) ? fav.filter(x => x !== id) : [...fav, id]; lset("luft_fav", fav); draw(); if (cat === "fav") apply(); };
document.addEventListener("click", e => {
  const s = e.target.closest(".sel"); if (s) { if (s.dataset.opts === "1") { toast("Escolha o tamanho na página do produto"); try { sessionStorage.setItem("luft_y", String(scrollY)); } catch (e) {} location.href = s.parentElement.querySelector("a.thumb").href; } else add({id: s.dataset.id, name: s.dataset.name, qty: 1, img: s.dataset.img, price: s.dataset.price, val: +s.dataset.val, max: s.dataset.max === "" ? null : +s.dataset.max}); }
  const f = e.target.closest(".fav,#pfav"); if (f) toggleFav(f.dataset.id);
  const pl = e.target.closest('a[href^="/produto/"]'); if (pl && $("#catalogo")) { try { sessionStorage.setItem("luft_y", String(scrollY)); } catch (e) {} }
  const w = e.target.closest("a[data-wa]"); if (w && !e.defaultPrevented) beacon("wa", w.dataset.pid);
});
draw();
const pw = $("#pwa");
if (pw) {
  const V = JSON.parse($("#vars").textContent || "[]"), pick = {}; let qty = 1;
  const need = {size: !!$('[data-g="size"]'), color: !!$('[data-g="color"]')}, lab = {size: "um tamanho", color: "uma cor"};
  const stock = (c, s) => V.filter(v => (!c || v.c === c) && (!s || v.s === s)).reduce((a, v) => a + v.q, 0);
  const S0 = pw.dataset.stock === "" ? null : +pw.dataset.stock, cap = () => V.length ? stock(pick.color, pick.size) : (S0 == null ? 99 : S0);
  const paint = () => {
    $$('[data-g="size"] .opt').forEach(b => b.classList.toggle("off", V.length > 0 && stock(pick.color, b.dataset.v) <= 0));
    $$('[data-g="color"] .opt').forEach(b => b.classList.toggle("off", V.length > 0 && stock(b.dataset.v, pick.size) <= 0));
    const c0 = cap(); if (qty > c0) qty = Math.max(1, c0); $("#qv").textContent = qty; $("#qhint").textContent = c0 < 99 ? (c0 < 1 ? "Indisponível" : `Disponível: ${c0} un.`) : "";
    const o = [pick.size && "Tamanho: " + pick.size, pick.color && "Cor: " + pick.color, qty > 1 && "Quantidade: " + qty].filter(Boolean);
    pw.href = `https://wa.me/${wanum}?text=` + encodeURIComponent(pw.dataset.tpl.replace("{produto}", pw.dataset.name).replace("{preco}", pw.dataset.price).replace("{opcoes}", o.length ? " (" + o.join(", ") + ")" : "")); };
  const ok = () => { for (const k of ["size", "color"]) if (need[k] && !pick[k]) { toast(`Selecione ${lab[k]} para continuar.`, 1); const g = $(`[data-g="${k}"]`); g.classList.remove("shake"); void g.offsetWidth; g.classList.add("shake"); return false; } return true; };
  $$(".opts").forEach(g => g.onclick = e => { const b = e.target.closest(".opt"); if (!b) return;
    if (b.classList.contains("off")) return toast("Essa combinação está indisponível.", 1);
    const was = b.classList.contains("on"); $$(".opt", g).forEach(x => x.classList.remove("on")); if (!was) b.classList.add("on"); pick[g.dataset.g] = was ? null : b.dataset.v; paint(); if (g.dataset.g === "color") gallery(pick.color); });
  $("#qm").onclick = () => { qty = Math.max(1, qty - 1); $("#qv").textContent = qty; paint(); };
  $("#qp").onclick = () => { const c = cap(); if (qty >= c) return toast(c < 1 ? "Essa combinação está indisponível." : `Limite de estoque: ${c} unidade${c > 1 ? "s" : ""}.`, 1); qty++; $("#qv").textContent = qty; paint(); };
  pw.addEventListener("click", e => { if (!ok()) return e.preventDefault(); if (cap() < 1) { e.preventDefault(); toast("Essa combinação está indisponível.", 1); } });
  $("#addsel").onclick = e => { if (!ok()) return; if (cap() < 1) return toast("Essa combinação está indisponível.", 1); const b = e.currentTarget; add({id: b.dataset.id, name: b.dataset.name, size: pick.size, color: pick.color, qty, max: cap() >= 99 ? null : cap(), img: ($("#mainimg") || {}).src || "", price: pw.dataset.price, val: +pw.dataset.val}); const t = b.textContent; b.textContent = "✓ Adicionado"; b.classList.add("done"); setTimeout(() => { b.textContent = t; b.classList.remove("done"); }, 1700); };
  paint();
}
const G = $("#gal") ? JSON.parse($("#gal").textContent) : null, mi = $("#mainimg"), th = $("#thumbs");
function gallery(color) { // troca as fotos conforme a cor escolhida
  if (!G || !mi) return; const k = color && Object.keys(G.colors).find(x => x.toLowerCase() === String(color).toLowerCase());
  const list = k && G.colors[k].length ? G.colors[k] : G.general; if (!list.length) return;
  mi.style.opacity = 0; setTimeout(() => { mi.src = list[0]; mi.hidden = false; const ph = $("#ph"); if (ph) ph.hidden = true; mi.style.opacity = 1; }, 180);
  th.innerHTML = list.length > 1 ? list.map((u, i) => `<button class="gt ${i ? "" : "on"}" data-src="${esc(u)}"><img src="${esc(u)}" alt=""></button>`).join("") : "";
}
if (th) th.onclick = e => { const b = e.target.closest(".gt"); if (!b) return; $$(".gt").forEach(x => x.classList.remove("on")); b.classList.add("on"); mi.style.opacity = 0; setTimeout(() => { mi.src = b.dataset.src; mi.style.opacity = 1; }, 180); };
gallery(null);
const xc = $("#xclose"), closeProduct = () => { let same = false; try { same = document.referrer && new URL(document.referrer).origin === location.origin; } catch (e) {} if (same) history.back(); else { try { sessionStorage.setItem("luft_return", "1"); } catch (e) {} location.href = "/"; } };
if (xc) xc.onclick = closeProduct;
const pb = $("#pbtn"); if (pb && pw) pb.onclick = () => pw.click();
const z = $(".zoom"); z && z.addEventListener("pointermove", e => { const r = z.getBoundingClientRect(); z.style.setProperty("--ox", (e.clientX - r.left) / r.width * 100 + "%"); z.style.setProperty("--oy", (e.clientY - r.top) / r.height * 100 + "%"); });

// carrossel principal + barra de categorias
$$(".cb,.slide .btn").forEach(b => b.onclick = () => { const g = b.dataset.g, pr = $("#promo");
  if (g === "promo") { pr.checked = true; setCat("all"); } else { pr.checked = false; setCat(g); } $("#catalogo").scrollIntoView({behavior: "smooth"}); });
const sl = $("#slider");
if (sl) {
  const S = $$(".slide", sl), D = $$(".sdots button", sl); let i = 0, t, paused = false, seen = true;
  const show = n => { i = (n + S.length) % S.length; S.forEach((x, k) => x.classList.toggle("on", k === i)); D.forEach((x, k) => x.classList.toggle("on", k === i)); };
  const go = () => { clearInterval(t); if (!calm) t = setInterval(() => !paused && seen && show(i + 1), 6500); };
  $(".next", sl).onclick = () => { show(i + 1); go(); }; $(".prev", sl).onclick = () => { show(i - 1); go(); };
  D.forEach((d, k) => d.onclick = () => { show(k); go(); });
  sl.addEventListener("pointerenter", e => e.pointerType === "mouse" && (paused = true)); sl.addEventListener("pointerleave", () => paused = false);
  let x0 = null; sl.addEventListener("touchstart", e => { x0 = e.touches[0].clientX; paused = true; }, {passive: true});
  sl.addEventListener("touchend", e => { const dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 45) { show(i + (dx < 0 ? 1 : -1)); go(); } setTimeout(() => paused = false, 2500); });
  addEventListener("keydown", e => { if (seen && e.key === "ArrowRight") show(i + 1); if (seen && e.key === "ArrowLeft") show(i - 1); });
  new IntersectionObserver(e => seen = e[0].isIntersecting).observe(sl); go();
}

// vistos recentemente, avise-me, filtros no celular
const rc = $(".zoom[data-rec]");
if (rc) { const id = rc.dataset.rec.split("|")[0]; lset("luft_rec", [id, ...ls("luft_rec", []).filter(x => typeof x === "string" && x !== id)].slice(0, 8)); }
async function sync() { // só mostra o que existe de verdade no servidor; remove o que foi apagado
  const rec = ls("luft_rec", []).filter(x => typeof x === "string"), ids = [...new Set([...rec, ...sel.map(x => x.id), ...fav])].filter(Boolean);
  if (!ids.length) return;
  try { const d = await (await fetch("/api/produtos?ids=" + ids.join(","))).json();
    sel = sel.filter(x => d[x.id]); let adj = false;
    sel.forEach(x => { const p = d[x.id]; Object.assign(x, {name: p.name, price: p.price, val: p.val, img: p.img}); const m = stockOf(x, p); x.max = m === Infinity ? null : m; x.out = !p.avail || m === 0; if (x.max != null && x.max > 0 && x.qty > x.max) { x.qty = x.max; adj = true; } });
    if (adj) toast("Ajustamos itens da sua seleção conforme o estoque atual.", 1); fav = fav.filter(x => d[x]);
    const ok = rec.filter(x => d[x]); lset("luft_sel", sel); lset("luft_fav", fav); lset("luft_rec", ok); draw();
    const rl = $("#recent"); if (rl && ok.length) { $("#recentw").hidden = false; rl.innerHTML = ok.map(id => { const x = d[id]; return `<a class="rcard" href="${esc(x.href)}">${x.img ? `<img src="${esc(x.img)}" alt="">` : "<i></i>"}<span>${esc(x.name)}</span><b>${esc(x.price)}</b></a>`; }).join(""); }
  } catch (e) {}
}
sync();
const nb = $("#nbtn");
if (nb) nb.onclick = async () => { const c = $("#ncontact").value.trim(); if (c.length < 5) return toast("Informe um WhatsApp ou e-mail válido.", 1);
  try { const r = await fetch("/avise/" + nb.dataset.id, {method: "POST", body: new URLSearchParams({contact: c})}); if (!r.ok) throw 0; nb.textContent = "✓ Pedido registrado"; nb.disabled = true; $("#ncontact").value = ""; toast("✓ Avisaremos você quando chegar"); }
  catch (e) { toast("Não foi possível registrar. Tente novamente.", 1); } };
const tools = $("#tools"), fb = $("#fbtn");
if (fb) { fb.onclick = () => tools.classList.toggle("open"); $("#fapply").onclick = () => { tools.classList.remove("open"); $("#catalogo").scrollIntoView({behavior: "smooth"}); };
  $("#fclear").onclick = () => { ["brand", "price", "team", "size", "color", "q"].forEach(id => { const e = $("#" + id); if (e) e.value = ""; }); $("#promo").checked = false; $("#sort").value = "new"; setCat("all"); tools.classList.remove("open"); toast("✓ Filtros limpos"); }; }

// volta para o mesmo ponto da página ao fechar um produto
(() => { let y = 0, ret = false, bf = false; try { y = +(sessionStorage.getItem("luft_y") || 0); ret = sessionStorage.getItem("luft_return") === "1"; bf = ((performance.getEntriesByType("navigation")[0] || {}).type === "back_forward"); } catch (e) {}
  if (!$("#catalogo") || !y || !(ret || bf)) return; try { history.scrollRestoration = "manual"; } catch (e) {} const go = () => scrollTo(0, y);
  go(); requestAnimationFrame(go); setTimeout(go, 350); addEventListener("load", () => { go(); try { sessionStorage.removeItem("luft_return"); } catch (e) {} }); })();
const cf2 = $("#fclear2"); if (cf2) cf2.onclick = () => { ["brand", "price", "team", "size", "color", "q"].forEach(id => { const e = $("#" + id); if (e) e.value = ""; }); $("#promo").checked = false; if ($("#avail")) $("#avail").checked = false; setCat("all"); };

{ const qc = new URLSearchParams(location.search).get("cat"); if (qc && $(`.chip[data-f="${qc}"]`)) setCat(qc); } // links do rodapé e do produto
