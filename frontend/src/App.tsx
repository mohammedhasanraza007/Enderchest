import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { ApiError } from "./api/client";
import { useProfile } from "./api/queries";
import { useThemeSync } from "./hooks/useThemeSync";
import { ErrorBoundary } from "./patterns/ErrorBoundary";
import { ToastProvider } from "./primitives/Toast";
import { AppRoutes } from "./routes";

// Server answers are not retried (they would answer the same again); a network failure is
// retried twice before the error state appears.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failures, error) => !(error instanceof ApiError) && failures < 2,
      refetchOnWindowFocus: false,
    },
  },
});

/** Keeps the page theme in step with the stored profile. Draws nothing. */
function ThemeSync() {
  useThemeSync(useProfile().data?.theme);
  return null;
}

export function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ToastProvider>
            <ThemeSync />
            <AppRoutes />
          </ToastProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
