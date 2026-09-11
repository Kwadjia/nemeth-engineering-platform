/** Formatting helpers. Engineering data is shown exactly; never rounded silently. */

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Trim trailing zeros from a decimal string ("2.0000" → "2", "0.0150" → "0.015"). */
export function formatQuantity(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const text = typeof value === "number" ? String(value) : value;
  if (!/^-?\d+(\.\d+)?$/.test(text)) return text;
  if (!text.includes(".")) return text;
  const trimmed = text.replace(/0+$/, "").replace(/\.$/, "");
  return trimmed === "" || trimmed === "-" ? "0" : trimmed;
}

export function formatNumber(value: string | number | null | undefined, unit?: string): string {
  const base = formatQuantity(value);
  return base === "—" || !unit ? base : `${base} ${unit}`;
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split(/[_\s]+/)
    .map((w) => (w ? w[0]!.toUpperCase() + w.slice(1) : w))
    .join(" ");
}

export function revisionLabel(identifier: string, label: string): string {
  return `${identifier} Rev ${label}`;
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

/** Read a text field from a form submission; files and missing keys become "". */
export function formText(fd: FormData, key: string): string {
  const value = fd.get(key);
  return typeof value === "string" ? value.trim() : "";
}

/** Same as formText but empty strings become null (the API's "not set"). */
export function formOptional(fd: FormData, key: string): string | null {
  const text = formText(fd, key);
  return text === "" ? null : text;
}

/** Render an unknown JSON value (dimension, tolerance) for display. */
export function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}
