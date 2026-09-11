/** React Query hooks for engineering changes. */
import type { ChangeCreate, ChangeRole, ChangeStatus, ChangeUpdate } from "@nemeth/domain-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "./api";
import { keys } from "./queries";

export interface ChangeFilters {
  q?: string;
  status?: ChangeStatus;
  open_only?: boolean;
}

export const changeKeys = {
  all: ["changes"] as const,
  list: (filters: ChangeFilters) => ["changes", "list", filters] as const,
  one: (ref: string) => ["changes", ref] as const,
  forRevision: (id: string) => ["revisions", id, "changes"] as const,
};

export function useChanges(filters: ChangeFilters) {
  return useQuery({
    queryKey: changeKeys.list(filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/changes", {
          params: {
            query: {
              q: filters.q || undefined,
              status: filters.status,
              open_only: filters.open_only,
              limit: 200,
            },
          },
        }),
      ),
  });
}

export function useChange(ref: string) {
  return useQuery({
    queryKey: changeKeys.one(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/changes/{ref}", { params: { path: { ref } } })),
  });
}

export function useRevisionChanges(id: string) {
  return useQuery({
    queryKey: changeKeys.forRevision(id),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/revisions/{revision_id}/changes", {
          params: { path: { revision_id: id } },
        }),
      ),
  });
}

function useInvalidate() {
  const client = useQueryClient();
  return (...prefixes: readonly (readonly unknown[])[]) =>
    Promise.all(prefixes.map((queryKey) => client.invalidateQueries({ queryKey })));
}

export function useCreateChange() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: ChangeCreate) => unwrap(await api.POST("/api/v1/changes", { body })),
    onSuccess: () => invalidate(changeKeys.all, ["revisions"], keys.dashboard),
  });
}

export function useUpdateChange(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: ChangeUpdate) =>
      unwrap(await api.PATCH("/api/v1/changes/{ref}", { params: { path: { ref } }, body })),
    onSuccess: () => invalidate(changeKeys.all, ["revisions"], keys.dashboard),
  });
}

export function useLinkChangeRevision(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: { component_revision_id: string; role: ChangeRole }) =>
      unwrap(
        await api.POST("/api/v1/changes/{ref}/revisions", { params: { path: { ref } }, body }),
      ),
    onSuccess: () => invalidate(changeKeys.all, ["revisions"]),
  });
}

export function useUnlinkChangeRevision(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async ({ revision_id, role }: { revision_id: string; role: ChangeRole }) =>
      unwrap(
        await api.DELETE("/api/v1/changes/{ref}/revisions/{revision_id}", {
          params: { path: { ref, revision_id }, query: { role } },
        }),
      ),
    onSuccess: () => invalidate(changeKeys.all, ["revisions"]),
  });
}

export function useLinkChangeExperiment(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (experiment_ref: string) =>
      unwrap(
        await api.POST("/api/v1/changes/{ref}/experiments/{experiment_ref}", {
          params: { path: { ref, experiment_ref } },
        }),
      ),
    onSuccess: () => invalidate(changeKeys.all),
  });
}

export function useUnlinkChangeExperiment(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (experiment_ref: string) =>
      unwrap(
        await api.DELETE("/api/v1/changes/{ref}/experiments/{experiment_ref}", {
          params: { path: { ref, experiment_ref } },
        }),
      ),
    onSuccess: () => invalidate(changeKeys.all),
  });
}

export function useLinkChangeTestRun(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (run_ref: string) =>
      unwrap(
        await api.POST("/api/v1/changes/{ref}/test-runs/{run_ref}", {
          params: { path: { ref, run_ref } },
        }),
      ),
    onSuccess: () => invalidate(changeKeys.all),
  });
}

export function useUnlinkChangeTestRun(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (run_ref: string) =>
      unwrap(
        await api.DELETE("/api/v1/changes/{ref}/test-runs/{run_ref}", {
          params: { path: { ref, run_ref } },
        }),
      ),
    onSuccess: () => invalidate(changeKeys.all),
  });
}
