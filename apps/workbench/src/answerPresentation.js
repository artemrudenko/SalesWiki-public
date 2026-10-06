/** Normalize the existing Answer Contract for a compact, honest UI card. */
export function answerPresentation(answer = {}) {
  const missing = Array.isArray(answer.missing) ? answer.missing : null;
  return {
    title: String(answer.title ?? "Guided answer"),
    summary: String(answer.conclusion ?? "No summary was provided."),
    nextAction: String(answer.next_action ?? "").trim(),
    freshness: String(answer.freshness ?? "not provided"),
    asOf: String(answer.as_of ?? "").trim(),
    confidence: String(answer.confidence ?? "not recorded"),
    missing,
    sections: Array.isArray(answer.sections) ? answer.sections : [],
    citations: Array.isArray(answer.citations) ? answer.citations : [],
  };
}

export function citationLabel(citation = {}) {
  return String(citation.title ?? citation.short ?? citation.code ?? citation.path ?? citation.handle ?? citation.boundary ?? "Cited source");
}
