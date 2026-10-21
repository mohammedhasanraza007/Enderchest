/*
  The only code in the app that calls fetch (ARCHITECTURE 7). It always sends the safety header
  on writes, speaks JSON, and turns the server's one error shape into an ApiError.
*/

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

let leavingForBootPage = false;

/** The server is not in state `ok`: reloading shows the boot page, which explains what to do. */
function showBootPage(): void {
  if (leavingForBootPage) return;
  leavingForBootPage = true;
  window.location.reload();
}

export async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== "GET") headers["X-Enderchest"] = "1";
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      0,
      "unreachable",
      "Enderchest is not answering. Check that it is running (run.bat), then retry.",
    );
  }

  const data: unknown = await response.json().catch(() => null);
  if (response.ok) return data as T;

  const error = (data as { error?: { code?: string; message?: string; details?: unknown } } | null)
    ?.error;
  const apiError = new ApiError(
    response.status,
    error?.code ?? "internal_error",
    error?.message ?? "Something went wrong. Nothing was lost.",
    (error?.details as Record<string, unknown> | undefined) ?? {},
  );
  if (apiError.code === "locked") showBootPage();
  throw apiError;
}

/** Field-level problems from a `validation_error`, keyed by field name. */
export function fieldProblems(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError) || error.code !== "validation_error") return {};
  const problems = error.details["problems"];
  if (!Array.isArray(problems)) return {};
  const found: Record<string, string> = {};
  for (const item of problems as Array<{ field?: string; problem?: string }>) {
    if (item.field !== undefined && item.problem !== undefined) found[item.field] = item.problem;
  }
  return found;
}
