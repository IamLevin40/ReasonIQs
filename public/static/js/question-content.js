// The API and future generators share this small content contract. A block can
// contain text, figures, or both; old `visual` questions remain readable.
export function contentFor(block, question = false) {
  const text = block?.text ?? (question ? block?.prompt : "");
  const figures = Array.isArray(block?.figures) ? block.figures : block?.visual ? [block.visual] : [];
  return {
    text: typeof text === "string" ? text.trim() : "",
    figures: figures.filter(figure => figure && typeof figure === "object")
  };
}

export function visualChoices(choices) {
  return choices.length > 0 && choices.every(choice => {
    const content = contentFor(choice);
    return content.figures.length > 0 && content.text.length < 45;
  });
}
