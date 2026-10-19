// Dernier Studio front end (no dependencies).
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const api = (p, opt) => fetch(p, opt).then(r => r.json());
const file = p => "/files/" + p.split("/").map(encodeURIComponent).join("/");
let PROJECT = null, CUR = null;

function toast(msg, bad) {
  const t = $("#toast"); t.textContent = msg; t.style.borderColor = bad ? "var(--bad)" : "var(--accent)";
  t.style.display = "block"; clearTimeout(t._h); t._h = setTimeout(() => t.style.display = "none", 3500);
}
function esc(s) { return String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c])); }

// ---------------------------------------------------------------- tabs
$$("#tabs button").forEach(b => b.onclick = () => show(b.dataset.tab));
function show(tab) {
  $$("#tabs button").forEach(b => b.classList.toggle("on", b.dataset.tab === tab));
  $$(".tab").forEach(t => t.classList.toggle("on", t.id === tab));
  if (tab === "scene" && !CUR && PROJECT) {
    const w = PROJECT.scenes.find(s => s.name.endsWith("Physics")) || PROJECT.scenes[0];
    openScene(w.id); return;
  }
  ({flow: drawFlow, dialogue: drawDialogue, map: drawMap, sprites: drawSprites, palettes: drawPalettes,
    vars: drawVars, guide: drawDoc})[tab]?.();
  location.hash = tab;
}

async function init() {
  PROJECT = await api("/api/project");
  const pick = $("#scenePick");
  pick.innerHTML = PROJECT.scenes.slice().sort((a, b) => a.name.localeCompare(b.name))
    .map(s => `<option value="${s.id}">${esc(s.name)}</option>`).join("");
  pick.onchange = () => openScene(pick.value);
  ["showColl", "showTrig", "showActors", "zoom"].forEach(id => $("#" + id).onchange = () => CUR && drawScene(CUR));
  $("#flowFilter").oninput = drawFlow; $("#flowThumbs").onchange = drawFlow;
  $("#dlgFilter").oninput = () => drawDialogue(true); $("#dlgType").onchange = () => drawDialogue(true);
  $("#docPick").onchange = drawDoc;
  $("#runCheck").onclick = async () => { $("#checkOut").textContent = "running..."; const r = await api("/api/check"); $("#checkOut").textContent = r.output; };
  show((location.hash || "#flow").slice(1));
}

// ---------------------------------------------------------------- flow graph
let GRAPH = null;
async function drawFlow() {
  GRAPH = GRAPH || await api("/api/graph");
  const f = $("#flowFilter").value.toLowerCase(), thumbs = $("#flowThumbs").checked;
  const nodes = GRAPH.nodes.filter(n => !f || n.name.toLowerCase().includes(f));
  const folderOf = n => n.name.includes("/") ? n.name.split("/")[0] : "Original B7 scenes";
  const order = ["0 Menus", "1 Prologue", "3 Days", "Original B7 scenes", "2 Campus", "2 Campus Interiors", "4 Outbreak", "5 The Middle", "6 Finale"];
  const cols = {};
  nodes.forEach(n => (cols[folderOf(n)] = cols[folderOf(n)] || []).push(n));
  const keys = Object.keys(cols).sort((a, b) => (order.indexOf(a) + 99 * (order.indexOf(a) < 0)) - (order.indexOf(b) + 99 * (order.indexOf(b) < 0)));
  const W = 190, H = thumbs ? 124 : 46, pos = {};
  document.documentElement.style.setProperty("--nodeh", H + "px");
  let html = "";
  keys.forEach((k, ci) => {
    html += `<div class="colhead" style="left:${ci * W + 10}px;top:6px">${esc(k)}</div>`;
    cols[k].sort((a, b) => a.name.localeCompare(b.name)).forEach((n, ri) => {
      const x = ci * W + 10, y = 30 + ri * (H + 10);
      pos[n.id] = [x, y];
      const short = n.name.includes("/") ? n.name.split("/").slice(1).join("/") : n.name;
      html += `<div class="node" data-id="${n.id}" style="left:${x}px;top:${y}px">` +
        (thumbs && n.preview ? `<img src="${file(n.preview)}" loading="lazy">` : "") +
        `<div class="t" title="${esc(n.name)}">${esc(short)}</div><div class="m">${n.bg ? esc(n.bg) + " - " : ""}${n.type} ${n.w}x${n.h}</div></div>`;
    });
  });
  const maxY = Math.max(400, ...Object.values(pos).map(p => p[1] + H + 20)), maxX = keys.length * W + 20;
  let svg = `<svg class="edges" width="${maxX}" height="${maxY}"><defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#78d4f088"/></marker></defs>`;
  const seen = new Set();
  GRAPH.edges.forEach(e => {
    const a = pos[e.from], b = pos[e.to]; const k = e.from + e.to;
    if (!a || !b || e.from === e.to || seen.has(k)) return; seen.add(k);
    const x1 = a[0] + 150, y1 = a[1] + H / 2, x2 = b[0], y2 = b[1] + H / 2;
    svg += `<path d="M${x1},${y1} C${x1 + 40},${y1} ${x2 - 40},${y2} ${x2},${y2}" stroke="#78d4f044" fill="none" marker-end="url(#ar)"/>`;
  });
  svg += "</svg>";
  $("#flowCanvas").innerHTML = `<div style="position:relative;width:${maxX}px;height:${maxY}px">${svg}${html}</div>`;
  $$("#flowCanvas .node").forEach(el => el.onclick = () => { openScene(el.dataset.id); });
}

// ---------------------------------------------------------------- scene view
async function openScene(id) {
  CUR = await api("/api/scene/" + id);
  $("#scenePick").value = id;
  if (!$("#scene").classList.contains("on")) show("scene");
  drawScene(CUR);
  inspect("scene", CUR);
}

function decompress(str) {
  const out = []; let i = 0;
  while (i < str.length) {
    const v = parseInt(str.slice(i, i + 2), 16); i += 2;
    if (str[i] === "!") { out.push(v); i++; continue; }
    const j = str.indexOf("+", i); const n = parseInt(str.slice(i, j), 16); i = j + 1;
    for (let k = 0; k < n; k++) out.push(v);
  }
  return out;
}

function drawScene(s) {
  const z = +$("#zoom").value, T = 8 * z;
  $("#sceneFile").textContent = s._file;
  let html = `<div class="layer" style="width:${s.width * T}px;height:${s.height * T}px">`;
  html += `<img class="bg" src="${file(s.preview)}" style="width:${s.width * T}px;height:${s.height * T}px">`;
  if ($("#showColl").checked && s.collisions) {
    const c = decompress(s.collisions);
    for (let y = 0; y < s.height; y++) for (let x = 0; x < s.width; x++)
      if (c[y * s.width + x]) html += `<div class="coll" style="left:${x * T}px;top:${y * T}px;width:${T}px;height:${T}px"></div>`;
  }
  if ($("#showTrig").checked) s._triggers.forEach((t, i) =>
    html += `<div class="trig" data-i="${i}" title="${esc(t.name)}" style="left:${t.x * T}px;top:${t.y * T}px;width:${t.width * T}px;height:${t.height * T}px"></div>`);
  if ($("#showActors").checked) s._actors.forEach((a, i) => {
    const src = s.spriteFiles[a.spriteSheetId];
    html += `<img class="act" data-i="${i}" title="${esc(a.name)}" src="${src ? file(src) : ""}" style="left:${a.x * T}px;top:${(a.y - 1) * T}px;width:${2 * T}px;height:${2 * T}px;object-fit:cover;object-position:left">`;
  });
  html += "</div>";
  $("#stage").innerHTML = html;
  $$("#stage .trig").forEach(el => el.onclick = () => { sel(el); inspect("trigger", s._triggers[+el.dataset.i]); });
  $$("#stage .act").forEach(el => el.onclick = () => { sel(el); inspect("actor", s._actors[+el.dataset.i]); });
}
function sel(el) { $$("#stage .sel").forEach(e => e.classList.remove("sel")); el.classList.add("sel"); }

const KEYS = {scene: ["script", "playerHit1Script"], actor: ["script", "startScript", "updateScript", "hit1Script"],
  trigger: ["script", "leaveScript"]};
const LABEL = {script: "On interact / enter / init", startScript: "On init", updateScript: "On update (loops)",
  hit1Script: "On hit (group 1)", leaveScript: "On leave", playerHit1Script: "Player hit"};

function inspect(kind, obj) {
  let h = `<h3>${kind === "scene" ? "Scene" : kind === "actor" ? "Actor" : "Trigger"}: ${esc(obj.name || "(unnamed)")}</h3>`;
  if (kind !== "scene") h += `<div class="hint">tile ${obj.x}, ${obj.y}${obj.width ? `, size ${obj.width}x${obj.height}` : ""} - file ${esc(obj._file || "")}</div>`;
  for (const k of KEYS[kind]) {
    const sc = obj[k] || [];
    if (!sc.length) continue;
    h += `<h3>${LABEL[k] || k}</h3>` + renderScript(sc);
  }
  if (h.indexOf("ev ") < 0) h += `<p class="hint">No events.</p>`;
  $("#inspector").innerHTML = h;
  bindEditors($("#inspector"));
  $$("#inspector a.go").forEach(a => a.onclick = () => openScene(a.dataset.id));
}

const V = id => (CUR?.vars || PROJECT?.vars || {})[id] || id;
const VAL = v => v == null ? "?" : typeof v !== "object" ? v : v.type === "number" ? v.value : v.type === "variable" ? V(v.value) : v.type === "direction" ? v.value : JSON.stringify(v);
const ACT = id => id === "player" ? "Player" : id === "$self$" ? "this actor" : (CUR?._actors.find(a => a.id === id)?.name || id?.slice(0, 6));

const OPN = {eq: "=", ne: "!=", lt: "<", lte: "<=", gt: ">", gte: ">=", and: "and", or: "or"};
function cond(c) {
  if (!c) return "?";
  if (c.type === "variable") return `<b>${esc(V(c.value))}</b> is true`;
  if (c.valueA) return `<b>${esc(VAL(c.valueA))}</b> ${OPN[c.type] || c.type} ${esc(VAL(c.valueB))}`;
  return esc(JSON.stringify(c).slice(0, 80));
}

function describe(e) {
  const a = e.args || {}, c = e.command;
  const scn = id => `<a class="go" data-id="${id}">${esc(CUR?.sceneNames?.[id] || id)}</a>`;
  switch (c) {
    case "EVENT_TEXT": return ["text", null];
    case "EVENT_CHOICE": return ["text", null];
    case "EVENT_MENU": return ["text", null];
    case "EVENT_COMMENT": return ["cmt", "# " + esc(a.text)];
    case "EVENT_SWITCH_SCENE": return ["go", `Go to ${scn(a.sceneId)} at ${VAL(a.x)}, ${VAL(a.y)}`];
    case "EVENT_IF_VALUE": return ["ctl", `If <b>${esc(V(a.variable))}</b> ${a.operator} ${a.comparator}`];
    case "EVENT_IF": return ["ctl", `If ${cond(a.condition)}`];
    case "EVENT_SWITCH": return ["ctl", `Switch on <b>${esc(V(a.variable))}</b>`];
    case "EVENT_LOOP_WHILE": return ["ctl", `While ${esc(V(a.condition?.valueA?.value))} ${a.condition?.type} ${VAL(a.condition?.valueB)}`];
    case "EVENT_SET_VALUE": return ["", `Set <b>${esc(V(a.variable))}</b> = ${VAL(a.value)}`];
    case "EVENT_INC_VALUE": return ["", `Add 1 to <b>${esc(V(a.variable))}</b>`];
    case "EVENT_VARIABLE_MATH": return ["", `<b>${esc(V(a.vectorX))}</b> ${a.operation} ${a.other === "rnd" ? `random ${a.minValue}-${a.maxValue}` : a.other === "var" ? esc(V(a.vectorY)) : a.value}`];
    case "EVENT_ACTOR_MOVE_TO": return ["", `Move ${esc(ACT(a.actorId))} to ${VAL(a.x)}, ${VAL(a.y)}`];
    case "EVENT_ACTOR_SET_POSITION": return ["", `Place ${esc(ACT(a.actorId))} at ${VAL(a.x)}, ${VAL(a.y)}`];
    case "EVENT_ACTOR_SET_DIRECTION": return ["", `Face ${esc(ACT(a.actorId))} ${VAL(a.direction)}`];
    case "EVENT_ACTOR_DEACTIVATE": return ["", `Remove ${esc(ACT(a.actorId))} from the scene`];
    case "EVENT_ACTOR_HIDE": return ["", `Hide ${esc(ACT(a.actorId))}`];
    case "EVENT_ACTOR_SHOW": return ["", `Show ${esc(ACT(a.actorId))}`];
    case "EVENT_ACTOR_EMOTE": return ["", `${esc(ACT(a.actorId))} shows an emote`];
    case "EVENT_MUSIC_PLAY": return ["", `Play music ${esc(CUR?.music?.[a.musicId] || a.musicId)}`];
    case "EVENT_PALETTE_SET_BACKGROUND": return ["", `Background palettes: ${esc(String(a.palette0).replace("muj-", ""))}...`];
    case "EVENT_WAIT": return ["", `Wait ${VAL(a.time)} s`];
    case "EVENT_CAMERA_SHAKE": return ["", `Camera shake`];
    case "EVENT_SET_INPUT_SCRIPT": return ["ctl", `When ${esc((a.input || []).join("/"))} is pressed`];
    case "EVENT_SET_TIMER_SCRIPT": return ["ctl", `Every ${a.duration}s (timer ${a.timer})`];
    case "EVENT_IF_INPUT": return ["ctl", `If ${esc((a.input || []).join("/"))} held`];
    case "EVENT_IF_ACTOR_DISTANCE_FROM_ACTOR": return ["ctl", `If ${esc(ACT(a.actorId))} within ${VAL(a.distance)} of ${esc(ACT(a.otherActorId))}`];
    case "EVENT_CALL_CUSTOM_EVENT": return ["go", `Run script <b>${esc(a.__name || a.customEventId)}</b> (Project > Scripts)`];
    case "EVENT_LAUNCH_PROJECTILE": return ["", `Fire a projectile ${a.direction}`];
    default: return ["", `${c.replace("EVENT_", "").toLowerCase().replace(/_/g, " ")}`];
  }
}

function renderScript(script) {
  let h = "";
  for (const e of script) {
    const [cls, txt] = describe(e);
    const a = e.args || {};
    h += `<div class="ev ${cls}">`;
    if (e.command === "EVENT_TEXT") {
      const pages = Array.isArray(a.text) ? a.text : [a.text];
      h += `<div class="c">dialogue</div><textarea data-id="${e.id}" data-kind="text">${esc(pages.join("\n---\n"))}</textarea>` +
        `<div class="row"><button data-save="${e.id}">Save</button><label><input type="checkbox" data-wrap="${e.id}"> auto-wrap</label><span class="warn" data-warn="${e.id}"></span></div>`;
    } else if (e.command === "EVENT_CHOICE") {
      h += `<div class="c">choice (sets ${esc(V(a.variable))}: 1st = 1, 2nd = 0)</div><textarea data-id="${e.id}" data-kind="choice">${esc(a.trueText + "\n---\n" + a.falseText)}</textarea><div class="row"><button data-save="${e.id}">Save</button><span class="warn" data-warn="${e.id}"></span></div>`;
    } else if (e.command === "EVENT_MENU") {
      const opts = []; for (let i = 1; i <= a.items; i++) opts.push(a["option" + i]);
      h += `<div class="c">menu (sets ${esc(V(a.variable))} = 1..${a.items})</div><textarea data-id="${e.id}" data-kind="menu">${esc(opts.join("\n---\n"))}</textarea><div class="row"><button data-save="${e.id}">Save</button><span class="warn" data-warn="${e.id}"></span></div>`;
    } else {
      h += txt;
    }
    const kids = e.children || {};
    const names = Object.keys(kids).filter(k => kids[k] && kids[k].length);
    for (const k of names) {
      let label = {true: "then", false: "else", script: "do"}[k] || k;
      if (k.startsWith("true") && e.command === "EVENT_SWITCH") label = "case " + VAL(a["value" + k.slice(4)]);
      h += `<div class="branch">${esc(label)}:</div>` + renderScript(kids[k]);
    }
    h += `</div>`;
  }
  return h;
}

function lineWarnings(pages) {
  const w = [];
  pages.forEach(p => p.split("\n").forEach(l => { const shown = l.replace(/\$(L\d|T\d|V\d|\d+)\$/g, "00"); if (shown.length > 18) w.push(`"${l.slice(0, 20)}..." is ${shown.length} chars`); }));
  pages.forEach(p => { if (p.split("\n").length > 3) w.push("a box has more than 3 lines"); });
  return w;
}

function bindEditors(root) {
  $$("textarea[data-id]", root).forEach(t => t.oninput = () => {
    const pages = t.value.split(/\n---\n/);
    $(`[data-warn="${t.dataset.id}"]`, root).textContent = t.dataset.kind === "text" ? lineWarnings(pages).join("; ") : "";
  });
  $$("button[data-save]", root).forEach(b => b.onclick = async () => {
    const id = b.dataset.save, t = $(`textarea[data-id="${id}"]`, root);
    const wrap = $(`input[data-wrap="${id}"]`, root)?.checked;
    const pages = t.value.split(/\n---\n/);
    const r = await api("/api/event", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({id, pages, autowrap: !!wrap})});
    if (r.ok) {
      toast("Saved to " + r.file + (r.warnings.length ? " (check line lengths)" : ""), r.warnings.length);
      if (wrap) t.value = r.pages.join("\n---\n");
      GRAPH = null; DLG = null;
    } else toast(r.error, true);
  });
}

// ---------------------------------------------------------------- dialogue table
let DLG = null;
async function drawDialogue(keep) {
  if (!DLG || !keep) DLG = await api("/api/dialogue");
  const f = $("#dlgFilter").value.toLowerCase(), ty = $("#dlgType").value;
  const rows = DLG.filter(l => (!ty || l.type === ty) &&
    (!f || (l.scene + l.owner + l.pages.join(" ")).toLowerCase().includes(f))).slice(0, 400);
  $("#dlgList").innerHTML = `<div class="hint">${rows.length} shown (of ${DLG.length}). Separate boxes with a line containing only ---</div>` +
    rows.map(l => `<div class="line"><div class="meta"><b>${esc(l.scene)}</b><br>${esc(l.owner)} - ${l.type}<br><a class="go" data-id="${l.sceneId}">open scene</a></div>
      <div class="ev"><textarea data-id="${l.id}" data-kind="${l.type}">${esc(l.pages.join("\n---\n"))}</textarea>
      <div class="row"><button data-save="${l.id}">Save</button>${l.type === "text" ? `<label><input type="checkbox" data-wrap="${l.id}"> auto-wrap</label>` : ""}<span class="warn" data-warn="${l.id}">${l.type === "text" ? lineWarnings(l.pages).join("; ") : ""}</span></div></div></div>`).join("");
  bindEditors($("#dlgList"));
  $$("#dlgList a.go").forEach(a => a.onclick = () => openScene(a.dataset.id));
}

// ---------------------------------------------------------------- map
async function drawMap() {
  const w = await api("/api/world"); if (!w.locations) return;
  const z = 1, T = 8 * z;
  const world = PROJECT.scenes.find(s => s.name.endsWith("Campus World Map"));
  let h = `<div style="position:relative;width:${w.cols * T}px"><img src="${file("art/maps/preview/world_campus.png")}" style="width:${w.cols * T}px">`;
  w.locations.forEach(l => {
    const target = PROJECT.scenes.find(s => s.file.includes("/" + l.target + "/")) ||
      (l.target === "legacy_b7_front" ? PROJECT.scenes.find(s => s.name === "Scene 13") : null);
    h += `<div class="loc" data-id="${target ? target.id : world?.id}" style="left:${(l.x + 1) * T}px;top:${l.y * T}px">${esc(l.name)}</div>`;
  });
  $("#mapStage").innerHTML = h + "</div>";
  $$("#mapStage .loc").forEach(el => el.onclick = () => openScene(el.dataset.id));
}

// ---------------------------------------------------------------- sprites / palettes / vars / docs
function drawSprites() {
  $("#spriteGrid").innerHTML = PROJECT.sprites.slice().sort((a, b) => a.name.localeCompare(b.name)).map(s =>
    `<div class="card"><img src="${file(s.preview)}"><div>${esc(s.name)}</div><div class="hint">${esc(s.file)}</div></div>`).join("");
}
function drawPalettes() {
  const groups = {};
  PROJECT.palettes.forEach(p => { const g = p.id.startsWith("muj-spr") ? "Sprite palettes (one per character)" : p.id.startsWith("muj-") ? "Background banks (" + (p.id.split("-")[1] || "") + ")" : p.id.startsWith("enr-") ? "Enriched legacy backgrounds" : "Other"; (groups[g] = groups[g] || []).push(p); });
  $("#palGrid").innerHTML = Object.keys(groups).sort().map(g => `<h3>${esc(g)}</h3>` + groups[g].sort((a, b) => a.id.localeCompare(b.id)).map(p =>
    `<div class="palrow"><span class="n">${esc(p.id)}</span>${p.colors.map(c => `<span class="sw" title="#${c}" style="background:#${c}"></span>`).join("")}</div>`).join("")).join("");
}
async function drawVars() {
  DLG = DLG || await api("/api/dialogue");
  const v = PROJECT.vars;
  $("#varList").innerHTML = `<p class="hint">Story variables (GB Studio > Variables). Chapter: 0 prologue, 1-3 days, 4 outbreak, 5 the Middle, 6 finale. Phase: 0 morning, 1 after class, 2 evening, 3 night.</p>` +
    Object.keys(v).sort((a, b) => +a - +b).map(k => `<div class="palrow"><span class="n">${k}</span>${esc(v[k])}</div>`).join("");
}
async function drawDoc() {
  const r = await api("/api/doc?name=" + $("#docPick").value);
  $("#doc").innerHTML = md(r.text);
}
function md(src) {
  const lines = src.split("\n"); let h = "", inCode = false, inList = false, table = [];
  const inline = s => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  const flushTable = () => { if (table.length) { h += "<table>" + table.filter(r => !/^\|[-\s|:]+\|$/.test(r)).map((r, i) => "<tr>" + r.split("|").slice(1, -1).map(c => `<${i ? "td" : "th"}>${inline(c.trim())}</${i ? "td" : "th"}>`).join("") + "</tr>").join("") + "</table>"; table = []; } };
  for (const l of lines) {
    if (l.startsWith("```")) { flushTable(); h += inCode ? "</pre>" : "<pre>"; inCode = !inCode; continue; }
    if (inCode) { h += esc(l) + "\n"; continue; }
    if (l.startsWith("|")) { table.push(l); continue; } else flushTable();
    if (/^\s*[-*] /.test(l)) { if (!inList) { h += "<ul>"; inList = true; } h += "<li>" + inline(l.replace(/^\s*[-*] /, "")) + "</li>"; continue; }
    if (inList) { h += "</ul>"; inList = false; }
    const m = l.match(/^(#{1,4}) (.*)/);
    if (m) h += `<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`;
    else if (l.trim()) h += "<p>" + inline(l) + "</p>";
  }
  flushTable(); if (inList) h += "</ul>";
  return h;
}

init();
