import { cloneFigureVisual } from "./figures.js";

let overlay = null;
let previousFocus = null;
let scale = 1;
let fitScale = 1;
let baseWidth = 1;
let baseHeight = 1;
let offsetX = 0;
let offsetY = 0;
let pointers = new Map();
let pinchDistance = 0;

function stage() { return overlay?.querySelector(".figure-stage"); }
function surface() { return overlay?.querySelector(".figure-inspect-visual"); }
function clampPan() {
  const box = stage().getBoundingClientRect();
  const content = surface().getBoundingClientRect();
  const limitX = Math.max(0, (content.width - box.width) / 2);
  const limitY = Math.max(0, (content.height - box.height) / 2);
  offsetX = Math.max(-limitX, Math.min(limitX, offsetX));
  offsetY = Math.max(-limitY, Math.min(limitY, offsetY));
}
function update() {
  if (!overlay) return;
  surface().style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${fitScale * scale})`;
  overlay.querySelector(".figure-zoom-value").textContent = `${Math.round(scale * 100)}%`;
  stage().classList.toggle("can-pan", scale > 1);
}
function fitToStage() {
  if (!overlay) return;
  const area = stage();
  const style = getComputedStyle(area);
  const width = area.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
  const height = area.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
  fitScale = Math.min(width / baseWidth, height / baseHeight);
  update();
  clampPan();
  update();
}
function zoomTo(next) {
  scale = Math.max(1, Math.min(6, next));
  if (scale === 1) offsetX = offsetY = 0;
  update();
  if (scale > 1) { clampPan(); update(); }
}
export function closeFigureInspector() {
  if (!overlay) return;
  overlay.remove();
  overlay = null;
  pointers.clear();
  document.body.classList.remove("figure-inspecting");
  document.querySelector(".app-shell")?.removeAttribute("inert");
  document.removeEventListener("keydown", onKeydown);
  window.removeEventListener("resize", fitToStage);
  previousFocus?.isConnected && previousFocus.focus({ preventScroll: true });
  previousFocus = null;
}
function onKeydown(event) {
  if (!overlay) return;
  if (event.key === "Escape") { event.preventDefault(); closeFigureInspector(); }
  else if (["+", "="].includes(event.key)) { event.preventDefault(); zoomTo(scale * 1.25); }
  else if (event.key === "-" || event.key === "_") { event.preventDefault(); zoomTo(scale / 1.25); }
  else if (event.key === "0" || event.key === "Home") { event.preventDefault(); zoomTo(1); }
  else if (event.key.startsWith("Arrow")) {
    event.preventDefault();
    if (event.key === "ArrowLeft") offsetX -= 40;
    if (event.key === "ArrowRight") offsetX += 40;
    if (event.key === "ArrowUp") offsetY -= 40;
    if (event.key === "ArrowDown") offsetY += 40;
    clampPan(); update();
  } else if (event.key === "Tab") {
    const focusable = [...overlay.querySelectorAll("button:not(:disabled)")];
    const first = focusable[0], last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
}
export function openFigureInspector(entry) {
  closeFigureInspector();
  previousFocus = document.activeElement;
  scale = 1; offsetX = 0; offsetY = 0;
  const bounds = entry.visual.getBoundingClientRect();
  baseWidth = Math.max(1, bounds.width);
  baseHeight = Math.max(1, bounds.height);
  overlay = document.createElement("div");
  overlay.className = "figure-overlay";
  overlay.innerHTML = `<div class="figure-dialog" role="dialog" aria-modal="true" aria-labelledby="figure-dialog-title" aria-describedby="figure-help">
    <header class="figure-dialog-header"><div><span class="figure-dialog-kicker">Figure inspection</span><h2 id="figure-dialog-title"></h2></div><button type="button" class="figure-close" aria-label="Close figure inspection">×</button></header>
    <div class="figure-stage"><div class="figure-inspect-visual"></div></div>
    <footer class="figure-dialog-footer"><p id="figure-help">Drag to pan · Scroll or pinch to zoom · Arrow keys to pan · Esc to close</p><div class="figure-zoom-controls"><button type="button" data-zoom="out" aria-label="Zoom out">−</button><output class="figure-zoom-value">100%</output><button type="button" data-zoom="in" aria-label="Zoom in">+</button><button type="button" data-zoom="fit">Fit</button></div></footer></div>`;
  overlay.querySelector("#figure-dialog-title").textContent = entry.label;
  surface().setAttribute("role", "img");
  surface().setAttribute("aria-label", entry.label);
  const visual = cloneFigureVisual(entry);
  visual.style.width = `${baseWidth}px`;
  visual.style.height = `${baseHeight}px`;
  surface().style.width = `${baseWidth}px`;
  surface().style.height = `${baseHeight}px`;
  surface().append(visual);
  document.body.append(overlay);
  document.body.classList.add("figure-inspecting");
  document.querySelector(".app-shell")?.setAttribute("inert", "");
  fitToStage();
  if (entry.visual instanceof HTMLImageElement && !entry.visual.complete) {
    const pendingOverlay = overlay;
    entry.visual.addEventListener("load", () => {
      if (overlay !== pendingOverlay) return;
      const loaded = entry.visual.getBoundingClientRect();
      baseWidth = Math.max(1, loaded.width);
      baseHeight = Math.max(1, loaded.height);
      visual.style.width = surface().style.width = `${baseWidth}px`;
      visual.style.height = surface().style.height = `${baseHeight}px`;
      fitToStage();
    }, { once: true });
  }
  overlay.querySelector(".figure-close").focus();
  document.addEventListener("keydown", onKeydown);
  window.addEventListener("resize", fitToStage);
  overlay.addEventListener("click", event => {
    if (event.target === overlay || event.target.closest(".figure-close")) closeFigureInspector();
    const action = event.target.closest("[data-zoom]")?.dataset.zoom;
    if (action === "in") zoomTo(scale * 1.25);
    if (action === "out") zoomTo(scale / 1.25);
    if (action === "fit") zoomTo(1);
  });
  const area = stage();
  area.addEventListener("wheel", event => {
    event.preventDefault();
    zoomTo(scale * (event.deltaY < 0 ? 1.15 : 1 / 1.15));
  }, { passive: false });
  area.addEventListener("pointerdown", event => {
    if (event.button !== 0 && event.pointerType === "mouse") return;
    area.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  });
  area.addEventListener("pointermove", event => {
    if (!pointers.has(event.pointerId)) return;
    const prior = pointers.get(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const distance = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinchDistance) zoomTo(scale * distance / pinchDistance);
      pinchDistance = distance;
    } else if (scale > 1) {
      offsetX += event.clientX - prior.x;
      offsetY += event.clientY - prior.y;
      clampPan(); update();
    }
  });
  for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) area.addEventListener(name, event => {
    pointers.delete(event.pointerId);
    pinchDistance = 0;
  });
}
