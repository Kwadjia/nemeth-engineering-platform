import { LIFECYCLE_STATES } from "@nemeth/domain-types";
import { Activity, FlaskConical, GitBranch, Layers, Watch } from "lucide-react";
import { Link } from "react-router-dom";

import type { PrototypeSummary } from "@nemeth/domain-types";
import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { ExperimentStatusBadge, OutcomeBadge } from "@/components/domain/experimentBadges";
import { PrototypeStatusBadge } from "@/components/domain/prototypeBadges";
import { WatchStatusBadge } from "@/components/domain/watchBadges";
import { TimingTable } from "@/components/domain/TimingTable";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader, Stat } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatDateTime, titleCase } from "@/lib/format";
import { useDashboard } from "@/lib/queries";

export function DashboardPage() {
  const dashboard = useDashboard();

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Dashboard"
        description="Live state of the NEMETH N1 programme. Panels without data show as empty; nothing here is simulated."
      />

      {dashboard.isError ? <ErrorNotice error={dashboard.error} /> : null}

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader eyebrow="Programme" title="N1 development status" />
          {dashboard.isLoading ? (
            <LoadingRows />
          ) : dashboard.data ? (
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="label mb-1.5">Products</div>
                <ul className="divide-y divide-border rounded border border-border">
                  {dashboard.data.products.length === 0 ? (
                    <li className="px-3 py-3 text-xs text-fg-subtle">No products yet.</li>
                  ) : (
                    dashboard.data.products.map((p) => (
                      <li key={p.id} className="flex items-center justify-between gap-3 px-3 py-2">
                        <span className="flex items-center gap-2">
                          <Identifier value={p.identifier} to={`/products/${p.identifier}`} />
                          <span className="text-sm text-fg">{p.name}</span>
                          <PlaceholderBadge show={p.is_placeholder} />
                        </span>
                        <LifecycleBadge state={p.lifecycle_state} />
                      </li>
                    ))
                  )}
                </ul>
              </div>
              <div>
                <div className="label mb-1.5">Calibers</div>
                <ul className="divide-y divide-border rounded border border-border">
                  {dashboard.data.calibers.length === 0 ? (
                    <li className="px-3 py-3 text-xs text-fg-subtle">No calibers yet.</li>
                  ) : (
                    dashboard.data.calibers.map((c) => (
                      <li key={c.id} className="flex items-center justify-between gap-3 px-3 py-2">
                        <span className="flex items-center gap-2">
                          <Identifier value={c.identifier} to={`/calibers/${c.identifier}`} />
                          <span className="text-sm text-fg">{c.name}</span>
                          <PlaceholderBadge show={c.is_placeholder} />
                        </span>
                        <LifecycleBadge state={c.lifecycle_state} />
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </CardContent>
          ) : null}
        </Card>

        <Card>
          <CardHeader eyebrow="Components" title="By lifecycle state" />
          {dashboard.isLoading ? (
            <LoadingRows />
          ) : dashboard.data ? (
            <CardContent>
              <div className="mb-3 grid grid-cols-2 gap-2">
                <Stat label="Components" value={dashboard.data.component_count} />
                <Stat label="Assemblies" value={dashboard.data.assembly_count} />
              </div>
              <StateBars
                counts={dashboard.data.components_by_state}
                total={dashboard.data.component_count}
              />
            </CardContent>
          ) : null}
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader
            eyebrow="Revision control"
            title="Recent revisions"
            actions={
              <Link
                to="/components"
                className="text-xs text-fg-muted hover:text-fg hover:underline"
              >
                All components
              </Link>
            }
          />
          {dashboard.isLoading ? (
            <LoadingRows />
          ) : dashboard.data && dashboard.data.recent_revisions.length > 0 ? (
            <Table>
              <THead>
                <TR>
                  <TH>Component</TH>
                  <TH>Name</TH>
                  <TH className="w-20">Rev</TH>
                  <TH className="w-28">State</TH>
                  <TH>Change</TH>
                  <TH className="w-40">Created</TH>
                </TR>
              </THead>
              <TBody>
                {dashboard.data.recent_revisions.map((r) => (
                  <TR key={r.id}>
                    <TD>
                      <Identifier
                        value={r.component.identifier}
                        to={`/components/${r.component.identifier}`}
                      />
                    </TD>
                    <TD>{r.component.name}</TD>
                    <TD mono>
                      <Link
                        to={`/components/${r.component.identifier}/revisions/${r.revision_label}`}
                        className="hover:text-accent hover:underline"
                      >
                        Rev {r.revision_label}
                      </Link>
                    </TD>
                    <TD>
                      <LifecycleBadge state={r.lifecycle_state} />
                    </TD>
                    <TD className="max-w-md truncate text-fg-muted">{r.change_summary ?? "—"}</TD>
                    <TD className="text-fg-subtle">{formatDateTime(r.created_at)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          ) : (
            <CardContent>
              <EmptyState
                title="No revisions yet"
                description="Create a component to start revision history."
              />
            </CardContent>
          )}
        </Card>

        <div className="grid gap-4">
          <Card>
            <CardHeader
              eyebrow="Development"
              title="Active prototype"
              actions={
                <Link
                  to="/prototypes"
                  className="text-xs text-fg-muted hover:text-fg hover:underline"
                >
                  All prototypes
                </Link>
              }
            />
            <CardContent>
              {dashboard.isLoading ? (
                <LoadingRows rows={2} />
              ) : dashboard.data?.active_prototype ? (
                <ActivePrototype prototype={dashboard.data.active_prototype} />
              ) : (
                <EmptyState
                  icon={Layers}
                  title={
                    dashboard.data && dashboard.data.prototype_count > 0
                      ? "No prototype is being built"
                      : "No prototypes yet"
                  }
                  description={
                    dashboard.data && dashboard.data.prototype_count > 0
                      ? `${dashboard.data.prototype_count} planned or retired. Record a build to activate one.`
                      : "Create a prototype to start a build log."
                  }
                  className="py-6"
                />
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader
              eyebrow="Serialized"
              title="Watches"
              actions={
                <Link to="/watches" className="text-xs text-fg-muted hover:text-fg hover:underline">
                  All watches
                </Link>
              }
            />
            {dashboard.isLoading ? (
              <LoadingRows rows={2} />
            ) : dashboard.data && dashboard.data.watches.length > 0 ? (
              <ul className="divide-y divide-border">
                {dashboard.data.watches.map((w) => (
                  <li key={w.id} className="flex items-center gap-3 px-4 py-2">
                    <Identifier value={w.identifier} to={`/watches/${w.identifier}`} />
                    <span className="flex-1 truncate text-sm text-fg">{w.owner_name ?? "—"}</span>
                    <WatchStatusBadge status={w.status} />
                  </li>
                ))}
              </ul>
            ) : (
              <CardContent>
                <EmptyState
                  icon={Watch}
                  title="No serialized watches"
                  description="Give a build a serial number when it earns one."
                  className="py-6"
                />
              </CardContent>
            )}
          </Card>
          <Card>
            <CardHeader
              eyebrow="Development"
              title="Recent experiments"
              actions={
                <Link
                  to="/experiments"
                  className="text-xs text-fg-muted hover:text-fg hover:underline"
                >
                  All experiments
                </Link>
              }
            />
            {dashboard.isLoading ? (
              <LoadingRows rows={2} />
            ) : dashboard.data && dashboard.data.recent_experiments.length > 0 ? (
              <ul className="divide-y divide-border">
                {dashboard.data.recent_experiments.map((e) => (
                  <li key={e.id} className="flex items-center gap-3 px-4 py-2">
                    <Identifier value={e.identifier} to={`/experiments/${e.identifier}`} />
                    <span className="flex-1 truncate text-sm text-fg">{e.title}</span>
                    <OutcomeBadge outcome={e.outcome} />
                    <ExperimentStatusBadge status={e.status} />
                  </li>
                ))}
              </ul>
            ) : (
              <CardContent>
                <EmptyState
                  icon={FlaskConical}
                  title="No experiments recorded"
                  description="Start with a hypothesis on the Experiments page."
                  className="py-6"
                />
              </CardContent>
            )}
          </Card>
        </div>

        <Card>
          <CardHeader
            eyebrow="Testing"
            title="Latest timegrapher run"
            actions={
              <Link to="/testing" className="text-xs text-fg-muted hover:text-fg hover:underline">
                All test runs
              </Link>
            }
          />
          <CardContent>
            {dashboard.isLoading ? (
              <LoadingRows rows={3} />
            ) : dashboard.data?.latest_timing && dashboard.data.latest_timing_run ? (
              <div className="grid gap-3">
                <div className="flex items-center gap-2 text-xs text-fg-muted">
                  <Identifier
                    value={dashboard.data.latest_timing_run.identifier}
                    to={`/testing/${dashboard.data.latest_timing_run.identifier}`}
                  />
                  <span>{dashboard.data.latest_timing_run.title ?? "Timegrapher"}</span>
                  <span className="text-fg-subtle">
                    {formatDateTime(dashboard.data.latest_timing_run.performed_at)}
                  </span>
                </div>
                <TimingTable timing={dashboard.data.latest_timing} />
              </div>
            ) : (
              <EmptyState
                icon={Activity}
                title="No measurements recorded"
                description="Record a timegrapher run on the Testing page."
                className="py-6"
              />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader eyebrow="Quality" title="Open engineering issues" />
          <CardContent>
            <EmptyState
              icon={GitBranch}
              title="No engineering changes or issues"
              description="Engineering change records arrive in slice 12."
              className="py-6"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StateBars({ counts, total }: { counts: Record<string, number>; total: number }) {
  return (
    <ul className="flex flex-col gap-1.5">
      {LIFECYCLE_STATES.map((state) => {
        const count = counts[state] ?? 0;
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        return (
          <li key={state} className="grid grid-cols-[6.5rem_1fr_2.5rem] items-center gap-2 text-xs">
            <Link
              to={`/components?state=${state}`}
              className="text-fg-muted hover:text-fg hover:underline"
            >
              {titleCase(state)}
            </Link>
            <div className="h-1.5 overflow-hidden rounded-sm bg-surface-2">
              <div className="h-full bg-steel/70" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-right font-mono text-fg">{count}</span>
          </li>
        );
      })}
    </ul>
  );
}

function ActivePrototype({ prototype }: { prototype: PrototypeSummary }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-3">
        <span className="flex items-center gap-2">
          <Identifier value={prototype.identifier} to={`/prototypes/${prototype.identifier}`} />
          <span className="text-sm text-fg">{prototype.name}</span>
          <PlaceholderBadge show={prototype.is_placeholder} />
        </span>
        <PrototypeStatusBadge status={prototype.status} />
      </div>
      <Link
        to={`/prototypes/${prototype.identifier}`}
        className="text-xs text-fg-muted hover:text-fg hover:underline"
      >
        Open configuration and build log
      </Link>
    </div>
  );
}
