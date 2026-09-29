import { getFarmerId } from '../api/client.js';

function storageKey() {
  return `kisansathi-finance-ledger:${getFarmerId()}`;
}

export function loadTransactions() {
  try {
    const stored = localStorage.getItem(storageKey());
    const records = stored ? JSON.parse(stored) : [];
    return Array.isArray(records) ? records : [];
  } catch {
    return [];
  }
}

export function saveTransaction(transaction) {
  const next = [{ ...transaction, id: globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}` }, ...loadTransactions()];
  localStorage.setItem(storageKey(), JSON.stringify(next));
  return next;
}

export function removeTransaction(id) {
  const next = loadTransactions().filter((transaction) => transaction.id !== id);
  localStorage.setItem(storageKey(), JSON.stringify(next));
  return next;
}
