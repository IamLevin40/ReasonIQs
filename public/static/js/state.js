const STORAGE_KEY = "reasoniqs.setup.v1";
export const cubeThemes = ["Mixed", "Shapes/Polygons", "Dice Dots", "Characters", "Abstract Structures"];
export const puzzleTypes = ["Linear", "Matrix", "Mixed"];
export const patternFittingModes = ["Mixed", "Cell Missing", "Four-Cell Junction Missing"];
const defaults = { item_count: 10, choice_count: 4, timer_enabled: false, seconds_per_item: 45, difficulty: "Average", theme: "Mixed", puzzle_type: "Mixed" };

function loadConfig() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return { ...defaults, ...saved, puzzle_type: saved?.puzzle_type === "Balanced" ? "Mixed" : saved?.puzzle_type ?? defaults.puzzle_type };
  } catch {
    return { ...defaults };
  }
}

export const state = {
  catalog: null,
  type: null,
  subtype: null,
  screen: "loading",
  config: loadConfig(),
  questions: [],
  index: 0,
  answers: [],
  submitted: [],
  timedOut: [],
  remaining: [],
  sessionStatus: "idle",
  result: null
};

export function saveConfig() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state.config)); } catch { /* Storage is optional. */ }
}

export function findType(id) {
  return state.catalog?.types.find(item => item.id === id && item.active) || null;
}

export function findSubtype(type, id) {
  return type?.subtypes?.find(item => item.id === id && item.parent_id === type.id && item.active) || null;
}

export function validateConfig(subtype = state.subtype) {
  const config = state.config;
  if (!Number.isInteger(config.item_count) || config.item_count < 5 || config.item_count > 50) return "Choose between 5 and 50 items.";
  if (!Number.isInteger(config.choice_count) || config.choice_count < 2 || config.choice_count > 6) return "Choose between 2 and 6 answer choices.";
  if (typeof config.timer_enabled !== "boolean") return "Choose whether to use an item timer.";
  if (!Number.isInteger(config.seconds_per_item) || config.seconds_per_item < 10 || config.seconds_per_item > 300) return "Choose a timer duration between 10 and 300 seconds.";
  if (!["Easy", "Average", "Challenge"].includes(config.difficulty) || !subtype?.difficulties.includes(config.difficulty)) return "Choose an available difficulty.";
  if (["spatial.dice_folding", "spatial.dice_unfolding"].includes(subtype?.generator_key) && !cubeThemes.includes(config.theme)) return "Choose an available cube marking theme.";
  if (subtype?.generator_key === "spatial.pattern_finding" && !puzzleTypes.includes(config.puzzle_type)) return "Choose an available puzzle type.";
  if (subtype?.generator_key === "spatial.pattern_fitting" && !patternFittingModes.includes(config.puzzle_type)) return "Choose an available missing-region mode.";
  return "";
}

export function beginSession(questions) {
  state.questions = questions;
  state.index = 0;
  state.answers = Array(questions.length).fill(null);
  state.submitted = Array(questions.length).fill(false);
  state.timedOut = Array(questions.length).fill(false);
  state.remaining = Array(questions.length).fill(state.config.seconds_per_item);
  state.sessionStatus = "active";
  state.result = null;
}

export function finishSession() {
  state.sessionStatus = "complete";
  const answered = state.submitted.filter(Boolean).length;
  const timedOut = state.timedOut.filter(Boolean).length;
  const correct = state.questions.reduce((total, question, index) =>
    total + Number(state.submitted[index] && state.answers[index] === question.correct_answer_id), 0);
  state.result = {
    answered, timedOut, unanswered: state.questions.length - answered,
    correct, total: state.questions.length
  };
}
