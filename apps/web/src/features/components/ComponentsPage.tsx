import {
  COMPONENT_FAMILIES,
  COMPONENT_KINDS,
  LIFECYCLE_STATES,
  type ComponentFamily,
  type ComponentKind,
  type LifecycleState,
} from "@nemeth/domain-types";
import { Box, Plus } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  Identifier,
  KindBadge,
  LifecycleBadge,
  PlaceholderBadge,
} from "@/components/domain/badges";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatDate, titleCase } from "@/lib/format";
import { useComponents } from "@/lib/queries";

export function ComponentsPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const filters = {
    q: params.get("q") ?? "",
    family: (params.get("family") as ComponentFamily | null) ?? undefined,
    kind: (params.get("kind") as ComponentKind | null) ?? undefined,
    state: (params.get("state") as LifecycleState | null) ?? undefined,
  };
  const components = useComponents(filters);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  return (
    <div>
      <PageHeader
        eyebrow="Product definition"
        title="Components"
        description="Every engineered item, identified once and revised forever. Content lives on revisions; identity lives here."
        actions={
          <Button variant="primary" onClick={() => navigate("/components/new")}>
            <Plus className="h-3.5 w-3.5" /> New component
          </Button>
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search identifier or name"
          value={filters.q}
          onChange={(e) => setFilter("q", e.target.value)}
          className="w-64"
          aria-label="Search"
        />
        <Select
          value={filters.family ?? ""}
          onChange={(e) => setFilter("family", e.target.value)}
          className="w-36"
          aria-label="Family"
        >
          <option value="">All families</option>
          {COMPONENT_FAMILIES.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </Select>
        <Select
          value={filters.kind ?? ""}
          onChange={(e) => setFilter("kind", e.target.value)}
          className="w-36"
          aria-label="Kind"
        >
          <option value="">Parts and assemblies</option>
          {COMPONENT_KINDS.map((k) => (
            <option key={k} value={k}>
              {titleCase(k)}
            </option>
          ))}
        </Select>
        <Select
          value={filters.state ?? ""}
          onChange={(e) => setFilter("state", e.target.value)}
          className="w-40"
          aria-label="State"
        >
          <option value="">Any state</option>
          {LIFECYCLE_STATES.map((s) => (
            <option key={s} value={s}>
              {titleCase(s)}
            </option>
          ))}
        </Select>
        {components.data ? (
          <span className="ml-auto font-mono text-xs text-fg-subtle">
            {components.data.total} components
          </span>
        ) : null}
      </div>

      {components.isError ? <ErrorNotice error={components.error} /> : null}

      <Card>
        {components.isLoading ? (
          <LoadingRows rows={8} />
        ) : components.data && components.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-36">Identifier</TH>
                <TH>Name</TH>
                <TH className="w-24">Kind</TH>
                <TH className="w-20">Family</TH>
                <TH className="w-44">Latest revision</TH>
                <TH className="w-24">Released</TH>
                <TH className="w-14" align="right">
                  Revs
                </TH>
                <TH className="w-28">Updated</TH>
              </TR>
            </THead>
            <TBody>
              {components.data.items.map((c) => (
                <TR key={c.id} interactive onClick={() => navigate(`/components/${c.identifier}`)}>
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
                    <KindBadge kind={c.kind} />
                  </TD>
                  <TD mono className="text-fg-muted">
                    {c.family}
                  </TD>
                  <TD>
                    {c.latest_revision ? (
                      <span className="inline-flex items-center gap-1.5">
                        <Identifier value={`Rev ${c.latest_revision.revision_label}`} />
                        <LifecycleBadge state={c.latest_revision.lifecycle_state} />
                      </span>
                    ) : (
                      "—"
                    )}
                  </TD>
                  <TD mono className="text-fg-muted">
                    {c.released_revision ? `Rev ${c.released_revision.revision_label}` : "—"}
                  </TD>
                  <TD align="right" mono>
                    {c.revision_count}
                  </TD>
                  <TD className="text-fg-subtle">{formatDate(c.updated_at)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={Box}
            title="No components match"
            description="Adjust the filters, or create the first component."
            action={
              <Link to="/components/new" className="text-accent hover:underline">
                New component
              </Link>
            }
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}
