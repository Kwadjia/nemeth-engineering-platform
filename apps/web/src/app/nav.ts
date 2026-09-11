import {
  Activity,
  Box,
  Boxes,
  Cog,
  FileText,
  FlaskConical,
  GitBranch,
  Layers,
  LayoutDashboard,
  ListTree,
  Package,
  Settings,
  Truck,
  Watch,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  /** Present when the area is documented but not yet implemented. */
  plannedSlice?: number;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV: NavGroup[] = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", to: "/", icon: LayoutDashboard }],
  },
  {
    label: "Product definition",
    items: [
      { label: "Products", to: "/products", icon: Package },
      { label: "Calibers", to: "/calibers", icon: Cog },
      { label: "Components", to: "/components", icon: Box },
      { label: "BOMs", to: "/boms", icon: ListTree },
    ],
  },
  {
    label: "Development",
    items: [
      { label: "Prototypes", to: "/prototypes", icon: Layers },
      { label: "Part instances", to: "/part-instances", icon: Boxes },
      { label: "Experiments", to: "/experiments", icon: FlaskConical },
      { label: "Testing", to: "/testing", icon: Activity },
      { label: "Watches", to: "/watches", icon: Watch },
    ],
  },
  {
    label: "Manufacturing & quality",
    items: [
      { label: "Suppliers", to: "/suppliers", icon: Truck, plannedSlice: 12 },
      { label: "Documents", to: "/documents", icon: FileText },
      { label: "Engineering changes", to: "/changes", icon: GitBranch, plannedSlice: 12 },
    ],
  },
  {
    label: "System",
    items: [{ label: "Settings", to: "/settings", icon: Settings }],
  },
];
