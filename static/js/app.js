import { loadReasoning, createPractice } from "./api.js";
import { state, findType, findSubtype, validateConfig, saveConfig, beginSession, finishSession, puzzleTypes, patternFittingModes } from "./state.js";
import { startTimer, stopTimer } from "./timer.js";
import { renderLoading, renderError, renderHome, renderSubtypes, renderSetup, updateSetup, renderTest, updateTimerDisplay, renderResult } from "./render.js";
import { figureEntry, exportFigureBlock } from "./figures.js";
import { openFigureInspector, closeFigureInspector } from "./figure-inspector.js";

const workspace = document.querySelector("#workspace");
const announcer = document.querySelector("#announcer");
let currentPath = "/";
let loading = false;

function announce(message) {
  announcer.textContent = "";
  requestAnimationFrame(() => { announcer.textContent = message; });
}

function pathFromHash() {
  try {
    const path = decodeURIComponent(location.hash.slice(1) || "/");
    return path.startsWith("/") ? path : "/";
  } catch {
    return "/";
  }
}

function navigate(path) {
  if (location.hash === `#${path}`) {
    route();
  } else {
    location.hash = path;
  }
}

function selectedPath(path) {
  const parts = path.split("/").filter(Boolean);
  if (parts.length === 0) return { screen: "home" };
  if (parts[0] === "type" && parts.length === 2) return { screen: "subtypes", typeId: parts[1] };
  if (["setup", "test", "result"].includes(parts[0]) && parts.length === 3) {
    return { screen: parts[0], typeId: parts[1], subtypeId: parts[2] };
  }
  return { screen: "home" };
}

function route() {
  if (!state.catalog) return;
  closeFigureInspector();
  const path = pathFromHash();
  if (state.screen === "test" && state.sessionStatus === "active" && path !== currentPath) {
    if (!window.confirm("Leave this practice session? Your current answers will be discarded.")) {
      location.hash = currentPath;
      return;
    }
    stopTimer();
    state.sessionStatus = "idle";
  }
  const target = selectedPath(path);
  const reasoningType = target.typeId ? findType(target.typeId) : null;
  const practiceSubtype = target.subtypeId ? findSubtype(reasoningType, target.subtypeId) : null;
  if ((target.typeId && !reasoningType) || (target.subtypeId && !practiceSubtype)) {
    location.hash = "/";
    return;
  }
  if (target.screen === "test" && state.sessionStatus !== "active") {
    location.hash = `/setup/${target.typeId}/${target.subtypeId}`;
    return;
  }
  if (target.screen === "result" && state.sessionStatus !== "complete") {
    location.hash = `/setup/${target.typeId}/${target.subtypeId}`;
    return;
  }
  state.type = reasoningType;
  state.subtype = practiceSubtype;
  if (target.screen === "setup" && practiceSubtype?.generator_key === "spatial.pattern_fitting" && !patternFittingModes.includes(state.config.puzzle_type)) state.config.puzzle_type = "Mixed";
  if (target.screen === "setup" && practiceSubtype?.generator_key === "spatial.pattern_finding" && !puzzleTypes.includes(state.config.puzzle_type)) state.config.puzzle_type = "Mixed";
  state.screen = target.screen;
  currentPath = path;
  if (target.screen === "home") renderHome();
  if (target.screen === "subtypes") renderSubtypes();
  if (target.screen === "setup") renderSetup();
  if (target.screen === "test") renderTest();
  if (target.screen === "result") renderResult();
  if (target.screen !== "test") stopTimer();
  workspace.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "instant" });
}

async function initialize() {
  if (loading) return;
  loading = true;
  renderLoading();
  try {
    state.catalog = await loadReasoning();
    if (!Array.isArray(state.catalog.types)) throw new Error("Reasoning data is incomplete. Please retry.");
    route();
  } catch (error) {
    state.screen = "error";
    renderError(error.message);
  } finally {
    loading = false;
  }
}

function setQuestion(index) {
  if (index < 0 || index >= state.questions.length) return;
  state.index = index;
  renderTest();
  announce(`Question ${index + 1} of ${state.questions.length}`);
  document.querySelector("#question-heading")?.focus?.();
}

function complete() {
  stopTimer();
  finishSession();
  navigate(`/result/${state.type.id}/${state.subtype.id}`);
  announce("Practice session complete.");
}

function requestCompletion() {
  const unsubmitted = state.submitted.filter(value => !value).length;
  if (unsubmitted > 0 && !window.confirm(`Finish with ${unsubmitted} unsubmitted ${unsubmitted === 1 ? "item" : "items"}? Only submitted answers count toward your score.`)) return;
  complete();
}

function submitAnswer() {
  const index = state.index;
  if (state.submitted[index] || state.timedOut[index]) return;
  if (!state.answers[index]) {
    document.querySelector("#answer-feedback").textContent = "Select an answer before submitting.";
    announce("Select an answer before submitting.");
    return;
  }
  state.submitted[index] = true;
  const correct = state.answers[index] === state.questions[index].correct_answer_id;
  renderTest();
  document.querySelector("#answer-feedback")?.focus();
  announce(`Question ${index + 1}: ${correct ? "correct" : "incorrect"}.`);
}

function tick(elapsed) {
  if (state.sessionStatus !== "active" || state.screen !== "test") return;
  const index = state.index;
  if (state.timedOut[index] || state.submitted[index]) return;
  state.remaining[index] = Math.max(0, state.remaining[index] - elapsed);
  updateTimerDisplay();
  if (state.remaining[index] > 0) return;
  state.timedOut[index] = true;
  state.answers[index] = null;
  announce(`Time ended for question ${index + 1}.`);
  if (index === state.questions.length - 1) {
    complete();
  } else {
    setQuestion(index + 1);
  }
}

async function startPractice() {
  const error = validateConfig();
  if (error) {
    const label = document.querySelector("#setup-error");
    if (label) label.textContent = error;
    else { navigate(`/setup/${state.type.id}/${state.subtype.id}`); }
    return;
  }
  const button = document.querySelector("#start-button");
  if (button) {
    button.disabled = true;
    button.textContent = "Preparing practice…";
  }
  try {
    const data = await createPractice({
      type_id: state.type.id, subtype_id: state.subtype.id, ...state.config
    });
    if (!Array.isArray(data.questions) || data.questions.length !== state.config.item_count) throw new Error("Practice questions could not be prepared. Please retry.");
    beginSession(data.questions);
    navigate(`/test/${state.type.id}/${state.subtype.id}`);
    if (state.config.timer_enabled) startTimer(tick);
    announce("Practice started. Question 1 of " + state.questions.length);
  } catch (error) {
    const label = document.querySelector("#setup-error");
    if (label) label.textContent = error.message;
    else { state.screen = "error"; renderError(error.message, false); }
    if (button) {
      button.disabled = false;
      button.textContent = "Start practice →";
    }
  }
}

workspace.addEventListener("click", async event => {
  const inspect = event.target.closest("[data-figure-inspect]");
  if (inspect) { openFigureInspector(figureEntry(inspect)); return; }
  const exportButton = event.target.closest("[data-figure-export]");
  if (exportButton) {
    const { block, host } = figureEntry(exportButton);
    exportButton.disabled = true;
    try { await exportFigureBlock(host, block); announce(`Downloaded ${block.filename}`); }
    catch (error) { announce(`Figure download failed: ${error.message}`); }
    finally { exportButton.disabled = false; }
    return;
  }
  const control = event.target.closest("button");
  if (!control) {
    const choice = event.target.closest(".choice");
    if (choice && !event.target.closest("label") && state.screen === "test") {
      const radio = choice.querySelector('input[name="answer"]');
      if (radio && !radio.disabled) radio.click();
    }
    return;
  }
  if (control.dataset.type) navigate(`/type/${control.dataset.type}`);
  else if (control.dataset.subtype) navigate(`/setup/${state.type.id}/${control.dataset.subtype}`);
  else if (control.dataset.route) navigate(control.dataset.route);
  else if (control.dataset.question !== undefined) setQuestion(Number(control.dataset.question));
  else if (control.dataset.action === "retry") initialize();
  else if (control.dataset.action === "previous") setQuestion(state.index - 1);
  else if (control.dataset.action === "next") {
    if (state.index === state.questions.length - 1) requestCompletion();
    else setQuestion(state.index + 1);
  }
  else if (control.dataset.action === "submit-answer") submitAnswer();
  else if (control.dataset.action === "submit") requestCompletion();
  else if (control.dataset.action === "restart") {
    startPractice();
  }
});

workspace.addEventListener("submit", event => {
  if (event.target.id !== "setup-form") return;
  event.preventDefault();
  startPractice();
});

function syncConfig(event) {
  const input = event.target;
  if (!input.closest("#setup-form")) return;
  if (input.name === "item_count" || input.name === "choice_count" || input.name === "seconds_per_item") {
    state.config[input.name] = input.value === "" ? NaN : Number(input.value);
  } else if (input.name === "timer_enabled") {
    state.config.timer_enabled = input.checked;
  } else if (input.name === "difficulty" && input.checked) {
    state.config.difficulty = input.value;
  } else if (input.name === "theme") {
    state.config.theme = input.value;
  } else if (input.name === "puzzle_type") {
    state.config.puzzle_type = input.value;
  }
  saveConfig();
  updateSetup();
}
workspace.addEventListener("input", syncConfig);
workspace.addEventListener("change", event => {
  syncConfig(event);
  if (event.target.name !== "answer" || state.screen !== "test" || state.timedOut[state.index] || state.submitted[state.index]) return;
  state.answers[state.index] = event.target.value;
  const current = state.index;
  const dot = document.querySelector(`.nav-dot[data-question="${current}"]`);
  dot?.classList.add("selected");
  dot?.setAttribute("aria-label", `Question ${current + 1}, selected`);
  const feedback = document.querySelector("#answer-feedback");
  if (feedback) feedback.textContent = "";
  announce(`Answer selected for question ${current + 1}.`);
});

workspace.addEventListener("error", event => {
  if (event.target.matches("img[data-icon]") && !event.target.dataset.fallback) {
    event.target.dataset.fallback = "true";
    event.target.src = "/static/assets/icons/mark.svg";
  }
}, true);

window.addEventListener("hashchange", route);
initialize();
