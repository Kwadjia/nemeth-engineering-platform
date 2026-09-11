import { Identifier } from "@/components/domain/badges";
import { InstanceStatusBadge, SourceBadge } from "@/components/domain/prototypeBadges";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, LoadingRows } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import { useComponentPartInstances } from "@/lib/prototypeQueries";

/** Physical parts made to any revision of this component, and where they are now. */
export function PartInstancesPanel({ componentRef }: { componentRef: string }) {
  const instances = useComponentPartInstances(componentRef);
  return (
    <Card>
      <CardHeader eyebrow="Physical traceability" title="Part instances" />
      {instances.isLoading ? (
        <LoadingRows rows={2} />
      ) : instances.data && instances.data.length > 0 ? (
        <Table>
          <THead>
            <TR>
              <TH className="w-24">Part</TH>
              <TH className="w-20">Rev</TH>
              <TH className="w-24">Status</TH>
              <TH className="w-24">Source</TH>
              <TH className="w-28">Serial</TH>
              <TH className="w-28">Lot</TH>
              <TH className="w-28">Installed in</TH>
              <TH className="w-28">Recorded</TH>
            </TR>
          </THead>
          <TBody>
            {instances.data.map((i) => (
              <TR key={i.id}>
                <TD>
                  <Identifier value={i.identifier} to={`/part-instances?q=${i.identifier}`} />
                </TD>
                <TD mono>Rev {i.revision.revision_label}</TD>
                <TD>
                  <InstanceStatusBadge status={i.status} />
                </TD>
                <TD>
                  <SourceBadge source={i.source} />
                </TD>
                <TD mono className="text-fg-muted">
                  {i.serial_number ?? "—"}
                </TD>
                <TD mono className="text-fg-muted">
                  {i.lot ?? "—"}
                </TD>
                <TD>
                  {i.current_prototype ? (
                    <Identifier
                      value={i.current_prototype.identifier}
                      to={`/prototypes/${i.current_prototype.identifier}`}
                    />
                  ) : (
                    <span className="text-fg-subtle">—</span>
                  )}
                </TD>
                <TD className="text-fg-subtle">{formatDate(i.created_at)}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      ) : (
        <CardContent>
          <EmptyState
            title="No physical parts recorded"
            description="Freeze a revision (Prototype or later) and record part instances against it."
            className="py-6"
          />
        </CardContent>
      )}
    </Card>
  );
}
