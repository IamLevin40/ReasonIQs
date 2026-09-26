import { contentFor, visualChoices } from "./question-content.js";

// Pure markup plus media descriptors: no generator code or session state here.
// The caller mounts the media after inserting markup into the document.
export function renderQuestionContent(question, number, selected, locked, escapeHtml, submitted = false) {
  const prompt = contentFor(question, true);
  const blocks = new Map();
  const numberPadded = String(number).padStart(2, "0");
  if (prompt.figures.length) blocks.set("question", {
    ...prompt, label: `question ${number}`, filename: `reasoniqs_question_${numberPadded}.png`
  });
  const choices = question.choices.map((choice, index) => {
    const content = contentFor(choice);
    const letter = String.fromCharCode(65 + index);
    if (content.figures.length) blocks.set(`choice-${index}`, {
      ...content, label: `choice ${letter} of question ${number}`,
      filename: `reasoniqs_question_${numberPadded}_choice_${letter.toLowerCase()}.png`
    });
    const description = content.text || content.figures.map(figure => figure.alt || "figure").join(", ");
    const correct = submitted && choice.id === question.correct_answer_id;
    const incorrectSelection = submitted && selected === choice.id && !correct;
    const resultClass = correct ? "choice-result-correct" : incorrectSelection ? "choice-result-incorrect" : "";
    const resultText = correct ? "Correct answer" : incorrectSelection ? "Your answer" : "";
    return `<div class="choice ${content.figures.length ? "choice-has-figures" : ""} ${resultClass}">
      <label class="choice-select"><input type="radio" name="answer" value="${escapeHtml(choice.id)}" ${selected === choice.id ? "checked" : ""} ${locked ? "disabled" : ""} aria-label="${escapeHtml(`Choice ${letter}${description ? `: ${description}` : ""}${resultText ? `, ${resultText}` : ""}`)}"><span class="choice-letter" aria-hidden="true">${letter}</span>${content.text ? `<span class="choice-text">${escapeHtml(content.text)}</span>` : ""}${resultText ? `<span class="choice-result-label">${resultText}</span>` : ""}<span class="choice-check" aria-hidden="true">${incorrectSelection ? "&#10005;" : "&#10003;"}</span></label>
      ${content.figures.length ? `<div class="figure-list choice-figures" data-figure-block="choice-${index}"></div>` : ""}</div>`;
  });
  const html = `<div class="question-content" aria-label="Question content">${prompt.text ? `<p class="question-prompt">${escapeHtml(prompt.text)}</p>` : ""}${prompt.figures.length ? '<div class="figure-list question-figures" data-figure-block="question"></div>' : ""}</div>
    <fieldset class="choices ${visualChoices(question.choices) ? "choices-visual" : ""}"><legend>Choose one answer</legend><div class="choice-list">${choices.join("")}</div></fieldset>`;
  return { html, blocks };
}
