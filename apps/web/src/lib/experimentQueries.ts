/** React Query hooks for experiments. */
import type { ExperimentCreate, ExperimentStatus, ExperimentUpdate } from "@nemeth/domain-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "./api";
import { keys } from "./queries";

export interface ExperimentFilters {
  q?: string;
  status?: ExperimentStatus;
}

export const experimentKeys = {
  all: ["experiments"] as const,
  list: (filters: ExperimentFilters) => ["experiments", "list", filters] as const,
  one: (ref: string) => ["experiments", ref] as const,
  forPrototype: (ref: string) => ["prototypes", ref, "experiments"] as const,
  forRevision: (id: string) => ["revisions", id, "experiments"] as const,
};

export function useExperiments(filters: ExperimentFilters) {
  return useQuery({
    queryKey: experimentKeys.list(filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/experiments", {
          params: { query: { q: filters.q || undefined, status: filters.status, limit: 200 } },
        }),
      ),
  });
}

export function useExperiment(ref: string) {
  return useQuery({
    queryKey: experimentKeys.one(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/experiments/{ref}", { params: { path: { ref } } })),
  });
}

export function usePrototypeExperiments(ref: string) {
  return useQuery({
    queryKey: experimentKeys.forPrototype(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/prototypes/{ref}/experiments", { params: { path: { ref } } })),
  });
}

export function useRevisionExperiments(id: string) {
  return useQuery({
    queryKey: experimentKeys.forRevision(id),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/revisions/{revision_id}/experiments", {
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

export function useCreateExperiment() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: ExperimentCreate) =>
      unwrap(await api.POST("/api/v1/experiments", { body })),
    onSuccess: () => invalidate(experimentKeys.all, keys.dashboard),
  });
}

export function useUpdateExperiment(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: ExperimentUpdate) =>
      unwrap(await api.PATCH("/api/v1/experiments/{ref}", { params: { path: { ref } }, body })),
    onSuccess: () => invalidate(experimentKeys.all, keys.dashboard),
  });
}

export function useLinkPrototype(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: { prototype_identifier: string; role?: string | null }) =>
      unwrap(
        await api.POST("/api/v1/experiments/{ref}/prototypes", {
          params: { path: { ref } },
          body,
        }),
      ),
    onSuccess: () => invalidate(experimentKeys.all, ["prototypes"]),
  });
}

export function useUnlinkPrototype(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (prototype_ref: string) =>
      unwrap(
        await api.DELETE("/api/v1/experiments/{ref}/prototypes/{prototype_ref}", {
          params: { path: { ref, prototype_ref } },
        }),
      ),
    onSuccess: () => invalidate(experimentKeys.all, ["prototypes"]),
  });
}

export function useLinkRevision(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: { component_revision_id: string; role?: string | null }) =>
      unwrap(
        await api.POST("/api/v1/experiments/{ref}/revisions", {
          params: { path: { ref } },
          body,
        }),
      ),
    onSuccess: () => invalidate(experimentKeys.all, ["revisions"]),
  });
}

export function useUnlinkRevision(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (revision_id: string) =>
      unwrap(
        await api.DELETE("/api/v1/experiments/{ref}/revisions/{revision_id}", {
          params: { path: { ref, revision_id } },
        }),
      ),
    onSuccess: () => invalidate(experimentKeys.all, ["revisions"]),
  });
}
