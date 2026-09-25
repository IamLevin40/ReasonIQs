import { state, validateConfig } from "./state.js";

const workspace = document.querySelector("#workspace");
const iconFallback = "/static/assets/icons/mark.svg";
const accentNames = new Set(["mechanical", "spatial", "verbal"]);

export const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const attr = escapeHtml;
const accent = item => accentNames.has(item?.accent) ? item.accent : "default";
const icon = item => attr(item?.icon || iconFallback);
const style = item => `style="--domain-accent:var(--${accent(item) === "default" ? "accent" : accent(item)});--domain-soft:var(--${accent(item) === "default" ? "accent-soft" : `${accent(item)}-soft`})"`;
const type = () => state.type;
const subtype = () => state.subtype;

function context(parts) {
  return `<nav class="context-bar" aria-label="Breadcrumb">${parts.map((part, i) =>
    `${i ? '<span class="context-separator" aria-hidden="true">/</span>' : ""}${part.path ?
      `<button type="button" data-route="${attr(part.path)}">${escapeHtml(part.label)}</button>` :
      `<span class="context-current" aria-current="page">${escapeHtml(part.label)}</span>`}`).join("")}</nav>`;
}
function shell(html) {
  workspace.innerHTML = `<div class="view-enter">${html}</div>`;
  document.querySelector("#home-link").setAttribute("aria-current", state.screen === "home" ? "page" : "false");
  document.title = `${state.screen === "home" ? "Practice workspace" : subtype()?.title || type()?.title || "Practice"} · ReasonIQs`;
}
export function renderLoading(message = "Opening your reasoning workspace…") {
  workspace.innerHTML = `<div class="loading-state" role="status">${escapeHtml(message)}</div>`;
}
export function renderError(message, retry = true) {
  shell(`<section class="panel notice" role="alert"><p class="eyebrow">Workspace status</p><h1>Something interrupted the path.</h1><p>${escapeHtml(message)}</p>${retry ? '<button class="btn btn-primary" type="button" data-action="retry">Try again</button>' : '<button class="btn btn-primary" type="button" data-route="/">Return home</button>'}</section>`);
}
export function renderHome() {
  const domains = state.catalog.types;
  const activeCount = domains.filter(item => item.active).length;
  const pathCount = domains.reduce((total, item) => total + (item.subtypes || []).filter(entry => entry.active).length, 0);
  shell(`<section class="play-hero" aria-labelledby="home-heading">
    <div class="hero-copy"><p class="hero-kicker"><span class="sparkle" aria-hidden="true">✦</span> REASONIQS PRACTICE LAB</p>
      <h1 id="home-heading">Give your brain<br><em>a new angle.</em></h1>
      <p>Practice the patterns behind IQ tests. Choose a reasoning world and make a round your own.</p>
      <div class="hero-facts"><span><strong>${activeCount.toString().padStart(2, "0")}</strong> worlds to explore</span><span><strong>${pathCount.toString().padStart(2, "0")}</strong> practice paths</span></div>
    </div>
    <div class="hero-puzzle" aria-hidden="true"><span class="puzzle-cell"><i class="puzzle-shape circle"></i></span><span class="puzzle-cell"><i class="puzzle-shape square"></i></span><span class="puzzle-cell"><i class="puzzle-shape triangle"></i></span><span class="puzzle-cell"><i class="puzzle-shape square"></i></span><span class="puzzle-cell"><i class="puzzle-shape triangle"></i></span><span class="puzzle-cell"><i class="puzzle-shape circle"></i></span><span class="puzzle-cell"><i class="puzzle-shape triangle"></i></span><span class="puzzle-cell"><i class="puzzle-shape circle"></i></span><span class="puzzle-cell puzzle-mystery">?</span></div>
    </section>
    <section class="domain-section" aria-labelledby="domain-heading"><div class="section-head"><div><p class="eyebrow">Start your round</p><h2 id="domain-heading">Choose a reasoning world</h2></div><span class="section-aside">Pick one to see its topics <span aria-hidden="true">↘</span></span></div>
    <div class="domain-grid">${domains.map((item, i) => `<button class="domain" ${style(item)} type="button" data-type="${attr(item.id)}" ${item.active ? "" : "disabled aria-disabled=\"true\""} aria-label="${attr(item.title)}: ${attr(item.subtitle)}${item.active ? "" : ", unavailable"}">
      <span class="domain-top"><span class="domain-index">WORLD ${String(i + 1).padStart(2, "0")}</span><span class="domain-spark" aria-hidden="true">✳</span></span>
      <span class="domain-symbol"><img src="${icon(item)}" alt="" loading="lazy" data-icon></span>
      <span class="domain-title">${escapeHtml(item.title)}</span><span class="domain-subtitle">${escapeHtml(item.subtitle)}</span>
      <span class="domain-foot"><span>${item.active ? `${(item.subtypes || []).filter(entry => entry.active).length} topics to explore` : "Unavailable"}</span><span class="domain-go" aria-hidden="true">↗</span></span></button>`).join("")}</div></section>`);
}
export function renderSubtypes() {
  const item = type();
  shell(`${context([{ label: "Home", path: "/" }, { label: item.title }])}
    <button class="back-link" type="button" data-route="/"><span aria-hidden="true">←</span> All reasoning domains</button>
    <section class="chapter-banner" ${style(item)}><div><p class="eyebrow">Choose your focus / World ${String(state.catalog.types.indexOf(item) + 1).padStart(2, "0")}</p><h1>${escapeHtml(item.title)}</h1><p class="lead">${escapeHtml(item.description || item.subtitle)}</p></div><span class="chapter-emblem"><img src="${icon(item)}" alt="" data-icon></span></section>
    <section aria-labelledby="subtype-heading"><div class="section-head"><div><p class="eyebrow">Next step</p><h2 id="subtype-heading">Pick a practice path</h2></div><span class="section-aside">${(item.subtypes || []).filter(entry => entry.active).length} topics available</span></div>
    <div class="subtype-grid">${(item.subtypes || []).map((entry, i) => `<button class="subtype" ${style(item)} type="button" data-subtype="${attr(entry.id)}" ${entry.active ? "" : "disabled aria-disabled=\"true\""} aria-label="${attr(entry.title)}: ${attr(entry.subtitle)}${entry.active ? "" : ", unavailable"}">
      <span class="subtype-number">${String(i + 1).padStart(2, "0")}</span><span class="subtype-icon"><img src="${icon(entry)}" alt="" loading="lazy" data-icon></span><span class="subtype-copy"><span class="subtype-title">${escapeHtml(entry.title)}</span><span class="subtype-subtitle">${escapeHtml(entry.subtitle)}</span><span class="subtype-status">${entry.active ? "READY TO PRACTICE" : "UNAVAILABLE"}</span></span><span class="subtype-go" aria-hidden="true">↗</span></button>`).join("")}</div></section>`);
}
export function renderSetup() {
  const config = state.config;
  shell(`${context([{ label: "Home", path: "/" }, { label: type().title, path: `/type/${type().id}` }, { label: subtype().title }])}
    <button class="back-link" type="button" data-route="/type/${attr(type().id)}"><span aria-hidden="true">←</span> All ${escapeHtml(type().title)} topics</button>
    <section class="setup-intro"><div><p class="eyebrow">Build your round / Step 03</p><h1>Set your practice pace.</h1><p class="lead">A few choices before you begin ${escapeHtml(subtype().title)}.</p></div><span class="setup-badge" aria-hidden="true">✦<small>READY<br>SET<br>THINK</small></span></section>
    <div class="setup-layout"><form id="setup-form" class="panel setup-panel" novalidate>
      <h2>Session settings</h2><p class="helper">Adjust these at any time before starting.</p>
      <div class="field-stack">
        <div class="field-row"><div class="field-copy"><label for="item-count">Number of items</label><small>5 to 50 questions</small></div><input class="field-control" id="item-count" name="item_count" type="number" min="5" max="50" step="1" required value="${attr(config.item_count)}"></div>
        <div class="field-row"><div class="field-copy"><label for="choice-count">Answer choices</label><small>2 to 6 per item</small></div><input class="field-control" id="choice-count" name="choice_count" type="number" min="2" max="6" step="1" required value="${attr(config.choice_count)}"></div>
        <hr class="field-divider">
        <div class="field-row"><div class="field-copy"><strong>Item timer</strong><small>Time pauses when you leave an item</small></div><label class="toggle"><input id="timer-enabled" name="timer_enabled" type="checkbox" ${config.timer_enabled ? "checked" : ""}><span>${config.timer_enabled ? "On" : "Off"}</span></label></div>
        <div class="field-row" id="duration-row" ${config.timer_enabled ? "" : 'hidden'}><div class="field-copy"><label for="seconds-per-item">Seconds per item</label><small>10 to 300 seconds</small></div><input class="field-control" id="seconds-per-item" name="seconds_per_item" type="number" min="10" max="300" step="1" required value="${attr(config.seconds_per_item)}" ${config.timer_enabled ? "" : "disabled"}></div>
        <hr class="field-divider">
        <fieldset class="difficulty-group"><legend>Difficulty</legend><div class="segmented">${["Easy", "Average", "Challenge"].map(level => `<label class="segment"><input type="radio" name="difficulty" value="${level}" ${config.difficulty === level ? "checked" : ""} ${subtype().difficulties.includes(level) ? "" : "disabled"}><span>${level}</span></label>`).join("")}</div></fieldset>
      </div><p class="validation" id="setup-error" role="status"></p>
    </form>
    <aside class="panel summary-panel" aria-label="Session summary" ${style(type())}><p class="small-heading">Your round at a glance</p><div class="summary-identity"><span class="summary-icon"><img src="${icon(type())}" alt="" data-icon></span><span><strong>${escapeHtml(subtype().title)}</strong><small>${escapeHtml(type().title)}</small></span></div>
    <dl class="summary-list"><div><dt>Items</dt><dd id="summary-items"></dd></div><div><dt>Choices</dt><dd id="summary-choices"></dd></div><div><dt>Difficulty</dt><dd id="summary-difficulty"></dd></div><div><dt>Timer</dt><dd id="summary-timer"></dd></div></dl>
    <p class="summary-line" id="summary-line" aria-live="polite"></p>
    <button class="btn btn-primary btn-full" id="start-button" type="submit" form="setup-form">Start practice <span aria-hidden="true">→</span></button></aside></div>`);
  updateSetup();
}
export function updateSetup() {
  const config = state.config;
  const error = validateConfig();
  const timerRow = document.querySelector("#duration-row");
  if (!timerRow) return;
  timerRow.hidden = !config.timer_enabled;
  document.querySelector("#seconds-per-item").disabled = !config.timer_enabled;
  document.querySelector(".toggle span").textContent = config.timer_enabled ? "On" : "Off";
  document.querySelector("#summary-items").textContent = Number.isFinite(config.item_count) ? config.item_count : "—";
  document.querySelector("#summary-choices").textContent = Number.isFinite(config.choice_count) ? config.choice_count : "—";
  document.querySelector("#summary-difficulty").textContent = config.difficulty;
  document.querySelector("#summary-timer").textContent = config.timer_enabled ? `${config.seconds_per_item} sec/item` : "Off";
  document.querySelector("#summary-line").textContent = `${config.item_count || "—"} items · ${config.choice_count || "—"} choices · ${config.difficulty} · ${config.timer_enabled ? `${config.seconds_per_item} sec/item` : "untimed"}`;
  document.querySelector("#setup-error").textContent = error;
  document.querySelector("#start-button").disabled = Boolean(error);
}
export function renderTest() {
  const question = state.questions[state.index];
  const count = state.questions.length;
  const selected = state.answers[state.index];
  const locked = state.timedOut[state.index];
  shell(`<div class="test-layout"><div class="test-topline"><button class="back-link" type="button" data-route="/setup/${attr(type().id)}/${attr(subtype().id)}"><span aria-hidden="true">←</span> Leave practice</button><span class="test-meta">${escapeHtml(type().title)} / ${escapeHtml(state.config.difficulty)}</span></div>
    <section class="panel test-card" aria-labelledby="question-heading"><div class="test-header"><div><span class="test-kicker">● ROUND IN PROGRESS · ${escapeHtml(subtype().title)}</span><h1 id="question-heading" tabindex="-1">Question ${state.index + 1} of ${count}</h1><p>${state.answers.filter(Boolean).length} answered · ${state.timedOut.filter(Boolean).length} timed out</p></div>
    ${state.config.timer_enabled ? '<div class="timer" id="timer" role="timer"><strong id="timer-value"></strong><small>seconds left</small></div>' : ""}</div>
    <div class="progress-track" role="progressbar" aria-valuenow="${state.index + 1}" aria-valuemin="1" aria-valuemax="${count}" aria-label="Question position"><span style="width:${((state.index + 1) / count) * 100}%"></span></div>
    <div class="question-area"><span class="placeholder-label">Prototype question</span><p class="question-prompt">${escapeHtml(question.prompt)}</p>
      ${question.visual?.src ? `<div class="question-visual"><img src="${attr(question.visual.src)}" alt="${attr(question.visual.alt || "Question visual")}" data-icon></div>` : ""}
      <fieldset class="choices" ${locked ? "disabled" : ""}><legend>Choose one answer</legend>${question.choices.map((choice, i) => `<label class="choice"><input type="radio" name="answer" value="${attr(choice.id)}" ${selected === choice.id ? "checked" : ""}><span class="choice-letter" aria-hidden="true">${String.fromCharCode(65 + i)}</span><span class="choice-text">${escapeHtml(choice.text)}</span><span class="choice-check" aria-hidden="true">✓</span></label>`).join("")}</fieldset>
      ${locked ? '<p class="timed-out-note">Time ran out for this item. You can continue through the session.</p>' : ""}
    </div><div class="test-actions"><button class="btn btn-secondary" type="button" data-action="previous" ${state.index === 0 ? "disabled" : ""}>← Previous</button><div class="right-actions"><button class="btn btn-text" type="button" data-action="submit">Finish</button><button class="btn btn-primary" type="button" data-action="next">${state.index === count - 1 ? "Finish session" : "Next →"}</button></div></div></section>
    <nav class="navigator" aria-label="Question navigator">${state.questions.map((_, i) => `<button type="button" class="nav-dot ${i === state.index ? "current" : ""} ${state.answers[i] ? "answered" : ""} ${state.timedOut[i] ? "timed-out" : ""}" data-question="${i}" aria-label="Question ${i + 1}, ${state.timedOut[i] ? "timed out" : state.answers[i] ? "answered" : "unanswered"}" ${i === state.index ? 'aria-current="step"' : ""}>${i + 1}</button>`).join("")}</nav></div>`);
  updateTimerDisplay();
}
export function updateTimerDisplay() {
  const timer = document.querySelector("#timer");
  if (!timer) return;
  const seconds = Math.max(0, Math.ceil(state.remaining[state.index] || 0));
  document.querySelector("#timer-value").textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  timer.classList.toggle("low", seconds <= Math.max(2, Math.floor(state.config.seconds_per_item * .2)));
  timer.setAttribute("aria-label", `${seconds} seconds remaining for this item`);
}
export function renderResult() {
  const result = state.result;
  shell(`<div class="result-layout">${context([{ label: "Home", path: "/" }, { label: type().title, path: `/type/${type().id}` }, { label: subtype().title, path: `/setup/${type().id}/${subtype().id}` }, { label: "Summary" }])}
    <section class="panel result-panel"><p class="eyebrow">Round recap / Step 04</p><h1>Session complete.</h1><p class="lead">${escapeHtml(type().title)} / ${escapeHtml(subtype().title)} · ${escapeHtml(state.config.difficulty)}</p>
    <div class="result-score"><strong>${result.correct}/${result.total}</strong><span>placeholder score</span></div>
    <div class="result-grid"><div class="result-stat"><strong>${result.answered}</strong><span>Answered</span></div><div class="result-stat"><strong>${result.unanswered}</strong><span>Unanswered</span></div><div class="result-stat"><strong>${result.timedOut}</strong><span>Timed out</span></div></div>
    <p class="helper" style="margin:20px 0 0">This score uses temporary placeholder answers. Procedural questions and explanations will replace them later.</p>
    <div class="result-actions"><button class="btn btn-primary" type="button" data-action="restart">Practice again</button><button class="btn btn-secondary" type="button" data-route="/setup/${attr(type().id)}/${attr(subtype().id)}">Change settings</button><button class="btn btn-text" type="button" data-route="/type/${attr(type().id)}">Choose another focus</button></div></section></div>`);
}
