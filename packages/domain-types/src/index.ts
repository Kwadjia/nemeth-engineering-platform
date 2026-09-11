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
