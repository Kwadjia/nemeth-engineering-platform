import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "@/app/AppShell";
import { NotFound, RouteError } from "@/app/ErrorPages";
import { BomExplorerPage } from "@/features/boms/BomExplorerPage";
import { BomsPage } from "@/features/boms/BomsPage";
import { CaliberDetailPage } from "@/features/calibers/CaliberDetailPage";
import { CalibersPage } from "@/features/calibers/CalibersPage";
import { ComponentCreatePage } from "@/features/components/ComponentCreatePage";
import { ComponentDetailPage } from "@/features/components/ComponentDetailPage";
import { ComponentsPage } from "@/features/components/ComponentsPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { PlannedPage } from "@/features/planned/PlannedPage";
import { ProductDetailPage } from "@/features/products/ProductDetailPage";
import { ProductsPage } from "@/features/products/ProductsPage";
import { SettingsPage } from "@/features/settings/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "products", element: <ProductsPage /> },
      { path: "products/:ref", element: <ProductDetailPage /> },
      { path: "calibers", element: <CalibersPage /> },
      { path: "calibers/:ref", element: <CaliberDetailPage /> },
      { path: "components", element: <ComponentsPage /> },
      { path: "components/new", element: <ComponentCreatePage /> },
      { path: "components/:ref", element: <ComponentDetailPage /> },
      { path: "components/:ref/revisions/:label", element: <ComponentDetailPage /> },
      { path: "boms", element: <BomsPage /> },
      { path: "boms/:ref", element: <BomExplorerPage /> },
      { path: "prototypes", element: <PlannedPage area="prototypes" /> },
      { path: "experiments", element: <PlannedPage area="experiments" /> },
      { path: "testing", element: <PlannedPage area="testing" /> },
      { path: "watches", element: <PlannedPage area="watches" /> },
      { path: "suppliers", element: <PlannedPage area="suppliers" /> },
      { path: "documents", element: <PlannedPage area="documents" /> },
      { path: "changes", element: <PlannedPage area="changes" /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
