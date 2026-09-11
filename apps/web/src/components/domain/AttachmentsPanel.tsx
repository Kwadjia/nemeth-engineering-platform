import { ATTACHMENT_KINDS, type AttachmentKind, type EntityType } from "@nemeth/domain-types";
import { Download, FileText, Paperclip, Trash2 } from "lucide-react";
import { useState } from "react";

import { Identifier } from "@/components/domain/badges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field, FormError, Input, Select } from "@/components/ui/form";
import { EmptyState, LoadingRows } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { describeError } from "@/lib/api";
import {
  contentUrl,
  formatBytes,
  useAttachments,
  useDeleteAttachment,
  useUploadAttachment,
} from "@/lib/documentQueries";
import { formatDateTime, titleCase } from "@/lib/format";

const KIND_TONE: Record<
  AttachmentKind,
  "accent" | "steel" | "ok" | "warn" | "outline" | "neutral"
> = {
  CAD: "accent",
  DRAWING: "steel",
  PHOTO: "ok",
  TEST_RESULT: "warn",
  MANUFACTURING: "outline",
  CERTIFICATE: "outline",
  OTHER: "neutral",
};

export function KindBadgeDoc({ kind }: { kind: AttachmentKind }) {
  return <Badge tone={KIND_TONE[kind]}>{titleCase(kind)}</Badge>;
}

/** Files attached to one entity, with upload and delete. */
export function AttachmentsPanel({
  entityType,
  entityId,
  eyebrow,
  defaultKind = "OTHER",
}: {
  entityType: EntityType;
  entityId: string;
  eyebrow?: string;
  defaultKind?: AttachmentKind;
}) {
  const attachments = useAttachments({ entity_type: entityType, entity_id: entityId });
  const upload = useUploadAttachment();
  const remove = useDeleteAttachment();
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = event.currentTarget;
    const fd = new FormData(form);
    const file = fd.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setError("Choose a file.");
      return;
    }
    const kind = fd.get("kind");
    const description = fd.get("description");
    upload.mutate(
      {
        file,
        entity_type: entityType,
        entity_id: entityId,
        kind: (typeof kind === "string" ? kind : defaultKind) as AttachmentKind,
        description:
          typeof description === "string" && description.trim() ? description.trim() : null,
      },
      { onSuccess: () => form.reset(), onError: (err) => setError(describeError(err)) },
    );
  }

  return (
    <Card>
      <CardHeader
        eyebrow={eyebrow ?? "Files"}
        title="Attachments"
        actions={
          attachments.data ? (
            <span className="font-mono text-xs text-fg-subtle">{attachments.data.total} files</span>
          ) : null
        }
      />
      {attachments.isLoading ? (
        <LoadingRows rows={2} />
      ) : attachments.data && attachments.data.items.length > 0 ? (
        <Table>
          <THead>
            <TR>
              <TH className="w-24">Doc</TH>
              <TH className="w-28">Kind</TH>
              <TH>File</TH>
              <TH className="w-20" align="right">
                Size
              </TH>
              <TH className="w-28">SHA-256</TH>
              <TH className="w-40">Uploaded</TH>
              <TH className="w-20" />
            </TR>
          </THead>
          <TBody>
            {attachments.data.items.map((a) => (
              <TR key={a.id}>
                <TD>
                  <Identifier value={a.identifier} />
                </TD>
                <TD>
                  <KindBadgeDoc kind={a.kind} />
                </TD>
                <TD>
                  <a
                    href={contentUrl(a.identifier, true)}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-fg hover:text-accent hover:underline"
                  >
                    <FileText className="h-3.5 w-3.5 text-fg-subtle" />
                    {a.original_filename}
                  </a>
                  {a.description ? (
                    <span className="ml-2 text-xs text-fg-subtle">{a.description}</span>
                  ) : null}
                </TD>
                <TD align="right" mono className="text-fg-muted">
                  {formatBytes(a.size_bytes)}
                </TD>
                <TD mono className="text-fg-subtle" title={a.sha256}>
                  {a.sha256.slice(0, 12)}
                </TD>
                <TD className="text-fg-subtle">
                  {formatDateTime(a.created_at)} · {a.created_by}
                </TD>
                <TD align="right">
                  <span className="inline-flex items-center gap-1">
                    <a
                      href={contentUrl(a.identifier)}
                      className="rounded p-1 text-fg-subtle hover:bg-surface-2 hover:text-fg"
                      aria-label={`Download ${a.original_filename}`}
                    >
                      <Download className="h-3.5 w-3.5" />
                    </a>
                    {confirming === a.id ? (
                      <Button
                        variant="danger"
                        size="sm"
                        disabled={remove.isPending}
                        onClick={() =>
                          remove.mutate(a.identifier, {
                            onSettled: () => setConfirming(null),
                            onError: (err) => setError(describeError(err)),
                          })
                        }
                      >
                        Confirm delete
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete ${a.original_filename}`}
                        onClick={() => setConfirming(a.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </span>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      ) : (
        <CardContent>
          <EmptyState icon={Paperclip} title="No files attached" className="py-5" />
        </CardContent>
      )}
      <CardContent className="border-t border-border">
        <form
          onSubmit={onSubmit}
          className="grid items-end gap-3 sm:grid-cols-[1fr_10rem_1fr_auto]"
        >
          <Field label="File" htmlFor={`att-file-${entityId}`}>
            <Input
              id={`att-file-${entityId}`}
              name="file"
              type="file"
              className="h-auto py-1 file:mr-3 file:rounded file:border-0 file:bg-surface-2 file:px-2 file:py-1 file:text-xs file:text-fg"
            />
          </Field>
          <Field label="Kind" htmlFor={`att-kind-${entityId}`}>
            <Select id={`att-kind-${entityId}`} name="kind" defaultValue={defaultKind}>
              {ATTACHMENT_KINDS.map((k) => (
                <option key={k} value={k}>
                  {titleCase(k)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Description" htmlFor={`att-desc-${entityId}`}>
            <Input
              id={`att-desc-${entityId}`}
              name="description"
              placeholder="Sheet 2 of 3, rev C"
            />
          </Field>
          <Button type="submit" variant="primary" disabled={upload.isPending}>
            {upload.isPending ? "Uploading…" : "Upload"}
          </Button>
        </form>
        <div className="mt-2">
          <FormError message={error} />
        </div>
        <p className="mt-2 text-2xs text-fg-subtle">
          Files are stored outside the database under a server-generated key. Identical content on
          the same record is reported, not duplicated.
        </p>
      </CardContent>
    </Card>
  );
}
