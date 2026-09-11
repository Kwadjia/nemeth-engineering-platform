import { Activity, Plus } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/form";
import { EmptyState, ErrorNotice, LoadingRows, PageHeader } from "@/components/ui/layout";
import { NewTestRunForm } from "@/features/testing/NewTestRunForm";
import { TestRunsTable } from "@/features/testing/TestRunsTable";
import { useTestRuns, useTestTypes } from "@/lib/testingQueries";

export function TestingPage() {
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(params.get("new") === "1");
  const filters = { test_type: params.get("type") ?? "" };
  const runs = useTestRuns(filters);
  const types = useTestTypes();

  function setType(value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set("type", value);
    else next.delete("type");
    next.delete("new");
    setParams(next, { replace: true });
  }

  return (
    <div>
      <PageHeader
        eyebrow="Development"
        title="Testing"
        description="Test runs and measurements. Test types are registry rows with a metric list, so a new kind of test is data, not a migration. Timegrapher runs get a per-position summary."
        actions={
          <Button variant="primary" onClick={() => setCreating((v) => !v)}>
            <Plus className="h-3.5 w-3.5" /> New test run
          </Button>
        }
      />
      {creating ? (
        <NewTestRunForm
          onDone={() => setCreating(false)}
          defaultPrototype={params.get("prototype") ?? undefined}
          defaultExperiment={params.get("experiment") ?? undefined}
        />
      ) : null}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Select
          value={filters.test_type}
          onChange={(e) => setType(e.target.value)}
          className="w-48"
          aria-label="Test type"
        >
          <option value="">All test types</option>
          {(types.data ?? []).map((t) => (
            <option key={t.id} value={t.code}>
              {t.name}
            </option>
          ))}
        </Select>
        {runs.data ? (
          <span className="ml-auto font-mono text-xs text-fg-subtle">{runs.data.total} runs</span>
        ) : null}
      </div>

      {runs.isError ? <ErrorNotice error={runs.error} /> : null}
      <Card>
        {runs.isLoading ? (
          <LoadingRows rows={6} />
        ) : runs.data && runs.data.items.length > 0 ? (
          <TestRunsTable runs={runs.data.items} />
        ) : (
          <EmptyState
            icon={Activity}
            title="No test runs"
            description="Put a movement on the timegrapher and record the first run."
            className="m-4"
          />
        )}
      </Card>
    </div>
  );
}
