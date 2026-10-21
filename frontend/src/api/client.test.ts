import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, fieldProblems, request } from "./client";

function answer(status: number, body: unknown) {
  return vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("request", () => {
  beforeEach(() => {
    vi.stubGlobal("window", { location: { reload: vi.fn() } });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the safety header on writes and not on reads", async () => {
    const fetchMock = answer(200, {});
    vi.stubGlobal("fetch", fetchMock);
    await request("GET", "/api/v1/profile");
    await request("PUT", "/api/v1/profile", { name: "Mo" });
    const [, read] = fetchMock.mock.calls[0] as [string, RequestInit];
    const [, write] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(read.headers).toEqual({});
    expect(write.headers).toEqual({ "X-Enderchest": "1", "Content-Type": "application/json" });
    expect(write.body).toBe('{"name":"Mo"}');
  });

  it("turns the server's error shape into an ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      answer(422, {
        error: {
          code: "validation_error",
          message: "Some values are not valid.",
          details: { x: 1 },
        },
      }),
    );
    const error = await request("PUT", "/api/v1/profile", {}).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("validation_error");
    expect((error as ApiError).status).toBe(422);
    expect((error as ApiError).message).toBe("Some values are not valid.");
  });

  it("says plainly that the app is not answering when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("failed")));
    const error = (await request("GET", "/health").catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe("unreachable");
    expect(error.message).toContain("run.bat");
  });

  it("reloads to the boot page when the server says it is locked, once", async () => {
    vi.stubGlobal("fetch", answer(503, { error: { code: "locked", message: "x", details: {} } }));
    await request("GET", "/api/v1/profile").catch(() => undefined);
    await request("GET", "/api/v1/profile").catch(() => undefined);
    const reload = (window as unknown as { location: { reload: ReturnType<typeof vi.fn> } })
      .location.reload;
    expect(reload).toHaveBeenCalledTimes(1);
  });
});

describe("fieldProblems", () => {
  it("keys the problems of a validation error by field", () => {
    const error = new ApiError(422, "validation_error", "x", {
      problems: [{ field: "name", problem: "Enter a name of 1 to 40 characters." }],
    });
    expect(fieldProblems(error)).toEqual({ name: "Enter a name of 1 to 40 characters." });
  });
  it("is empty for any other error", () => {
    expect(fieldProblems(new ApiError(500, "internal_error", "x"))).toEqual({});
    expect(fieldProblems(new Error("x"))).toEqual({});
  });
});
