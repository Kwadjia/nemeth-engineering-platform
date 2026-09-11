import { ATTACHMENT_KINDS, type AttachmentKind } from "@nemeth/domain-types";
import { Download, FileText } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { KindBadgeDoc } from "@/components/domain/AttachmentsPanel";
import { Identifier } from "@/components/domain/badges";
import { Card } from "@/components/ui/card";
import { Input, Select } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  contentUrl,
  entityRoute,
  formatBytes,
  useAttachments,
  useUploadPolicy,
} from "@/lib/documentQueries";
import { formatDateTime, titleCase } from "@/lib/format";

export function DocumentsPage() {
  const [params, setParams] = useSearchParams();
  const filters = {
    q: params.get("q") ?? "",
    kind: (params.get("kind") as AttachmentKind | null) ?? undefined,
  };
  const attachments = useAttachments(filters);
  const policy = useUploadPolicy();

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  return (
    <div>
      <PageHeader
        eyebrow="Manufacturing & quality"
        title="Documents"
        description="Every file attached to any record: CAD, drawings, photos, test results, manufacturing documents, certificates. Upload from the record the file belongs to."
        meta={
          policy.data ? (
            <span className="text-xs text-fg-subtle">
              Up to {formatBytes(policy.data.max_bytes)} per file ·{" "}
              {policy.data.allowed_extensions.join(" ")}
            </span>
          ) : null
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search filename, identifier or description"
          value={filters.q}
          onChange={(e) => setFilter("q", e.target.value)}
          className="w-80"
          aria-label="Search"
        />
        <Select
          value={filters.kind ?? ""}
          onChange={(e) => setFilter("kind", e.target.value)}
          className="w-40"
          aria-label="Kind"
        >
          <option value="">Any kind</option>
          {ATTACHMENT_KINDS.map((k) => (
            <option key={k} value={k}>
              {titleCase(k)}
            </option>
          ))}
        </Select>
        {attachments.data ? (
          <span className="ml-auto font-mono text-xs text-fg-subtle">
            {attachments.data.total} files
          </span>
        ) : null}
      </div>

      {attachments.isError ? <ErrorNotice error={attachments.error} /> : null}
      <Card>
        {attachments.isLoading ? (
          <LoadingRows rows={6} />
        ) : attachments.data && attachments.data.items.length > 0 ? (
          <Table>
            <THead>
              <TR>
                <TH className="w-24">Doc</TH>
                <TH className="w-28">Kind</TH>
                <TH>File</TH>
                <TH className="w-56">Attached to</TH>
                <TH className="w-20" align="right">
                  Size
                </TH>
                <TH className="w-28">SHA-256</TH>
                <TH className="w-40">Uploaded</TH>
                <TH className="w-10" />
              </TR>
            </THead>
            <TBody>
              {attachments.data.items.map((a) => {
                const route = a.entity
                  ? entityRoute(a.entity.entity_type, a.entity.identifier)
                  : null;
                return (
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
                    <TD>
                      {a.entity ? (
                        <span className="inline-flex items-center gap-2">
                          <span className="text-2xs uppercase tracking-label text-fg-subtle">
                            {titleCase(a.entity.entity_type)}
                          </span>
                          {route ? (
                            <Link
                              to={route}
                              className="font-mono text-xs text-fg hover:text-accent hover:underline"
                            >
                              {a.entity.identifier}
                            </Link>
                          ) : (
                            <Identifier value={a.entity.identifier} />
                          )}
                        </span>
                      ) : (
                        <span className="text-xs text-warn">Owner missing</span>
                      )}
                    </TD>
                    <TD align="right" mono className="text-fg-muted">
                      {formatBytes(a.size_bytes)}
                    </TD>
                    <TD mono className="text-fg-subtle" title={a.sha256}>
                      {a.sha256.slice(0, 12)}
                    </TD>
                    <TD className="text-fg-subtle">{formatDateTime(a.created_at)}</TD>
                    <TD align="right">
                      <a
                        href={contentUrl(a.identifier)}
                        className="inline-block rounded p-1 text-fg-subtle hover:bg-surface-2 hover:text-fg"
                        aria-label={`Download ${a.original_filename}`}
                      >
                        <Download className="h-3.5 w-3.5" />
                      </a>
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>
        ) : (
          <EmptyState
            icon={FileText}
            title="No documents"
            description="Attach files from a component revision, prototype, experiment, test run or watch."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}
