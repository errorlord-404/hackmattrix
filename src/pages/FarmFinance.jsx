import { useEffect, useMemo, useState } from 'react';
import { Calculator, Coins, Plus, Receipt, Trash2 } from 'lucide-react';
import { referenceApi } from '../api/referenceApi.js';
import { useFarmData } from '../context/FarmDataContext.jsx';
import { EmptyState, ErrorState, LoadingState, SourceStamp } from '../components/feedback/ApiState.jsx';
import { farmStateApi } from '../api/farmStateApi.js';
import { useLanguage } from '../hooks/useLanguage.jsx';

const Card = ({ children, className = '' }) => <section className={`rounded-card border border-border bg-white p-5 shadow-card ${className}`}>{children}</section>;

function money(value) {
  return `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

function locationParts(location) {
  const parts = (location || '').split(',').map((part) => part.trim()).filter(Boolean);
  return { district: parts[parts.length - 2] || '', state: parts[parts.length - 1] || '' };
}

export default function FarmFinance() {
  const { language } = useLanguage();
  const { fields, profile } = useFarmData();
  const isHindi = language === 'hi';
  const isMarathi = language === 'mr';
  const [tab, setTab] = useState('ledger');
  const [transactions, setTransactions] = useState([]);
  const [ledgerSummary, setLedgerSummary] = useState({ income_inr: 0, expense_inr: 0, balance_inr: 0, active_entry_count: 0 });
  const [ledgerLoading, setLedgerLoading] = useState(true);
  const [ledgerError, setLedgerError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState('ALL');
  const [form, setForm] = useState({ title: '', type: 'EXPENSE', category: 'Other', amount: '', date: new Date().toISOString().slice(0, 10), crop: fields[0]?.current_crop || '', fieldId: fields[0]?.id || '', notes: '' });
  const [acres, setAcres] = useState(2.5);
  const [yieldPerAcre, setYieldPerAcre] = useState(24);
  const [price, setPrice] = useState(0);
  const [costPerAcre, setCostPerAcre] = useState(8200);
  const [quantity, setQuantity] = useState(1);
  const [crop, setCrop] = useState(fields.find((field) => field.current_crop)?.current_crop || '');
  const [comparison, setComparison] = useState(null);
  const [marketLoading, setMarketLoading] = useState(false);
  const [marketError, setMarketError] = useState(null);

  const totals = useMemo(() => ({ income: ledgerSummary.income_inr || 0, expense: ledgerSummary.expense_inr || 0 }), [ledgerSummary]);
  const filteredTransactions = transactions.filter((transaction) => filter === 'ALL' || transaction.entry_type === filter.toLowerCase());
  const totalYield = Math.max(0, Math.round(Number(acres) * Number(yieldPerAcre)));
  const grossRevenue = totalYield * Number(price || 0);
  const totalCost = Number(acres) * Number(costPerAcre || 0);
  const netProfit = grossRevenue - totalCost;
  const crops = [...new Set(fields.map((field) => field.current_crop).filter(Boolean))];
  const { district, state } = locationParts(profile?.location);

  const refreshLedger = async () => {
    setLedgerLoading(true); setLedgerError(null);
    try {
      const [entries, summary] = await Promise.all([farmStateApi.listLedgerEntries(), farmStateApi.getLedgerSummary()]);
      setTransactions(entries); setLedgerSummary(summary);
    } catch (error) { setLedgerError(error); }
    finally { setLedgerLoading(false); }
  };

  useEffect(() => {
    const initialLoad = window.setTimeout(() => { void refreshLedger(); }, 0);
    return () => window.clearTimeout(initialLoad);
  }, []);

  const addTransaction = async (event) => {
    event.preventDefault();
    if (!form.title.trim() || Number(form.amount) <= 0) return;
    setLedgerError(null);
    try {
      await farmStateApi.createLedgerEntry({
        field_id: form.fieldId || null, entry_type: form.type.toLowerCase(), category: form.category.trim() || 'Other',
        title: form.title.trim(), amount_inr: Number(form.amount), occurred_at: form.date,
        crop_name: form.crop.trim() || null, note: form.notes.trim() || null, source: 'farmer_confirmed:manual_ui',
      });
      setForm((current) => ({ ...current, title: '', amount: '', notes: '' }));
      setShowForm(false); await refreshLedger();
    } catch (error) { setLedgerError(error); }
  };

  const voidTransaction = async (id) => {
    setLedgerError(null);
    try { await farmStateApi.updateLedgerEntryStatus(id, 'void'); await refreshLedger(); }
    catch (error) { setLedgerError(error); }
  };

  const compareMandis = async () => {
    if (!crop || !district || !state) return;
    setMarketLoading(true); setMarketError(null);
    try {
      setComparison(await referenceApi.compareMandis(crop, { farmer_district: district, farmer_state: state, quantity_quintals: quantity }));
    } catch (error) { setMarketError(error); }
    finally { setMarketLoading(false); }
  };

  const labels = isMarathi ? { title: 'शेती वित्त व हिशोब', subtitle: 'तुमच्या नोंदी, नफा अंदाज आणि बाजार तुलना', ledger: 'खर्च वही', simulator: 'नफा सिम्युलेटर', arbitrage: 'मंडी तुलना', add: 'नोंद जोडा', income: 'उत्पन्न', expense: 'खर्च', balance: 'शिल्लक' } : isHindi ? { title: 'कृषि वित्त और खाता', subtitle: 'आपकी नोंद, लाभ अनुमान और बाजार तुलना', ledger: 'खाता बही', simulator: 'लाभ सिम्युलेटर', arbitrage: 'मंडी तुलना', add: 'प्रविष्टि जोड़ें', income: 'आय', expense: 'खर्च', balance: 'शेष' } : { title: 'Farm Finance & Ledger', subtitle: 'Record private transactions, model profit, and compare dated mandi scenarios.', ledger: 'Ledger', simulator: 'Profit simulator', arbitrage: 'Mandi comparison', add: 'Add transaction', income: 'Income', expense: 'Expenses', balance: 'Balance' };

  return <div className="mx-auto max-w-[1440px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
    {tab === 'arbitrage' && <p role="note" className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">This screen is an illustrative price scenario, not a live sale recommendation. Default transport charges are not road-distance quotes. Ask the assistant to compare routes using recent comparable mandi records and dated transport quotes.</p>}
    <div className="flex flex-wrap items-start justify-between gap-4"><div><div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-primary text-white"><Coins size={22} /></span><div><h1 className="text-2xl font-bold">{labels.title}</h1><p className="mt-1 text-sm text-text-secondary">{labels.subtitle}</p></div></div><p className="mt-3 text-xs text-text-muted">Farmer-confirmed INR records are stored in your farmer-scoped ledger. They do not make a payment, create credit, or calculate tax.</p></div>{tab === 'ledger' && <button onClick={() => setShowForm(true)} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white"><Plus size={16} />{labels.add}</button>}</div>
    <div className="mt-6 inline-flex max-w-full overflow-x-auto rounded-lg bg-surface-muted p-1"><button onClick={() => setTab('ledger')} className={`whitespace-nowrap rounded-md px-3 py-2 text-xs font-semibold ${tab === 'ledger' ? 'bg-white text-primary shadow-card' : 'text-text-secondary'}`}>{labels.ledger}</button><button onClick={() => setTab('simulator')} className={`whitespace-nowrap rounded-md px-3 py-2 text-xs font-semibold ${tab === 'simulator' ? 'bg-white text-primary shadow-card' : 'text-text-secondary'}`}>{labels.simulator}</button><button onClick={() => setTab('arbitrage')} className={`whitespace-nowrap rounded-md px-3 py-2 text-xs font-semibold ${tab === 'arbitrage' ? 'bg-white text-primary shadow-card' : 'text-text-secondary'}`}>{labels.arbitrage}</button></div>
    {tab === 'ledger' && <><div className="mt-5 grid gap-4 sm:grid-cols-3"><Card><p className="text-xs text-text-secondary">{labels.income}</p><p className="mt-2 text-2xl font-bold text-emerald-700">{money(totals.income)}</p></Card><Card><p className="text-xs text-text-secondary">{labels.expense}</p><p className="mt-2 text-2xl font-bold text-rose-700">{money(totals.expense)}</p></Card><Card><p className="text-xs text-text-secondary">{labels.balance}</p><p className="mt-2 text-2xl font-bold text-primary-dark">{money(ledgerSummary.balance_inr)}</p></Card></div>{ledgerError && <div className="mt-5"><ErrorState error={ledgerError} onRetry={refreshLedger} /></div>}<Card className="mt-5 p-0"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4"><h2 className="font-bold">{isMarathi ? 'खाजगी आर्थिक नोंदी' : isHindi ? 'निजी वित्तीय प्रविष्टियां' : 'Farmer-confirmed transaction ledger'}</h2><select value={filter} onChange={(event) => setFilter(event.target.value)} className="rounded-lg border border-border bg-white px-3 py-2 text-xs"><option value="ALL">All</option><option value="INCOME">{labels.income}</option><option value="EXPENSE">{labels.expense}</option></select></div>{ledgerLoading ? <div className="p-5"><LoadingState label="Loading ledger records…" /></div> : filteredTransactions.length ? <div className="divide-y divide-border">{filteredTransactions.map((transaction) => <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4" key={transaction.id}><div className="flex items-center gap-3"><span className={`grid size-9 place-items-center rounded-lg ${transaction.entry_type === 'income' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}><Receipt size={17} /></span><div><p className="text-sm font-semibold">{transaction.title}</p><p className="mt-1 text-xs text-text-secondary">{transaction.category} · {transaction.occurred_at}{transaction.crop_name ? ` · ${transaction.crop_name}` : ''}</p></div></div><div className="flex items-center gap-3"><b className={transaction.entry_type === 'income' ? 'text-emerald-700' : 'text-rose-700'}>{transaction.entry_type === 'income' ? '+' : '-'}{money(transaction.amount_inr)}</b><button onClick={() => voidTransaction(transaction.id)} className="rounded-lg p-2 text-text-muted hover:bg-rose-50 hover:text-rose-700" aria-label="Void transaction"><Trash2 size={15} /></button></div></div>)}</div> : <div className="p-5"><EmptyState title="No transactions recorded" detail="Add a farmer-entered income or expense; no sample financial values are seeded." /></div>}</Card></>}
    {tab === 'simulator' && <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_360px]"><Card><div className="flex items-center gap-2"><Calculator size={19} className="text-primary" /><h2 className="font-bold">{labels.simulator}</h2></div><p className="mt-2 text-sm text-text-secondary">Change the assumptions to model a scenario. This is not a yield forecast.</p><div className="mt-5 grid gap-4 sm:grid-cols-2">{[['Acres', acres, setAcres], ['Yield per acre (quintal)', yieldPerAcre, setYieldPerAcre], ['Price per quintal (₹)', price, setPrice], ['Cost per acre (₹)', costPerAcre, setCostPerAcre]].map(([label, value, setter]) => <label className="text-sm" key={label}>{label}<input type="number" min="0" step="any" value={value} onChange={(event) => setter(event.target.value)} className="mt-2 w-full rounded-lg border border-border px-3 py-2" /></label>)}</div></Card><Card className="bg-primary-50"><p className="text-sm text-primary">Scenario output</p><p className="mt-3 text-3xl font-bold text-primary-dark">{money(netProfit)}</p><p className="mt-1 text-xs text-text-secondary">Estimated net after entered costs</p><div className="mt-5 space-y-3 border-t border-primary/10 pt-4 text-sm"><p className="flex justify-between"><span>Yield</span><b>{totalYield} qtl</b></p><p className="flex justify-between"><span>Gross revenue</span><b>{money(grossRevenue)}</b></p><p className="flex justify-between"><span>Total cost</span><b>{money(totalCost)}</b></p></div></Card></div>}
    {tab === 'arbitrage' && <div className="mt-5"><Card><div className="flex flex-wrap items-end gap-3"><label className="text-sm">Crop<select value={crop} onChange={(event) => setCrop(event.target.value)} className="mt-2 block rounded-lg border border-border bg-white px-3 py-2">{crops.length ? crops.map((item) => <option value={item} key={item}>{item}</option>) : <option value="">No crop recorded</option>}</select></label><label className="text-sm">Quantity (quintals)<input type="number" min="0.1" step="0.1" value={quantity} onChange={(event) => setQuantity(event.target.value)} className="mt-2 block rounded-lg border border-border px-3 py-2" /></label><button disabled={marketLoading || !crop || !district || !state} onClick={compareMandis} className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{marketLoading ? 'Comparing…' : 'Compare dated mandi scenarios'}</button></div><p className="mt-3 text-xs text-text-muted">Uses dated market records with flat transport/fee assumptions for {district || 'your district'}, {state || 'your state'}.</p>{marketError && <div className="mt-4"><ErrorState error={marketError} /></div>}{marketLoading && <div className="mt-4"><LoadingState label="Loading market comparison…" /></div>}{comparison && (comparison.results.length ? <div className="mt-5 space-y-3">{comparison.results.map((result) => <div className="rounded-xl border border-border p-4" key={result.market_price_id}><div className="flex flex-wrap justify-between gap-2"><div><p className="font-bold">{result.mandi_name}</p><p className="mt-1 text-xs text-text-secondary">{result.quantity_quintals} qtl · sale revenue {money(result.sale_revenue)}</p></div><p className="text-lg font-bold text-primary-dark">{money(result.net_realisation)}</p></div><p className="mt-2 text-xs text-text-muted">Costs: {money(result.transport_cost + result.loading_cost + result.unloading_cost + result.market_fees + result.storage_cost + result.expected_spoilage)} · source: {result.data_source}</p><SourceStamp source="market reference service" fetchedAt={result.fetched_at} /></div>)}</div> : <EmptyState title="No dated market records" detail="The reference service returned no comparable mandis for this crop." />)}</Card></div>}
    {showForm && <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4"><Card className="w-full max-w-lg"><div className="flex items-center justify-between"><h2 className="font-bold">{labels.add}</h2><button onClick={() => setShowForm(false)} className="text-sm text-text-muted">Close</button></div><form onSubmit={addTransaction} className="mt-4 grid gap-3"><input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Description" className="rounded-lg border border-border px-3 py-2 text-sm" /><div className="grid gap-3 sm:grid-cols-2"><select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })} className="rounded-lg border border-border px-3 py-2 text-sm"><option value="EXPENSE">{labels.expense}</option><option value="INCOME">{labels.income}</option></select><input required min="0.01" type="number" step="0.01" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} placeholder="Amount (₹)" className="rounded-lg border border-border px-3 py-2 text-sm" /></div><div className="grid gap-3 sm:grid-cols-2"><input type="date" value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} className="rounded-lg border border-border px-3 py-2 text-sm" /><input value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} placeholder="Category" className="rounded-lg border border-border px-3 py-2 text-sm" /></div><select value={form.fieldId} onChange={(event) => setForm({ ...form, fieldId: event.target.value })} className="rounded-lg border border-border px-3 py-2 text-sm"><option value="">Whole farm / no field</option>{fields.map((field) => <option key={field.id} value={field.id}>{field.name}</option>)}</select><input value={form.crop} onChange={(event) => setForm({ ...form, crop: event.target.value })} placeholder="Crop (optional)" className="rounded-lg border border-border px-3 py-2 text-sm" /><textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} placeholder="Notes (optional)" className="rounded-lg border border-border px-3 py-2 text-sm" /><p className="text-xs text-text-muted">Saving records this entry only; it does not make a payment or credit decision.</p><button className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white">Save ledger record</button></form></Card></div>}
  </div>;
}
