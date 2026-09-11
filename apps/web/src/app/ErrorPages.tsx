import { isRouteErrorResponse, Link, useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/layout";

export function RouteError() {
  const error = useRouteError();
  const message = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : "Unknown error";
  return (
    <div className="p-8">
      <EmptyState
        title="Something went wrong"
        description={message}
        action={<Button onClick={() => window.location.assign("/")}>Back to dashboard</Button>}
      />
    </div>
  );
}

export function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="The address does not match any screen in the platform."
      action={
        <Link to="/" className="text-accent hover:underline">
          Back to dashboard
        </Link>
      }
    />
  );
}
