import { useEffect, useMemo, useState } from "react";
import {
  CalendarDays,
  CheckCircle2,
  Circle,
  ListTodo,
  Plus,
} from "lucide-react";
import { farmStateApi } from "../api/farmStateApi.js";
import { useFarmData } from "../context/FarmDataContext.jsx";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  SourceStamp,
} from "../components/feedback/ApiState.jsx";

function formatDue(value) {
  return value ? new Date(value).toLocaleString() : "No due time";
}

export default function FieldTasks() {
  const { fields } = useFarmData();
  const [selectedFieldId, setSelectedFieldId] = useState("");
  const [tasks, setTasks] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const activeFieldId = selectedFieldId || fields[0]?.id || "";
  const activeField = useMemo(
    () => fields.find((field) => field.id === activeFieldId),
    [activeFieldId, fields],
  );
  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextTasks, nextProposals] = await Promise.all([
        farmStateApi.listFieldTasks(activeFieldId || undefined, "open"),
        activeFieldId ? farmStateApi.getCropStageActionProposals(activeFieldId) : Promise.resolve([]),
      ]);
      setTasks(nextTasks);
      setProposals(nextProposals);
    } catch (nextError) {
      setError(nextError);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      farmStateApi.listFieldTasks(activeFieldId || undefined, "open"),
      activeFieldId ? farmStateApi.getCropStageActionProposals(activeFieldId) : Promise.resolve([]),
    ])
      .then(([nextTasks, nextProposals]) => {
        if (cancelled) return;
        setTasks(nextTasks);
        setProposals(nextProposals);
        setError(null);
      })
      .catch((nextError) => {
        if (!cancelled) setError(nextError);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeFieldId]);

  const createTask = async (event) => {
    event.preventDefault();
    if (!activeFieldId || !title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await farmStateApi.createFieldTask({
        field_id: activeFieldId,
        title: title.trim(),
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
        source: "farmer_confirmed:manual_ui",
      });
      setTitle("");
      setDueAt("");
      await refresh();
    } catch (nextError) {
      setError(nextError);
    } finally {
      setSaving(false);
    }
  };

  const completeTask = async (taskId) => {
    setSaving(true);
    setError(null);
    try {
      await farmStateApi.updateFieldTaskStatus(taskId, "completed");
      await refresh();
    } catch (nextError) {
      setError(nextError);
    } finally {
      setSaving(false);
    }
  };

  const acceptProposal = async (proposal) => {
    if (!activeFieldId) return;
    setSaving(true);
    setError(null);
    try {
      await farmStateApi.createFieldTask({
        field_id: activeFieldId,
        title: proposal.title,
        source: `farmer_confirmed:${proposal.source}`,
      });
      await refresh();
    } catch (nextError) {
      setError(nextError);
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="mx-auto max-w-5xl px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
      <header className="overflow-hidden rounded-3xl border border-primary/20 bg-[radial-gradient(circle_at_top_right,_#e8f6dd,_#fff_52%,_#f7efe1)] p-6 shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="flex items-start gap-4">
            <span className="grid size-12 place-items-center rounded-2xl bg-primary text-white shadow-lg">
              <ListTodo size={24} />
            </span>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
                Field action ledger
              </p>
              <h1 className="mt-1 text-2xl font-bold">What needs attention</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-text-secondary">
                Turn a confirmed recommendation into a task, then record when it
                is done. Tasks never place orders or control equipment.
              </p>
            </div>
          </div>
          <div className="rounded-2xl border border-primary/15 bg-white/80 px-4 py-3 text-right">
            <p className="text-[11px] font-bold uppercase tracking-wide text-text-secondary">
              Open actions
            </p>
            <p className="mt-1 text-2xl font-bold text-primary">
              {tasks.length}
            </p>
          </div>
        </div>
      </header>
      {!loading && !error && proposals.length > 0 && (
        <section className="mt-6 rounded-card border border-primary/20 bg-[#fbfdf6] p-5 shadow-card">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">Stage-aware proposals</p>
              <h2 className="mt-1 font-bold">Review before adding an action</h2>
              <p className="mt-1 text-sm text-text-secondary">These are generic lifecycle prompts for {proposals[0].crop_name} at {proposals[0].stage}. They do not create a task until you accept one.</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {proposals.map((proposal) => (
              <article className="rounded-xl border border-primary/15 bg-white p-4" key={`${proposal.crop_cycle_id}-${proposal.title}`}>
                <p className="font-semibold">{proposal.title}</p>
                <p className="mt-2 text-sm leading-5 text-text-secondary">{proposal.why}</p>
                <p className="mt-2 text-xs text-text-muted">When: {proposal.due_hint}</p>
                <button type="button" disabled={saving} onClick={() => acceptProposal(proposal)} className="mt-4 rounded-lg border border-primary/25 px-3 py-2 text-xs font-bold text-primary hover:bg-primary hover:text-white disabled:opacity-50">Accept as field action</button>
              </article>
            ))}
          </div>
        </section>
      )}
      <section className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section className="rounded-card border border-border bg-white p-5 shadow-card">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="font-bold">Open field actions</h2>
              <p className="mt-1 text-sm text-text-secondary">
                {activeField?.name || "All fields"}
              </p>
            </div>
            {fields.length > 1 && (
              <label className="text-xs font-semibold text-text-secondary">
                Field
                <select
                  aria-label="Filter tasks by field"
                  value={selectedFieldId}
                  onChange={(event) => setSelectedFieldId(event.target.value)}
                  className="ml-2 rounded-lg border border-border bg-white px-2 py-1.5 text-sm text-text-primary"
                >
                  {fields.map((field) => (
                    <option value={field.id} key={field.id}>
                      {field.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {loading ? (
            <div className="mt-5">
              <LoadingState label="Loading field actions…" />
            </div>
          ) : error ? (
            <div className="mt-5">
              <ErrorState error={error} onRetry={refresh} />
            </div>
          ) : !tasks.length ? (
            <div className="mt-5">
              <EmptyState
                title="No open actions"
                detail="Create a farmer-confirmed task when there is work to track."
              />
            </div>
          ) : (
            <ul className="mt-5 divide-y divide-border">
              {tasks.map((task) => (
                <li className="flex items-start gap-3 py-4" key={task.id}>
                  <button
                    type="button"
                    aria-label={`Mark ${task.title} complete`}
                    disabled={saving}
                    onClick={() => completeTask(task.id)}
                    className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full border-2 border-primary/35 text-primary transition hover:bg-primary hover:text-white disabled:opacity-50"
                  >
                    <Circle size={15} />
                  </button>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{task.title}</p>
                    <p className="mt-1 flex items-center gap-1 text-xs text-text-secondary">
                      <CalendarDays size={13} />
                      {formatDue(task.due_at)}
                    </p>
                    <SourceStamp
                      source={task.source}
                      fetchedAt={task.created_at}
                    />
                  </div>
                  <CheckCircle2
                    size={18}
                    className="mt-1 text-primary/30"
                    aria-hidden="true"
                  />
                </li>
              ))}
            </ul>
          )}
        </section>
        <form
          onSubmit={createTask}
          className="rounded-card border border-primary/20 bg-[#fbfdf6] p-5 shadow-card"
        >
          <div className="flex items-center gap-2">
            <Plus size={18} className="text-primary" />
            <h2 className="font-bold">Add confirmed action</h2>
          </div>
          <p className="mt-2 text-xs leading-5 text-text-secondary">
            Record only work the farmer has agreed to do.
          </p>
          {!fields.length ? (
            <div className="mt-5">
              <EmptyState
                title="Create a field first"
                detail="Tasks must belong to a mapped field."
              />
            </div>
          ) : (
            <>
              <label className="mt-5 block text-sm font-semibold">
                Action title
                <input
                  aria-label="Action title"
                  required
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="e.g. Inspect affected leaves"
                  className="mt-2 w-full rounded-lg border border-border bg-white px-3 py-2.5 text-sm"
                />
              </label>
              <label className="mt-4 block text-sm font-semibold">
                Due time{" "}
                <span className="font-normal text-text-muted">(optional)</span>
                <input
                  aria-label="Task due time"
                  type="datetime-local"
                  value={dueAt}
                  onChange={(event) => setDueAt(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-border bg-white px-3 py-2.5 text-sm"
                />
              </label>
              <button
                disabled={saving}
                className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50"
              >
                <Plus size={16} />
                {saving ? "Saving…" : "Add field action"}
              </button>
            </>
          )}
        </form>
      </section>
    </main>
  );
}
