import { PROTOTYPE_STATUSES, type PrototypeRead, type PrototypeStatus } from "@nemeth/domain-types";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AttachmentsPanel } from "@/components/domain/AttachmentsPanel";
import { Identifier, PlaceholderBadge } from "@/components/domain/badges";
import { PrototypeStatusBadge } from "@/components/domain/prototypeBadges";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { FormError, Select } from "@/components/ui/form";
import { ErrorNotice, KV, LoadingRows, PageHeader, Stat } from "@/components/ui/layout";
import { ExperimentsPanel } from "@/features/prototypes/ExperimentsPanel";
import { PrototypeTestRunsPanel } from "@/features/testing/TestRunsPanel";
import { BuildLogPanel, ConfigurationPanel, NewBuildForm } from "@/features/units/BuildPanels";
import { describeError } from "@/lib/api";
import { formatDate, formatDateTime, titleCase } from "@/lib/format";
import {
  useBuildRecords,
  useCreateBuildRecord,
  usePrototype,
  usePrototypeConfiguration,
  useUpdatePrototype,
} from "@/lib/prototypeQueries";

export function PrototypeDetailPage() {
  const { ref = "" } = useParams();
  const prototype = usePrototype(ref);
  const configuration = usePrototypeConfiguration(ref);
  const builds = useBuildRecords(ref);
  const createBuild = useCreateBuildRecord(ref);

  if (prototype.isLoading) return <LoadingRows />;
  if (prototype.isError) return <ErrorNotice error={prototype.error} />;
  if (!prototype.data) return null;
  const p = prototype.data;

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/prototypes" className="hover:underline">
              Prototypes
            </Link>{" "}
            / {p.identifier}
          </span>
        }
        title={
          <>
            <Identifier value={p.identifier} className="text-xl" />
            <span>{p.name}</span>
          </>
        }
        description={p.purpose}
        meta={
          <>
            <PrototypeStatusBadge status={p.status} />
            <PlaceholderBadge show={p.is_placeholder} />
          </>
        }
        actions={<StatusControl prototype={p} />}
      />

      <div className="mb-4 grid gap-2 sm:grid-cols-4">
        <Stat label="Installed parts" value={p.installed_count} />
        <Stat label="Build records" value={p.build_count} />
        <Stat
          label="Model"
          value={
            p.product_model ? (
              <Identifier
                value={p.product_model.identifier}
                to={`/products/${p.product_model.identifier.split(".")[0] ?? ""}`}
              />
            ) : (
              "—"
            )
          }
        />
        <Stat
          label="Caliber"
          value={
            p.caliber ? (
              <Identifier value={p.caliber.identifier} to={`/calibers/${p.caliber.identifier}`} />
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
          {p.status !== "RETIRED" ? (
            <NewBuildForm unitKind="prototype" unitId={p.id} create={createBuild} />
          ) : null}
          <ExperimentsPanel prototypeRef={p.identifier} />
          <PrototypeTestRunsPanel prototypeRef={p.identifier} />
          <AttachmentsPanel entityType="prototype" entityId={p.id} defaultKind="PHOTO" />
        </div>
        <Card className="self-start">
          <CardHeader eyebrow="Record" title="Details" />
          <CardContent>
            <KV
              columns={1}
              items={[
                { label: "Started", value: formatDate(p.started_on) },
                { label: "Retired", value: formatDate(p.retired_on) },
                { label: "Notes", value: p.notes },
                { label: "Created", value: `${formatDateTime(p.created_at)} · ${p.created_by}` },
                { label: "Updated", value: `${formatDateTime(p.updated_at)} · ${p.updated_by}` },
                { label: "Internal id", value: p.id, mono: true },
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatusControl({ prototype }: { prototype: PrototypeRead }) {
  const update = useUpdatePrototype(prototype.identifier);
  const [error, setError] = useState<string | null>(null);
  const currentIndex = PROTOTYPE_STATUSES.indexOf(prototype.status);
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        <span className="label">Status</span>
        <Select
          value={prototype.status}
          onChange={(e) => {
            setError(null);
            update.mutate(
              { status: e.target.value as PrototypeStatus },
              { onError: (err) => setError(describeError(err)) },
            );
          }}
          className="w-36"
          aria-label="Prototype status"
          disabled={update.isPending}
        >
          {PROTOTYPE_STATUSES.map((s, i) => (
            <option key={s} value={s} disabled={i < currentIndex}>
              {titleCase(s)}
            </option>
          ))}
        </Select>
      </div>
      <FormError message={error} />
    </div>
  );
}
