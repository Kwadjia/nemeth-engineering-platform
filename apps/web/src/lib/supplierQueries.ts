/** React Query hooks for suppliers. */
import type { SupplierCreate, SupplierUpdate } from "@nemeth/domain-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "./api";
import { keys } from "./queries";

export const supplierKeys = {
  all: ["suppliers"] as const,
  one: (ref: string) => ["suppliers", ref] as const,
  revisions: (ref: string) => ["suppliers", ref, "revisions"] as const,
  instances: (ref: string) => ["suppliers", ref, "part-instances"] as const,
};

export function useSuppliers(q?: string) {
  return useQuery({
    queryKey: [...supplierKeys.all, q ?? ""] as const,
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/suppliers", {
          params: { query: { q: q || undefined, limit: 200 } },
        }),
      ),
  });
}

export function useSupplier(ref: string) {
  return useQuery({
    queryKey: supplierKeys.one(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/suppliers/{ref}", { params: { path: { ref } } })),
  });
}

export function useSupplierRevisions(ref: string) {
  return useQuery({
    queryKey: supplierKeys.revisions(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/suppliers/{ref}/revisions", { params: { path: { ref } } })),
  });
}

export function useSupplierPartInstances(ref: string) {
  return useQuery({
    queryKey: supplierKeys.instances(ref),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/suppliers/{ref}/part-instances", { params: { path: { ref } } }),
      ),
  });
}

function useInvalidate() {
  const client = useQueryClient();
  return (...prefixes: readonly (readonly unknown[])[]) =>
    Promise.all(prefixes.map((queryKey) => client.invalidateQueries({ queryKey })));
}

export function useCreateSupplier() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: SupplierCreate) =>
      unwrap(await api.POST("/api/v1/suppliers", { body })),
    onSuccess: () => invalidate(supplierKeys.all, keys.dashboard),
  });
}

export function useUpdateSupplier(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: SupplierUpdate) =>
      unwrap(await api.PATCH("/api/v1/suppliers/{ref}", { params: { path: { ref } }, body })),
    onSuccess: () => invalidate(supplierKeys.all),
  });
}
