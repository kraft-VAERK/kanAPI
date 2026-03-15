import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const API = '/api/v1'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    const res = await fetch(`${API}/user/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    })

    if (res.ok) {
      await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      })
      navigate('/dashboard', { replace: true })
    } else {
      const data = await res.json().catch(() => ({}))
      setError(data.detail || 'Registration failed')
    }
  }

  return (
    <div className='auth-page'>
      <h1>kanAPI</h1>
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
        <button type='submit'>Create account</button>
        {error && <p className='error'>{error}</p>}
        <p className='switch'>
          Already have an account? <Link to='/'>Sign in</Link>
        </p>
      </form>
    </div>
  )
}
