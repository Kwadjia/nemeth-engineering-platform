import type {
  BomNode,
  BomTree as BomTreeData,
  ComponentSummary,
  RevisionSummary,
} from "@nemeth/domain-types";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { BomTree } from "./BomTree";

function component(identifier: string, kind: "PART" | "ASSEMBLY" = "PART"): ComponentSummary {
  return {
    id: identifier,
    identifier,
    name: `Name ${identifier}`,
    kind,
    family: "MVT",
    is_placeholder: false,
  };
}

function revision(
  label: string,
  state: RevisionSummary["lifecycle_state"] = "CONCEPT",
): RevisionSummary {
  return {
    id: `rev-${label}`,
    revision_number: 1,
    revision_label: label,
    lifecycle_state: state,
    is_frozen: false,
    frozen_at: null,
    change_summary: null,
    created_at: "2026-09-11T00:00:00Z",
  };
}

function node(
  child: ComponentSummary,
  opts: Partial<BomNode> & { find: number; pinned?: boolean; qty?: string } = { find: 10 },
): BomNode {
  return {
    line: {
      id: `line-${child.identifier}`,
      parent_revision_id: "parent",
      find_number: opts.find,
      quantity: opts.qty ?? "1",
      unit: "ea",
      reference_designator: null,
      notes: null,
      is_pinned: opts.pinned ?? false,
      child_component: child,
      child_revision: opts.pinned ? revision("A") : null,
      created_at: "2026-09-11T00:00:00Z",
      created_by: "test",
      updated_at: "2026-09-11T00:00:00Z",
      updated_by: "test",
    },
    resolved_revision:
      opts.resolved_revision === undefined ? revision("A") : opts.resolved_revision,
    resolution: opts.resolution ?? (opts.pinned ? "pinned" : "latest"),
    level: opts.level ?? 1,
    children: opts.children ?? [],
  };
}

const tree: BomTreeData = {
  root_component: component("N1-MVT-001", "ASSEMBLY"),
  root_revision: revision("A"),
  mode: "latest",
  line_count: 3,
  unresolved_count: 1,
  max_depth: 2,
  nodes: [
    node(component("N1-MVT-002"), { find: 10 }),
    node(component("N1-MVT-007", "ASSEMBLY"), {
      find: 20,
      children: [
        node(component("N1-MVT-008"), { find: 10, level: 2, pinned: true, qty: "2.0000" }),
        node(component("N1-MVT-011"), {
          find: 20,
          level: 2,
          resolved_revision: null,
          resolution: "unresolved",
        }),
      ],
    }),
  ],
};

function renderTree(props: Partial<React.ComponentProps<typeof BomTree>> = {}) {
  return render(
    <MemoryRouter>
      <BomTree tree={tree} {...props} />
    </MemoryRouter>,
  );
}

describe("BomTree", () => {
  it("renders nested assemblies with their children expanded by default", () => {
    renderTree();
    expect(screen.getByText("N1-MVT-002")).toBeInTheDocument();
    expect(screen.getByText("N1-MVT-007")).toBeInTheDocument();
    expect(screen.getByText("N1-MVT-008")).toBeInTheDocument();
    expect(screen.getByText("N1-MVT-011")).toBeInTheDocument();
  });

  it("shows pins, trimmed quantities and unresolved children explicitly", () => {
    renderTree();
    expect(screen.getByText("Pinned")).toBeInTheDocument();
    expect(screen.getByTestId("bom-row-N1-MVT-008")).toHaveTextContent("2");
    expect(screen.getByTestId("bom-row-N1-MVT-008")).not.toHaveTextContent("2.0000");
    expect(screen.getByText("Unresolved")).toBeInTheDocument();
  });

  it("collapses a sub-assembly on click", () => {
    renderTree();
    fireEvent.click(screen.getByLabelText("Collapse"));
    expect(screen.queryByText("N1-MVT-008")).not.toBeInTheDocument();
    expect(screen.getByText("N1-MVT-007")).toBeInTheDocument();
  });

  it("only offers removal for top-level lines when editable", () => {
    const onRemoveLine = vi.fn();
    renderTree({ onRemoveLine });
    fireEvent.click(screen.getByLabelText("Remove N1-MVT-002"));
    expect(onRemoveLine).toHaveBeenCalledWith("line-N1-MVT-002");
    expect(screen.queryByLabelText("Remove N1-MVT-008")).not.toBeInTheDocument();
  });
});
