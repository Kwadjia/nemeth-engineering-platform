import { type WatchRead, type WatchStatus } from "@nemeth/domain-types";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Identifier, PlaceholderBadge } from "@/components/domain/badges";
import { ExperimentStatusBadge, OutcomeBadge } from "@/components/domain/experimentBadges";
import { PrototypeStatusBadge } from "@/components/domain/prototypeBadges";
import { TimingTable } from "@/components/domain/TimingTable";
import { WatchStatusBadge } from "@/components/domain/watchBadges";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select } from "@/components/ui/form";
import { EmptyState, ErrorNotice, KV, LoadingRows, PageHeader, Stat } from "@/components/ui/layout";
import { TestRunsTable } from "@/features/testing/TestRunsTable";
import { BuildLogPanel, ConfigurationPanel, NewBuildForm } from "@/features/units/BuildPanels";
import { describeError } from "@/lib/api";
import { formatDate, formatDateTime, formOptional, titleCase } from "@/lib/format";
import { useWatchTestRuns } from "@/lib/testingQueries";
import {
  useCreateWatchBuild,
  useUpdateWatch,
  useWatchBuilds,
  useWatchConfiguration,
  useWatchDossier,
} from "@/lib/watchQueries";

const STATUSES: WatchStatus[] = [
  "PLANNED",
  "IN_BUILD",
  "BUILT",
  "PERSONAL_PROTOTYPE",
  "DELIVERED",
  "IN_SERVICE",
  "RETIRED",
];

export function WatchDetailPage() {
  const { ref = "" } = useParams();
  const dossier = useWatchDossier(ref);
  const configuration = useWatchConfiguration(ref);
  const builds = useWatchBuilds(ref);
  const runs = useWatchTestRuns(ref);
  const createBuild = useCreateWatchBuild(ref);

  if (dossier.isLoading) return <LoadingRows />;
  if (dossier.isError) return <ErrorNotice error={dossier.error} />;
  if (!dossier.data) return null;
  const d = dossier.data;
  const w = d.watch;

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/watches" className="hover:underline">
              Watches
            </Link>{" "}
            / {w.identifier}
          </span>
        }
        title={
          <>
            <Identifier value={w.identifier} className="text-xl" />
            <span>
              {d.product.name} · {d.model.identifier}
            </span>
          </>
        }
        description={w.notes}
        meta={
          <>
            <WatchStatusBadge status={w.status} />
            <PlaceholderBadge show={w.is_placeholder} />
            {w.owner_name ? (
              <span className="text-xs text-fg-subtle">Owner: {w.owner_name}</span>
            ) : null}
          </>
        }
        actions={<OwnerAndStatus watch={w} />}
      />

      <div className="mb-4 grid gap-2 sm:grid-cols-5">
        <Stat label="Serial" value={w.serial_number} />
        <Stat label="Installed parts" value={w.installed_count} />
        <Stat label="Build records" value={w.build_count} />
        <Stat
          label="Caliber"
          value={
            d.caliber ? (
              <Identifier value={d.caliber.identifier} to={`/calibers/${d.caliber.identifier}`} />
            ) : (
              "—"
            )
          }
        />
        <Stat
          label="Origin prototype"
          value={
            d.origin_prototype ? (
              <span className="inline-flex items-center gap-2">
                <Identifier
                  value={d.origin_prototype.identifier}
                  to={`/prototypes/${d.origin_prototype.identifier}`}
                />
                <PrototypeStatusBadge status={d.origin_prototype.status} />
              </span>
            ) : (
              "—"
            )
          }
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="grid gap-4 xl:col-span-2">
          <ConfigurationPanel configuration={configuration} />
          <BuildLogPanel builds={builds} />
          {w.status !== "RETIRED" ? (
            <NewBuildForm unitKind="watch" unitId={w.id} create={createBuild} />
          ) : null}
          <Card>
            <CardHeader eyebrow="Latest timegrapher run" title="Timing" />
            <CardContent>
              {d.latest_timing ? (
                <div className="grid gap-3">
                  {d.latest_timing_run ? (
                    <div className="flex items-center gap-2 text-xs text-fg-muted">
                      <Identifier
                        value={d.latest_timing_run.identifier}
                        to={`/testing/${d.latest_timing_run.identifier}`}
                      />
                      <span className="text-fg-subtle">
                        {formatDateTime(d.latest_timing_run.performed_at)}
                      </span>
                    </div>
                  ) : null}
                  <TimingTable timing={d.latest_timing} />
                </div>
              ) : (
                <EmptyState
                  title="No timegrapher run yet"
                  description="Record one from the Testing page."
                  className="py-6"
                />
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader
              eyebrow="Testing"
              title="Test runs"
              actions={
                <Link
                  to={`/testing?new=1&watch=${w.identifier}`}
                  className="text-xs text-fg-muted hover:text-fg hover:underline"
                >
                  New test run
                </Link>
              }
            />
            {runs.isLoading ? (
              <LoadingRows rows={2} />
            ) : runs.data && runs.data.length > 0 ? (
              <TestRunsTable runs={runs.data} showSubject={false} />
            ) : (
              <CardContent>
                <EmptyState title="No test runs on this watch" className="py-6" />
              </CardContent>
            )}
          </Card>
        </div>
        <div className="grid gap-4 self-start">
          <Card>
            <CardHeader eyebrow="Record" title="Details" />
            <CardContent>
              <KV
                columns={1}
                items={[
                  {
                    label: "Product",
                    value: (
                      <Identifier
                        value={d.product.identifier}
                        to={`/products/${d.product.identifier}`}
                      />
                    ),
                  },
                  { label: "Model", value: d.model.name },
                  { label: "Assembled", value: formatDate(w.assembled_on) },
                  { label: "Delivered", value: formatDate(w.delivered_on) },
                  { label: "Created", value: `${formatDateTime(w.created_at)} · ${w.created_by}` },
                  { label: "Updated", value: `${formatDateTime(w.updated_at)} · ${w.updated_by}` },
                  { label: "Internal id", value: w.id, mono: true },
                ]}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader eyebrow="Lineage" title="Experiments" />
            {d.experiments.length > 0 ? (
              <ul className="divide-y divide-border">
                {d.experiments.map((e) => (
                  <li key={e.id} className="flex items-center gap-2 px-4 py-2">
                    <Identifier value={e.identifier} to={`/experiments/${e.identifier}`} />
                    <span className="flex-1 truncate text-xs text-fg-muted">{e.title}</span>
                    <OutcomeBadge outcome={e.outcome} />
                    <ExperimentStatusBadge status={e.status} />
                  </li>
                ))}
              </ul>
            ) : (
              <CardContent>
                <EmptyState
                  title="No experiment lineage"
                  description="Experiments linked to the origin prototype appear here."
                  className="py-6"
                />
              </CardContent>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function OwnerAndStatus({ watch }: { watch: WatchRead }) {
  const update = useUpdateWatch(watch.identifier);
  const [error, setError] = useState<string | null>(null);

  function saveOwner(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    update.mutate(
      {
        owner_name: formOptional(fd, "owner_name"),
        delivered_on: formOptional(fd, "delivered_on"),
      },
      { onError: (err) => setError(describeError(err)) },
    );
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex items-end gap-2">
        <Field label="Status" htmlFor="w-status">
          <Select
            id="w-status"
            value={watch.status}
            className="w-44"
            disabled={update.isPending}
            onChange={(e) => {
              setError(null);
              update.mutate(
                { status: e.target.value as WatchStatus },
                { onError: (err) => setError(describeError(err)) },
              );
            }}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {titleCase(s)}
              </option>
            ))}
          </Select>
        </Field>
        <form onSubmit={saveOwner} className="flex items-end gap-2">
          <Field label="Owner" htmlFor="w-owner">
            <Input
              id="w-owner"
              name="owner_name"
              defaultValue={watch.owner_name ?? ""}
              className="w-40"
            />
          </Field>
          <Field label="Delivered" htmlFor="w-delivered">
            <Input
              id="w-delivered"
              name="delivered_on"
              type="date"
              defaultValue={watch.delivered_on ?? ""}
              className="w-36 font-mono"
            />
          </Field>
          <button
            type="submit"
            className="mb-px h-8 rounded border border-border-strong bg-surface px-3 text-sm text-fg hover:bg-surface-2"
            disabled={update.isPending}
          >
            Save
          </button>
        </form>
      </div>
      <FormError message={error} />
    </div>
  );
}
