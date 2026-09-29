import { requestJson } from './httpClient.js';

export async function loadSession() {
  return requestJson('/auth/session');
}

export function startLogin() {
  globalThis.location.assign('/auth/login');
}

export async function logout() {
  return requestJson('/auth/logout', { method: 'POST' });
}

export const authClient = { loadSession, startLogin, logout };
