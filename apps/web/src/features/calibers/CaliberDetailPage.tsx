import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { BomTree } from "@/components/domain/BomTree";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorNotice, KV, LoadingRows, PageHeader } from "@/components/ui/layout";
import { formatDateTime, formatNumber } from "@/lib/format";
import { useCaliber, useCaliberBom, type ResolveMode } from "@/lib/queries";

export function CaliberDetailPage() {
  const { ref = "" } = useParams();
  const caliber = useCaliber(ref);
  const [mode, setMode] = useState<ResolveMode>("latest");
  const bom = useCaliberBom(ref, mode, Boolean(caliber.data?.root_component));

  if (caliber.isLoading) return <LoadingRows />;
  if (caliber.isError) return <ErrorNotice error={caliber.error} />;
  if (!caliber.data) return null;
  const c = caliber.data;

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/calibers" className="hover:underline">
              Calibers
            </Link>{" "}
            / {c.identifier}
          </span>
        }
        title={
          <>
            <Identifier value={c.identifier} className="text-xl" />
            <span>{c.name}</span>
          </>
        }
        description={c.description}
        meta={
          <>
            <LifecycleBadge state={c.lifecycle_state} />
            <PlaceholderBadge show={c.is_placeholder} />
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader eyebrow="Engineering" title="Specification" />
          <CardContent>
            <KV
              columns={3}
              items={[
                { label: "Architecture", value: c.architecture, span: 2 },
                {
                  label: "Root assembly",
                  value: c.root_component ? (
                    <Identifier
                      value={c.root_component.identifier}
                      to={`/boms/${c.root_component.identifier}`}
                    />
                  ) : null,
                },
                { label: "Diameter", value: formatNumber(c.diameter_mm, "mm") },
                { label: "Thickness", value: formatNumber(c.thickness_mm, "mm") },
                { label: "Frequency", value: formatNumber(c.frequency_bph, "bph") },
                { label: "Jewels", value: formatNumber(c.jewel_count) },
                { label: "Power reserve", value: formatNumber(c.power_reserve_hours, "h") },
                { label: "Lift angle", value: formatNumber(c.lift_angle_deg, "°") },
                { label: "Target amplitude", value: formatNumber(c.target_amplitude_deg, "°") },
                {
                  label: "Rate tolerance",
                  value: c.target_rate_tolerance_spd
                    ? `±${formatNumber(c.target_rate_tolerance_spd, "s/d")}`
                    : null,
                },
              ]}
            />
            {c.specification ? (
              <div className="mt-4">
                <div className="label mb-1">Extended specification</div>
                <pre className="overflow-x-auto rounded border border-border bg-bg-elevated p-3 font-mono text-xs text-fg-muted">
                  {JSON.stringify(c.specification, null, 2)}
                </pre>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader eyebrow="Record" title="Details" />
          <CardContent>
            <KV
              columns={1}
              items={[
                { label: "Notes", value: c.notes },
                { label: "Created", value: `${formatDateTime(c.created_at)} · ${c.created_by}` },
                { label: "Updated", value: `${formatDateTime(c.updated_at)} · ${c.updated_by}` },
                { label: "Internal id", value: c.id, mono: true },
              ]}
            />
          </CardContent>
        </Card>

        <Card className="xl:col-span-3">
          <CardHeader
            eyebrow="Design BOM"
            title={
              c.root_component
                ? `${c.root_component.identifier} ${c.root_component.name}`
                : "Movement assembly"
            }
            actions={
              <div className="flex items-center gap-1">
                <Button
                  size="sm"
                  variant={mode === "latest" ? "primary" : "ghost"}
                  onClick={() => setMode("latest")}
                >
                  Latest
                </Button>
                <Button
                  size="sm"
                  variant={mode === "released" ? "primary" : "ghost"}
                  onClick={() => setMode("released")}
                >
                  Released
                </Button>
              </div>
            }
          />
          {!c.root_component ? (
            <CardContent>
              <EmptyState
                title="No root assembly"
                description="Assign the movement assembly component to this caliber to see its BOM."
              />
            </CardContent>
          ) : bom.isLoading ? (
            <LoadingRows />
          ) : bom.isError ? (
            <CardContent>
              <ErrorNotice error={bom.error} />
            </CardContent>
          ) : bom.data ? (
            <>
              <BomTree tree={bom.data} />
              <div className="border-t border-border px-4 py-2 text-xs text-fg-subtle">
                {bom.data.line_count} lines · depth {bom.data.max_depth} ·{" "}
                {bom.data.unresolved_count} unresolved in {mode} mode
              </div>
            </>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
