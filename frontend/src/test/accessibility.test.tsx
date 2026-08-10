/**
 * Automated accessibility audit.
 *
 * One suite rather than a check bolted onto each component's own tests, so
 * that adding a screen to the app and forgetting to audit it is visible in a
 * single place.
 *
 * What this can and cannot do is worth being blunt about: axe runs against
 * jsdom, which has no layout engine, so colour contrast is not checked here
 * (see `axe.ts`). Contrast has been the source of every accessibility bug this
 * project has shipped, and it is still found by opening the app and looking at
 * it. What this suite does catch is structural: unlabelled controls, broken
 * name/role/value, list and heading markup, duplicate ids, ARIA attributes
 * used on elements that do not accept them.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AIPanel } from "@/components/ai/ai-panel";
import { Activity } from "@/components/analytics/activity";
import { Funnel } from "@/components/analytics/funnel";
import { Sources } from "@/components/analytics/sources";
import { StatusSplit } from "@/components/analytics/status-split";
import { Timing } from "@/components/analytics/timing";
import { ApplicationForm } from "@/components/applications/application-form";
import { StatusBadge } from "@/components/applications/status-badge";
import { AuthShell } from "@/components/auth/auth-shell";
import { UserMenu } from "@/components/layout/user-menu";
import { UploadDropzone } from "@/components/resumes/upload-dropzone";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemedSelect } from "@/components/ui/themed-select";
import { ALL_STATUSES } from "@/lib/application-status";
import type { User } from "@/lib/types";

import { expectNoAxeViolations } from "./axe";
import { renderWithProviders } from "./render";

// The app router has no provider in a unit test, and useRouter throws without
// one. Only navigation is stubbed — the components themselves are real.
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

const user: User = {
  id: "0b6f2c1e-0000-4000-8000-000000000001",
  email: "priya@example.com",
  first_name: "Priya",
  last_name: "Nair",
  is_active: true,
  created_at: "2026-01-04T09:00:00Z",
};

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

// Several of these components fetch on mount. Nothing here is testing the
// data, only the markup, so requests answer with an empty result rather than
// reaching for a backend that is not running. Collections come back as bare
// arrays or wrapped in `items` depending on the endpoint, and handing back the
// wrong shape crashes the render rather than failing the assertion.
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      const body = String(url).includes("/resumes") ? [] : { items: [] };
      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }),
  );
});

describe("accessibility", () => {
  describe("analytics", () => {
    it("funnel", async () => {
      const { container } = render(
        <Funnel
          steps={[
            { key: "sent", label: "Sent", count: 24, rate: null },
            { key: "assessment", label: "Assessment", count: 11, rate: 0.4583 },
            { key: "interview", label: "Interview", count: 7, rate: 0.2917 },
            { key: "final", label: "Final round", count: 3, rate: 0.125 },
            { key: "offer", label: "Offer", count: 2, rate: 0.0833 },
            { key: "accepted", label: "Accepted", count: 1, rate: 0.0417 },
          ]}
        />,
      );
      await expectNoAxeViolations(container);
    });

    it("funnel, with nothing sent", async () => {
      const { container } = render(
        <Funnel steps={[{ key: "sent", label: "Sent", count: 0, rate: null }]} />,
      );
      await expectNoAxeViolations(container);
    });

    it("activity chart", async () => {
      const { container } = render(
        <Activity
          volume={[
            { week_start: "2026-07-20", created: 2, moved: 1 },
            { week_start: "2026-07-27", created: 5, moved: 3 },
            { week_start: "2026-08-03", created: 1, moved: 4 },
          ]}
        />,
      );
      await expectNoAxeViolations(container);
    });

    it("status split", async () => {
      const { container } = render(
        <StatusSplit
          statuses={[
            { status: "applied", count: 9 },
            { status: "technical_interview", count: 3 },
            { status: "rejected", count: 6 },
          ]}
        />,
      );
      await expectNoAxeViolations(container);
    });

    it("timing", async () => {
      const { container } = render(
        <Timing
          stages={[
            { status: "applied", average_days: 6.4, median_days: 5, moves: 12 },
            {
              status: "technical_interview",
              average_days: 0.5,
              median_days: 0.5,
              moves: 4,
            },
          ]}
        />,
      );
      await expectNoAxeViolations(container);
    });

    it("sources", async () => {
      const { container } = render(
        <Sources
          sources={[
            {
              source: "LinkedIn",
              total: 14,
              sent: 12,
              interviews: 5,
              offers: 1,
              interview_rate: 0.4167,
            },
            {
              source: null,
              total: 3,
              sent: 0,
              interviews: 0,
              offers: 0,
              interview_rate: null,
            },
          ]}
        />,
      );
      await expectNoAxeViolations(container);
    });
  });

  describe("forms", () => {
    it("application form", async () => {
      const { container } = renderWithProviders(
        <ApplicationForm submitLabel="Save" onSubmit={vi.fn()} />,
      );
      await expectNoAxeViolations(container);
    });

    it("application form showing validation errors", async () => {
      renderWithProviders(<ApplicationForm submitLabel="Save" onSubmit={vi.fn()} />);

      // Submitting empty is the state a form is most likely to be broken in:
      // the messages appear, and nothing connects them to the fields unless
      // someone wired that up.
      await userEvent.click(screen.getByRole("button", { name: "Save" }));
      const message = await screen.findByText("Company is required");

      const company = screen.getByLabelText(/Company/);
      expect(company).toHaveAttribute("aria-invalid", "true");
      // The rule that matters and that axe cannot check: the message has to be
      // reachable from the input, or a screen reader announces "invalid" and
      // never says why.
      expect(company).toHaveAccessibleDescription(message.textContent!);
    });

    it("select", async () => {
      const { container } = render(
        <>
          <Label htmlFor="stage">Stage</Label>
          <ThemedSelect
            id="stage"
            value="applied"
            onChange={vi.fn()}
            options={[
              { value: "wishlist", label: "Wishlist" },
              { value: "applied", label: "Applied" },
            ]}
          />
        </>,
      );
      await expectNoAxeViolations(container);
    });

    it("upload dropzone", async () => {
      const { container } = render(<UploadDropzone onFile={vi.fn()} />);
      await expectNoAxeViolations(container);
    });

    it("labelled input", async () => {
      const { container } = render(
        <>
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" />
          <Button type="submit">Sign in</Button>
        </>,
      );
      await expectNoAxeViolations(container);
    });
  });

  describe("chrome", () => {
    it("account menu, closed", async () => {
      const { container } = renderWithProviders(<UserMenu />);
      await expectNoAxeViolations(container);
    });

    it("account menu, open", async () => {
      renderWithProviders(<UserMenu />);
      await userEvent.click(screen.getByRole("button", { name: "Account and settings" }));
      await screen.findByRole("menuitem", { name: /Sign out/ });

      // The menu is portalled out of the container, so the audit has to run
      // against the whole document or it would pass without seeing it.
      await expectNoAxeViolations(document.body);
    });

    it("exposes the theme choice as a radio group inside the menu", async () => {
      renderWithProviders(<UserMenu />);
      await userEvent.click(screen.getByRole("button", { name: "Account and settings" }));

      // Plain buttons here render as children a menu is not allowed to have,
      // and the menu's own arrow-key navigation skips them — visible, but not
      // reachable without a mouse.
      const options = await screen.findAllByRole("menuitemradio");
      expect(options.map((o) => o.textContent)).toEqual(["Light", "Dark", "System"]);

      await userEvent.click(screen.getByRole("menuitemradio", { name: "Dark" }));
      expect(screen.getByRole("menuitemradio", { name: "Dark" })).toBeChecked();

      // Comparing two themes should not mean reopening the menu each time.
      expect(screen.getByRole("menuitemradio", { name: "Light" })).toBeVisible();
    });

    it("auth shell", async () => {
      const { container } = render(
        <AuthShell
          title="Welcome back"
          subtitle="Sign in to pick up where you left off."
          footer={<p>No account yet?</p>}
        >
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" />
        </AuthShell>,
      );
      await expectNoAxeViolations(container);
    });

    it("every status badge", async () => {
      const { container } = render(
        <ul>
          {ALL_STATUSES.map((status) => (
            <li key={status}>
              <StatusBadge status={status} />
            </li>
          ))}
        </ul>,
      );
      await expectNoAxeViolations(container);
    });

    it("ai panel", async () => {
      const { container } = renderWithProviders(
        <AIPanel applicationId="0b6f2c1e-0000-4000-8000-000000000002" />,
      );
      await expectNoAxeViolations(container);
    });
  });
});
