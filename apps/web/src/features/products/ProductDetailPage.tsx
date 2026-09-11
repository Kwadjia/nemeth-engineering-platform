import { Link, useParams } from "react-router-dom";

import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { BomTree } from "@/components/domain/BomTree";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorNotice, KV, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatDateTime } from "@/lib/format";
import { useModelBom, useProduct, useProductModels } from "@/lib/queries";

export function ProductDetailPage() {
  const { ref = "" } = useParams();
  const product = useProduct(ref);
  const models = useProductModels(ref);
  const firstModel = models.data?.[0];
  const bom = useModelBom(firstModel?.identifier ?? "", "latest");

  if (product.isLoading) return <LoadingRows />;
  if (product.isError) return <ErrorNotice error={product.error} />;
  if (!product.data) return null;
  const p = product.data;

  return (
    <div>
      <PageHeader
        eyebrow={
          <span>
            <Link to="/products" className="hover:underline">
              Products
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
        description={p.description}
        meta={
          <>
            <LifecycleBadge state={p.lifecycle_state} />
            <PlaceholderBadge show={p.is_placeholder} />
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader eyebrow="References" title="Models" />
          {models.isLoading ? (
            <LoadingRows />
          ) : models.data && models.data.length > 0 ? (
            <Table>
              <THead>
                <TR>
                  <TH className="w-24">Model</TH>
                  <TH>Name</TH>
                  <TH className="w-28">State</TH>
                  <TH className="w-32">Caliber</TH>
                  <TH className="w-40">Root assembly</TH>
                </TR>
              </THead>
              <TBody>
                {models.data.map((m) => (
                  <TR key={m.id}>
                    <TD>
                      <Identifier value={m.identifier} />
                    </TD>
                    <TD className="font-medium">
                      <span className="inline-flex items-center gap-2">
                        {m.name}
                        <PlaceholderBadge show={m.is_placeholder} />
                      </span>
                    </TD>
                    <TD>
                      <LifecycleBadge state={m.lifecycle_state} />
                    </TD>
                    <TD>
                      {m.caliber ? (
                        <Identifier
                          value={m.caliber.identifier}
                          to={`/calibers/${m.caliber.identifier}`}
                        />
                      ) : (
                        <span className="text-fg-subtle">—</span>
                      )}
                    </TD>
                    <TD>
                      {m.root_component ? (
                        <Identifier
                          value={m.root_component.identifier}
                          to={`/boms/${m.root_component.identifier}`}
                        />
                      ) : (
                        <span className="text-fg-subtle">—</span>
                      )}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          ) : (
            <CardContent>
              <EmptyState
                title="No models"
                description="Add a reference through the API (POST /products/{id}/models)."
              />
            </CardContent>
          )}
        </Card>

        <Card>
          <CardHeader eyebrow="Record" title="Details" />
          <CardContent>
            <KV
              columns={1}
              items={[
                { label: "Notes", value: p.notes },
                { label: "Created", value: `${formatDateTime(p.created_at)} · ${p.created_by}` },
                { label: "Updated", value: `${formatDateTime(p.updated_at)} · ${p.updated_by}` },
                { label: "Internal id", value: p.id, mono: true },
              ]}
            />
          </CardContent>
        </Card>

        {firstModel ? (
          <Card className="xl:col-span-3">
            <CardHeader
              eyebrow={`Design BOM · ${firstModel.identifier} · latest revisions`}
              title={
                firstModel.root_component
                  ? `${firstModel.root_component.identifier} ${firstModel.root_component.name}`
                  : "Root assembly"
              }
              actions={
                firstModel.root_component ? (
                  <Link
                    to={`/boms/${firstModel.root_component.identifier}`}
                    className="text-xs text-fg-muted hover:text-fg hover:underline"
                  >
                    Open BOM explorer
                  </Link>
                ) : null
              }
            />
            {bom.isLoading ? (
              <LoadingRows />
            ) : bom.isError ? (
              <CardContent>
                <EmptyState
                  title="No root assembly"
                  description="Assign a root assembly component to the model to see its BOM."
                />
              </CardContent>
            ) : bom.data ? (
              <BomTree tree={bom.data} />
            ) : null}
          </Card>
        ) : null}
      </div>
    </div>
  );
}
