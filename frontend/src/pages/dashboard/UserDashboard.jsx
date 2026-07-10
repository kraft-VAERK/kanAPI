import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { API, PAGE_SIZE } from "./constants";
import { CasesTable } from "./CasesTable";
import { CaseSearchBar } from "./CaseSearchBar";
import { CustomersTable } from "./CustomersTable";
import { Pagination } from "./Pagination";
import { CreateCaseModal } from "./CreateCaseModal";
import { useDebouncedValue, usePagination } from "./hooks";
import { caseQueryString, deriveCustomers } from "./utils";

export function UserDashboard({ user }) {
  const { customer: rawCustomer } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const customer = rawCustomer ? decodeURIComponent(rawCustomer) : null;
  const tab = location.pathname.startsWith("/dashboard/customers")
    ? "customers"
    : "cases";

  const [cases, setCases] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [searchQ, setSearchQ] = useState("");
  const [searchStatus, setSearchStatus] = useState("");
  const [searchArchived, setSearchArchived] = useState("");
  const [myResponsible, setMyResponsible] = useState(false);
  const debouncedQ = useDebouncedValue(searchQ);
  const [page, setPage] = usePagination([tab, customer, debouncedQ, searchStatus, searchArchived, myResponsible]);

  function fetchCases(q, status, archived) {
    fetch(`${API}/case/${caseQueryString(q, status, archived)}`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then(setCases);
  }

  useEffect(() => {
    fetchCases(debouncedQ, searchStatus, searchArchived);
  }, [debouncedQ, searchStatus, searchArchived]);

  const customers = deriveCustomers(cases);

  const filteredCases = myResponsible
    ? cases.filter((c) => c.responsible_user_id === user?.username)
    : cases;
  const activeCases = customer
    ? filteredCases.filter((c) => c.customer === customer)
    : filteredCases;
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
                onCustomerClick={(name, companyId) =>
                  navigate(`/customer/${companyId}`, { state: { customerName: name } })
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
              currentUsername={user?.full_name || user?.username}
              currentUserId={user?.username}
              onClose={() => setShowCreate(false)}
              onCreated={() => {
                setShowCreate(false);
                fetchCases(debouncedQ, searchStatus, searchArchived);
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
                onSelect={(name, companyId) =>
                  navigate(`/customer/${companyId}`, { state: { customerName: name } })
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
    </main>
  );
}
