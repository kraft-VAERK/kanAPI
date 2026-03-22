import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { API, PAGE_SIZE } from "./constants";
import { CasesTable } from "./CasesTable";
import { CaseSearchBar } from "./CaseSearchBar";
import { CustomersTable } from "./CustomersTable";
import { Pagination } from "./Pagination";
import { CreateCaseModal } from "./CreateCaseModal";

export function CompanyAdminDashboard({ user }) {
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
  const [searchQ, setSearchQ] = useState("");
  const [searchStatus, setSearchStatus] = useState("");
  const [searchArchived, setSearchArchived] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [myResponsible, setMyResponsible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(searchQ), 300);
    return () => clearTimeout(t);
  }, [searchQ]);

  function loadCases(q, status, archived) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    if (archived !== "") params.set("archived", archived);
    const qs = params.toString();
    fetch(`${API}/company/my-cases${qs ? `?${qs}` : ""}`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setCases);
  }

  useEffect(() => {
    loadCases(debouncedQ, searchStatus, searchArchived);
  }, [debouncedQ, searchStatus, searchArchived]);

  useEffect(() => {
    fetch(`${API}/company/my-users`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setUsers);
  }, []);

  useEffect(() => {
    setPage(1);
  }, [tab, customer, debouncedQ, searchStatus, searchArchived, myResponsible]);

  const customerMap = {};
  for (const c of cases) {
    const key = `${c.customer}\0${c.company_id}`;
    if (!customerMap[key]) customerMap[key] = { name: c.customer, count: 0, company_id: c.company_id };
    customerMap[key].count += 1;
  }
  const customers = Object.values(customerMap);

  const filteredCases = myResponsible
    ? cases.filter((c) => c.responsible_user_id === user?.username)
    : cases;
  const activeCases = customer
    ? filteredCases.filter((c) => c.customer === customer)
    : filteredCases;
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
          <div className="section-heading">
            <h2>Cases</h2>
          </div>
          <CaseSearchBar
            q={searchQ}
            onQChange={setSearchQ}
            status={searchStatus}
            onStatusChange={setSearchStatus}
            archived={searchArchived}
            onArchivedChange={setSearchArchived}
            responsible={myResponsible}
            onResponsibleChange={(v) => { setMyResponsible(v); setPage(1); }}
            onCreate={() => setShowCreate(true)}
          />
          {cases.length === 0 ? (
            <p className="no-cases">No cases found.</p>
          ) : (
            <>
              <CasesTable
                cases={pageSlice}
                onCaseClick={(c) =>
                  navigate(`/case/${c.id}`, { state: { case: c } })
                }
                onCustomerClick={(name, cId) =>
                  navigate(`/customer/${cId}`, { state: { customerName: name } })
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
              customers={customers}
              users={[user, ...users]}
              onClose={() => setShowCreate(false)}
              onCreated={() => {
                setShowCreate(false);
                loadCases(debouncedQ, searchStatus, searchArchived);
              }}
            />
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
                onSelect={(name, cId) =>
                  navigate(`/customer/${cId}`, { state: { customerName: name } })
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
          </div>
          <CaseSearchBar
            q={searchQ}
            onQChange={setSearchQ}
            status={searchStatus}
            onStatusChange={setSearchStatus}
            archived={searchArchived}
            onArchivedChange={setSearchArchived}
            responsible={myResponsible}
            onResponsibleChange={(v) => { setMyResponsible(v); setPage(1); }}
          />
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
