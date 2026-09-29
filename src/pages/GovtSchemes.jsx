import { useCallback, useEffect, useMemo, useState } from 'react';
import { ExternalLink, Landmark, Search } from 'lucide-react';
import { getReferenceCacheMeta, referenceApi } from '../api/referenceApi.js';
import { useFarmData } from '../context/FarmDataContext.jsx';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { EmptyState, ErrorState, LoadingState, SourceStamp, StaleDataNotice } from '../components/feedback/ApiState.jsx';
import { parseDisplayLocation } from '../lib/location.js';

const Page = ({ children }) => (
  <div className="mx-auto max-w-[1440px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">{children}</div>
);

function matchesScheme(scheme, query) {
  if (!query) return true;
  const haystack = [
    scheme.name,
    scheme.description,
    scheme.benefits,
    ...(scheme.eligibility_criteria || []),
  ].join(' ').toLowerCase();
  return haystack.includes(query.toLowerCase());
}

export default function GovtSchemes() {
  const { profile } = useFarmData();
  const { language } = useLanguage();
  const [schemes, setSchemes] = useState([]);
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cacheMeta, setCacheMeta] = useState(null);
  const state = parseDisplayLocation(profile?.location).state;
  const isHindi = language === 'hi';

  const loadSchemes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await (state ? referenceApi.listSchemesByState(state) : referenceApi.listSchemes());
      setSchemes(Array.isArray(result) ? result : []);
      setCacheMeta(getReferenceCacheMeta(result));
    } catch (reason) {
      setError(reason);
    } finally {
      setLoading(false);
    }
  }, [state]);

  // Load the reference catalog whenever the saved farmer state changes.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { loadSchemes(); }, [loadSchemes]);

  const visibleSchemes = useMemo(
    () => schemes.filter((scheme) => matchesScheme(scheme, query)),
    [schemes, query],
  );
  const selected = visibleSchemes.find((scheme) => scheme.id === selectedId) || visibleSchemes[0];
  const title = isHindi ? 'सरकारी योजनाएं' : 'Government schemes';
  const subtitle = state
    ? `${isHindi ? 'आपके राज्य के लिए उपलब्ध योजनाएं' : `Reference schemes available for ${state}`}.`
    : (isHindi ? 'सरकारी स्रोत से उपलब्ध योजनाएं और लाभ' : 'Benefits and application details from the reference service.');

  return (
    <Page>
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>
      <div className="mt-6">
        <StaleDataNotice meta={cacheMeta} />
        {loading && <LoadingState label={isHindi ? 'योजनाओं की जानकारी लोड हो रही है…' : 'Loading reference schemes…'} />}
        {!loading && error && <ErrorState error={error} onRetry={loadSchemes} />}
        {!loading && !error && !schemes.length && (
          <EmptyState
            title={isHindi ? 'अभी कोई योजना उपलब्ध नहीं है' : 'No schemes are available'}
            detail={state ? 'The reference service returned no schemes for this state.' : 'Save a state in Settings or load the reference catalog first.'}
          />
        )}
        {!loading && !error && schemes.length > 0 && (
          <>
            <label className="flex max-w-xl items-center gap-2 rounded-xl border border-border bg-white px-3 py-2 shadow-card">
              <Search size={17} className="text-text-muted" />
              <span className="sr-only">Search schemes</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 text-sm outline-none" placeholder={isHindi ? 'योजना खोजें' : 'Search schemes, benefits, or eligibility'} />
            </label>
            {!visibleSchemes.length ? (
              <div className="mt-5"><EmptyState title="No matching schemes" detail="Try a broader search term." /></div>
            ) : (
              <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
                <div className="grid gap-4 sm:grid-cols-2">
                  {visibleSchemes.map((scheme) => (
                    <button key={scheme.id} onClick={() => setSelectedId(scheme.id)} className={`rounded-card border bg-white p-5 text-left shadow-card transition hover:border-primary ${selected?.id === scheme.id ? 'border-primary ring-2 ring-primary/10' : 'border-border'}`}>
                      <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary"><Landmark size={20} /></span>
                      <h2 className="mt-4 font-bold">{scheme.name}</h2>
                      <p className="mt-2 line-clamp-3 text-sm leading-6 text-text-secondary">{scheme.description}</p>
                      <p className="mt-4 text-sm font-semibold text-primary-dark">{scheme.benefits}</p>
                    </button>
                  ))}
                </div>
                {selected && (
                  <aside className="h-fit rounded-card border border-border bg-white p-5 shadow-card">
                    <h2 className="text-lg font-bold">{selected.name}</h2>
                    <p className="mt-3 text-sm leading-6 text-text-secondary">{selected.description}</p>
                    <div className="mt-5 space-y-4 border-y border-border py-4 text-sm">
                      <div><p className="font-semibold">Benefits</p><p className="mt-1 text-text-secondary">{selected.benefits || 'Not provided by the reference source.'}</p></div>
                      <div><p className="font-semibold">Eligibility</p>{selected.eligibility_criteria?.length ? <ul className="mt-1 list-disc space-y-1 pl-5 text-text-secondary">{selected.eligibility_criteria.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-1 text-text-secondary">Not provided by the reference source.</p>}</div>
                      <div><p className="font-semibold">Required documents</p>{selected.required_documents?.length ? <ul className="mt-1 list-disc space-y-1 pl-5 text-text-secondary">{selected.required_documents.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-1 text-text-secondary">Not provided by the reference source.</p>}</div>
                    </div>
                    {selected.application_deadline && <p className="mt-4 text-xs text-amber-700">Application deadline: {new Date(selected.application_deadline).toLocaleDateString()}</p>}
                    {selected.official_source_url && <a href={selected.official_source_url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white">Open official source <ExternalLink size={14} /></a>}
                    <SourceStamp source="government scheme reference service" />
                  </aside>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </Page>
  );
}
