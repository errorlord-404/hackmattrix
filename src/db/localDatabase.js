/**
 * KisanSathi Local Client-Side Database Engine
 * -------------------------------------------------------------
 * Provides an offline-first, private storage layer on the farmer's device.
 * Stores sensitive private financial ledgers, soil test records,
 * and hyperlocal weather/AI caches locally without sending private data to cloud.
 */

const DB_NAME = 'KisanSathiLocalDB';
const DB_VERSION = 1;

class LocalDatabase {
  constructor() {
    this.db = null;
    this.initPromise = this._initDB();
  }

  _initDB() {
    return new Promise((resolve) => {
      if (typeof window === 'undefined' || !window.indexedDB) {
        console.warn('IndexedDB not supported in current environment, using memory/localStorage fallback.');
        resolve(null);
        return;
      }

      const request = window.indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // 1. Private Farm Finance Ledger Store
        if (!db.objectStoreNames.contains('finance_ledger')) {
          const store = db.createObjectStore('finance_ledger', { keyPath: 'id', autoIncrement: true });
          store.createIndex('date', 'date', { unique: false });
          store.createIndex('type', 'type', { unique: false });
          store.createIndex('category', 'category', { unique: false });
          store.createIndex('crop', 'crop', { unique: false });
        }

        // 2. Field Soil Test Logs Store
        if (!db.objectStoreNames.contains('soil_logs')) {
          const store = db.createObjectStore('soil_logs', { keyPath: 'id', autoIncrement: true });
          store.createIndex('field_id', 'field_id', { unique: false });
          store.createIndex('date', 'date', { unique: false });
        }

        // 3. Hyperlocal Weather Cache Store
        if (!db.objectStoreNames.contains('weather_cache')) {
          db.createObjectStore('weather_cache', { keyPath: 'key' });
        }

        // 4. Offline AI Assistant Query Cache Store
        if (!db.objectStoreNames.contains('offline_ai_cache')) {
          db.createObjectStore('offline_ai_cache', { keyPath: 'prompt_hash' });
        }
      };

      request.onsuccess = (event) => {
        this.db = event.target.result;
        this._seedDefaultDataIfEmpty();
        resolve(this.db);
      };

      request.onerror = (event) => {
        console.error('IndexedDB open error:', event.target.error);
        resolve(null);
      };
    });
  }

  async _seedDefaultDataIfEmpty() {
    try {
      const count = await this.countTransactions();
      if (count === 0) {
        const seedTransactions = [
          {
            date: '2024-11-15',
            type: 'EXPENSE',
            category: 'Seeds',
            categoryHi: 'बीज खरीद',
            categoryMr: 'बियाणे खरेदी',
            title: 'HD-2967 Certified Wheat Seeds (100 kg)',
            titleHi: 'प्रमाणित गेहूं बीज (100 किग्रा)',
            titleMr: 'प्रमाणित गहू बियाणे (१०० किलो)',
            amount: 3200,
            crop: 'Wheat',
            notes: 'Purchased from National Seeds Corporation outlet',
          },
          {
            date: '2024-11-20',
            type: 'EXPENSE',
            category: 'Fertilizers',
            categoryHi: 'खाद व उर्वरक',
            categoryMr: 'खते खरेदी',
            title: 'IFFCO DAP (2 bags) + Urea (2 bags)',
            titleHi: 'डीएपी व यूरिया खाद',
            titleMr: 'डीएपी आणि युरिया खते',
            amount: 3850,
            crop: 'Wheat',
            notes: 'Government subsidized MRP rate',
          },
          {
            date: '2024-12-05',
            type: 'EXPENSE',
            category: 'Machinery',
            categoryHi: 'ट्रैक्टर जुताई',
            categoryMr: 'ट्रॅक्टर नांगरणी',
            title: 'Tractor Ploughing & Seed Drilling (2.5 Acres)',
            titleHi: 'ट्रैक्टर जुताई व बुआई',
            titleMr: 'ट्रॅक्टर मशागत व पेरणी',
            amount: 4800,
            crop: 'Wheat',
            notes: 'Local rental tractor @ ₹950/hour (5 hrs)',
          },
          {
            date: '2024-12-28',
            type: 'EXPENSE',
            category: 'Labor',
            categoryHi: 'निंदाई व मजदूरी',
            categoryMr: 'खुरपणी व मजुरी',
            title: 'First Weeding Labor (4 workers x 2 days)',
            titleHi: 'प्रथम निंदाई मजदूरी',
            titleMr: 'पहिली खुरपणी मजुरी',
            amount: 2800,
            crop: 'Wheat',
            notes: 'Manual weeding around CRI stage',
          },
          {
            date: '2025-01-15',
            type: 'INCOME',
            category: 'Subsidy',
            categoryHi: 'सरकारी अनुदान',
            categoryMr: 'सरकारी अनुदान',
            title: 'PM-KISAN 16th Installment DBT',
            titleHi: 'पीएम-किसान 16वीं किस्त',
            titleMr: 'पीएम-किसान १६ वा हप्ता थेट जमा',
            amount: 2000,
            crop: 'General',
            notes: 'Direct Bank Transfer to Bank of Maharashtra A/C',
          },
        ];

        for (const item of seedTransactions) {
          await this.addTransaction(item);
        }
      }
    } catch (err) {
      console.warn('Could not seed local database:', err);
    }
  }

  // ========================================================
  // 1. FARM FINANCE LEDGER CRUD OPERATIONS
  // ========================================================

  async addTransaction(tx) {
    await this.initPromise;
    if (!this.db) return this._fallbackAdd('finance_ledger', tx);

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['finance_ledger'], 'readwrite');
      const store = transaction.objectStore('finance_ledger');
      const record = {
        ...tx,
        amount: Number(tx.amount),
        createdAt: new Date().toISOString(),
      };
      const request = store.add(record);

      request.onsuccess = () => resolve(request.result);
      request.onerror = (e) => reject(e.target.error);
    });
  }

  async deleteTransaction(id) {
    await this.initPromise;
    if (!this.db) return this._fallbackDelete('finance_ledger', id);

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['finance_ledger'], 'readwrite');
      const store = transaction.objectStore('finance_ledger');
      const request = store.delete(Number(id));

      request.onsuccess = () => resolve(true);
      request.onerror = (e) => reject(e.target.error);
    });
  }

  async getAllTransactions() {
    await this.initPromise;
    if (!this.db) return this._fallbackGetAll('finance_ledger');

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['finance_ledger'], 'readonly');
      const store = transaction.objectStore('finance_ledger');
      const request = store.getAll();

      request.onsuccess = () => {
        // Return sorted newest first
        const records = (request.result || []).sort(
          (a, b) => new Date(b.date || b.createdAt) - new Date(a.date || a.createdAt)
        );
        resolve(records);
      };
      request.onerror = (e) => reject(e.target.error);
    });
  }

  async countTransactions() {
    await this.initPromise;
    if (!this.db) return (this._fallbackGetAll('finance_ledger') || []).length;

    return new Promise((resolve) => {
      const transaction = this.db.transaction(['finance_ledger'], 'readonly');
      const store = transaction.objectStore('finance_ledger');
      const request = store.count();
      request.onsuccess = () => resolve(request.result || 0);
      request.onerror = () => resolve(0);
    });
  }

  async getFinanceSummary() {
    const list = await this.getAllTransactions();
    let totalIncome = 0;
    let totalExpense = 0;
    const categoryTotals = {};

    for (const item of list) {
      const amt = Number(item.amount) || 0;
      if (item.type === 'INCOME') {
        totalIncome += amt;
      } else {
        totalExpense += amt;
        const cat = item.category || 'Other';
        categoryTotals[cat] = (categoryTotals[cat] || 0) + amt;
      }
    }

    return {
      totalIncome,
      totalExpense,
      netProfit: totalIncome - totalExpense,
      count: list.length,
      categoryTotals,
      transactions: list,
    };
  }

  // ========================================================
  // 2. SOIL TEST HISTORIC LOGS
  // ========================================================

  async addSoilTestLog(log) {
    await this.initPromise;
    if (!this.db) return this._fallbackAdd('soil_logs', log);

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['soil_logs'], 'readwrite');
      const store = transaction.objectStore('soil_logs');
      const request = store.add({ ...log, createdAt: new Date().toISOString() });
      request.onsuccess = () => resolve(request.result);
      request.onerror = (e) => reject(e.target.error);
    });
  }

  async getSoilLogsByField(fieldId) {
    await this.initPromise;
    if (!this.db) return [];

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction(['soil_logs'], 'readonly');
      const store = transaction.objectStore('soil_logs');
      const request = store.getAll();

      request.onsuccess = () => {
        const filtered = (request.result || []).filter(
          (r) => !fieldId || r.field_id === fieldId
        );
        resolve(filtered);
      };
      request.onerror = (e) => reject(e.target.error);
    });
  }

  // ========================================================
  // 3. HYPERLOCAL WEATHER & OFFLINE CACHE
  // ========================================================

  async cacheWeather(locationKey, weatherData) {
    await this.initPromise;
    if (!this.db) return;

    return new Promise((resolve) => {
      const transaction = this.db.transaction(['weather_cache'], 'readwrite');
      const store = transaction.objectStore('weather_cache');
      store.put({ key: locationKey, data: weatherData, timestamp: Date.now() });
      transaction.oncomplete = () => resolve(true);
    });
  }

  async getCachedWeather(locationKey) {
    await this.initPromise;
    if (!this.db) return null;

    return new Promise((resolve) => {
      const transaction = this.db.transaction(['weather_cache'], 'readonly');
      const store = transaction.objectStore('weather_cache');
      const request = store.get(locationKey);
      request.onsuccess = () => resolve(request.result?.data || null);
      request.onerror = () => resolve(null);
    });
  }

  // LocalStorage fallback for environments without IndexedDB
  _fallbackAdd(storeName, item) {
    const key = `ks_local_${storeName}`;
    const list = JSON.parse(localStorage.getItem(key) || '[]');
    const newId = list.length > 0 ? Math.max(...list.map((x) => x.id || 0)) + 1 : 1;
    const record = { ...item, id: newId, createdAt: new Date().toISOString() };
    list.unshift(record);
    localStorage.setItem(key, JSON.stringify(list));
    return newId;
  }

  _fallbackGetAll(storeName) {
    const key = `ks_local_${storeName}`;
    return JSON.parse(localStorage.getItem(key) || '[]');
  }

  _fallbackDelete(storeName, id) {
    const key = `ks_local_${storeName}`;
    const list = JSON.parse(localStorage.getItem(key) || '[]');
    const filtered = list.filter((x) => x.id !== Number(id));
    localStorage.setItem(key, JSON.stringify(filtered));
    return true;
  }
}

export const localDB = new LocalDatabase();
