import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";

import { ThemeProvider } from "@/components/theme/theme-provider";

/**
 * A query client that behaves in tests: no retries (a failed request should
 * fail once and be visible, not stall the test for several seconds) and no
 * cache shared between tests.
 */
function testQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
}

export function renderWithProviders(ui: ReactElement): RenderResult {
  const client = testQueryClient();

  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider>{ui}</ThemeProvider>
    </QueryClientProvider>,
  );
}
