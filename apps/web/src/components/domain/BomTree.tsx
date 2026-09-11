import type { BomNode, BomTree as BomTreeData } from "@nemeth/domain-types";
import { ChevronDown, ChevronRight, CircleAlert, Trash2 } from "lucide-react";
import { useState } from "react";

import { Identifier, KindBadge, LifecycleBadge, PinnedBadge } from "@/components/domain/badges";
import { Button } from "@/components/ui/button";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatQuantity } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface BomTreeProps {
  tree: BomTreeData;
  /** Called with the line id; only rendered when provided (i.e. the parent is editable). */
  onRemoveLine?: (lineId: string) => void;
  removing?: boolean;
}

/** Recursive, indented BOM with per-node resolution details. */
export function BomTree({ tree, onRemoveLine, removing }: BomTreeProps) {
  return (
    <Table data-testid="bom-tree">
      <THead>
        <TR>
          <TH className="w-14" align="right">
            Find
          </TH>
          <TH>Component</TH>
          <TH>Name</TH>
          <TH className="w-24">Kind</TH>
          <TH className="w-16" align="right">
            Qty
          </TH>
          <TH className="w-56">Resolved revision</TH>
          <TH className="w-28">Via</TH>
          {onRemoveLine ? <TH className="w-10" /> : null}
        </TR>
      </THead>
      <TBody>
        {tree.nodes.length === 0 ? (
          <TR>
            <TD colSpan={onRemoveLine ? 8 : 7} className="py-6 text-center text-fg-subtle">
              No BOM lines on this revision yet.
            </TD>
          </TR>
        ) : (
          tree.nodes.map((node) => (
            <BomRow
              key={node.line.id}
              node={node}
              onRemoveLine={onRemoveLine}
              removing={removing}
            />
          ))
        )}
      </TBody>
    </Table>
  );
}

function BomRow({
  node,
  onRemoveLine,
  removing,
}: {
  node: BomNode;
  onRemoveLine?: (lineId: string) => void;
  removing?: boolean;
}) {
  const [open, setOpen] = useState(true);
  const hasChildren = node.children.length > 0;
  const child = node.line.child_component;
  const unresolved = node.resolution === "unresolved";
  const indent = (node.level - 1) * 18;

  return (
    <>
      <TR className={cn(unresolved && "bg-warn/5")} data-testid={`bom-row-${child.identifier}`}>
        <TD align="right" mono className="text-fg-subtle">
          {node.line.find_number}
        </TD>
        <TD>
          <div className="flex items-center gap-1" style={{ paddingLeft: indent }}>
            {hasChildren ? (
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className="-ml-1 rounded p-0.5 text-fg-subtle hover:bg-surface-2 hover:text-fg"
                aria-label={open ? "Collapse" : "Expand"}
              >
                {open ? (
                  <ChevronDown className="h-3.5 w-3.5" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" />
                )}
              </button>
            ) : (
              <span className="inline-block w-4" />
            )}
            <Identifier value={child.identifier} to={`/components/${child.identifier}`} />
          </div>
        </TD>
        <TD className="text-fg">
          {child.name}
          {node.line.reference_designator ? (
            <span className="ml-2 text-xs text-fg-subtle">{node.line.reference_designator}</span>
          ) : null}
        </TD>
        <TD>
          <KindBadge kind={child.kind} />
        </TD>
        <TD align="right" mono>
          {formatQuantity(node.line.quantity)}
          {node.line.unit !== "ea" ? (
            <span className="ml-1 text-fg-subtle">{node.line.unit}</span>
          ) : null}
        </TD>
        <TD>
          {node.resolved_revision ? (
            <span className="inline-flex items-center gap-1.5">
              <Identifier
                value={`Rev ${node.resolved_revision.revision_label}`}
                to={`/components/${child.identifier}/revisions/${node.resolved_revision.revision_label}`}
              />
              <LifecycleBadge state={node.resolved_revision.lifecycle_state} />
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-xs text-warn">
              <CircleAlert className="h-3.5 w-3.5" /> Unresolved
            </span>
          )}
        </TD>
        <TD>
          {node.resolution === "pinned" ? (
            <PinnedBadge pinned />
          ) : (
            <span className="font-mono text-2xs uppercase tracking-label text-fg-subtle">
              {node.resolution}
            </span>
          )}
        </TD>
        {onRemoveLine ? (
          <TD align="right">
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Remove ${child.identifier}`}
              disabled={removing}
              onClick={() => onRemoveLine(node.line.id)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </TD>
        ) : null}
      </TR>
      {open && hasChildren
        ? node.children.map((c) => <BomRow key={c.line.id} node={c} removing={removing} />)
        : null}
    </>
  );
}
