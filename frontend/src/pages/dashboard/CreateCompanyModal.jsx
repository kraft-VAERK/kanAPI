import { useState } from "react";

import { API } from "./constants";

export function CreateCompanyModal({ companies, onClose, onCreated }) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    address: "",
    owner_id: "",
  });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    if (!form.name.trim()) {
      setError("Name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    const body = {
      name: form.name.trim(),
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      address: form.address.trim() || null,
      owner_id: form.owner_id || null,
    };
    try {
      const res = await fetch(`${API}/company/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Failed to create company.");
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
        <h3>Add Company</h3>
        <form onSubmit={submit}>
          <label>
            Name *
            <input
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
            />
          </label>
          <label>
            Phone
            <input
              value={form.phone}
              onChange={(e) => set("phone", e.target.value)}
            />
          </label>
          <label>
            Address
            <input
              value={form.address}
              onChange={(e) => set("address", e.target.value)}
            />
          </label>
          <label>
            Owner (optional)
            <select
              value={form.owner_id}
              onChange={(e) => set("owner_id", e.target.value)}
            >
              <option value="">— None (top-level) —</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
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
