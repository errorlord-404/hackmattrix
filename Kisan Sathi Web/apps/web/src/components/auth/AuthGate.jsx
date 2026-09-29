import { useEffect, useState } from 'react';
import { loadSession, startLogin } from '../../api/authClient.js';

export default function AuthGate({ children }) {
  const [state, setState] = useState({ status: 'checking', error: null });
  const check = () => {
    setState({ status: 'checking', error: null });
    loadSession().then(() => setState({ status: 'authenticated', error: null })).catch((error) => setState({ status: error?.status === 401 ? 'unauthenticated' : 'error', error }));
  };
  useEffect(() => { check(); }, []);
  if (state.status === 'authenticated') return children;
  if (state.status === 'checking') return <main className="auth-gate" aria-busy="true"><p>Checking your secure field session…</p></main>;
  return <main className="auth-gate"><h1>Sign in to Kisan Sathi</h1><p>{state.status === 'unauthenticated' ? 'Your field data is private to your account.' : 'The secure session service is temporarily unavailable.'}</p><div className="auth-actions"><button type="button" onClick={startLogin}>Continue securely</button><button type="button" onClick={check}>Try again</button></div></main>;
}
