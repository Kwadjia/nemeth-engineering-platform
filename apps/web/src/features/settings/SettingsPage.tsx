import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ErrorNotice, KV, LoadingRows, PageHeader } from "@/components/ui/layout";
import { useHealth, useSystemInfo } from "@/lib/queries";

export function SettingsPage() {
  const info = useSystemInfo();
  const health = useHealth();

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="System"
        title="Settings"
        description="Runtime configuration is read from the API. Values are set through NEMETH_* environment variables (see .env.example)."
      />
      <div className="grid gap-4">
        <Card>
          <CardHeader eyebrow="API" title="Connection" />
          <CardContent>
            {health.isLoading ? (
              <LoadingRows rows={2} />
            ) : health.isError ? (
              <ErrorNotice error={health.error} title="API unreachable" />
            ) : health.data ? (
              <KV
                columns={3}
                items={[
                  { label: "Status", value: health.data.status },
                  { label: "Version", value: health.data.version, mono: true },
                  { label: "Database", value: health.data.database },
                ]}
              />
            ) : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader eyebrow="Runtime" title="Environment" />
          <CardContent>
            {info.isLoading ? (
              <LoadingRows rows={3} />
            ) : info.data ? (
              <KV
                columns={2}
                items={[
                  { label: "Application", value: info.data.app_name },
                  { label: "Environment", value: info.data.environment },
                  { label: "API prefix", value: info.data.api_prefix, mono: true },
                  { label: "Storage backend", value: info.data.storage_backend },
                  { label: "Storage root", value: info.data.storage_root, mono: true, span: 2 },
                  { label: "Actor", value: `${info.data.actor_name} (${info.data.actor_id})` },
                ]}
              />
            ) : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader eyebrow="Identity" title="Authentication" />
          <CardContent className="text-sm text-fg-muted">
            The platform runs as a single local actor. Writes are attributed to the configured actor
            in
            <code className="mx-1 font-mono text-xs text-fg">created_by</code>/
            <code className="mx-1 font-mono text-xs text-fg">updated_by</code>. Real authentication
            replaces one dependency on the API (
            <code className="font-mono text-xs text-fg">get_actor</code>) when it is needed.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
