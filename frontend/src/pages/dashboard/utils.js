export function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

// Build the ?q=&status=&archived= query string shared by all case list fetches.
export function caseQueryString(q, status, archived) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  if (archived !== "") params.set("archived", archived);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

// Derive {name, count, company_id} customer entries from a list of cases.
export function deriveCustomers(cases) {
  const map = {};
  for (const c of cases) {
    if (!map[c.customer]) map[c.customer] = { name: c.customer, count: 0, company_id: c.company_id };
    map[c.customer].count += 1;
  }
  return Object.values(map);
}
