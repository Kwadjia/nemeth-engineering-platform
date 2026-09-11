/** React Query hooks for test types, test runs and measurements. */
import type { MeasurementCreate, TestRunCreate, TestRunUpdate } from "@nemeth/domain-types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "./api";
import { keys } from "./queries";

export interface TestRunFilters {
  test_type?: string;
  prototype_id?: string;
  experiment_id?: string;
}

export const testingKeys = {
  types: ["test-types"] as const,
  runs: ["test-runs"] as const,
  list: (filters: TestRunFilters) => ["test-runs", "list", filters] as const,
  one: (ref: string) => ["test-runs", ref] as const,
  forPrototype: (ref: string) => ["prototypes", ref, "test-runs"] as const,
  timing: (ref: string) => ["prototypes", ref, "timing"] as const,
  forExperiment: (ref: string) => ["experiments", ref, "test-runs"] as const,
};

export function useTestTypes() {
  return useQuery({
    queryKey: testingKeys.types,
    queryFn: async () => unwrap(await api.GET("/api/v1/test-types")),
    staleTime: 60_000,
  });
}

export function useTestRuns(filters: TestRunFilters) {
  return useQuery({
    queryKey: testingKeys.list(filters),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/test-runs", {
          params: {
            query: {
              test_type: filters.test_type || undefined,
              prototype_id: filters.prototype_id,
              experiment_id: filters.experiment_id,
              limit: 200,
            },
          },
        }),
      ),
  });
}

export function useTestRun(ref: string) {
  return useQuery({
    queryKey: testingKeys.one(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/test-runs/{ref}", { params: { path: { ref } } })),
  });
}

export function usePrototypeTestRuns(ref: string) {
  return useQuery({
    queryKey: testingKeys.forPrototype(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/prototypes/{ref}/test-runs", { params: { path: { ref } } })),
  });
}

export function usePrototypeTiming(ref: string) {
  return useQuery({
    queryKey: testingKeys.timing(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/prototypes/{ref}/timing", { params: { path: { ref } } })),
  });
}

export function useExperimentTestRuns(ref: string) {
  return useQuery({
    queryKey: testingKeys.forExperiment(ref),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/experiments/{ref}/test-runs", { params: { path: { ref } } })),
  });
}

function useInvalidate() {
  const client = useQueryClient();
  return (...prefixes: readonly (readonly unknown[])[]) =>
    Promise.all(prefixes.map((queryKey) => client.invalidateQueries({ queryKey })));
}

export function useCreateTestRun() {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: TestRunCreate) =>
      unwrap(await api.POST("/api/v1/test-runs", { body })),
    onSuccess: () => invalidate(testingKeys.runs, ["prototypes"], ["experiments"], keys.dashboard),
  });
}

export function useUpdateTestRun(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: TestRunUpdate) =>
      unwrap(await api.PATCH("/api/v1/test-runs/{ref}", { params: { path: { ref } }, body })),
    onSuccess: () => invalidate(testingKeys.runs, keys.dashboard),
  });
}

export function useAddMeasurements(ref: string) {
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: async (body: MeasurementCreate[]) =>
      unwrap(
        await api.POST("/api/v1/test-runs/{ref}/measurements", {
          params: { path: { ref } },
          body,
        }),
      ),
    onSuccess: () => invalidate(testingKeys.runs, ["prototypes"], keys.dashboard),
  });
}
