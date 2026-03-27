import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { API, PAGE_SIZE } from "./constants";
import { CasesTable } from "./CasesTable";
import { CaseSearchBar } from "./CaseSearchBar";
import { Pagination } from "./Pagination";

export function CustomerProfilePage({ companyId, user }) {
  const location = useLocation();
  const navigate = useNavigate();

  const customerName = location.state?.customerName || null;
  const [company, setCompany] = useState(null);
  const [loadingCompany, setLoadingCompany] = useState(true);
  const [allCases, setAllCases] = useState([]);
  const [page, setPage] = useState(1);

  const [searchQ, setSearchQ] = useState("");
  const [searchStatus, setSearchStatus] = useState("");
  const [searchArchived, setSearchArchived] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(searchQ), 300);
    return () => clearTimeout(t);
  }, [searchQ]);

  // Fetch company detail
  useEffect(() => {
    fetch(`${API}/company/${companyId}`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data) setCompany(data);
        setLoadingCompany(false);
      });
  }, [companyId]);

  // Fetch cases — company admins use my-cases so all client companies are included
  function fetchCases(q, status, archived) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    if (archived !== "") params.set("archived", archived);
    const qs = params.toString();
    const url = isSuperAdmin
      ? `${API}/company/${companyId}/cases${qs ? `?${qs}` : ""}`
      : `${API}/company/my-cases${qs ? `?${qs}` : ""}`;
    fetch(url, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setAllCases);
  }

  useEffect(() => {
    fetchCases(debouncedQ, searchStatus, searchArchived);
  }, [companyId, debouncedQ, searchStatus, searchArchived]);

  const isSuperAdmin = user?.is_admin && !user?.parent_id;

  // Reset page on filter change
  useEffect(() => {
    setPage(1);
  }, [debouncedQ, searchStatus, searchArchived]);

  const cases = customerName
    ? allCases.filter((c) => c.customer === customerName)
    : allCases;
  const totalPages = Math.max(1, Math.ceil(cases.length / PAGE_SIZE));
  const pageSlice = cases.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  if (loadingCompany)
    return (
      <main className="dashboard-main">
        <p className="no-cases">Loading...</p>
      </main>
    );

  if (!company)
    return (
      <main className="dashboard-main">
        <div className="section-heading">
          <button className="back-btn" onClick={() => navigate(-1)}>
            ← Back
          </button>
          <h2>Company not found</h2>
        </div>
      </main>
    );

  const displayName = customerName || company.name;
  const initials = displayName.slice(0, 2).toUpperCase();

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
      </div>

      <div className="customer-hero">
        <div className="customer-hero-avatar">{initials}</div>
        <h2 className="customer-hero-name">{displayName}</h2>
        {customerName && (
          <span className="customer-hero-subtitle">{company.name}</span>
        )}
        <span className="customer-hero-tag">Customer</span>

        <div className="customer-stats">
          <div className="customer-stat">
            <span className="customer-stat-value">{cases.length}</span>
            <span className="customer-stat-label">Cases</span>
          </div>
          <div className="customer-stat">
            <span className="customer-stat-value">
              {company.created_at
                ? new Date(company.created_at).toLocaleDateString(undefined, {
                    month: "short",
                    year: "numeric",
                  })
                : "—"}
            </span>
            <span className="customer-stat-label">Since</span>
          </div>
        </div>
      </div>

      <div className="customer-info-grid">
        <InfoCard icon="✉" label="Email" value={company.email} />
        <InfoCard icon="☎" label="Phone" value={company.phone} />
        <InfoCard icon="◎" label="CEO" value={company.ceo} />
        <InfoCard icon="⌂" label="HQ / Origin" value={company.hq_origin} />
        <InfoCard icon="▤" label="Business No." value={company.business_number} />
        <InfoCard icon="⚑" label="Address" value={company.address} />
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <CaseSearchBar
            q={searchQ}
            onQChange={setSearchQ}
            status={searchStatus}
            onStatusChange={setSearchStatus}
            archived={searchArchived}
            onArchivedChange={setSearchArchived}
          />
        {cases.length === 0 ? (
          <p className="no-cases">No cases for this customer.</p>
        ) : (
          <>
            <CasesTable
              cases={pageSlice}
              onCaseClick={(c) =>
                navigate(`/case/${c.id}`, { state: { case: c } })
              }
            />
            <Pagination
              page={page}
              totalPages={totalPages}
              setPage={setPage}
            />
          </>
        )}
      </div>

    </main>
  );
}

function InfoCard({ icon, label, value }) {
  return (
    <div className="customer-info-card">
      <span className="customer-info-icon">{icon}</span>
      <div className="customer-info-content">
        <span className="customer-info-label">{label}</span>
        <span className="customer-info-value">{value || "—"}</span>
      </div>
    </div>
  );
}
