import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

const API = "/api/v1";
const PAGE_SIZE = 10;

// ─── Root ────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { caseId, userId } = useParams();

  useEffect(() => {
    fetch(`${API}/auth/me`, { credentials: "include" })
      .then(async (r) => {
        if (!r.ok) {
          navigate("/", { replace: true });
          return;
        }
        setUser(await r.json());
      })
      .catch(() => navigate("/", { replace: true }));
  }, [navigate]);

  async function handleLogout() {
    await fetch(`${API}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    navigate("/", { replace: true });
  }

  if (!user) return null;

  const isSuperAdmin = user.is_admin && !user.parent_id;
  const isCompanyAdmin = user.is_admin && !!user.parent_id;
  const isProfilePage = location.pathname === "/dashboard/profile";

  const header = (
    <header className="dashboard-header">
      <span>{user.username}</span>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button onClick={() => navigate("/dashboard/profile")}>Profile</button>
        <button onClick={handleLogout}>Logout</button>
      </div>
    </header>
  );

  if (caseId)
    return (
      <>
        {header}
        <CaseDetailPage caseId={caseId} />
      </>
    );

  if (userId)
    return (
      <>
        {header}
        <UserProfileView
          userId={userId}
          viewerIsSuperAdmin={user.is_admin && !user.parent_id}
        />
      </>
    );

  if (isProfilePage)
    return (
      <>
        {header}
        <main className="dashboard-main">
          <div className="tabs">
            <button className="tab" onClick={() => navigate("/dashboard")}>
              ← Back
            </button>
            <button className="tab active">Profile</button>
          </div>
          <ProfileView user={user} />
        </main>
      </>
    );

  return (
    <>
      {header}
      {isSuperAdmin ? (
        <SuperAdminDashboard user={user} />
      ) : isCompanyAdmin ? (
        <CompanyAdminDashboard user={user} />
      ) : (
        <UserDashboard user={user} />
      )}
    </>
  );
}

// ─── Super admin ──────────────────────────────────────────────────────────────

function SuperAdminDashboard() {
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

  function deriveClients(fetchedCases) {
    const map = {};
    for (const c of fetchedCases) map[c.customer] = (map[c.customer] || 0) + 1;
    setClients(Object.entries(map).map(([name, count]) => ({ name, count })));
  }

  useEffect(() => {
    fetch(`${API}/company/`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((all) =>
        setCompany(
          all.find((c) => c.id === companyId) || { id: companyId, name: "…" },
        ),
      );

    Promise.all([
      fetch(`${API}/company/${companyId}/cases`, {
        credentials: "include",
      }).then((r) => (r.ok ? r.json() : [])),
      fetch(`${API}/company/${companyId}/users`, {
        credentials: "include",
      }).then((r) => (r.ok ? r.json() : [])),
    ]).then(([fetchedCases, fetchedUsers]) => {
      setCases(fetchedCases);
      setUsers(fetchedUsers);
      deriveClients(fetchedCases);
    });
  }, [companyId]);

  useEffect(() => {
    setPage(1);
  }, [activeTab, selectedCustomer]);

  async function reloadCases() {
    const res = await fetch(`${API}/company/${companyId}/cases`, {
      credentials: "include",
    });
    const fetchedCases = res.ok ? await res.json() : [];
    setCases(fetchedCases);
    deriveClients(fetchedCases);
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

      {activeTab === "cases" &&
        (cases.length === 0 ? (
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
        ))}

      {activeTab === "clients" &&
        !selectedCustomer &&
        (clients.length === 0 ? (
          <p className="no-cases">No clients for this company.</p>
        ) : (
          <>
            <CustomersTable
              customers={pageSlice}
              onSelect={(name) =>
                navigate(
                  `/company/${companyId}/clients/${encodeURIComponent(name)}`,
                )
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

// ─── Company admin ─────────────────────────────────────────────────────────────

function CompanyAdminDashboard({ user }) {
  const { customer: rawCustomer } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const customer = rawCustomer ? decodeURIComponent(rawCustomer) : null;

  const tab = location.pathname.startsWith("/dashboard/users")
    ? "users"
    : location.pathname.startsWith("/dashboard/customers")
      ? "customers"
      : "cases";

  const [cases, setCases] = useState([]);
  const [users, setUsers] = useState([]);
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);

  function loadCases() {
    fetch(`${API}/company/my-cases`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setCases);
  }

  useEffect(() => {
    loadCases();
    fetch(`${API}/company/my-users`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setUsers);
  }, []);

  useEffect(() => {
    setPage(1);
  }, [tab, customer]);

  const customerMap = {};
  for (const c of cases)
    customerMap[c.customer] = (customerMap[c.customer] || 0) + 1;
  const customers = Object.entries(customerMap).map(([name, count]) => ({
    name,
    count,
  }));

  const activeCases = customer
    ? cases.filter((c) => c.customer === customer)
    : cases;
  const visibleItems =
    tab === "customers" && !customer
      ? customers
      : tab === "users"
        ? users
        : activeCases;
  const totalPages = Math.max(1, Math.ceil(visibleItems.length / PAGE_SIZE));
  const pageSlice = visibleItems.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  return (
    <main className="dashboard-main">
      <div className="tabs">
        <button
          className={`tab${tab === "cases" ? " active" : ""}`}
          onClick={() => navigate("/dashboard")}
        >
          Cases
        </button>
        <button
          className={`tab${tab === "customers" ? " active" : ""}`}
          onClick={() => navigate("/dashboard/customers")}
        >
          Customers
        </button>
        <button
          className={`tab${tab === "users" ? " active" : ""}`}
          onClick={() => navigate("/dashboard/users")}
        >
          Users
        </button>
      </div>

      {tab === "cases" && (
        <>
          <h2>All Cases</h2>
          {cases.length === 0 ? (
            <p className="no-cases">No cases found.</p>
          ) : (
            <>
              <CasesTable
                cases={pageSlice}
                onCaseClick={(c) =>
                  navigate(`/case/${c.id}`, { state: { case: c } })
                }
                onCustomerClick={(name) =>
                  navigate(`/dashboard/customers/${encodeURIComponent(name)}`)
                }
              />
              <Pagination
                page={page}
                totalPages={totalPages}
                setPage={setPage}
              />
            </>
          )}
        </>
      )}

      {tab === "customers" && !customer && (
        <>
          <h2>Customers</h2>
          {customers.length === 0 ? (
            <p className="no-cases">No customers found.</p>
          ) : (
            <>
              <CustomersTable
                customers={pageSlice}
                onSelect={(name) =>
                  navigate(`/dashboard/customers/${encodeURIComponent(name)}`)
                }
              />
              <Pagination
                page={page}
                totalPages={totalPages}
                setPage={setPage}
              />
            </>
          )}
        </>
      )}

      {tab === "customers" && customer && (
        <>
          <div className="section-heading">
            <button
              className="back-btn"
              onClick={() => {
                setShowCreate(false);
                navigate("/dashboard/customers");
              }}
            >
              ← Back
            </button>
            <h2>{customer}</h2>
            <button className="create-btn" onClick={() => setShowCreate(true)}>
              + Add Case
            </button>
          </div>
          {activeCases.length === 0 ? (
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
          {showCreate && (
            <CreateCaseModal
              fixedCompanyId={
                cases.find((c) => c.customer === customer)?.company_id || ""
              }
              fixedCustomer={customer}
              users={[user, ...users]}
              onClose={() => setShowCreate(false)}
              onCreated={() => {
                setShowCreate(false);
                loadCases();
              }}
            />
          )}
        </>
      )}

      {tab === "users" && (
        <>
          <h2>Users</h2>
          {users.length === 0 ? (
            <p className="no-cases">No users found.</p>
          ) : (
            <>
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Username</th>
                    <th>Email</th>
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
                    </tr>
                  ))}
                </tbody>
              </table>
              <Pagination
                page={page}
                totalPages={totalPages}
                setPage={setPage}
              />
            </>
          )}
        </>
      )}
    </main>
  );
}

// ─── Regular user ─────────────────────────────────────────────────────────────

function UserDashboard({ user }) {
  const { customer: rawCustomer } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const customer = rawCustomer ? decodeURIComponent(rawCustomer) : null;
  const tab = location.pathname.startsWith("/dashboard/customers")
    ? "customers"
    : "cases";

  const [cases, setCases] = useState([]);
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);

  function loadCases() {
    fetch(`${API}/case/`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setCases);
  }

  useEffect(() => {
    loadCases();
  }, []);
  useEffect(() => {
    setPage(1);
  }, [tab, customer]);

  const customerMap = {};
  for (const c of cases)
    customerMap[c.customer] = (customerMap[c.customer] || 0) + 1;
  const customers = Object.entries(customerMap).map(([name, count]) => ({
    name,
    count,
  }));

  const activeCases = customer
    ? cases.filter((c) => c.customer === customer)
    : cases;
  const visibleItems =
    tab === "customers" && !customer ? customers : activeCases;
  const totalPages = Math.max(1, Math.ceil(visibleItems.length / PAGE_SIZE));
  const pageSlice = visibleItems.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  return (
    <main className="dashboard-main">
      <div className="tabs">
        <button
          className={`tab${tab === "cases" ? " active" : ""}`}
          onClick={() => navigate("/dashboard")}
        >
          Cases
        </button>
        <button
          className={`tab${tab === "customers" ? " active" : ""}`}
          onClick={() => navigate("/dashboard/customers")}
        >
          Customers
        </button>
      </div>

      {tab === "cases" && (
        <>
          <h2>My Cases</h2>
          {cases.length === 0 ? (
            <p className="no-cases">No cases found.</p>
          ) : (
            <>
              <CasesTable
                cases={pageSlice}
                onCaseClick={(c) =>
                  navigate(`/case/${c.id}`, { state: { case: c } })
                }
                onCustomerClick={(name) =>
                  navigate(`/dashboard/customers/${encodeURIComponent(name)}`)
                }
              />
              <Pagination
                page={page}
                totalPages={totalPages}
                setPage={setPage}
              />
            </>
          )}
        </>
      )}

      {tab === "customers" && !customer && (
        <>
          <h2>Customers</h2>
          {customers.length === 0 ? (
            <p className="no-cases">No customers found.</p>
          ) : (
            <>
              <CustomersTable
                customers={pageSlice}
                onSelect={(name) =>
                  navigate(`/dashboard/customers/${encodeURIComponent(name)}`)
                }
              />
              <Pagination
                page={page}
                totalPages={totalPages}
                setPage={setPage}
              />
            </>
          )}
        </>
      )}

      {tab === "customers" && customer && (
        <>
          <div className="section-heading">
            <button
              className="back-btn"
              onClick={() => {
                setShowCreate(false);
                navigate("/dashboard/customers");
              }}
            >
              ← Back
            </button>
            <h2>{customer}</h2>
            <button className="create-btn" onClick={() => setShowCreate(true)}>
              + New Case
            </button>
          </div>
          {activeCases.length === 0 ? (
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
          {showCreate && (
            <CreateCaseModal
              fixedCompanyId={
                cases.find((c) => c.customer === customer)?.company_id || ""
              }
              fixedCustomer={customer}
              currentUsername={user?.full_name || user?.username}
              currentUserId={user?.username}
              onClose={() => setShowCreate(false)}
              onCreated={() => {
                setShowCreate(false);
                loadCases();
              }}
            />
          )}
        </>
      )}
    </main>
  );
}

// ─── Admin user profile view ──────────────────────────────────────────────────

function UserProfileView({ userId, viewerIsSuperAdmin }) {
  const [u, setU] = useState(null);
  const [cases, setCases] = useState([]);
  const [casesPage, setCasesPage] = useState(1);
  const [error, setError] = useState(null);
  const [deleteState, setDeleteState] = useState(null); // null | 'confirm' | 'deleting'
  const [deleteError, setDeleteError] = useState(null);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const stateUser = location.state?.user;
    if (stateUser && stateUser.username === userId) {
      setU(stateUser);
      setForm({
        username: stateUser.username,
        email: stateUser.email,
        full_name: stateUser.full_name || "",
        is_active: stateUser.is_active,
      });
    } else {
      fetch(`${API}/user/${userId}`, { credentials: "include" })
        .then(async (r) => {
          if (!r.ok) {
            setError("User not found.");
            return;
          }
          const data = await r.json();
          setU(data);
          setForm({
            username: data.username,
            email: data.email,
            full_name: data.full_name || "",
            is_active: data.is_active,
          });
        })
        .catch(() => setError("Failed to load user."));
    }
    fetch(`${API}/user/${userId}/cases`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setCases);
  }, [userId]);

  async function handleDelete() {
    setDeleteState("deleting");
    setDeleteError(null);
    try {
      const res = await fetch(`${API}/user/${userId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setDeleteError(data.detail || "Failed to delete user.");
        setDeleteState(null);
        return;
      }
      navigate(-1);
    } catch {
      setDeleteError("Network error.");
      setDeleteState(null);
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      const body = {
        username: form.username,
        email: form.email,
        full_name: form.full_name || null,
        is_active: form.is_active,
      };
      const res = await fetch(`${API}/user/${userId}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setSaveError(data.detail || "Failed to save.");
        return;
      }
      const updated = await res.json();
      setU(updated);
      setForm({
        username: updated.username,
        email: updated.email,
        full_name: updated.full_name || "",
        is_active: updated.is_active,
      });
      setSaveSuccess(true);
    } catch {
      setSaveError("Network error.");
    } finally {
      setSaving(false);
    }
  }

  const role = u
    ? u.is_admin
      ? u.parent_id
        ? "Company admin"
        : "Super admin"
      : "User"
    : "…";
  const initials = u
    ? (u.full_name || u.username).slice(0, 2).toUpperCase()
    : "?";
  const dirty =
    form &&
    u &&
    (form.username !== u.username ||
      form.email !== u.email ||
      (form.full_name || null) !== u.full_name ||
      form.is_active !== u.is_active);

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <h2>User Profile</h2>
        {u &&
          (deleteState === "confirm" ? (
            <div className="delete-confirm">
              <span>Delete this user?</span>
              <button className="back-btn" onClick={() => setDeleteState(null)}>
                Cancel
              </button>
              <button className="delete-btn" onClick={handleDelete}>
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
          ))}
      </div>
      {deleteError && (
        <p className="form-error" style={{ marginBottom: "1rem" }}>
          {deleteError}
        </p>
      )}
      {error ? (
        <p className="no-cases">{error}</p>
      ) : !u || !form ? (
        <p className="no-cases">Loading…</p>
      ) : (
        <>
          <div className="profile-card">
            <div className="profile-header">
              <div className="profile-avatar">{initials}</div>
              <div className="profile-header-info">
                <span className="profile-header-name">
                  {u.full_name || u.username}
                </span>
                <span className="profile-header-role">{role}</span>
              </div>
            </div>
            <div className="profile-fields">
              <div className="profile-field">
                <label>ID</label>
                {viewerIsSuperAdmin ? (
                  <input
                    value={form.username}
                    onChange={(e) => {
                      setForm((f) => ({ ...f, username: e.target.value }));
                      setSaveSuccess(false);
                    }}
                  />
                ) : (
                  <div className="profile-field-static">{u.username}</div>
                )}
              </div>
              <div className="profile-field">
                <label>Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, email: e.target.value }));
                    setSaveSuccess(false);
                  }}
                />
              </div>
              <div className="profile-field">
                <label>Full name</label>
                <input
                  value={form.full_name}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, full_name: e.target.value }));
                    setSaveSuccess(false);
                  }}
                />
              </div>
              <div className="profile-field">
                <label>Status</label>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => {
                      setForm((f) => ({ ...f, is_active: e.target.checked }));
                      setSaveSuccess(false);
                    }}
                  />
                  {form.is_active ? "Active" : "Inactive"}
                </label>
              </div>
            </div>
            {(dirty || saveError || saveSuccess) && (
              <div className="profile-save-row">
                {dirty && (
                  <button
                    className="profile-save-btn"
                    onClick={handleSave}
                    disabled={saving}
                  >
                    {saving ? "Saving…" : "Save changes"}
                  </button>
                )}
                {saveError && <span className="form-error">{saveError}</span>}
                {saveSuccess && (
                  <span className="profile-success">Changes saved.</span>
                )}
              </div>
            )}
          </div>
          <section className="detail-section">
            <h3 className="detail-section-title">
              Cases{" "}
              {cases.length > 0 && (
                <span className="detail-count">({cases.length})</span>
              )}
            </h3>
            {cases.length === 0 ? (
              <p className="no-cases">No cases assigned to this user.</p>
            ) : (
              <>
                <CasesTable
                  cases={cases.slice(
                    (casesPage - 1) * PAGE_SIZE,
                    casesPage * PAGE_SIZE,
                  )}
                  onCaseClick={(c) =>
                    navigate(`/case/${c.id}`, { state: { case: c } })
                  }
                />
                <Pagination
                  page={casesPage}
                  totalPages={Math.max(1, Math.ceil(cases.length / PAGE_SIZE))}
                  setPage={setCasesPage}
                />
              </>
            )}
          </section>
        </>
      )}
    </main>
  );
}

// ─── Profile view ─────────────────────────────────────────────────────────────

function ProfileView({ user }) {
  const [email, setEmail] = useState(user.email);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [cases, setCases] = useState([]);
  const [casesPage, setCasesPage] = useState(1);
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${API}/user/${user.username}/cases`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setCases);
  }, [user.username]);

  const dirty = email !== user.email;
  const role = user.is_admin
    ? user.parent_id
      ? "Company admin"
      : "Super admin"
    : "User";
  const initials = (user.full_name || user.username).slice(0, 2).toUpperCase();

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const res = await fetch(`${API}/user/${user.username}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Failed to save.");
        return;
      }
      setSuccess(true);
    } catch {
      setError("Network error.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="profile-card">
        <div className="profile-header">
          <div className="profile-avatar">{initials}</div>
          <div className="profile-header-info">
            <span className="profile-header-name">
              {user.full_name || user.username}
            </span>
            <span className="profile-header-role">{role}</span>
          </div>
        </div>

        <div className="profile-fields">
          <div className="profile-field">
            <label>ID</label>
            <div className="profile-field-static">{user.username}</div>
          </div>
          <div className="profile-field">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setSuccess(false);
              }}
            />
          </div>
          <div className="profile-field">
            <label>Full name</label>
            <div className="profile-field-static">{user.full_name || "—"}</div>
          </div>
          <div className="profile-field">
            <label>Status</label>
            <div className="profile-badge">
              {user.is_active ? "Active" : "Inactive"}
            </div>
          </div>
        </div>

        {(dirty || error || success) && (
          <div className="profile-save-row">
            {dirty && (
              <button
                className="profile-save-btn"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? "Saving…" : "Save changes"}
              </button>
            )}
            {error && <span className="form-error">{error}</span>}
            {success && <span className="profile-success">Changes saved.</span>}
          </div>
        )}
      </div>

      <section className="detail-section">
        <h3 className="detail-section-title">
          Cases{" "}
          {cases.length > 0 && (
            <span className="detail-count">({cases.length})</span>
          )}
        </h3>
        {cases.length === 0 ? (
          <p className="no-cases">No cases assigned to you.</p>
        ) : (
          <>
            <CasesTable
              cases={cases.slice(
                (casesPage - 1) * PAGE_SIZE,
                casesPage * PAGE_SIZE,
              )}
              onCaseClick={(c) =>
                navigate(`/case/${c.id}`, { state: { case: c } })
              }
            />
            <Pagination
              page={casesPage}
              totalPages={Math.max(1, Math.ceil(cases.length / PAGE_SIZE))}
              setPage={setCasesPage}
            />
          </>
        )}
      </section>
    </>
  );
}

// ─── Create Company modal ─────────────────────────────────────────────────────

function CreateCompanyModal({ companies, onClose, onCreated }) {
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

// ─── Create Case modal ────────────────────────────────────────────────────────

function CreateCaseModal({
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

// ─── Case detail page ─────────────────────────────────────────────────────────

function CaseDetailPage({ caseId }) {
  const location = useLocation();
  const [c, setC] = useState(location.state?.case || null);
  const [docs, setDocs] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loadingCase, setLoadingCase] = useState(!location.state?.case);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingActivity, setLoadingActivity] = useState(true);
  const [deleteState, setDeleteState] = useState(null); // null | 'confirm' | 'deleting'
  const [deleteError, setDeleteError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!location.state?.case) {
      fetch(`${API}/case/${caseId}`, { credentials: "include" })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          setC(data);
          setLoadingCase(false);
        });
    }
    fetch(`${API}/case/${caseId}/documents`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => {
        setDocs(d);
        setLoadingDocs(false);
      });
    fetch(`${API}/case/${caseId}/activity`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((a) => {
        setActivity(a);
        setLoadingActivity(false);
      });
  }, [caseId]);

  async function download(filename) {
    const res = await fetch(`${API}/case/${caseId}/documents/${filename}`, {
      credentials: "include",
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleDelete() {
    setDeleteState("deleting");
    setDeleteError(null);
    try {
      const res = await fetch(`${API}/case/${caseId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setDeleteError(data.detail || "Failed to delete case.");
        setDeleteState(null);
        return;
      }
      navigate(-1);
    } catch {
      setDeleteError("Network error.");
      setDeleteState(null);
    }
  }

  if (loadingCase)
    return (
      <main className="dashboard-main">
        <p className="no-cases">Loading…</p>
      </main>
    );
  if (!c)
    return (
      <main className="dashboard-main">
        <p className="no-cases">Case not found.</p>
      </main>
    );

  return (
    <main className="dashboard-main">
      <div className="section-heading">
        <button className="back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <h2>Case</h2>
        {deleteState === "confirm" ? (
          <div className="delete-confirm">
            <span>Delete this case?</span>
            <button className="back-btn" onClick={() => setDeleteState(null)}>
              Cancel
            </button>
            <button className="delete-btn" onClick={handleDelete}>
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

      <section className="detail-section">
        <h3 className="detail-section-title">Information</h3>
        <CaseDetail c={c} />
      </section>

      <section className="detail-section">
        <h3 className="detail-section-title">Documents</h3>
        {loadingDocs ? (
          <p className="no-cases">Loading…</p>
        ) : docs.length === 0 ? (
          <p className="no-cases">No documents attached.</p>
        ) : (
          <DocumentsTable docs={docs} onDownload={download} />
        )}
      </section>

      <section className="detail-section">
        <h3 className="detail-section-title">Activity</h3>
        {loadingActivity ? (
          <p className="no-cases">Loading…</p>
        ) : activity.length === 0 ? (
          <p className="no-cases">No activity recorded.</p>
        ) : (
          <ActivityTimeline entries={activity} />
        )}
      </section>
    </main>
  );
}

// ─── Shared components ────────────────────────────────────────────────────────

function CasesTable({ cases, onCaseClick, onCustomerClick }) {
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Customer</th>
          <th>Responsible</th>
          <th>Status</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {cases.map((c) => (
          <tr key={c.id}>
            <td className="id">
              {onCaseClick ? (
                <button
                  className="link-btn id-link"
                  onClick={() => onCaseClick(c)}
                >
                  {c.id}
                </button>
              ) : (
                c.id
              )}
            </td>
            <td>
              {onCustomerClick ? (
                <button
                  className="link-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onCustomerClick(c.customer);
                  }}
                >
                  {c.customer}
                </button>
              ) : (
                c.customer
              )}
            </td>
            <td>{c.responsible_person}</td>
            <td>{c.status}</td>
            <td>{new Date(c.created_at).toLocaleDateString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CustomersTable({ customers, onSelect }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Cases</th>
        </tr>
      </thead>
      <tbody>
        {customers.map(({ name, count }) => (
          <tr key={name} className="clickable" onClick={() => onSelect(name)}>
            <td>{name}</td>
            <td>{count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DocumentsTable({ docs, onDownload }) {
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
            <td>
              <button className="link-btn" onClick={() => onDownload(d.name)}>
                Download
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const ACTIVITY_LABELS = {
  case_created: 'Case created',
  status_changed: 'Status changed',
  responsible_changed: 'Responsible person changed',
  document_uploaded: 'Document uploaded',
};

function ActivityTimeline({ entries }) {
  return (
    <ul className="activity-timeline">
      {entries.map((e) => (
        <li key={e.id} className="activity-entry">
          <span className="activity-dot" />
          <div className="activity-body">
            <span className="activity-action">{ACTIVITY_LABELS[e.action] ?? e.action}</span>
            {e.detail && <span className="activity-detail">{e.detail}</span>}
            <span className="activity-meta">
              {e.user_id && <span>{e.user_id}</span>}
              <span>{new Date(e.created_at).toLocaleString()}</span>
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function CaseDetail({ c }) {
  const fields = [
    ["ID", c.id],
    ["Customer", c.customer],
    ["Responsible", c.responsible_person],
    ["Status", c.status],
    ["Created", new Date(c.created_at).toLocaleDateString()],
    [
      "Updated",
      c.updated_at ? new Date(c.updated_at).toLocaleDateString() : "—",
    ],
  ];
  return (
    <div className="case-detail">
      {fields.map(([label, value]) => (
        <div key={label} className="case-detail-row">
          <span className="case-detail-label">{label}</span>
          <span className="case-detail-value">{value}</span>
        </div>
      ))}
    </div>
  );
}

function Pagination({ page, totalPages, setPage }) {
  if (totalPages <= 1) return null;
  return (
    <div className="pagination">
      <button onClick={() => setPage((p) => p - 1)} disabled={page === 1}>
        Previous
      </button>
      <span>
        {page} / {totalPages}
      </span>
      <button
        onClick={() => setPage((p) => p + 1)}
        disabled={page === totalPages}
      >
        Next
      </button>
    </div>
  );
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
