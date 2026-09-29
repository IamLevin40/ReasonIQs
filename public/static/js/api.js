async function readJson(response) {
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error || "Something went wrong. Please retry.");
  return body;
}

export async function loadReasoning() {
  return readJson(await fetch("/api/reasoning", { headers: { Accept: "application/json" } }));
}

export async function createPractice(payload) {
  const questions = [];
  let placeholder = true;
  let remaining = payload.item_count;
  while (remaining > 0) {
    // Keep each response below Vercel's function payload limit. Nonfinal batches
    // are even so Mixed pattern sessions still alternate evenly overall.
    const itemCount = remaining <= 10 ? remaining : remaining < 15 ? 6 : 10;
    const data = await readJson(await fetch("/api/practice", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ ...payload, item_count: itemCount })
    }));
    if (!Array.isArray(data.questions) || data.questions.length !== itemCount) {
      throw new Error("Practice questions could not be prepared. Please retry.");
    }
    for (const question of data.questions) {
      questions.push({ ...question, id: `${payload.subtype_id}-${questions.length + 1}` });
    }
    placeholder &&= data.placeholder === true;
    remaining -= itemCount;
  }
  return { questions, placeholder };
}
