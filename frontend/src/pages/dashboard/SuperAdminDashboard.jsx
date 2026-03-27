import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { API, PAGE_SIZE } from "./constants";
import { CasesTable } from "./CasesTable";
import { CaseSearchBar } from "./CaseSearchBar";
import { CustomersTable } from "./CustomersTable";
import { Pagination } from "./Pagination";
import { CreateCaseModal } from "./CreateCaseModal";
import { CreateCompanyModal } from "./CreateCompanyModal";

export function SuperAdminDashboard() {
  const { companyId, customer: rawCustomer } = useParams();
  const location = useLocation();
  const customer = rawCustomer ? decodeURIComponent(rawCustomer) : null;
  const isClientsTab = !!companyId && location.pathname.includes("/clients");
  const isUsersTab = !!companyId && location.pathname.endsWith("/users");

  if (!companyId) return <CompaniesListView />;
  const activeTab = isUsersTab ? "users" : isClientsTab ? "clients" : "cases";
  return (
    <CompanyDetailView
      companyId={companyId}
      activeTab={activeTab}
      selectedCustomer={customer}
    />
  );
}

function CompaniesListView() {
  const [companies, setCompanies] = useState([]);
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const navigate = useNavigate();


  function load() {
    fetch(`${API}/company/`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setCompanies);
  }

  useEffect(() => {
    load();
  }, []);

  const totalPages = Math.max(1, Math.ceil(companies.length / PAGE_SIZE));

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <h2>Companies</h2>
        <button className="btn" onClick={() => navigate("/dashboard/audit")}>
          Audit Log
        </button>
        <button className="create-btn" onClick={() => setShowCreate(true)}>
          + Add Company
        </button>
      </div>
      {companies.length === 0 ? (
        <p className="no-cases">No companies found.</p>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
              </tr>
            </thead>
            <tbody>
              {companies
                .slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
                .map((c) => (
                  <tr
                    key={c.id}
                    className="clickable"
                    onClick={() => navigate(`/company/${c.id}`)}
                  >
                    <td>{c.name}</td>
                    <td>{c.email || "—"}</td>
                    <td>{c.phone || "—"}</td>
                  </tr>
                ))}
            </tbody>
          </table>
          <Pagination page={page} totalPages={totalPages} setPage={setPage} />
        </>
      )}
      {showCreate && (
        <CreateCompanyModal
          companies={companies}
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}
    </main>
  );
}

function CompanyDetailView({ companyId, activeTab, selectedCustomer }) {
  const [company, setCompany] = useState(null);
  const [cases, setCases] = useState([]);
  const [users, setUsers] = useState([]);
  const [clients, setClients] = useState([]);
  const [page, setPage] = useState(1);
  const [showCreateCase, setShowCreateCase] = useState(false);
  const [deleteState, setDeleteState] = useState(null); // null | 'confirm' | 'deleting'
  const [deleteError, setDeleteError] = useState(null);
  const [searchQ, setSearchQ] = useState("");
  const [searchStatus, setSearchStatus] = useState("");
  const [searchArchived, setSearchArchived] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const navigate = useNavigate();

  async function handleDeleteCompany() {
    setDeleteState("deleting");
    setDeleteError(null);
    try {
      const r = await fetch(`${API}/company/${companyId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (r.ok) {
        navigate("/dashboard");
      } else {
        const data = await r.json().catch(() => ({}));
        setDeleteError(data.detail || "Failed to delete company.");
        setDeleteState(null);
      }
    } catch {
      setDeleteError("Network error.");
      setDeleteState(null);
    }
  }

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(searchQ), 300);
    return () => clearTimeout(t);
  }, [searchQ]);

  function deriveClients(fetchedCases) {
    const map = {};
    for (const c of fetchedCases) {
      const key = `${c.customer}\0${c.company_id}`;
      if (!map[key]) map[key] = { name: c.customer, count: 0, company_id: c.company_id };
      map[key].count += 1;
    }
    setClients(Object.values(map));
  }

  function fetchCases(q, status, archived) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    if (archived !== "") params.set("archived", archived);
    const qs = params.toString();
    fetch(`${API}/company/${companyId}/cases${qs ? `?${qs}` : ""}`, {
      credentials: "include",
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((fetchedCases) => {
        setCases(fetchedCases);
        deriveClients(fetchedCases);
      });
  }

  useEffect(() => {
    fetch(`${API}/company/`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((all) =>
        setCompany(
          all.find((c) => c.id === companyId) || { id: companyId, name: "…" },
        ),
      );

    fetch(`${API}/company/${companyId}/users`, {
      credentials: "include",
    })
      .then((r) => (r.ok ? r.json() : []))
      .then(setUsers);
  }, [companyId]);

  useEffect(() => {
    fetchCases(debouncedQ, searchStatus, searchArchived);
  }, [companyId, debouncedQ, searchStatus, searchArchived]);

  useEffect(() => {
    setPage(1);
  }, [activeTab, selectedCustomer, debouncedQ, searchStatus, searchArchived]);

  async function reloadCases() {
    fetchCases(debouncedQ, searchStatus, searchArchived);
  }

  const filteredCases = selectedCustomer
    ? cases.filter((c) => c.customer === selectedCustomer)
    : cases;
  const visibleItems =
    activeTab === "users"
      ? users
      : activeTab === "clients" && !selectedCustomer
        ? clients
        : activeTab === "clients"
          ? filteredCases
          : cases;
  const totalPages = Math.max(1, Math.ceil(visibleItems.length / PAGE_SIZE));
  const pageSlice = visibleItems.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate("/dashboard")}>
          ← Companies
        </button>
        <h2>{company?.name || "…"}</h2>
        {deleteState === "confirm" ? (
          <div className="delete-confirm">
            <span>Delete this company?</span>
            <button className="back-btn" onClick={() => setDeleteState(null)}>
              Cancel
            </button>
            <button className="delete-btn" onClick={handleDeleteCompany}>
              Confirm
            </button>
          </div>
        ) : (
          <button
            className="delete-btn"
            onClick={() => setDeleteState("confirm")}
          >
            Delete
          </button>
        )}
      </div>
      {deleteError && (
        <p className="form-error" style={{ marginBottom: "1rem" }}>
          {deleteError}
        </p>
      )}
      <div className="tabs">
        <button
          className={`tab${activeTab === "cases" ? " active" : ""}`}
          onClick={() => navigate(`/company/${companyId}`)}
        >
          Cases
        </button>
        <button
          className={`tab${activeTab === "clients" ? " active" : ""}`}
          onClick={() => navigate(`/company/${companyId}/clients`)}
        >
          Clients
        </button>
        <button
          className={`tab${activeTab === "users" ? " active" : ""}`}
          onClick={() => navigate(`/company/${companyId}/users`)}
        >
          Users
        </button>
      </div>

      {activeTab === "cases" && (
        <>
          <CaseSearchBar
            q={searchQ}
            onQChange={setSearchQ}
            status={searchStatus}
            onStatusChange={setSearchStatus}
            archived={searchArchived}
            onArchivedChange={setSearchArchived}
          />
          {cases.length === 0 ? (
            <p className="no-cases">No cases for this company.</p>
          ) : (
            <>
              <CasesTable
                cases={pageSlice}
                onCaseClick={(c) =>
                  navigate(`/case/${c.id}`, { state: { case: c } })
                }
              />
              <Pagination page={page} totalPages={totalPages} setPage={setPage} />
            </>
          )}
        </>
      )}

      {activeTab === "clients" &&
        !selectedCustomer &&
        (clients.length === 0 ? (
          <p className="no-cases">No clients for this company.</p>
        ) : (
          <>
            <CustomersTable
              customers={pageSlice}
              onSelect={(name, cId) =>
                navigate(`/customer/${cId}`, { state: { customerName: name } })
              }
            />
            <Pagination page={page} totalPages={totalPages} setPage={setPage} />
          </>
        ))}

      {activeTab === "clients" && selectedCustomer && (
        <>
          <div className="section-heading">
            <button
              className="back-btn"
              onClick={() => {
                setShowCreateCase(false);
                navigate(`/company/${companyId}/clients`);
              }}
            >
              ← Clients
            </button>
            <h2>{selectedCustomer}</h2>
            <button
              className="create-btn"
              onClick={() => setShowCreateCase(true)}
            >
              + Add Case
            </button>
          </div>
          {filteredCases.length === 0 ? (
            <p className="no-cases">No cases for this client.</p>
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
          {showCreateCase && (
            <CreateCaseModal
              fixedCompanyId={companyId}
              fixedCustomer={selectedCustomer}
              users={users}
              onClose={() => setShowCreateCase(false)}
              onCreated={() => {
                setShowCreateCase(false);
                reloadCases();
              }}
            />
          )}
        </>
      )}

      {activeTab === "users" &&
        (users.length === 0 ? (
          <p className="no-cases">No users for this company.</p>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {pageSlice.map((u) => (
                  <tr key={u.username}>
                    <td>{u.full_name || "—"}</td>
                    <td>
                      <button
                        className="link-btn"
                        onClick={() =>
                          navigate(`/user/${u.username}`, {
                            state: { user: u },
                          })
                        }
                      >
                        {u.username}
                      </button>
                    </td>
                    <td>{u.email}</td>
                    <td>{u.is_admin ? "Admin" : "User"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} totalPages={totalPages} setPage={setPage} />
          </>
        ))}
    </main>
  );
}
