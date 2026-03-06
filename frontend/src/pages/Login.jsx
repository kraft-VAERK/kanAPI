import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const API = '/api/v1'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    fetch(`${API}/auth/me`, { credentials: 'include' })
      .then(r => { if (r.ok) navigate('/dashboard', { replace: true }) })
      .catch(() => {})
  }, [navigate])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    })

    if (res.ok) {
      navigate('/dashboard', { replace: true })
    } else {
      const data = await res.json().catch(() => ({}))
      setError(data.detail || 'Login failed')
    }
  }

  return (
    <div className='auth-page'>
      <div className='auth-logo'>
        <span className='auth-logo-mouse'>🐭</span>
        <h1>kanAPI</h1>
        <p className='auth-logo-motto'>Managing cases, one mouse at a time.</p>
      </div>
      <form className='auth-form' onSubmit={handleSubmit} autoComplete='on'>
        <label>
          Email
          <input
            type='email'
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder='you@example.com'
            required
            autoFocus
          />
        </label>
        <label>
          Password
          <input
            type='password'
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder='••••••••'
            required
          />
        </label>
        <button type='submit'>Sign in</button>
        {error && <p className='error'>{error}</p>}
        <p className='switch'>
          No account? <Link to='/register'>Create one</Link>
        </p>
      </form>
    </div>
  )
}
