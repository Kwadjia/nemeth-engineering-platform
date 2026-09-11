import type { BomFlat } from "@nemeth/domain-types";

import { Identifier, KindBadge, LifecycleBadge, PinnedBadge } from "@/components/domain/badges";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatQuantity } from "@/lib/format";

/** Indented (multi-level) BOM listing with extended quantities. */
export function BomFlatTable({ flat }: { flat: BomFlat }) {
  return (
    <Table>
      <THead>
        <TR>
          <TH className="w-12" align="right">
            Lvl
          </TH>
          <TH className="w-14" align="right">
            Find
          </TH>
          <TH>Component</TH>
          <TH>Name</TH>
          <TH className="w-24">Kind</TH>
          <TH className="w-16" align="right">
            Qty
          </TH>
          <TH className="w-20" align="right">
            Ext. qty
          </TH>
          <TH className="w-52">Revision</TH>
          <TH>Path</TH>
        </TR>
      </THead>
      <TBody>
        {flat.rows.map((row, i) => (
          <TR key={`${row.path.join("/")}-${i}`}>
            <TD align="right" mono className="text-fg-subtle">
              {row.level}
            </TD>
            <TD align="right" mono className="text-fg-subtle">
              {row.find_number}
            </TD>
            <TD>
              <span style={{ paddingLeft: (row.level - 1) * 14 }}>
                <Identifier
                  value={row.component.identifier}
                  to={`/components/${row.component.identifier}`}
                />
              </span>
            </TD>
            <TD>{row.component.name}</TD>
            <TD>
              <KindBadge kind={row.component.kind} />
            </TD>
            <TD align="right" mono>
              {formatQuantity(row.quantity)}
            </TD>
            <TD align="right" mono className="text-fg">
              {formatQuantity(row.extended_quantity)}
            </TD>
            <TD>
              {row.revision ? (
                <span className="inline-flex items-center gap-1.5">
                  <Identifier value={`Rev ${row.revision.revision_label}`} />
                  <LifecycleBadge state={row.revision.lifecycle_state} />
                  <PinnedBadge pinned={row.is_pinned} />
                </span>
              ) : (
                <span className="text-xs text-warn">Unresolved</span>
              )}
            </TD>
            <TD mono className="text-fg-subtle">
              {row.path.slice(0, -1).join(" › ")}
            </TD>
          </TR>
        ))}
      </TBody>
    </Table>
  );
}
