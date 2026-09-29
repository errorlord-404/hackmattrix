import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, apiLimits, createTurnId, getSessionId, readNdjsonStream } from '../src/lib/api.js';

function streamOf(text) {
  return new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
}

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => payload,
    text: async () => JSON.stringify(payload),
  };
}

afterEach(() => vi.restoreAllMocks());

describe('standalone API contract', () => {
  it('uses the liveness, readiness, and tools endpoints', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse({ status: 'ok' }));
    await api.healthz();
    await api.readyz();
    await api.tools();
    await api.visionCapabilities();
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(['/healthz', '/readyz', '/tools', '/v1/vision/capabilities']);
  });

  it('posts local session and turn IDs to chat/stream', async () => {
    const response = { ok: true, status: 200, body: streamOf('{"kind":"ready"}\n{"kind":"turnCompleted","payload":{"status":"ok"}}\n') };
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response);
    const events = [];
    await api.streamChat({
      sessionId: 'session-local-1',
      turnId: 'turn-local-1',
      messages: [{ role: 'user', content: 'Hello' }],
      onEvent: (event) => events.push(event),
    });
    const [url, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(url).toBe('/chat/stream');
    expect(options.method).toBe('POST');
    expect(options.headers['X-Session-ID']).toBe('session-local-1');
    expect(body).toMatchObject({ session_id: 'session-local-1', turn_id: 'turn-local-1' });
    expect(events).toHaveLength(2);
  });
});

describe('bounded NDJSON reader', () => {
  it('parses NDJSON and tolerates complete SSE data frames', async () => {
    const events = [];
    const response = {
      ok: true,
      body: streamOf('{"kind":"ready"}\n' + 'data: {"kind":"agentMessageDelta","payload":{"text":"Hello"}}\n\n' + 'data: [DONE]\n\n'),
    };
    await readNdjsonStream(response, (event) => events.push(event));
    expect(events).toEqual([
      { kind: 'ready' },
      { kind: 'agentMessageDelta', payload: { text: 'Hello' } },
    ]);
  });

  it('joins multiline SSE data before parsing', async () => {
    const events = [];
    const response = { ok: true, body: streamOf('data: {"kind":"diagnostic",\ndata: "payload":{"status":"degraded"}}\n\n') };
    await readNdjsonStream(response, (event) => events.push(event));
    expect(events[0]).toEqual({ kind: 'diagnostic', payload: { status: 'degraded' } });
  });

  it('rejects oversized and malformed streams', async () => {
    const oversized = { ok: true, body: streamOf('{"kind":"ready","payload":"' + 'x'.repeat(100) + '"}\n') };
    await expect(readNdjsonStream(oversized, () => {}, { maxBytes: 20 })).rejects.toMatchObject({ code: 'stream_too_large' });
    const malformed = { ok: true, body: streamOf('not-json\n') };
    await expect(readNdjsonStream(malformed, () => {})).rejects.toMatchObject({ code: 'invalid_stream' });
  });
});

describe('local identifiers and safety bounds', () => {
  it('creates stable session IDs and distinct turn IDs', () => {
    const session = getSessionId();
    expect(session).toMatch(/^session-/);
    expect(getSessionId()).toBe(session);
    expect(createTurnId()).not.toBe(createTurnId());
  });

  it('keeps stream limits finite', () => {
    expect(apiLimits.MAX_STREAM_BYTES).toBe(512 * 1024);
    expect(apiLimits.MAX_STREAM_EVENTS).toBe(120);
  });
});
