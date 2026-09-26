// Figure media is kept independent of question generators and the test view.
const canvasRenderers = new Map();
const domRenderers = new Map();
const entries = new WeakMap();

export function registerCanvasRenderer(name, draw) { canvasRenderers.set(name, draw); }
export function registerDomRenderer(name, render, exportCanvas) {
  domRenderers.set(name, { render, exportCanvas });
}
export function figureEntry(element) { return entries.get(element); }

function safeSource(figure) {
  let source = figure.src;
  if (!source && figure.base64 && /^image\/(png|jpeg|webp)$/.test(figure.mime || "")) {
    source = `data:${figure.mime};base64,${figure.base64}`;
  }
  if (typeof source !== "string") return null;
  if (/^data:image\/(png|jpeg|webp);base64,[a-z0-9+/=]+$/i.test(source)) return source;
  try {
    const url = new URL(source, location.href);
    return url.origin === location.origin && /^https?:$/.test(url.protocol) ? url.href : null;
  } catch { return null; }
}

const svgTags = new Set("svg g path circle ellipse rect line polyline polygon text tspan defs linearGradient radialGradient stop clipPath mask use symbol".split(" "));
const svgAttrs = new Set("xmlns viewBox width height x y x1 y1 x2 y2 cx cy r rx ry d points transform fill fill-rule stroke stroke-width stroke-linecap stroke-linejoin stroke-dasharray opacity fill-opacity stroke-opacity font-size font-family font-weight text-anchor dominant-baseline id offset stop-color stop-opacity clip-path mask preserveAspectRatio href".split(" "));

function cleanSvg(markup) {
  const parsed = new DOMParser().parseFromString(markup, "image/svg+xml");
  const root = parsed.documentElement;
  if (root.localName !== "svg" || parsed.querySelector("parsererror")) throw new Error("Invalid SVG figure");
  function clean(node) {
    if (node.nodeType === Node.TEXT_NODE) return document.createTextNode(node.textContent);
    if (node.nodeType !== Node.ELEMENT_NODE || !svgTags.has(node.localName)) return null;
    const result = document.createElementNS("http://www.w3.org/2000/svg", node.localName);
    for (const { name, value } of node.attributes) {
      const local = name === "xlink:href" ? "href" : name;
      if (!svgAttrs.has(local)) continue;
      if (/url\s*\(/i.test(value) && !/^url\(#[a-zA-Z0-9_-]+\)$/.test(value)) continue;
      if (local === "href" && !/^#[a-zA-Z0-9_-]+$/.test(value)) continue;
      if (/javascript:|data:|https?:/i.test(value)) continue;
      result.setAttribute(local, value);
    }
    for (const child of node.childNodes) {
      const safe = clean(child);
      if (safe) result.append(safe);
    }
    return result;
  }
  const svg = clean(root);
  svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  svg.setAttribute("role", "img");
  svg.setAttribute("focusable", "false");
  return svg;
}

function visualFor(figure) {
  const kind = figure.kind || figure.type || (figure.svg ? "svg" : figure.src || figure.base64 ? "image" : "");
  if (kind === "svg" && typeof figure.svg === "string") return cleanSvg(figure.svg);
  if (kind === "image") {
    const source = safeSource(figure);
    if (!source) throw new Error("Figure image must be local or generated");
    const img = document.createElement("img");
    img.src = source;
    img.alt = "";
    img.decoding = "async";
    return img;
  }
  if (kind === "canvas") {
    const draw = canvasRenderers.get(figure.renderer);
    if (!draw) throw new Error("Canvas renderer is unavailable");
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.min(4096, Number(figure.width) || 640));
    canvas.height = Math.max(1, Math.min(4096, Number(figure.height) || 480));
    draw(canvas.getContext("2d"), figure.data, canvas);
    return canvas;
  }
  if (kind === "dom") {
    const renderer = domRenderers.get(figure.renderer);
    if (!renderer) throw new Error("DOM renderer is unavailable");
    const node = renderer.render(figure.data);
    if (!(node instanceof HTMLElement)) throw new Error("DOM renderer must return an element");
    return node;
  }
  throw new Error("Unsupported figure format");
}

export function mountFigures(root, figureBlocks) {
  root.querySelectorAll("[data-figure-block]").forEach(host => {
    const block = figureBlocks.get(host.dataset.figureBlock);
    if (!block) return;
    block.figures.forEach((figure, index) => {
      const card = document.createElement("div");
      card.className = "figure-card";
      const label = figure.alt || `Figure ${index + 1}`;
      const surface = document.createElement("div");
      surface.className = "figure-surface";
      const view = document.createElement("div");
      view.className = "figure-view";
      let available = true;
      try { view.append(visualFor(figure)); }
      catch {
        view.textContent = "Figure unavailable";
        available = false;
      }
      surface.append(view);
      const actions = document.createElement("div");
      actions.className = "figure-actions";
      const inspectButton = document.createElement("button");
      inspectButton.type = "button";
      inspectButton.className = "figure-inspect";
      inspectButton.dataset.figureInspect = "";
      inspectButton.setAttribute("aria-label", `Inspect ${label}`);
      inspectButton.title = "Inspect figure";
      inspectButton.textContent = "Inspect";
      const exportButton = document.createElement("button");
      exportButton.type = "button";
      exportButton.className = "figure-export";
      exportButton.dataset.figureExport = "";
      exportButton.setAttribute("aria-label", `Download ${block.figures.length > 1 ? "all figures in " : "figure in "}${block.label} as PNG`);
      exportButton.title = "Download PNG";
      exportButton.textContent = "↓ PNG";
      inspectButton.disabled = exportButton.disabled = !available;
      actions.append(inspectButton, exportButton);
      card.append(surface, actions);
      if (figure.caption) {
        const caption = document.createElement("span");
        caption.className = "figure-caption";
        caption.textContent = figure.caption;
        card.append(caption);
      }
      host.append(card);
      entries.set(inspectButton, { figure, visual: view.firstElementChild, label });
      entries.set(exportButton, { block, host });
    });
  });
}

export function cloneFigureVisual(entry) {
  if (entry.visual instanceof HTMLCanvasElement) {
    const copy = document.createElement("canvas");
    copy.width = entry.visual.width;
    copy.height = entry.visual.height;
    copy.getContext("2d").drawImage(entry.visual, 0, 0);
    return copy;
  }
  return entry.visual.cloneNode(true);
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Could not load figure for PNG export"));
    img.src = src;
  });
}

function svgImage(svg) {
  const copy = svg.cloneNode(true);
  copy.removeAttribute("role");
  copy.removeAttribute("focusable");
  const viewBox = copy.getAttribute("viewBox")?.split(/[ ,]+/).map(Number);
  const width = viewBox?.[2] || Number(copy.getAttribute("width")) || 800;
  const height = viewBox?.[3] || Number(copy.getAttribute("height")) || 600;
  copy.setAttribute("width", width);
  copy.setAttribute("height", height);
  return loadImage(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(new XMLSerializer().serializeToString(copy))}`);
}

function domImage(element) {
  // Inline computed styles so the export does not depend on the page stylesheet.
  const clone = element.cloneNode(true);
  function inline(source, target) {
    const style = getComputedStyle(source);
    for (const name of style) target.style.setProperty(name, style.getPropertyValue(name));
    [...source.children].forEach((child, i) => inline(child, target.children[i]));
  }
  inline(element, clone);
  clone.setAttribute("xmlns", "http://www.w3.org/1999/xhtml");
  const width = Math.ceil(element.getBoundingClientRect().width);
  const height = Math.ceil(element.getBoundingClientRect().height);
  const xml = new XMLSerializer().serializeToString(clone);
  return loadImage(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><foreignObject width="100%" height="100%">${xml}</foreignObject></svg>`)}`);
}

async function drawable(entry) {
  const visual = entry.visual;
  if (visual instanceof HTMLImageElement) {
    if (!visual.complete || !visual.naturalWidth) await visual.decode();
    return visual;
  }
  if (visual instanceof SVGSVGElement) return svgImage(visual);
  if (visual instanceof HTMLCanvasElement) return visual;
  const custom = domRenderers.get(entry.figure.renderer)?.exportCanvas;
  if (custom) return custom(entry.figure.data, visual);
  return domImage(visual);
}

export async function exportFigureBlock(host, block) {
  const cards = [...host.querySelectorAll(".figure-card")];
  if (!cards.length) return;
  const visuals = cards.map(card => card.querySelector(".figure-view").firstElementChild);
  const bounds = visuals.map(visual => visual.getBoundingClientRect());
  const left = Math.min(...bounds.map(rect => rect.left));
  const top = Math.min(...bounds.map(rect => rect.top));
  const right = Math.max(...bounds.map(rect => rect.right));
  const bottom = Math.max(...bounds.map(rect => rect.bottom));
  const width = Math.max(1, right - left);
  const height = Math.max(1, bottom - top);
  const padding = 32;
  const scale = Math.min(12, Math.max(2, 1600 / width), 8192 / Math.max(width + padding * 2, height + padding * 2));
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil((width + padding * 2) * scale);
  canvas.height = Math.ceil((height + padding * 2) * scale);
  const context = canvas.getContext("2d");
  context.scale(scale, scale);
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width / scale, canvas.height / scale);
  for (let i = 0; i < cards.length; i++) {
    const entry = figureEntry(cards[i].querySelector(".figure-inspect"));
    const image = await drawable(entry);
    const rect = bounds[i];
    context.drawImage(image, padding + rect.left - left, padding + rect.top - top, rect.width, rect.height);
  }
  const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("Could not create PNG");
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = block.filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
