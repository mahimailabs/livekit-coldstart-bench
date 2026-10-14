// Shared drawing helpers for the README visuals (rough.js on a dark, dotted canvas).
const NS = "http://www.w3.org/2000/svg";
const C = {
  ink: "#e6edf3", muted: "#8b949e", dim: "#30363d",
  red: "#ff7b72", redF: "#4a1d1d", green: "#7ee787", greenF: "#173d22",
  blue: "#79c0ff", blueF: "#132f4c", violet: "#d2a8ff", violetF: "#33224f",
  yellow: "#f2cc60", yellowF: "#47390f", teal: "#56d4dd", tealF: "#0f3b3e",
  orange: "#ffa657", orangeF: "#4a2a0f",
};

function setup(svgId, seed0) {
  const svg = document.getElementById(svgId);
  const rc = rough.svg(svg);
  let seed = seed0 || 7;
  const o = (x) => Object.assign({ stroke: C.ink, strokeWidth: 1.8, roughness: 1.2, bowing: 1, seed: seed++ }, x || {});
  const hf = (f, style) => ({ fill: f, fillStyle: style || "hachure", hachureGap: 7, fillWeight: 1.4 });
  const add = (p, n) => (p || svg).appendChild(n);
  function T(p, x, y, s, opt) {
    opt = opt || {};
    const t = document.createElementNS(NS, "text");
    t.setAttribute("x", x); t.setAttribute("y", y);
    t.setAttribute("text-anchor", opt.anchor || "middle");
    t.setAttribute("font-size", opt.size || 20);
    if (opt.weight) t.setAttribute("font-weight", opt.weight);
    if (opt.cls) t.setAttribute("class", opt.cls);
    if (opt.fill) t.style.fill = opt.fill;
    t.textContent = s; (p || svg).appendChild(t); return t;
  }
  function arrow(p, x1, y1, x2, y2, ex) {
    add(p, rc.line(x1, y1, x2, y2, o(ex)));
    const a = Math.atan2(y2 - y1, x2 - x1), L = 11;
    add(p, rc.line(x2, y2, x2 - L * Math.cos(a - 0.5), y2 - L * Math.sin(a - 0.5), o(ex)));
    add(p, rc.line(x2, y2, x2 - L * Math.cos(a + 0.5), y2 - L * Math.sin(a + 0.5), o(ex)));
  }
  function box(p, x, y, w, h, col, fill, title, sub) {
    add(p, rc.rectangle(x, y, w, h, o({ stroke: col, ...hf(fill) })));
    if (title) T(p, x + w / 2, y + (sub ? h / 2 - 4 : h / 2 + 8), title, { size: 22, weight: 700 });
    if (sub) T(p, x + w / 2, y + h / 2 + 22, sub, { size: 16, cls: "m" });
  }
  function group(p) { const g = document.createElementNS(NS, "g"); (p || svg).appendChild(g); return g; }
  return { svg, rc, o, hf, add, T, arrow, box, group };
}

async function fontsReady() {
  await Promise.all(["700 54px Kalam", "400 20px Kalam", "500 15px JBM"].map((f) => document.fonts.load(f)));
}
