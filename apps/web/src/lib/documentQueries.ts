/** Attachments: listing through the typed client, upload through multipart fetch. */
import type {
  AttachmentKind,
  AttachmentRead,
  AttachmentUpdate,
  EntityType,
  ProblemDetails,
} from "@nemeth/domain-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { API_BASE, ApiError, api, unwrap } from "./api";

export interface AttachmentFilters {
  entity_type?: EntityType;
  entity_id?: string;
  kind?: AttachmentKind;
  q?: string;
}

export const documentKeys = {
  all: ["attachments"] as const,
  list: (filters: AttachmentFilters) => ["attachments", "list", filters] as const,
  policy: ["attachments", "policy"] as const,
};

export function useUploadPolicy() {
  return useQuery({
    queryKey: documentKeys.policy,
    queryFn: async () => unwrap(await api.GET("/api/v1/attachments/policy")),
    staleTime: 300_000,
  });
}

export function useAttachments(filters: AttachmentFilters) {
  return useQuery({
    queryKey: documentKeys.list(filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/attachments", {
          params: {
            query: {
              entity_type: filters.entity_type,
              entity_id: filters.entity_id,
              kind: filters.kind,
              q: filters.q || undefined,
              limit: 200,
            },
          },
        }),
      ),
  });
}

export interface UploadInput {
  file: File;
  entity_type: EntityType;
  entity_id: string;
  kind: AttachmentKind;
  description?: string | null;
}

async function uploadFile(input: UploadInput): Promise<AttachmentRead> {
  const form = new FormData();
  form.set("file", input.file, input.file.name);
  form.set("entity_type", input.entity_type);
  form.set("entity_id", input.entity_id);
  form.set("kind", input.kind);
  if (input.description) form.set("description", input.description);
  const response = await fetch(`${API_BASE}/attachments`, { method: "POST", body: form });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const problem =
      payload && typeof payload === "object" && "status" in payload
        ? (payload as ProblemDetails)
        : { type: "about:blank", title: response.statusText, status: response.status };
    throw new ApiError(problem);
  }
  return payload as AttachmentRead;
}

function useInvalidate() {
  const client = useQueryClient();
  return (...prefixes: readonly (readonly unknown[])[]) =>
    Promise.all(prefixes.map((queryKey) => client.invalidateQueries({ queryKey })));
}

export function useUploadAttachment() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: uploadFile,
    onSuccess: () => invalidate(documentKeys.all, ["dashboard"]),
  });
}

export function useUpdateAttachment() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ ref, body }: { ref: string; body: AttachmentUpdate }) =>
      unwrap(await api.PATCH("/api/v1/attachments/{ref}", { params: { path: { ref } }, body })),
    onSuccess: () => invalidate(documentKeys.all),
  });
}

export function useDeleteAttachment() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (ref: string) =>
      unwrap(await api.DELETE("/api/v1/attachments/{ref}", { params: { path: { ref } } })),
    onSuccess: () => invalidate(documentKeys.all, ["dashboard"]),
  });
}

export function contentUrl(ref: string, inline = false): string {
  return `${API_BASE}/attachments/${encodeURIComponent(ref)}/content${inline ? "?inline=true" : ""}`;
}

/** Where an entity lives in the UI, for links from attachments back to their owner. */
export function entityRoute(entityType: EntityType, identifier: string): string | null {
  switch (entityType) {
    case "product":
      return `/products/${identifier}`;
    case "product_model":
      return `/products/${identifier.split(".")[0] ?? identifier}`;
    case "caliber":
      return `/calibers/${identifier}`;
    case "component":
      return `/components/${identifier}`;
    case "component_revision": {
      const [component, , label] = identifier.split(" ");
      return component && label ? `/components/${component}/revisions/${label}` : null;
    }
    case "prototype":
      return `/prototypes/${identifier}`;
    case "part_instance":
      return `/part-instances?q=${identifier}`;
    case "experiment":
      return `/experiments/${identifier}`;
    case "test_run":
      return `/testing/${identifier}`;
    case "watch":
      return `/watches/${identifier}`;
    default:
      return null;
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
