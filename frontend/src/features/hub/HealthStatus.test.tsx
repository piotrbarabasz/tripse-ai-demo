import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HealthStatus, HEALTH_TIMEOUT_MS } from "./HealthStatus";
import { parseHealth } from "./health";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function mockResponse(
  body: unknown,
  status = 200,
  contentType = "application/json",
) {
  const fetchMock = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { "content-type": contentType },
      }),
    );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("health connectivity proof", () => {
  it.each(["live", "mock"])(
    "validates actual local %s responses and drops operational fields",
    (mode) => {
      expect(
        parseHealth({
          status: "ok",
          generation_mode: mode,
          service: "private-name",
          image_version: "private-version",
        }),
      ).toEqual({ status: "ok", generation_mode: mode });
    },
  );
  it("shows loading then success without implying authentication", async () => {
    const fetchMock = mockResponse({
      status: "ok",
      generation_mode: "mock",
      feature_mode: "cloud_demo",
      service: "private-service",
    });
    render(<HealthStatus />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Sprawdzanie połączenia",
    );
    expect(
      await screen.findByText("Usługa odpowiada prawidłowo."),
    ).toBeVisible();
    expect(screen.getByText(/Nie potwierdza zalogowania/)).toBeVisible();
    expect(screen.queryByText("private-service")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      "/health",
      expect.objectContaining({
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        redirect: "error",
      }),
    );
  });
  it.each([401, 403, 404, 503])(
    "handles HTTP %s without exposing the body or retrying",
    async (status) => {
      const fetchMock = mockResponse(
        { detail: "private-internal-error" },
        status,
      );
      render(<HealthStatus />);
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "Nie udało się sprawdzić połączenia",
      );
      expect(
        screen.queryByText("private-internal-error"),
      ).not.toBeInTheDocument();
      expect(fetchMock).toHaveBeenCalledOnce();
    },
  );
  it.each([
    null,
    {},
    { status: "error", generation_mode: "mock" },
    { status: "ok", generation_mode: "other" },
  ])("rejects malformed health data: %j", async (body) => {
    mockResponse(body);
    render(<HealthStatus />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Nie udało się sprawdzić połączenia",
    );
  });
  it("rejects successful login HTML instead of treating it as health", async () => {
    mockResponse("private login body", 200, "text/html");
    render(<HealthStatus />);
    expect(await screen.findByRole("alert")).toBeVisible();
  });
  it("handles invalid JSON and network failure safely", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response("not-json", {
            headers: { "content-type": "application/json" },
          }),
        ),
    );
    const first = render(<HealthStatus />);
    expect(await screen.findByRole("alert")).toBeVisible();
    first.unmount();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("private transport failure")),
    );
    render(<HealthStatus />);
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(
      screen.queryByText("private transport failure"),
    ).not.toBeInTheDocument();
  });
  it("times out a bounded request and aborts without retry", async () => {
    vi.useFakeTimers();
    let signal: AbortSignal | undefined;
    const fetchMock = vi.fn((_url: string, options: RequestInit) => {
      signal = options.signal ?? undefined;
      return new Promise<Response>(() => undefined);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<HealthStatus />);
    await act(() => vi.advanceTimersByTimeAsync(HEALTH_TIMEOUT_MS));
    expect(signal?.aborted).toBe(true);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Przekroczono czas oczekiwania",
    );
    expect(fetchMock).toHaveBeenCalledOnce();
  });
  it("cancels on unmount and ignores a late response", async () => {
    let signal: AbortSignal | undefined;
    let resolve: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, options: RequestInit) => {
        signal = options.signal ?? undefined;
        return new Promise<Response>((done) => {
          resolve = done;
        });
      }),
    );
    const page = render(<HealthStatus />);
    page.unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      resolve?.(Response.json({ status: "ok", generation_mode: "mock" }));
      await Promise.resolve();
    });
    await waitFor(() =>
      expect(screen.queryByRole("status")).not.toBeInTheDocument(),
    );
  });
});
