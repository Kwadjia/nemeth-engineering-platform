import {
  COMPONENT_FAMILIES,
  COMPONENT_KINDS,
  type ComponentFamily,
  type ComponentKind,
} from "@nemeth/domain-types";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select, Textarea } from "@/components/ui/form";
import { PageHeader } from "@/components/ui/layout";
import { describeError } from "@/lib/api";
import { formOptional as optionalText, formText, titleCase } from "@/lib/format";
import { useCreateComponent } from "@/lib/queries";

function optional(value: FormDataEntryValue | null): string | null {
  const text = typeof value === "string" ? value.trim() : "";
  return text === "" ? null : text;
}

export function ComponentCreatePage() {
  const navigate = useNavigate();
  const create = useCreateComponent();
  const [error, setError] = useState<string | null>(null);
  const [useGenerated, setUseGenerated] = useState(true);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const fd = new FormData(event.currentTarget);
    const identifier = optional(fd.get("identifier"));
    const productCode = optional(fd.get("product_code"));
    if (useGenerated && !productCode) {
      setError("A product code is required to generate an identifier.");
      return;
    }
    if (!useGenerated && !identifier) {
      setError("An explicit identifier is required.");
      return;
    }
    create.mutate(
      {
        identifier: useGenerated ? null : identifier,
        product_code: useGenerated ? productCode : null,
        name: formText(fd, "name"),
        kind: formText(fd, "kind") as ComponentKind,
        family: formText(fd, "family") as ComponentFamily,
        description: optionalText(fd, "description"),
        is_placeholder: fd.get("is_placeholder") === "on",
        change_summary: optional(fd.get("change_summary")) ?? "Initial revision",
        initial_revision: {
          material: optional(fd.get("material")),
          heat_treatment: optional(fd.get("heat_treatment")),
          finish: optional(fd.get("finish")),
          manufacturing_method: optional(fd.get("manufacturing_method")),
          supplier_note: optional(fd.get("supplier_note")),
          inspection_requirements: optional(fd.get("inspection_requirements")),
          notes: optional(fd.get("notes")),
        },
      },
      {
        onSuccess: (component) => navigate(`/components/${component.identifier}`),
        onError: (err) => setError(describeError(err)),
      },
    );
  }

  return (
    <div className="max-w-4xl">
      <PageHeader
        eyebrow={
          <span>
            <Link to="/components" className="hover:underline">
              Components
            </Link>{" "}
            / New
          </span>
        }
        title="New component"
        description="Creates the component identity and its first revision (Rev A, Concept). Engineering content can be edited until the revision is frozen."
      />
      <form onSubmit={onSubmit} className="grid gap-4">
        <Card>
          <CardHeader eyebrow="Identity" title="Component" />
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2 sm:col-span-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="idmode"
                  checked={useGenerated}
                  onChange={() => setUseGenerated(true)}
                />
                Generate identifier from product code and family
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="idmode"
                  checked={!useGenerated}
                  onChange={() => setUseGenerated(false)}
                />
                Use an explicit identifier
              </label>
            </div>
            {useGenerated ? (
              <Field label="Product code" htmlFor="product_code" hint="e.g. N1 → N1-MVT-017">
                <Input
                  id="product_code"
                  name="product_code"
                  defaultValue="N1"
                  className="font-mono uppercase"
                />
              </Field>
            ) : (
              <Field label="Identifier" htmlFor="identifier" hint="Uppercase, A–Z 0–9 . -">
                <Input
                  id="identifier"
                  name="identifier"
                  placeholder="N1-MVT-017"
                  className="font-mono uppercase"
                />
              </Field>
            )}
            <Field label="Name" htmlFor="name">
              <Input id="name" name="name" required placeholder="Escape wheel" />
            </Field>
            <Field label="Kind" htmlFor="kind">
              <Select id="kind" name="kind" defaultValue="PART">
                {COMPONENT_KINDS.map((k) => (
                  <option key={k} value={k}>
                    {titleCase(k)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Family" htmlFor="family">
              <Select id="family" name="family" defaultValue="MVT">
                {COMPONENT_FAMILIES.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Description" htmlFor="description" className="sm:col-span-2">
              <Textarea id="description" name="description" />
            </Field>
            <label className="flex items-center gap-2 text-sm text-fg-muted sm:col-span-2">
              <input type="checkbox" name="is_placeholder" />
              Mark as placeholder / sample data
            </label>
          </CardContent>
        </Card>

        <Card>
          <CardHeader eyebrow="Rev A · Concept" title="Initial engineering content" />
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field label="Change summary" htmlFor="change_summary" className="sm:col-span-2">
              <Input id="change_summary" name="change_summary" defaultValue="Initial revision" />
            </Field>
            <Field label="Material" htmlFor="material">
              <Input id="material" name="material" placeholder="316L stainless steel" />
            </Field>
            <Field label="Heat treatment" htmlFor="heat_treatment">
              <Input id="heat_treatment" name="heat_treatment" />
            </Field>
            <Field label="Finish" htmlFor="finish">
              <Input id="finish" name="finish" placeholder="Rhodium plated, perlage" />
            </Field>
            <Field label="Manufacturing method" htmlFor="manufacturing_method">
              <Input
                id="manufacturing_method"
                name="manufacturing_method"
                placeholder="CNC milling"
              />
            </Field>
            <Field label="Supplier note" htmlFor="supplier_note">
              <Input id="supplier_note" name="supplier_note" />
            </Field>
            <Field label="Inspection requirements" htmlFor="inspection_requirements">
              <Input id="inspection_requirements" name="inspection_requirements" />
            </Field>
            <Field label="Notes" htmlFor="notes" className="sm:col-span-2">
              <Textarea id="notes" name="notes" />
            </Field>
          </CardContent>
        </Card>

        <FormError message={error} />
        <div className="flex items-center gap-2">
          <Button type="submit" variant="primary" disabled={create.isPending}>
            {create.isPending ? "Creating…" : "Create component"}
          </Button>
          <Button variant="ghost" onClick={() => navigate("/components")}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
