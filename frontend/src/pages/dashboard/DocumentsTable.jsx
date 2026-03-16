import { useState } from "react";
import { formatBytes } from "./utils";

export function DocumentsTable({ docs, onDownload, onDelete }) {
  const [confirming, setConfirming] = useState(null); // filename pending confirm

  return (
    <table>
      <thead>
        <tr>
          <th>File</th>
          <th>Size</th>
          <th>Uploaded</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {docs.map((d) => (
          <tr key={d.name}>
            <td>{d.name}</td>
            <td>{formatBytes(d.size)}</td>
            <td>{new Date(d.last_modified).toLocaleDateString()}</td>
            <td style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <button className="link-btn" onClick={() => onDownload(d.name)}>
                Download
              </button>
              {onDelete && (
                confirming === d.name ? (
                  <>
                    <button className="delete-btn" onClick={() => { onDelete(d.name); setConfirming(null); }}>
                      Confirm
                    </button>
                    <button className="back-btn" onClick={() => setConfirming(null)}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <button className="delete-btn" onClick={() => setConfirming(d.name)}>
                    Delete
                  </button>
                )
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
