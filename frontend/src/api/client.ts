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

async function send<T>(method: Method, path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, method });
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

/** JSON in and out. `headers` carries extras such as an Idempotency-Key (API 1). */
export function request<T>(
  method: Method,
  path: string,
  body?: unknown,
  headers: Record<string, string> = {},
): Promise<T> {
  const all: Record<string, string> = { ...headers };
  if (method !== "GET") all["X-Enderchest"] = "1";
  if (body !== undefined) all["Content-Type"] = "application/json";
  return send<T>(method, path, {
    headers: all,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** A multipart upload (photos). The browser writes the Content-Type with its boundary.
 *  `signal` lets a caller abandon it (a coach frame when the coach is switched off). */
export function upload<T>(path: string, form: FormData, signal?: AbortSignal): Promise<T> {
  return send<T>("POST", path, { headers: { "X-Enderchest": "1" }, body: form, signal });
}

/** A fresh key per create, so a double click or a retry never makes two (API 1). */
export function idempotencyKey(): Record<string, string> {
  return { "Idempotency-Key": crypto.randomUUID() };
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
