import { Link } from "react-router-dom";

import { Identifier } from "@/components/domain/badges";
import { ExperimentStatusBadge, OutcomeBadge } from "@/components/domain/experimentBadges";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, LoadingRows } from "@/components/ui/layout";
import { usePrototypeExperiments } from "@/lib/experimentQueries";

/** Experiments that involve this prototype. */
export function ExperimentsPanel({ prototypeRef }: { prototypeRef: string }) {
  const experiments = usePrototypeExperiments(prototypeRef);
  return (
    <Card>
      <CardHeader
        eyebrow="Development"
        title="Experiments"
        actions={
          <Link to="/experiments" className="text-xs text-fg-muted hover:text-fg hover:underline">
            All experiments
          </Link>
        }
      />
      {experiments.isLoading ? (
        <LoadingRows rows={2} />
      ) : experiments.data && experiments.data.length > 0 ? (
        <ul className="divide-y divide-border">
          {experiments.data.map((e) => (
            <li key={e.id} className="flex items-center gap-3 px-4 py-2">
              <Identifier value={e.identifier} to={`/experiments/${e.identifier}`} />
              <span className="flex-1 truncate text-sm text-fg">{e.title}</span>
              <OutcomeBadge outcome={e.outcome} />
              <ExperimentStatusBadge status={e.status} />
            </li>
          ))}
        </ul>
      ) : (
        <CardContent>
          <EmptyState
            title="No experiments involve this prototype"
            description="Link it from an experiment's page."
            className="py-6"
          />
        </CardContent>
      )}
    </Card>
  );
}
