import axe, { type Result, type RunOptions } from "axe-core";
import { expect } from "vitest";

/**
 * Rules turned off for every audit, with the reason.
 *
 * Everything else runs. The list is deliberately short — each entry is a hole
 * in the coverage, so it should be obvious why it is there.
 */
const OPTIONS: RunOptions = {
  rules: {
    // jsdom has no layout engine. Elements have no size, and colours resolve
    // to the literal string "var(--foreground)" rather than a colour, so axe
    // cannot compute a ratio. Left on, it reports every element as
    // "incomplete", which is noise rather than a result.
    //
    // This matters more here than it looks: every accessibility bug this
    // project has actually shipped was a contrast bug. They were caught by
    // opening the pages and looking at them, and that is still the only way.
    "color-contrast": { enabled: false },

    // A component is not a page. Landmark and page-structure rules judge a
    // whole document, so they fail on every fragment for reasons that have
    // nothing to do with the fragment.
    region: { enabled: false },
  },
};

function describeViolation(violation: Result): string {
  const where = violation.nodes
    .map((node) => `      ${node.target.join(" ")}\n        ${node.failureSummary}`)
    .join("\n");
  return `  ${violation.id} (${violation.impact}): ${violation.help}\n${where}`;
}

/**
 * Runs axe over a rendered fragment and fails with the offending selectors.
 *
 * Pass the container from `render()`, or an element inside it when only part
 * of the tree is the thing under test.
 */
export async function expectNoAxeViolations(element: HTMLElement): Promise<void> {
  const results = await axe.run(element, OPTIONS);

  const report =
    results.violations.length === 0
      ? ""
      : `${results.violations.length} accessibility violation(s):\n` +
        results.violations.map(describeViolation).join("\n");

  expect(report).toBe("");
}
