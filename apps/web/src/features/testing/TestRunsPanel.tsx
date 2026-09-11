import { Link } from "react-router-dom";

import { TimingTable } from "@/components/domain/TimingTable";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, LoadingRows } from "@/components/ui/layout";
import { TestRunsTable } from "@/features/testing/TestRunsTable";
import {
  useExperimentTestRuns,
  usePrototypeTestRuns,
  usePrototypeTiming,
} from "@/lib/testingQueries";

export function PrototypeTestRunsPanel({ prototypeRef }: { prototypeRef: string }) {
  const runs = usePrototypeTestRuns(prototypeRef);
  const timing = usePrototypeTiming(prototypeRef);
  return (
    <>
      <Card>
        <CardHeader eyebrow="Latest timegrapher run" title="Timing" />
        <CardContent>
          {timing.isLoading ? (
            <LoadingRows rows={2} />
          ) : timing.data ? (
            <TimingTable timing={timing.data} />
          ) : (
            <EmptyState
              title="No timegrapher run yet"
              description="Record one from the Testing page."
              className="py-6"
            />
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader
          eyebrow="Testing"
          title="Test runs"
          actions={
            <Link
              to={`/testing?new=1&prototype=${prototypeRef}`}
              className="text-xs text-fg-muted hover:text-fg hover:underline"
            >
              New test run
            </Link>
          }
        />
        {runs.isLoading ? (
          <LoadingRows rows={2} />
        ) : runs.data && runs.data.length > 0 ? (
          <TestRunsTable runs={runs.data} showSubject={false} />
        ) : (
          <CardContent>
            <EmptyState title="No test runs on this prototype" className="py-6" />
          </CardContent>
        )}
      </Card>
    </>
  );
}

export function ExperimentTestRunsPanel({ experimentRef }: { experimentRef: string }) {
  const runs = useExperimentTestRuns(experimentRef);
  return (
    <Card>
      <CardHeader
        eyebrow="Evidence"
        title="Test runs"
        actions={
          <Link
            to={`/testing?new=1&experiment=${experimentRef}`}
            className="text-xs text-fg-muted hover:text-fg hover:underline"
          >
            New test run
          </Link>
        }
      />
      {runs.isLoading ? (
        <LoadingRows rows={2} />
      ) : runs.data && runs.data.length > 0 ? (
        <TestRunsTable runs={runs.data} />
      ) : (
        <CardContent>
          <EmptyState
            title="No test runs attached"
            description="Record measurements against this experiment to build before/after evidence."
            className="py-6"
          />
        </CardContent>
      )}
    </Card>
  );
}
