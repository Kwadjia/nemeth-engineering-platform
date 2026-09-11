import { Link } from "react-router-dom";

import { Identifier } from "@/components/domain/badges";
import { ChangeStatusBadge } from "@/components/domain/changeBadges";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, LoadingRows } from "@/components/ui/layout";
import { useRevisionChanges } from "@/lib/changeQueries";

/** Engineering changes in which a revision is affected or proposed. */
export function RevisionChangesPanel({ revisionId, label }: { revisionId: string; label: string }) {
  const changes = useRevisionChanges(revisionId);
  return (
    <Card>
      <CardHeader
        eyebrow={`Why Rev ${label} exists, or why it ended`}
        title="Engineering changes"
        actions={
          <Link to="/changes" className="text-xs text-fg-muted hover:text-fg hover:underline">
            All changes
          </Link>
        }
      />
      {changes.isLoading ? (
        <LoadingRows rows={2} />
      ) : changes.data && changes.data.length > 0 ? (
        <ul className="divide-y divide-border">
          {changes.data.map((c) => (
            <li key={c.id} className="flex items-center gap-3 px-4 py-2">
              <Identifier value={c.identifier} to={`/changes/${c.identifier}`} />
              <span className="flex-1 truncate text-sm text-fg">{c.title}</span>
              <ChangeStatusBadge status={c.status} />
            </li>
          ))}
        </ul>
      ) : (
        <CardContent>
          <EmptyState title="No engineering change references this revision" className="py-5" />
        </CardContent>
      )}
    </Card>
  );
}
