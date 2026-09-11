import { Package } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Identifier, LifecycleBadge, PlaceholderBadge } from "@/components/domain/badges";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import { useProducts } from "@/lib/queries";

export function ProductsPage() {
  const products = useProducts();
  const navigate = useNavigate();

  return (
    <div>
      <PageHeader
        eyebrow="Product definition"
        title="Products"
        description="Marketable product lines. Each product has one or more references (models) that choose a caliber and a top-level watch assembly."
      />
      {products.isError ? <ErrorNotice error={products.error} /> : null}
      <Card>
        {products.isLoading ? (
          <LoadingRows />
        ) : products.data && products.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-28">Product</TH>
                <TH>Name</TH>
                <TH className="w-28">State</TH>
                <TH className="w-20" align="right">
                  Models
                </TH>
                <TH>Description</TH>
                <TH className="w-32">Updated</TH>
              </TR>
            </THead>
            <TBody>
              {products.data.items.map((p) => (
                <TR key={p.id} interactive onClick={() => navigate(`/products/${p.identifier}`)}>
                  <TD>
                    <Identifier value={p.identifier} />
                  </TD>
                  <TD className="font-medium">
                    <span className="inline-flex items-center gap-2">
                      {p.name}
                      <PlaceholderBadge show={p.is_placeholder} />
                    </span>
                  </TD>
                  <TD>
                    <LifecycleBadge state={p.lifecycle_state} />
                  </TD>
                  <TD align="right" mono>
                    {p.models.length}
                  </TD>
                  <TD className="max-w-lg truncate text-fg-muted">{p.description ?? "—"}</TD>
                  <TD className="text-fg-subtle">{formatDate(p.updated_at)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={Package}
            title="No products"
            description="Run the N1 seed or create a product through the API."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}
