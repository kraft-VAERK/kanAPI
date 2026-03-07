import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const API = '/api/v1'
const PAGE_SIZE = 10

// ─── Root ────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [user, setUser] = useState(null)
  const [globalCase, setGlobalCase] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    fetch(`${API}/auth/me`, { credentials: 'include' })
      .then(async r => {
        if (!r.ok) { navigate('/', { replace: true }); return }
        setUser(await r.json())
      })
      .catch(() => navigate('/', { replace: true }))
  }, [navigate])

  async function handleLogout() {
    await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' })
    navigate('/', { replace: true })
  }

  if (!user) return null

  const isSuperAdmin = user.is_admin && !user.parent_id
  const isCompanyAdmin = user.is_admin && !!user.parent_id

  const header = (
    <header className='dashboard-header'>
      <span>{user.username}</span>
      <button onClick={handleLogout}>Sign out</button>
    </header>
  )

  function handleCaseDeleted() {
    setGlobalCase(null)
    setRefreshKey(k => k + 1)
  }

  if (globalCase) return (
    <>
      {header}
      <CaseDetailPage c={globalCase} onBack={() => setGlobalCase(null)} onDeleted={handleCaseDeleted} />
    </>
  )

  return (
    <>
      {header}
      {isSuperAdmin
        ? <SuperAdminDashboard key={refreshKey} onOpenCase={setGlobalCase} user={user} />
        : isCompanyAdmin
          ? <CompanyAdminDashboard key={refreshKey} onOpenCase={setGlobalCase} user={user} />
          : <UserDashboard key={refreshKey} onOpenCase={setGlobalCase} user={user} />
      }
    </>
  )
}

// ─── Super admin view ─────────────────────────────────────────────────────────

function SuperAdminDashboard({ onOpenCase, user }) {
  const [view, setView] = useState('companies')
  const [companies, setCompanies] = useState([])
  const [selectedCompany, setSelectedCompany] = useState(null)
  const [companyCases, setCompanyCases] = useState([])
  const [companyClients, setCompanyClients] = useState([])
  const [companyUsers, setCompanyUsers] = useState([])
  const [selectedClient, setSelectedClient] = useState(null)
  const [companyTab, setCompanyTab] = useState('cases')
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const [showCreateCase, setShowCreateCase] = useState(false)

  function loadCompanies() {
    fetch(`${API}/company/`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : [])
      .then(setCompanies)
  }

  useEffect(() => { loadCompanies() }, [])

  async function openCompany(company) {
    const [casesRes, usersRes] = await Promise.all([
      fetch(`${API}/company/${company.id}/cases`, { credentials: 'include' }),
      fetch(`${API}/company/${company.id}/users`, { credentials: 'include' }),
    ])
    const cases = casesRes.ok ? await casesRes.json() : []
    const users = usersRes.ok ? await usersRes.json() : []
    const customerMap = {}
    for (const c of cases) customerMap[c.customer] = (customerMap[c.customer] || 0) + 1
    setCompanyCases(cases)
    setCompanyClients(Object.entries(customerMap).map(([name, count]) => ({ name, count })))
    setCompanyUsers(users)
    setSelectedCompany(company)
    setCompanyTab('cases')
    setSelectedClient(null)
    setPage(1)
    setView('company')
  }

  async function reloadCompanyCases() {
    const casesRes = await fetch(`${API}/company/${selectedCompany.id}/cases`, { credentials: 'include' })
    const cases = casesRes.ok ? await casesRes.json() : []
    const customerMap = {}
    for (const c of cases) customerMap[c.customer] = (customerMap[c.customer] || 0) + 1
    setCompanyCases(cases)
    setCompanyClients(Object.entries(customerMap).map(([name, count]) => ({ name, count })))
  }

  function backToCompanies() {
    setSelectedCompany(null)
    setCompanyCases([])
    setCompanyClients([])
    setCompanyUsers([])
    setSelectedClient(null)
    setShowCreateCase(false)
    setPage(1)
    setView('companies')
  }

  function switchCompanyTab(t) { setCompanyTab(t); setSelectedClient(null); setPage(1) }

  const filteredCases = selectedClient ? companyCases.filter(c => c.customer === selectedClient) : companyCases
  const companyViewItems = companyTab === 'clients' && !selectedClient ? companyClients
    : companyTab === 'clients' ? filteredCases
    : companyCases
  const totalPages = Math.max(1, Math.ceil(
    view === 'companies' ? companies.length / PAGE_SIZE : companyViewItems.length / PAGE_SIZE
  ))

  return (
    <main className='dashboard-main'>
      {view === 'companies' && (
        <>
          <div className='section-heading'>
            <h2>Companies</h2>
            <button className='create-btn' onClick={() => setShowCreate(true)}>+ Add Company</button>
          </div>
          {companies.length === 0
            ? <p className='no-cases'>No companies found.</p>
            : (
              <>
                <table>
                  <thead><tr><th>Name</th><th>Email</th><th>Phone</th></tr></thead>
                  <tbody>
                    {companies
                      .slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
                      .map(c => (
                        <tr key={c.id} className='clickable' onClick={() => openCompany(c)}>
                          <td>{c.name}</td>
                          <td>{c.email || '—'}</td>
                          <td>{c.phone || '—'}</td>
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
              onCreated={() => { setShowCreate(false); loadCompanies() }}
            />
          )}
        </>
      )}

      {view === 'company' && (
        <>
          <div className='section-heading'>
            <button className='back-btn' onClick={backToCompanies}>← Companies</button>
            <h2>{selectedCompany?.name}</h2>
          </div>
          <div className='tabs'>
            <button className={`tab${companyTab === 'cases' ? ' active' : ''}`} onClick={() => switchCompanyTab('cases')}>Cases</button>
            <button className={`tab${companyTab === 'clients' ? ' active' : ''}`} onClick={() => switchCompanyTab('clients')}>Clients</button>
          </div>

          {companyTab === 'cases' && (
            companyCases.length === 0
              ? <p className='no-cases'>No cases for this company.</p>
              : <><CasesTable cases={companyCases.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)} onCaseClick={onOpenCase} /><Pagination page={page} totalPages={totalPages} setPage={setPage} /></>
          )}

          {companyTab === 'clients' && !selectedClient && (
            companyClients.length === 0
              ? <p className='no-cases'>No clients for this company.</p>
              : <><CustomersTable customers={companyClients.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)} onSelect={name => { setSelectedClient(name); setPage(1) }} /><Pagination page={page} totalPages={totalPages} setPage={setPage} /></>
          )}

          {companyTab === 'clients' && selectedClient && (
            <>
              <div className='section-heading'>
                <button className='back-btn' onClick={() => { setSelectedClient(null); setPage(1); setShowCreateCase(false) }}>← Clients</button>
                <h2>{selectedClient}</h2>
                <button className='create-btn' onClick={() => setShowCreateCase(true)}>+ Add Case</button>
              </div>
              {filteredCases.length === 0
                ? <p className='no-cases'>No cases for this client.</p>
                : <><CasesTable cases={filteredCases.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)} onCaseClick={onOpenCase} /><Pagination page={page} totalPages={totalPages} setPage={setPage} /></>
              }
              {showCreateCase && (
                <CreateCaseModal
                  fixedCompanyId={selectedCompany.id}
                  fixedCustomer={selectedClient}
                  users={companyUsers}
                  onClose={() => setShowCreateCase(false)}
                  onCreated={() => { setShowCreateCase(false); reloadCompanyCases() }}
                />
              )}
            </>
          )}
        </>
      )}
    </main>
  )
}

// ─── Create Company modal ─────────────────────────────────────────────────────

function CreateCompanyModal({ companies, onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', email: '', phone: '', address: '', owner_id: '' })
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  function set(field, value) { setForm(f => ({ ...f, [field]: value })) }

  async function submit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setError('Name is required.'); return }
    setSaving(true)
    setError(null)
    const body = {
      name: form.name.trim(),
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      address: form.address.trim() || null,
      owner_id: form.owner_id || null,
    }
    try {
      const res = await fetch(`${API}/company/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Failed to create company.')
        return
      }
      onCreated()
    } catch {
      setError('Network error.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className='modal-overlay' onClick={onClose}>
      <div className='modal' onClick={e => e.stopPropagation()}>
        <h3>Add Company</h3>
        <form onSubmit={submit}>
          <label>Name *<input value={form.name} onChange={e => set('name', e.target.value)} /></label>
          <label>Email<input type='email' value={form.email} onChange={e => set('email', e.target.value)} /></label>
          <label>Phone<input value={form.phone} onChange={e => set('phone', e.target.value)} /></label>
          <label>Address<input value={form.address} onChange={e => set('address', e.target.value)} /></label>
          <label>Owner (optional)
            <select value={form.owner_id} onChange={e => set('owner_id', e.target.value)}>
              <option value=''>— None (top-level) —</option>
              {companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          {error && <p className='form-error'>{error}</p>}
          <div className='modal-actions'>
            <button type='button' onClick={onClose}>Cancel</button>
            <button type='submit' disabled={saving}>{saving ? 'Saving…' : 'Create'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Company admin view ───────────────────────────────────────────────────────

function CompanyAdminDashboard({ onOpenCase, user }) {
  const [cases, setCases] = useState([])
  const [users, setUsers] = useState([])
  const [tab, setTab] = useState('cases')
  const [selectedCustomer, setSelectedCustomer] = useState(null)
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)

  function loadCases() {
    fetch(`${API}/company/my-cases`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : []).then(setCases)
  }

  useEffect(() => {
    loadCases()
    fetch(`${API}/company/my-users`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : []).then(setUsers)
  }, [])

  function switchTab(t) { setTab(t); setSelectedCustomer(null); setPage(1) }
  function selectCustomer(name) { setSelectedCustomer(name); setPage(1) }

  const customerMap = {}
  for (const c of cases) customerMap[c.customer] = (customerMap[c.customer] || 0) + 1
  const customers = Object.entries(customerMap).map(([name, count]) => ({ name, count }))

  const activeCases = selectedCustomer ? cases.filter(c => c.customer === selectedCustomer) : cases
  const visibleItems = tab === 'customers' && !selectedCustomer ? customers
    : tab === 'users' ? users
    : activeCases
  const totalPages = Math.max(1, Math.ceil(visibleItems.length / PAGE_SIZE))
  const pageSlice = visibleItems.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <main className='dashboard-main'>
      <div className='tabs'>
        <button className={`tab${tab === 'cases' ? ' active' : ''}`} onClick={() => switchTab('cases')}>Cases</button>
        <button className={`tab${tab === 'customers' ? ' active' : ''}`} onClick={() => switchTab('customers')}>Customers</button>
        <button className={`tab${tab === 'users' ? ' active' : ''}`} onClick={() => switchTab('users')}>Users</button>
      </div>

      {tab === 'cases' && (
        <>
          <h2>All Cases</h2>
          {cases.length === 0
            ? <p className='no-cases'>No cases found.</p>
            : <><CasesTable cases={pageSlice} onCaseClick={onOpenCase} onCustomerClick={name => { setTab('customers'); selectCustomer(name) }} /><Pagination page={page} totalPages={totalPages} setPage={setPage} /></>
          }
        </>
      )}

      {tab === 'customers' && !selectedCustomer && (
        <>
          <h2>Customers</h2>
          {customers.length === 0
            ? <p className='no-cases'>No customers found.</p>
            : <><CustomersTable customers={pageSlice} onSelect={selectCustomer} /><Pagination page={page} totalPages={totalPages} setPage={setPage} /></>
          }
        </>
      )}

      {tab === 'customers' && selectedCustomer && (
        <>
          <div className='section-heading'>
            <button className='back-btn' onClick={() => { setSelectedCustomer(null); setPage(1); setShowCreate(false) }}>← Back</button>
            <h2>{selectedCustomer}</h2>
            <button className='create-btn' onClick={() => setShowCreate(true)}>+ Add Case</button>
          </div>
          {activeCases.length === 0
            ? <p className='no-cases'>No cases for this customer.</p>
            : <><CasesTable cases={pageSlice} onCaseClick={onOpenCase} /><Pagination page={page} totalPages={totalPages} setPage={setPage} /></>
          }
          {showCreate && (
            <CreateCaseModal
              fixedCompanyId={cases.find(c => c.customer === selectedCustomer)?.company_id || ''}
              fixedCustomer={selectedCustomer}
              users={[user, ...users]}
              onClose={() => setShowCreate(false)}
              onCreated={() => { setShowCreate(false); loadCases() }}
            />
          )}
        </>
      )}

      {tab === 'users' && (
        <>
          <h2>Users</h2>
          {users.length === 0
            ? <p className='no-cases'>No users found.</p>
            : (
              <>
                <table>
                  <thead><tr><th>Name</th><th>Username</th><th>Email</th></tr></thead>
                  <tbody>
                    {pageSlice.map(u => (
                      <tr key={u.id}>
                        <td>{u.full_name || '—'}</td>
                        <td>{u.username}</td>
                        <td>{u.email}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <Pagination page={page} totalPages={totalPages} setPage={setPage} />
              </>
            )}
        </>
      )}
    </main>
  )
}

// ─── Regular user view ────────────────────────────────────────────────────────

function UserDashboard({ onOpenCase, user }) {
  const [cases, setCases] = useState([])
  const [tab, setTab] = useState('cases')
  const [selectedCustomer, setSelectedCustomer] = useState(null)
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)

  function loadCases() {
    fetch(`${API}/case/`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : [])
      .then(setCases)
  }

  useEffect(() => { loadCases() }, [])

  function switchTab(t) { setTab(t); setSelectedCustomer(null); setPage(1) }
  function selectCustomer(name) { setSelectedCustomer(name); setPage(1) }

  const customerMap = {}
  for (const c of cases) customerMap[c.customer] = (customerMap[c.customer] || 0) + 1
  const customers = Object.entries(customerMap).map(([name, count]) => ({ name, count }))

  const activeCases = selectedCustomer ? cases.filter(c => c.customer === selectedCustomer) : cases
  const visibleItems = tab === 'customers' && !selectedCustomer ? customers : activeCases
  const totalPages = Math.max(1, Math.ceil(visibleItems.length / PAGE_SIZE))
  const pageSlice = visibleItems.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <main className='dashboard-main'>
      <div className='tabs'>
        <button className={`tab${tab === 'cases' ? ' active' : ''}`} onClick={() => switchTab('cases')}>Cases</button>
        <button className={`tab${tab === 'customers' ? ' active' : ''}`} onClick={() => switchTab('customers')}>Customers</button>
      </div>

      {tab === 'cases' && (
        <>
          <h2>My Cases</h2>
          {cases.length === 0
            ? <p className='no-cases'>No cases found.</p>
            : <><CasesTable cases={pageSlice} onCaseClick={onOpenCase} onCustomerClick={name => { setTab('customers'); selectCustomer(name) }} /><Pagination page={page} totalPages={totalPages} setPage={setPage} /></>
          }
        </>
      )}

      {tab === 'customers' && !selectedCustomer && (
        <>
          <h2>Customers</h2>
          {customers.length === 0
            ? <p className='no-cases'>No customers found.</p>
            : <><CustomersTable customers={pageSlice} onSelect={selectCustomer} /><Pagination page={page} totalPages={totalPages} setPage={setPage} /></>
          }
        </>
      )}

      {tab === 'customers' && selectedCustomer && (
        <>
          <div className='section-heading'>
            <button className='back-btn' onClick={() => { setSelectedCustomer(null); setPage(1); setShowCreate(false) }}>← Back</button>
            <h2>{selectedCustomer}</h2>
            <button className='create-btn' onClick={() => setShowCreate(true)}>+ New Case</button>
          </div>
          {activeCases.length === 0
            ? <p className='no-cases'>No cases for this customer.</p>
            : <><CasesTable cases={pageSlice} onCaseClick={onOpenCase} /><Pagination page={page} totalPages={totalPages} setPage={setPage} /></>
          }
          {showCreate && (
            <CreateCaseModal
              fixedCompanyId={cases.find(c => c.customer === selectedCustomer)?.company_id || ''}
              fixedCustomer={selectedCustomer}
              currentUsername={user?.full_name || user?.username}
              onClose={() => setShowCreate(false)}
              onCreated={() => { setShowCreate(false); loadCases() }}
            />
          )}
        </>
      )}
    </main>
  )
}

// ─── Create Case modal ────────────────────────────────────────────────────────

// Props:
//   fixedCompanyId  — company ID inferred from context (always required)
//   fixedCustomer   — if set, pre-fill customer and hide the field
//   users           — if set (array), show a dropdown for responsible person
//   currentUsername — if set (and no users), auto-assign and show as read-only
function CreateCaseModal({ onClose, onCreated, fixedCompanyId = null, fixedCustomer = null, users = null, currentUsername = null }) {
  const [form, setForm] = useState({ responsible_person: '', status: 'open', customer: fixedCustomer || '' })
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  function set(field, value) { setForm(f => ({ ...f, [field]: value })) }

  async function submit(e) {
    e.preventDefault()
    const responsible = users ? form.responsible_person : currentUsername
    if (!responsible) { setError('Responsible person is required.'); return }
    if (!form.customer.trim()) { setError('Customer is required.'); return }
    if (!fixedCompanyId) { setError('Client company is required.'); return }
    setSaving(true)
    setError(null)
    try {
      const res = await fetch(`${API}/case/create`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          responsible_person: responsible,
          status: form.status,
          customer: form.customer.trim(),
          company_id: fixedCompanyId,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError(data.detail || 'Failed to create case.')
        return
      }
      onCreated()
    } catch {
      setError('Network error.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className='modal-overlay' onClick={onClose}>
      <div className='modal' onClick={e => e.stopPropagation()}>
        <h3>New Case</h3>
        <form onSubmit={submit}>
          {!fixedCustomer && (
            <label>Customer / Contact *
              <input value={form.customer} onChange={e => set('customer', e.target.value)} placeholder='Person or organisation name' />
            </label>
          )}
          {users ? (
            <label>Responsible Person *
              <select value={form.responsible_person} onChange={e => set('responsible_person', e.target.value)}>
                <option value=''>— Select a user —</option>
                {users.map(u => <option key={u.id} value={u.full_name || u.username}>{u.full_name || u.username}</option>)}
              </select>
            </label>
          ) : (
            <label>Responsible Person
              <input value={currentUsername || ''} readOnly />
            </label>
          )}
          <label>Status
            <select value={form.status} onChange={e => set('status', e.target.value)}>
              <option value='open'>Open</option>
              <option value='in_progress'>In Progress</option>
              <option value='pending'>Pending</option>
              <option value='closed'>Closed</option>
            </select>
          </label>
          {error && <p className='form-error'>{error}</p>}
          <div className='modal-actions'>
            <button type='button' onClick={onClose}>Cancel</button>
            <button type='submit' disabled={saving}>{saving ? 'Saving…' : 'Create'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Case detail page ─────────────────────────────────────────────────────────

function CaseDetailPage({ c, onBack, onDeleted }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [deleteState, setDeleteState] = useState(null) // null | 'confirm' | 'deleting'
  const [deleteError, setDeleteError] = useState(null)

  useEffect(() => {
    fetch(`${API}/case/${c.id}/documents`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : [])
      .then(d => { setDocs(d); setLoading(false) })
  }, [c.id])

  async function download(filename) {
    const res = await fetch(`${API}/case/${c.id}/documents/${filename}`, { credentials: 'include' })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handleDelete() {
    setDeleteState('deleting')
    setDeleteError(null)
    try {
      const res = await fetch(`${API}/case/${c.id}`, { method: 'DELETE', credentials: 'include' })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setDeleteError(data.detail || 'Failed to delete case.')
        setDeleteState(null)
        return
      }
      onDeleted()
    } catch {
      setDeleteError('Network error.')
      setDeleteState(null)
    }
  }

  return (
    <main className='dashboard-main'>
      <div className='section-heading'>
        <button className='back-btn' onClick={onBack}>← Back</button>
        <h2>Case</h2>
        {deleteState === 'confirm'
          ? (
            <div className='delete-confirm'>
              <span>Delete this case?</span>
              <button className='back-btn' onClick={() => setDeleteState(null)}>Cancel</button>
              <button className='delete-btn' onClick={handleDelete}>Confirm</button>
            </div>
          )
          : (
            <button className='delete-btn' onClick={() => setDeleteState('confirm')}>
              Delete
            </button>
          )
        }
      </div>
      {deleteError && <p className='form-error' style={{ marginBottom: '1rem' }}>{deleteError}</p>}

      <section className='detail-section'>
        <h3 className='detail-section-title'>Information</h3>
        <CaseDetail c={c} />
      </section>

      <section className='detail-section'>
        <h3 className='detail-section-title'>Documents</h3>
        {loading
          ? <p className='no-cases'>Loading…</p>
          : docs.length === 0
            ? <p className='no-cases'>No documents attached.</p>
            : <DocumentsTable docs={docs} onDownload={download} />
        }
      </section>
    </main>
  )
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
        {cases.map(c => (
          <tr key={c.id}>
            <td className='id'>
              {onCaseClick
                ? <button className='link-btn id-link' onClick={() => onCaseClick(c)}>{c.id}</button>
                : c.id}
            </td>
            <td>
              {onCustomerClick
                ? <button className='link-btn' onClick={e => { e.stopPropagation(); onCustomerClick(c.customer) }}>{c.customer}</button>
                : c.customer}
            </td>
            <td>{c.responsible_person}</td>
            <td>{c.status}</td>
            <td>{new Date(c.created_at).toLocaleDateString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function CustomersTable({ customers, onSelect }) {
  return (
    <table>
      <thead><tr><th>Name</th><th>Cases</th></tr></thead>
      <tbody>
        {customers.map(({ name, count }) => (
          <tr key={name} className='clickable' onClick={() => onSelect(name)}>
            <td>{name}</td>
            <td>{count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function DocumentsTable({ docs, onDownload }) {
  return (
    <table>
      <thead>
        <tr><th>File</th><th>Size</th><th>Modified</th><th></th></tr>
      </thead>
      <tbody>
        {docs.map(d => (
          <tr key={d.name}>
            <td>{d.name}</td>
            <td>{formatBytes(d.size)}</td>
            <td>{new Date(d.last_modified).toLocaleDateString()}</td>
            <td>
              <button className='link-btn' onClick={() => onDownload(d.name)}>Download</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function CaseDetail({ c }) {
  const fields = [
    ['ID',          c.id],
    ['Customer',    c.customer],
    ['Responsible', c.responsible_person],
    ['Status',      c.status],
    ['Created',     new Date(c.created_at).toLocaleDateString()],
    ['Updated',     c.updated_at ? new Date(c.updated_at).toLocaleDateString() : '—'],
  ]
  return (
    <div className='case-detail'>
      {fields.map(([label, value]) => (
        <div key={label} className='case-detail-row'>
          <span className='case-detail-label'>{label}</span>
          <span className='case-detail-value'>{value}</span>
        </div>
      ))}
    </div>
  )
}

function Pagination({ page, totalPages, setPage }) {
  if (totalPages <= 1) return null
  return (
    <div className='pagination'>
      <button onClick={() => setPage(p => p - 1)} disabled={page === 1}>Previous</button>
      <span>{page} / {totalPages}</span>
      <button onClick={() => setPage(p => p + 1)} disabled={page === totalPages}>Next</button>
    </div>
  )
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}
