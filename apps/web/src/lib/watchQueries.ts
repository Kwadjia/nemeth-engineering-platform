/** React Query hooks for serialized watches. */
import type { BuildRecordCreate, WatchCreate, WatchUpdate } from "@nemeth/domain-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "./api";
import { keys } from "./queries";

export const watchKeys = {
  all: ["watches"] as const,
  one: (ref: string) => ["watches", ref] as const,
  configuration: (ref: string) => ["watches", ref, "configuration"] as const,
  builds: (ref: string) => ["watches", ref, "builds"] as const,
  dossier: (ref: string) => ["watches", ref, "dossier"] as const,
  forModel: (ref: string) => ["models", ref, "watches"] as const,
};

export function useWatches() {
  return useQuery({
    queryKey: watchKeys.all,
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/watches", { params: { query: { limit: 200 } } })),
  });
}

export function useWatch(ref: string) {
  return useQuery({
    queryKey: watchKeys.one(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/watches/{ref}", { params: { path: { ref } } })),
  });
}

export function useWatchConfiguration(ref: string) {
  return useQuery({
    queryKey: watchKeys.configuration(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/watches/{ref}/configuration", { params: { path: { ref } } })),
  });
}

export function useWatchBuilds(ref: string) {
  return useQuery({
    queryKey: watchKeys.builds(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/watches/{ref}/builds", { params: { path: { ref } } })),
  });
}

export function useWatchDossier(ref: string) {
  return useQuery({
    queryKey: watchKeys.dossier(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/watches/{ref}/dossier", { params: { path: { ref } } })),
  });
}

export function useModelWatches(ref: string) {
  return useQuery({
    queryKey: watchKeys.forModel(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/models/{ref}/watches", { params: { path: { ref } } })),
  });
}

function useInvalidate() {
  const client = useQueryClient();
  return (...prefixes: readonly (readonly unknown[])[]) =>
    Promise.all(prefixes.map((queryKey) => client.invalidateQueries({ queryKey })));
}

export function useCreateWatch() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: WatchCreate) => unwrap(await api.POST("/api/v1/watches", { body })),
    onSuccess: () => invalidate(watchKeys.all, ["models"], keys.dashboard),
  });
}

export function useUpdateWatch(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: WatchUpdate) =>
      unwrap(await api.PATCH("/api/v1/watches/{ref}", { params: { path: { ref } }, body })),
    onSuccess: () => invalidate(watchKeys.all, keys.dashboard),
  });
}

export function useCreateWatchBuild(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: BuildRecordCreate) =>
      unwrap(await api.POST("/api/v1/watches/{ref}/builds", { params: { path: { ref } }, body })),
    onSuccess: () =>
      invalidate(watchKeys.all, ["prototypes"], ["part-instances"], ["components"], keys.dashboard),
  });
}
