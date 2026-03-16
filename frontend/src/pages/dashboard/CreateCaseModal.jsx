import { useState } from "react";

import { API } from "./constants";

export function CreateCaseModal({
  onClose,
  onCreated,
  fixedCompanyId = null,
  fixedCustomer = null,
  users = null,
  currentUsername = null,
  currentUserId = null,
}) {
  const [form, setForm] = useState({
    responsible_user_id: "",
    status: "open",
    customer: fixedCustomer || "",
  });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    const responsibleUserId = users ? form.responsible_user_id : currentUserId;
    const responsibleName = users
      ? users.find((u) => u.username === form.responsible_user_id)?.full_name ||
        users.find((u) => u.username === form.responsible_user_id)?.username ||
        ""
      : currentUsername;
    if (!responsibleName) {
      setError("Responsible person is required.");
      return;
    }
    if (!form.customer.trim()) {
      setError("Customer is required.");
      return;
    }
    if (!fixedCompanyId) {
      setError("Client company is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API}/case/create`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          responsible_person: responsibleName,
          responsible_user_id: responsibleUserId,
          status: form.status,
          customer: form.customer.trim(),
          company_id: fixedCompanyId,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Failed to create case.");
        return;
      }
      onCreated();
    } catch {
      setError("Network error.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>New Case</h3>
        <form onSubmit={submit}>
          {!fixedCustomer && (
            <label>
              Customer / Contact *
              <input
                value={form.customer}
                onChange={(e) => set("customer", e.target.value)}
                placeholder="Person or organisation name"
              />
            </label>
          )}
          {users ? (
            <label>
              Responsible Person *
              <select
                value={form.responsible_user_id}
                onChange={(e) => set("responsible_user_id", e.target.value)}
              >
                <option value="">— Select a user —</option>
                {users.map((u) => (
                  <option key={u.username} value={u.username}>
                    {u.full_name || u.username}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <label>
              Responsible Person
              <input value={currentUsername || ""} readOnly />
            </label>
          )}
          <label>
            Status
            <select
              value={form.status}
              onChange={(e) => set("status", e.target.value)}
            >
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="pending">Pending</option>
              <option value="closed">Closed</option>
            </select>
          </label>
          {error && <p className="form-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
