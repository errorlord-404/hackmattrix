import { BookOpen, FlaskConical, Sprout } from 'lucide-react';
import { SourceStamp } from '../feedback/ApiState.jsx';

function CatalogShell({ eyebrow, title, children, detail }) {
  return <section className="mt-5" aria-label={title}>
    <div className="rounded-2xl border border-sky-200 bg-sky-50 px-5 py-4">
      <div className="flex items-start gap-3">
        <span className="rounded-xl bg-sky-600 p-2.5 text-white"><BookOpen size={20} /></span>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-sky-700">{eyebrow}</p>
          <h2 className="mt-1 font-bold text-slate-900">{title}</h2>
          <p className="mt-1 text-sm text-sky-900/75">{detail}</p>
        </div>
      </div>
    </div>
    <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{children}</div>
  </section>;
}

export function SeedReferenceCatalog({ items, query }) {
  const normalized = query.trim().toLowerCase();
  const visible = items.filter((item) => !normalized || [item.crop, item.variety, item.disease_resistance, item.recommended_zone].join(' ').toLowerCase().includes(normalized));
  return <CatalogShell eyebrow="Reference catalog" title="Seed options to discuss with a certified supplier" detail="These are agronomy references, not stock, price or yield guarantees. Confirm certification, local availability and label guidance before purchasing.">
    {visible.map((item) => <article key={item.id} className="rounded-card border border-border bg-white p-5 shadow-card">
      <div className="flex items-start justify-between gap-3"><span className="rounded-lg bg-emerald-50 p-2 text-emerald-700"><Sprout size={19} /></span><span className="rounded-full bg-surface-muted px-2 py-1 text-[10px] font-bold uppercase text-text-secondary">seed reference</span></div>
      <h3 className="mt-4 font-bold">{item.crop}</h3>
      <p className="mt-1 text-sm font-semibold text-primary">{item.variety}</p>
      <dl className="mt-4 grid gap-2 text-xs text-text-secondary"><div className="flex justify-between gap-3"><dt>Duration</dt><dd className="text-right font-semibold text-slate-800">{item.duration_days}</dd></div><div className="flex justify-between gap-3"><dt>Yield potential</dt><dd className="text-right font-semibold text-slate-800">{item.yield_potential}</dd></div><div className="flex justify-between gap-3"><dt>Disease resistance</dt><dd className="text-right font-semibold text-slate-800">{item.disease_resistance}</dd></div></dl>
      <p className="mt-4 rounded-lg bg-amber-50 p-3 text-xs text-amber-900">{item.recommended_zone}</p>
      <SourceStamp source="Shared Mongo reference catalog" warning="Reference only · not a live supplier offer" />
    </article>)}
    {!visible.length && <div className="md:col-span-2 xl:col-span-3"><p className="rounded-card border border-dashed border-border bg-white p-8 text-center text-sm text-text-secondary">No seed references match this search.</p></div>}
  </CatalogShell>;
}

export function FertilizerReferenceCatalog({ items, query }) {
  const normalized = query.trim().toLowerCase();
  const visible = items.filter((item) => !normalized || [item.name, item.type, item.bag_size, item.dosage_per_acre, ...(item.suitable_crops || [])].join(' ').toLowerCase().includes(normalized));
  return <CatalogShell eyebrow="Reference catalog" title="Fertilizer guidance to validate with a soil test" detail="This catalog is not a supplier quote. Use a current soil test and an authorised agronomist or label before applying any product.">
    {visible.map((item) => <article key={item.id} className="rounded-card border border-border bg-white p-5 shadow-card">
      <div className="flex items-start justify-between gap-3"><span className="rounded-lg bg-violet-50 p-2 text-violet-700"><FlaskConical size={19} /></span><span className="rounded-full bg-surface-muted px-2 py-1 text-[10px] font-bold uppercase text-text-secondary">fertilizer reference</span></div>
      <h3 className="mt-4 font-bold">{item.name}</h3>
      <p className="mt-1 text-sm font-semibold text-primary">{item.type} · {item.bag_size}</p>
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs"><span className="rounded-lg bg-surface-muted p-3">MRP <b className="block text-sm text-slate-900">₹{Number(item.subsidized_mrp || 0).toLocaleString()}</b></span><span className="rounded-lg bg-surface-muted p-3">Subsidy <b className="block text-sm text-slate-900">₹{Number(item.govt_subsidy_per_bag || 0).toLocaleString()}</b></span></div>
      <p className="mt-4 text-sm text-text-secondary"><b className="text-slate-900">Dosage:</b> {item.dosage_per_acre}</p>
      <p className="mt-3 text-xs text-text-secondary"><b className="text-slate-900">Suitable crops:</b> {(item.suitable_crops || []).join(', ') || 'Verify locally'}</p>
      <SourceStamp source="Shared Mongo reference catalog" warning="Reference only · not a live supplier offer" />
    </article>)}
    {!visible.length && <div className="md:col-span-2 xl:col-span-3"><p className="rounded-card border border-dashed border-border bg-white p-8 text-center text-sm text-text-secondary">No fertilizer references match this search.</p></div>}
  </CatalogShell>;
}

export function MarketplaceCoverage({ activeType, directoryStatus }) {
  const rows = [
    ['machinery', 'Live', 'Government of India FARMS custom-hiring records', 'bg-emerald-50 text-emerald-800'],
    ['exporter', 'Live', 'APEDA registered exporter directory', 'bg-emerald-50 text-emerald-800'],
    ['seed', 'Reference', 'Shared agronomy catalog; no supplier stock feed', 'bg-sky-50 text-sky-800'],
    ['fertilizer', 'Reference', 'Shared agronomy catalog; no supplier stock feed', 'bg-sky-50 text-sky-800'],
    ['logistics', 'Live', 'APEDA recognised packhouse directory (post-harvest facilities)', 'bg-emerald-50 text-emerald-800'],
    ['buyer', 'Live', 'APEDA FarmerConnect public importer directory', 'bg-emerald-50 text-emerald-800'],
  ];
  const visible = activeType === 'all' ? rows : rows.filter(([type]) => type === activeType);
  return <section className="mt-5" aria-label="Marketplace data coverage"><div className="mb-3 flex items-center justify-between gap-3"><div><h2 className="font-bold">Data coverage</h2><p className="text-xs text-text-secondary">The directory only shows source-attributed information; it never invents vendors or prices.</p></div>{directoryStatus?.source_count != null && <span className="rounded-full bg-surface-muted px-2.5 py-1 text-[11px] font-semibold text-text-secondary">{directoryStatus.source_count} approved source{directoryStatus.source_count === 1 ? '' : 's'}</span>}</div><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{visible.map(([type, status, detail, tone]) => <div key={type} className="rounded-xl border border-border bg-white p-3"><div className="flex items-center justify-between gap-2"><span className="text-xs font-bold capitalize text-slate-900">{type === 'seed' ? 'Seeds' : type === 'fertilizer' ? 'Fertilizers' : type === 'exporter' ? 'Exporters' : type === 'buyer' ? 'Buyers' : 'Logistics'}</span><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${tone}`}>{status}</span></div><p className="mt-2 text-xs text-text-secondary">{detail}</p></div>)}</div></section>;
}
