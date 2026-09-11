/** React Query hooks for prototypes, part instances and build records. */
import type {
  BuildRecordCreate,
  PartInstanceCreate,
  PartInstanceStatus,
  PrototypeCreate,
  PrototypeUpdate,
} from "@nemeth/domain-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "./api";
import { keys } from "./queries";

export const prototypeKeys = {
  all: ["prototypes"] as const,
  one: (ref: string) => ["prototypes", ref] as const,
  configuration: (ref: string) => ["prototypes", ref, "configuration"] as const,
  builds: (ref: string) => ["prototypes", ref, "builds"] as const,
  instances: (filters: InstanceFilters) => ["part-instances", filters] as const,
  componentInstances: (ref: string) => ["components", ref, "part-instances"] as const,
  revisionPrototypes: (id: string) => ["revisions", id, "prototypes"] as const,
};

export interface InstanceFilters {
  q?: string;
  status?: PartInstanceStatus;
  prototype_id?: string;
  watch_id?: string;
}

export function usePrototypes() {
  return useQuery({
    queryKey: prototypeKeys.all,
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/prototypes", { params: { query: { limit: 200 } } })),
  });
}

export function usePrototype(ref: string) {
  return useQuery({
    queryKey: prototypeKeys.one(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/prototypes/{ref}", { params: { path: { ref } } })),
  });
}

export function usePrototypeConfiguration(ref: string) {
  return useQuery({
    queryKey: prototypeKeys.configuration(ref),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/prototypes/{ref}/configuration", { params: { path: { ref } } }),
      ),
  });
}

export function useBuildRecords(ref: string) {
  return useQuery({
    queryKey: prototypeKeys.builds(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/prototypes/{ref}/builds", { params: { path: { ref } } })),
  });
}

export function usePartInstances(filters: InstanceFilters) {
  return useQuery({
    queryKey: prototypeKeys.instances(filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/part-instances", {
          params: {
            query: {
              q: filters.q || undefined,
              status: filters.status,
              prototype_id: filters.prototype_id,
              watch_id: filters.watch_id,
              limit: 200,
            },
          },
        }),
      ),
  });
}

export function useComponentPartInstances(ref: string) {
  return useQuery({
    queryKey: prototypeKeys.componentInstances(ref),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/components/{ref}/part-instances", { params: { path: { ref } } }),
      ),
  });
}

function useInvalidate() {
  const client = useQueryClient();
  return (...prefixes: readonly (readonly unknown[])[]) =>
    Promise.all(prefixes.map((queryKey) => client.invalidateQueries({ queryKey })));
}

export function useCreatePrototype() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: PrototypeCreate) =>
      unwrap(await api.POST("/api/v1/prototypes", { body })),
    onSuccess: () => invalidate(prototypeKeys.all, keys.dashboard),
  });
}

export function useUpdatePrototype(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: PrototypeUpdate) =>
      unwrap(await api.PATCH("/api/v1/prototypes/{ref}", { params: { path: { ref } }, body })),
    onSuccess: () => invalidate(prototypeKeys.all, keys.dashboard),
  });
}

export function useCreateBuildRecord(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: BuildRecordCreate) =>
      unwrap(
        await api.POST("/api/v1/prototypes/{ref}/builds", { params: { path: { ref } }, body }),
      ),
    onSuccess: () =>
      invalidate(prototypeKeys.all, ["part-instances"], ["components"], keys.dashboard),
  });
}

export function useCreatePartInstances() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: PartInstanceCreate) =>
      unwrap(await api.POST("/api/v1/part-instances", { body })),
    onSuccess: () => invalidate(["part-instances"], ["components"]),
  });
}
