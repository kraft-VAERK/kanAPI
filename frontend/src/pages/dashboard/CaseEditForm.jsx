import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API } from "./constants";

const STATUSES = ["open", "pending", "in_progress", "closed"];

export function CaseEditForm({ c, caseId, onSaved }) {
  const [status, setStatus] = useState(c.status);
  const [customer, setCustomer] = useState(c.customer);
  const [responsiblePerson, setResponsiblePerson] = useState(c.responsible_person);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [users, setUsers] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const suggestionsRef = useRef(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API}/user/all`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setUsers);
  }, []);

  useEffect(() => {
    function handleClickOutside(e) {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(e.target) &&
        inputRef.current &&
        !inputRef.current.contains(e.target)
      ) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = users.filter((u) => {
    const search = responsiblePerson.toLowerCase();
    return (
      (u.full_name && u.full_name.toLowerCase().includes(search)) ||
      u.username.toLowerCase().includes(search)
    );
  });

  const hasChanges =
    status !== c.status ||
    customer !== c.customer ||
    responsiblePerson !== c.responsible_person;

  async function handleSave(e) {
    e.preventDefault();
    if (!hasChanges) return;
    setSaving(true);
    setError(null);
    try {
      const body = {};
      if (status !== c.status) body.status = status;
      if (customer !== c.customer) body.customer = customer;
      if (responsiblePerson !== c.responsible_person) body.responsible_person = responsiblePerson;

      const res = await fetch(`${API}/case/${caseId}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const updated = await res.json();
        onSaved(updated);
        navigate(`/case/${caseId}`, { replace: true, state: { toast: "Changes saved successfully" } });
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Failed to save changes.");
      }
    } catch {
      setError("Network error.");
    } finally {
      setSaving(false);
    }
  }

  function selectUser(u) {
    setResponsiblePerson(u.full_name || u.username);
    setShowSuggestions(false);
  }

  return (
    <form className="case-edit-form" onSubmit={handleSave}>
      <div className="case-detail-row">
        <label className="case-detail-label" htmlFor="edit-status">Status</label>
        <select
          id="edit-status"
          className="case-detail-value"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
      <div className="case-detail-row">
        <label className="case-detail-label" htmlFor="edit-customer">Customer</label>
        <input
          id="edit-customer"
          className="case-detail-value"
          type="text"
          value={customer}
          onChange={(e) => setCustomer(e.target.value)}
        />
      </div>
      <div className="case-detail-row" style={{ position: "relative" }}>
        <label className="case-detail-label" htmlFor="edit-responsible">Responsible</label>
        <div className="autocomplete-wrapper">
          <input
            ref={inputRef}
            id="edit-responsible"
            className="case-detail-value"
            type="text"
            value={responsiblePerson}
            autoComplete="off"
            onChange={(e) => {
              setResponsiblePerson(e.target.value);
              setShowSuggestions(true);
              setError(null);
            }}
            onFocus={() => setShowSuggestions(true)}
          />
          {showSuggestions && responsiblePerson && filtered.length > 0 && (
            <ul className="autocomplete-list" ref={suggestionsRef}>
              {filtered.slice(0, 8).map((u) => (
                <li
                  key={u.username}
                  className="autocomplete-item"
                  onMouseDown={() => selectUser(u)}
                >
                  <span className="autocomplete-name">{u.full_name || u.username}</span>
                  {u.full_name && (
                    <span className="autocomplete-username">{u.username}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      {error && (
        <p className="form-error" style={{ marginTop: "0.5rem" }}>{error}</p>
      )}
      <button
        type="submit"
        className="create-btn"
        style={{ marginTop: "0.75rem" }}
        disabled={!hasChanges || saving}
      >
        {saving ? "Saving…" : "Save Changes"}
      </button>
    </form>
  );
}
