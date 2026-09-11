import { ListTree } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import { useComponents } from "@/lib/queries";

export function BomsPage() {
  const assemblies = useComponents({ kind: "ASSEMBLY" });
  const navigate = useNavigate();

  return (
    <div>
      <PageHeader
        eyebrow="Product definition"
        title="Bills of materials"
        description="Every assembly revision carries its own design BOM. Lines reference child components and may pin an exact child revision; unpinned lines resolve to the latest or released revision when viewed."
      />
      {assemblies.isError ? <ErrorNotice error={assemblies.error} /> : null}
      <Card>
        {assemblies.isLoading ? (
          <LoadingRows rows={6} />
        ) : assemblies.data && assemblies.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-36">Assembly</TH>
                <TH>Name</TH>
                <TH className="w-20">Family</TH>
                <TH className="w-44">Latest revision</TH>
                <TH className="w-24">Released</TH>
                <TH className="w-28">Updated</TH>
              </TR>
            </THead>
            <TBody>
              {assemblies.data.items.map((a) => (
                <TR key={a.id} interactive onClick={() => navigate(`/boms/${a.identifier}`)}>
                  <TD>
                    <Identifier value={a.identifier} />
                  </TD>
                  <TD className="font-medium">
                    <span className="inline-flex items-center gap-2">
                      {a.name}
                      <PlaceholderBadge show={a.is_placeholder} />
                    </span>
                  </TD>
                  <TD mono className="text-fg-muted">
                    {a.family}
                  </TD>
                  <TD>
                    {a.latest_revision ? (
                      <span className="inline-flex items-center gap-1.5">
                        <Identifier value={`Rev ${a.latest_revision.revision_label}`} />
                        <LifecycleBadge state={a.latest_revision.lifecycle_state} />
                      </span>
                    ) : (
                      "—"
                    )}
                  </TD>
                  <TD mono className="text-fg-muted">
                    {a.released_revision ? `Rev ${a.released_revision.revision_label}` : "—"}
                  </TD>
                  <TD className="text-fg-subtle">{formatDate(a.updated_at)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={ListTree}
            title="No assemblies"
            description="Create a component of kind Assembly to start a BOM."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}
