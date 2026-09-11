import { Cog } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatNumber } from "@/lib/format";
import { useCalibers } from "@/lib/queries";

export function CalibersPage() {
  const calibers = useCalibers();
  const navigate = useNavigate();

  return (
    <div>
      <PageHeader
        eyebrow="Product definition"
        title="Calibers"
        description="Mechanical movements as first-class engineered products. Each caliber owns a movement assembly whose BOM is the caliber's BOM."
      />
      {calibers.isError ? <ErrorNotice error={calibers.error} /> : null}
      <Card>
        {calibers.isLoading ? (
          <LoadingRows />
        ) : calibers.data && calibers.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-28">Caliber</TH>
                <TH>Name</TH>
                <TH className="w-28">State</TH>
                <TH className="w-24" align="right">
                  Ø mm
                </TH>
                <TH className="w-24" align="right">
                  bph
                </TH>
                <TH className="w-20" align="right">
                  Jewels
                </TH>
                <TH className="w-24" align="right">
                  PR h
                </TH>
                <TH className="w-40">Root assembly</TH>
              </TR>
            </THead>
            <TBody>
              {calibers.data.items.map((c) => (
                <TR key={c.id} interactive onClick={() => navigate(`/calibers/${c.identifier}`)}>
                  <TD>
                    <Identifier value={c.identifier} />
                  </TD>
                  <TD className="font-medium">
                    <span className="inline-flex items-center gap-2">
                      {c.name}
                      <PlaceholderBadge show={c.is_placeholder} />
                    </span>
                  </TD>
                  <TD>
                    <LifecycleBadge state={c.lifecycle_state} />
                  </TD>
                  <TD align="right" mono>
                    {formatNumber(c.diameter_mm)}
                  </TD>
                  <TD align="right" mono>
                    {formatNumber(c.frequency_bph)}
                  </TD>
                  <TD align="right" mono>
                    {formatNumber(c.jewel_count)}
                  </TD>
                  <TD align="right" mono>
                    {formatNumber(c.power_reserve_hours)}
                  </TD>
                  <TD>
                    {c.root_component ? (
                      <Identifier value={c.root_component.identifier} />
                    ) : (
                      <span className="text-fg-subtle">—</span>
                    )}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={Cog}
            title="No calibers"
            description="Run the N1 seed or create a caliber through the API."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}
