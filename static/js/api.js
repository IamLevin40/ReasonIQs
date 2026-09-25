async function readJson(response) {
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error || "Something went wrong. Please retry.");
  return body;
}

export async function loadReasoning() {
  return readJson(await fetch("/api/reasoning", { headers: { Accept: "application/json" } }));
}

export async function createPractice(payload) {
  return readJson(await fetch("/api/practice", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload)
  }));
}
