/**
 * React Query hooks, one per API resource. Query keys are centralised here so
 * invalidation after a mutation is a single line in the calling component.
 */
import type {
  BomLineCreate,
  ComponentCreate,
  ComponentFamily,
  ComponentKind,
  LifecycleState,
  RevisionCreate,
  RevisionUpdate,
} from "@nemeth/domain-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "./api";

export const keys = {
  dashboard: ["dashboard"] as const,
  systemInfo: ["system", "info"] as const,
  health: ["health"] as const,
  products: ["products"] as const,
  product: (ref: string) => ["products", ref] as const,
  models: ["models"] as const,
  model: (ref: string) => ["models", ref] as const,
  modelBom: (ref: string, mode: string) => ["models", ref, "bom", mode] as const,
  calibers: ["calibers"] as const,
  caliber: (ref: string) => ["calibers", ref] as const,
  caliberBom: (ref: string, mode: string) => ["calibers", ref, "bom", mode] as const,
  components: (filters: ComponentFilters) => ["components", filters] as const,
  component: (ref: string) => ["components", ref] as const,
  revisions: (ref: string) => ["components", ref, "revisions"] as const,
  revision: (id: string) => ["revisions", id] as const,
  bom: (revisionId: string, mode: string) => ["revisions", revisionId, "bom", mode] as const,
  bomFlat: (revisionId: string, mode: string) =>
    ["revisions", revisionId, "bom", "flat", mode] as const,
  whereUsed: (ref: string) => ["components", ref, "where-used"] as const,
};

export interface ComponentFilters {
  q?: string;
  family?: ComponentFamily;
  kind?: ComponentKind;
  state?: LifecycleState;
  limit?: number;
  offset?: number;
}

export type ResolveMode = "latest" | "released";

// --- system ------------------------------------------------------------------------

export function useDashboard() {
  return useQuery({
    queryKey: keys.dashboard,
    queryFn: async () => unwrap(await api.GET("/api/v1/dashboard/summary")),
  });
}

export function useSystemInfo() {
  return useQuery({
    queryKey: keys.systemInfo,
    queryFn: async () => unwrap(await api.GET("/api/v1/system/info")),
  });
}

export function useHealth() {
  return useQuery({
    queryKey: keys.health,
    queryFn: async () => unwrap(await api.GET("/api/v1/health")),
    refetchInterval: 30_000,
    retry: false,
  });
}

// --- products ----------------------------------------------------------------------

export function useProducts() {
  return useQuery({
    queryKey: keys.products,
    queryFn: async () => unwrap(await api.GET("/api/v1/products")),
  });
}

export function useProduct(ref: string) {
  return useQuery({
    queryKey: keys.product(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/products/{ref}", { params: { path: { ref } } })),
  });
}

export function useProductModels(ref: string) {
  return useQuery({
    queryKey: [...keys.product(ref), "models"],
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/products/{ref}/models", { params: { path: { ref } } })),
  });
}

export function useModelBom(ref: string, mode: ResolveMode) {
  return useQuery({
    queryKey: keys.modelBom(ref, mode),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/models/{ref}/bom", { params: { path: { ref }, query: { mode } } }),
      ),
  });
}

export function useCalibers() {
  return useQuery({
    queryKey: keys.calibers,
    queryFn: async () => unwrap(await api.GET("/api/v1/calibers")),
  });
}

export function useCaliber(ref: string) {
  return useQuery({
    queryKey: keys.caliber(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/calibers/{ref}", { params: { path: { ref } } })),
  });
}

export function useCaliberBom(ref: string, mode: ResolveMode, enabled = true) {
  return useQuery({
    queryKey: keys.caliberBom(ref, mode),
    enabled,
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/calibers/{ref}/bom", {
          params: { path: { ref }, query: { mode } },
        }),
      ),
  });
}

// --- components --------------------------------------------------------------------

export function useComponents(filters: ComponentFilters) {
  return useQuery({
    queryKey: keys.components(filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/components", {
          params: {
            query: {
              q: filters.q || undefined,
              family: filters.family,
              kind: filters.kind,
              state: filters.state,
              limit: filters.limit ?? 200,
              offset: filters.offset ?? 0,
            },
          },
        }),
      ),
  });
}

export function useComponent(ref: string) {
  return useQuery({
    queryKey: keys.component(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/components/{ref}", { params: { path: { ref } } })),
  });
}

export function useRevisions(ref: string) {
  return useQuery({
    queryKey: keys.revisions(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/components/{ref}/revisions", { params: { path: { ref } } })),
  });
}

export function useRevision(id: string | undefined) {
  return useQuery({
    queryKey: keys.revision(id ?? ""),
    enabled: Boolean(id),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/revisions/{revision_id}", {
          params: { path: { revision_id: id! } },
        }),
      ),
  });
}

export function useWhereUsed(ref: string) {
  return useQuery({
    queryKey: keys.whereUsed(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/components/{ref}/where-used", { params: { path: { ref } } })),
  });
}

export function useBom(revisionId: string | undefined, mode: ResolveMode) {
  return useQuery({
    queryKey: keys.bom(revisionId ?? "", mode),
    enabled: Boolean(revisionId),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/revisions/{revision_id}/bom", {
          params: { path: { revision_id: revisionId! }, query: { mode } },
        }),
      ),
  });
}

export function useBomFlat(revisionId: string | undefined, mode: ResolveMode) {
  return useQuery({
    queryKey: keys.bomFlat(revisionId ?? "", mode),
    enabled: Boolean(revisionId),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/revisions/{revision_id}/bom/flat", {
          params: { path: { revision_id: revisionId! }, query: { mode } },
        }),
      ),
  });
}

// --- mutations ---------------------------------------------------------------------

function useInvalidate() {
  const client = useQueryClient();
  return (...prefixes: readonly (readonly unknown[])[]) =>
    Promise.all(prefixes.map((queryKey) => client.invalidateQueries({ queryKey })));
}

export function useCreateComponent() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: ComponentCreate) =>
      unwrap(await api.POST("/api/v1/components", { body })),
    onSuccess: () => invalidate(["components"], keys.dashboard),
  });
}

export function useCreateRevision(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: RevisionCreate) =>
      unwrap(
        await api.POST("/api/v1/components/{ref}/revisions", { params: { path: { ref } }, body }),
      ),
    onSuccess: () => invalidate(["components"], ["revisions"], keys.dashboard),
  });
}

export function useUpdateRevision(revisionId: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: RevisionUpdate) =>
      unwrap(
        await api.PATCH("/api/v1/revisions/{revision_id}", {
          params: { path: { revision_id: revisionId } },
          body,
        }),
      ),
    onSuccess: () => invalidate(["components"], ["revisions"]),
  });
}

export function useTransitionRevision(revisionId: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (target_state: LifecycleState) =>
      unwrap(
        await api.POST("/api/v1/revisions/{revision_id}/transition", {
          params: { path: { revision_id: revisionId } },
          body: { target_state },
        }),
      ),
    onSuccess: () => invalidate(["components"], ["revisions"], keys.dashboard),
  });
}

export function useAddBomLine(revisionId: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: BomLineCreate) =>
      unwrap(
        await api.POST("/api/v1/revisions/{revision_id}/bom-lines", {
          params: { path: { revision_id: revisionId } },
          body,
        }),
      ),
    onSuccess: () => invalidate(["revisions"], ["components"], ["models"], ["calibers"]),
  });
}

export function useDeleteBomLine() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (lineId: string) =>
      unwrap(
        await api.DELETE("/api/v1/bom-lines/{line_id}", { params: { path: { line_id: lineId } } }),
      ),
    onSuccess: () => invalidate(["revisions"], ["components"], ["models"], ["calibers"]),
  });
}
