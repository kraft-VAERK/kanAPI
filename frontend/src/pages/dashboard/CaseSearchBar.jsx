export function CaseSearchBar({
  q,
  onQChange,
  status,
  onStatusChange,
  archived,
  onArchivedChange,
}) {
  return (
    <div className="search-bar">
      <input
        type="text"
        placeholder="Search customer or person…"
        value={q}
        onChange={(e) => onQChange(e.target.value)}
      />
      <select value={status} onChange={(e) => onStatusChange(e.target.value)}>
        <option value="">All statuses</option>
        <option value="open">Open</option>
        <option value="pending">Pending</option>
        <option value="in_progress">In progress</option>
        <option value="closed">Closed</option>
      </select>
      <select
        value={archived}
        onChange={(e) => onArchivedChange(e.target.value)}
      >
        <option value="">All</option>
        <option value="false">Active</option>
        <option value="true">Archived</option>
      </select>
    </div>
  );
}
