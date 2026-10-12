export function summarizePriorities(actions) {
  const needsReview = actions.filter((action) => action.needsReview || action.score === "—").length;
  return {
    total: actions.length,
    needsReview,
    ready: actions.length - needsReview,
  };
}
