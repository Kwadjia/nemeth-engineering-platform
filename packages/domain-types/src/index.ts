/**
 * Typed view of the NEMETH API.
 *
 * `api.d.ts` is generated from `openapi.json` (run `npm run api:types` at the repo root).
 * This file adds short aliases so application code never spells out
 * `components["schemas"]["..."]`.
 */
import type { components, paths } from "./api";

export type { components, paths };

export type Schemas = components["schemas"];

export type LifecycleState = Schemas["LifecycleState"];
export type ComponentKind = Schemas["ComponentKind"];
export type ComponentFamily = Schemas["ComponentFamily"];

export type ProductRead = Schemas["ProductRead"];
export type ProductSummary = Schemas["ProductSummary"];
export type ProductModelRead = Schemas["ProductModelRead"];
export type ProductModelSummary = Schemas["ProductModelSummary"];
export type CaliberRead = Schemas["CaliberRead"];
export type CaliberSummary = Schemas["CaliberSummary"];

export type ComponentSummary = Schemas["ComponentSummary"];
export type ComponentRead = Schemas["ComponentRead"];
export type ComponentDetail = Schemas["ComponentDetail"];
export type ComponentCreate = Schemas["ComponentCreate"];
export type ComponentUpdate = Schemas["ComponentUpdate"];

export type RevisionSummary = Schemas["RevisionSummary"];
export type RevisionRead = Schemas["RevisionRead"];
export type RevisionCreate = Schemas["RevisionCreate"];
export type RevisionUpdate = Schemas["RevisionUpdate"];
export type RevisionContent = Schemas["RevisionContent"];

export type BomLineRead = Schemas["BomLineRead"];
export type BomLineCreate = Schemas["BomLineCreate"];
export type BomNode = Schemas["BomNode"];
export type BomTree = Schemas["BomTree"];
export type BomFlat = Schemas["BomFlat"];
export type BomFlatRow = Schemas["BomFlatRow"];
export type WhereUsedRow = Schemas["WhereUsedRow"];

export type DashboardSummary = Schemas["DashboardSummary"];
export type SystemInfo = Schemas["SystemInfo"];
export type Health = Schemas["Health"];

export type PrototypeStatus = Schemas["PrototypeStatus"];
export type PartInstanceStatus = Schemas["PartInstanceStatus"];
export type PartSource = Schemas["PartSource"];
export type BuildAction = Schemas["BuildAction"];
export type PrototypeSummary = Schemas["PrototypeSummary"];
export type PrototypeRead = Schemas["PrototypeRead"];
export type PrototypeCreate = Schemas["PrototypeCreate"];
export type PrototypeUpdate = Schemas["PrototypeUpdate"];
export type PrototypeConfiguration = Schemas["PrototypeConfiguration"];
export type ConfigurationRow = Schemas["ConfigurationRow"];
export type PartInstanceSummary = Schemas["PartInstanceSummary"];
export type PartInstanceRead = Schemas["PartInstanceRead"];
export type PartInstanceCreate = Schemas["PartInstanceCreate"];
export type BuildRecordRead = Schemas["BuildRecordRead"];
export type BuildRecordCreate = Schemas["BuildRecordCreate"];
export type BuildEntryCreate = Schemas["BuildEntryCreate"];
export type BuildEntryRead = Schemas["BuildEntryRead"];

export type ExperimentStatus = Schemas["ExperimentStatus"];
export type ExperimentOutcome = Schemas["ExperimentOutcome"];
export type ExperimentSummary = Schemas["ExperimentSummary"];
export type ExperimentRead = Schemas["ExperimentRead"];
export type ExperimentCreate = Schemas["ExperimentCreate"];
export type ExperimentUpdate = Schemas["ExperimentUpdate"];

export type TestOutcome = Schemas["TestOutcome"];
export type TestTypeRead = Schemas["TestTypeRead"];
export type TestTypeSummary = Schemas["TestTypeSummary"];
export type MetricDef = Schemas["MetricDef"];
export type TestRunRead = Schemas["TestRunRead"];
export type TestRunSummary = Schemas["TestRunSummary"];
export type TestRunCreate = Schemas["TestRunCreate"];
export type TestRunUpdate = Schemas["TestRunUpdate"];
export type MeasurementCreate = Schemas["MeasurementCreate"];
export type MeasurementRead = Schemas["MeasurementRead"];
export type TimingSummary = Schemas["TimingSummary"];
export type PositionReading = Schemas["PositionReading"];

export const TEST_OUTCOMES: readonly TestOutcome[] = ["INFO", "PASS", "FAIL"] as const;

/** Timegrapher positions in the conventional order. */
export const POSITIONS: readonly { code: string; label: string }[] = [
  { code: "DU", label: "Dial up" },
  { code: "DD", label: "Dial down" },
  { code: "CU", label: "Crown up" },
  { code: "CD", label: "Crown down" },
  { code: "CL", label: "Crown left" },
  { code: "CR", label: "Crown right" },
] as const;

export const EXPERIMENT_STATUSES: readonly ExperimentStatus[] = [
  "PLANNED",
  "IN_PROGRESS",
  "COMPLETED",
  "ABANDONED",
] as const;

export const EXPERIMENT_OUTCOMES: readonly ExperimentOutcome[] = [
  "IMPROVEMENT",
  "NO_CHANGE",
  "REGRESSION",
  "INCONCLUSIVE",
] as const;

export const PROTOTYPE_STATUSES: readonly PrototypeStatus[] = [
  "PLANNED",
  "BUILDING",
  "ACTIVE",
  "RETIRED",
] as const;

export const PART_SOURCES: readonly PartSource[] = [
  "IN_HOUSE",
  "PURCHASED",
  "SALVAGED",
  "OTHER",
] as const;

export const PART_INSTANCE_STATUSES: readonly PartInstanceStatus[] = [
  "AVAILABLE",
  "INSTALLED",
  "REMOVED",
  "SCRAPPED",
] as const;

/** RFC 9457 problem details as emitted by the API. */
export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  errors?: { loc: string; msg: string; type: string }[];
  [key: string]: unknown;
}

export const LIFECYCLE_STATES: readonly LifecycleState[] = [
  "CONCEPT",
  "DESIGN",
  "PROTOTYPE",
  "VALIDATION",
  "RELEASED",
  "OBSOLETE",
] as const;

export const COMPONENT_FAMILIES: readonly ComponentFamily[] = [
  "WATCH",
  "CASE",
  "DIAL",
  "HAND",
  "MVT",
  "STRAP",
  "PKG",
  "MISC",
] as const;

export const COMPONENT_KINDS: readonly ComponentKind[] = ["PART", "ASSEMBLY"] as const;
