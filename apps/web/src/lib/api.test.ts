import type { paths } from "@nemeth/domain-types";
import createClient from "openapi-fetch";
import { describe, expect, it, vi } from "vitest";

import { API_BASE, CLIENT_BASE_URL } from "./api";
import { contentUrl } from "./documentQueries";

describe("API client URLs", () => {
  it("does not double the /api/v1 prefix (OpenAPI paths already carry it)", async () => {
    const seen: string[] = [];
    const fetchSpy = vi.fn((input: Request) => {
      seen.push(input.url);
      return Promise.resolve(
        new Response("{}", { status: 200, headers: { "content-type": "application/json" } }),
      );
    });
    // Node's Request needs an absolute URL; the browser client uses the same relative base.
    const client = createClient<paths>({
      baseUrl: `http://test.local${CLIENT_BASE_URL}`,
      fetch: fetchSpy,
    });
    await client.GET("/api/v1/health");
    expect(seen).toHaveLength(1);
    expect(new URL(seen[0]!).pathname).toBe("/api/v1/health");
  });

  it("builds manual URLs under the API prefix", () => {
    expect(API_BASE).toBe("/api/v1");
    expect(contentUrl("DOC-00001")).toBe("/api/v1/attachments/DOC-00001/content");
    expect(contentUrl("DOC-00001", true)).toBe("/api/v1/attachments/DOC-00001/content?inline=true");
  });
});
