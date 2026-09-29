const appShell = document.querySelector(".app-shell");
let activeDialog = null;

const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

export function hasDialog() { return Boolean(activeDialog); }

export function showDialog({ kind = "notice", title, message, confirmLabel, cancelLabel, progress = false }) {
  activeDialog?.close(false);
  const previousFocus = document.activeElement;
  const overlay = document.createElement("div");
  overlay.className = `app-dialog-overlay app-dialog-${kind}`;
  overlay.innerHTML = `<div class="app-dialog" role="dialog" aria-modal="true" aria-labelledby="app-dialog-title" aria-describedby="app-dialog-message" tabindex="-1">
    <span class="app-dialog-kicker">${escapeHtml(kind === "loading" ? "Preparing your session" : kind === "warning" ? "Please confirm" : kind === "error" ? "Something went wrong" : "Notice")}</span>
    <h2 id="app-dialog-title">${escapeHtml(title)}</h2>
    <p id="app-dialog-message">${escapeHtml(message)}</p>
    ${progress ? '<div class="generation-progress" role="progressbar" aria-label="Generating practice questions"><span></span></div><p class="app-dialog-hint">Please wait while your questions are prepared.</p>' : ""}
    ${confirmLabel ? `<div class="app-dialog-actions">${cancelLabel ? `<button class="btn btn-secondary" type="button" data-dialog="cancel">${escapeHtml(cancelLabel)}</button>` : ""}<button class="btn btn-primary" type="button" data-dialog="confirm">${escapeHtml(confirmLabel)}</button></div>` : ""}
  </div>`;
  document.body.append(overlay);
  appShell.setAttribute("inert", "");
  document.body.classList.add("dialog-open");
  let resolveResult;
  const result = new Promise(resolve => { resolveResult = resolve; });
  const panel = overlay.querySelector(".app-dialog");
  const close = accepted => {
    if (activeDialog?.overlay !== overlay) return;
    overlay.remove();
    activeDialog = null;
    appShell.removeAttribute("inert");
    document.body.classList.remove("dialog-open");
    document.removeEventListener("keydown", onKeydown, true);
    if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
    resolveResult(accepted);
  };
  function onKeydown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      if (cancelLabel) close(false);
    } else if (event.key === "Tab") {
      const buttons = [...panel.querySelectorAll("button")];
      if (!buttons.length) { event.preventDefault(); panel.focus(); return; }
      const first = buttons[0], last = buttons.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  }
  overlay.addEventListener("click", event => {
    const action = event.target.closest("[data-dialog]")?.dataset.dialog;
    if (action) close(action === "confirm");
  });
  document.addEventListener("keydown", onKeydown, true);
  activeDialog = { overlay, close };
  (overlay.querySelector("[data-dialog='cancel']") || overlay.querySelector("[data-dialog='confirm']") || panel).focus();
  return { close, result };
}
