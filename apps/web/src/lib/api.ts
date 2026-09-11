/**
 * Typed API client. Every request goes through `openapi-fetch` with types generated from
 * the backend's OpenAPI document, so a renamed field fails the build rather than a user.
 */
import type { ProblemDetails, paths } from "@nemeth/domain-types";
import createClient from "openapi-fetch";

/** Prefix for URLs built by hand (downloads, multipart uploads). */
export const API_BASE = "/api/v1";

/**
 * The generated OpenAPI paths already include the /api/v1 prefix, so the typed client
 * must be rooted at the origin. Rooting it at API_BASE doubles the prefix.
 */
export const CLIENT_BASE_URL = "";

export const api = createClient<paths>({ baseUrl: CLIENT_BASE_URL });

export class ApiError extends Error {
  readonly problem: ProblemDetails;
  readonly status: number;

  constructor(problem: ProblemDetails) {
    super(problem.detail ?? problem.title);
    this.name = "ApiError";
    this.problem = problem;
    this.status = problem.status;
  }

  /** Short machine-readable type, e.g. "immutable-revision". */
  get kind(): string {
    return this.problem.type.split("/").pop() ?? "error";
  }
}

/**
 * Convert an openapi-fetch result into data-or-throw. Problem details from the API are
 * preserved so forms can show the server's explanation verbatim.
 */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined) {
    throw new ApiError(toProblem(result.error, result.response));
  }
  if (result.data === undefined) {
    // 204 No Content and similar.
    return undefined as T;
  }
  return result.data;
}

function toProblem(error: unknown, response: Response): ProblemDetails {
  if (error && typeof error === "object" && "status" in error && "title" in error) {
    return error as ProblemDetails;
  }
  return {
    type: "about:blank",
    title: response.statusText || "Request failed",
    status: response.status,
    detail: typeof error === "string" ? error : undefined,
  };
}

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    const fields = error.problem.errors?.map((e) => `${e.loc}: ${e.msg}`).join("; ");
    return fields ? `${error.message} (${fields})` : error.message;
  }
  if (error instanceof Error) return error.message;
  return "Unexpected error";
}
