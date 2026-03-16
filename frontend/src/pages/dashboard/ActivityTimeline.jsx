import { useState } from "react";

const ACTIVITY_LABELS = {
  case_created: "Case created",
  status_changed: "Status changed",
  responsible_changed: "Responsible person changed",
  document_uploaded: "Document uploaded",
};

const PREVIEW_COUNT = 5;

export function ActivityTimeline({ entries }) {
  const [showAll, setShowAll] = useState(false);
  const sorted = [...entries].reverse();
  const visible = showAll ? sorted : sorted.slice(0, PREVIEW_COUNT);
  const hasMore = sorted.length > PREVIEW_COUNT;

  return (
    <>
      <ul className="activity-timeline">
        {visible.map((e) => (
          <li key={e.id} className="activity-entry">
            <span className="activity-dot" />
            <div className="activity-body">
              <span className="activity-action">
                {ACTIVITY_LABELS[e.action] ?? e.action}
              </span>
              {e.detail && (
                <span className="activity-detail">{e.detail}</span>
              )}
              <span className="activity-meta">
                {e.user_id && <span>{e.user_id}</span>}
                <span>{new Date(e.created_at).toLocaleString()}</span>
              </span>
            </div>
          </li>
        ))}
      </ul>
      {hasMore && (
        <button
          className="view-all-activity-btn"
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll
            ? "Show recent only"
            : `View all activity (${sorted.length})`}
        </button>
      )}
    </>
  );
}
