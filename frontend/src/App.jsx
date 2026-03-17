import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path='/' element={<Login />} />
        <Route path='/register' element={<Register />} />
        {/* Shared case detail + edit */}
        <Route path='/case/:caseId' element={<Dashboard />} />
        <Route path='/case/:caseId/edit' element={<Dashboard />} />
        {/* Super admin: company drill-down */}
        <Route path='/company/:companyId' element={<Dashboard />} />
        <Route path='/company/:companyId/clients' element={<Dashboard />} />
        <Route path='/company/:companyId/clients/:customer' element={<Dashboard />} />
        <Route path='/company/:companyId/users' element={<Dashboard />} />
        <Route path='/user/:userId' element={<Dashboard />} />
        {/* Company admin + regular user */}
        <Route path='/dashboard' element={<Dashboard />} />
        <Route path='/dashboard/customers' element={<Dashboard />} />
        <Route path='/dashboard/customers/:customer' element={<Dashboard />} />
        <Route path='/dashboard/users' element={<Dashboard />} />
        <Route path='/dashboard/profile' element={<Dashboard />} />
        <Route path='*' element={<Navigate to='/' replace />} />
      </Routes>
    </BrowserRouter>
  )
}
