const { EventEmitter } = require('node:events');
const test = require('node:test');
const assert = require('node:assert/strict');
const { CodexHarness, mcpDenyArgs } = require('../../desktop/codex-harness.cjs');

class FakeProcess extends EventEmitter {
  constructor({ respondTurns = true } = {}) {
    super();
    this.respondTurns = respondTurns;
    this.killed = false;
    this.messages = [];
    this.stdout = new EventEmitter();
    this.stderr = new EventEmitter();
    this.stdin = { writable: true, write: (line) => this.receive(line) };
    this.stdout.setEncoding = () => {};
    this.stderr.setEncoding = () => {};
  }

  receive(line) {
    const message = JSON.parse(line);
    this.messages.push(message);
    if (message.method === 'initialize') this.reply(message.id, { serverInfo: { name: 'fake-codex' } });
    if (message.method === 'thread/start') this.reply(message.id, { thread: { id: 'thread-1' } });
    if (message.method === 'thread/resume') this.reply(message.id, { thread: { id: message.params.threadId } });
    if (message.method === 'mcpServerStatus/list') this.reply(message.id, {
      data: [
        { name: 'kisansathi', tools: {
          get_onboarding_status: {}, get_profile: {}, list_fields: {}, get_diagnosis: {},
          get_latest_field_observations: {}, list_device_health: {},
          get_weather_for_field: {}, get_weather_alerts_for_field: {},
        } },
        ...(this.unexpectedMcp ? [{ name: 'gmail', tools: { search_emails: {} } }] : []),
      ], nextCursor: null,
    });
    if (message.method === 'turn/start' && this.respondTurns) this.reply(message.id, { turn: { id: 'turn-1' } });
    if (message.method === 'turn/interrupt') this.reply(message.id, {});
  }

  reply(id, result) { process.nextTick(() => this.stdout.emit('data', `${JSON.stringify({ id, result })}\n`)); }
  emitServerRequest(id = 77) { this.stdout.emit('data', `${JSON.stringify({ id, method: 'item/tool/requestApproval', params: { reason: 'Confirm irrigation log' } })}\n`); }
  stop(code = 1) { this.killed = true; this.emit('exit', code); }
  kill() { this.stop(0); }
}

function makeHarness(options = {}) {
  const processes = [];
  const launches = [];
  const harness = new CodexHarness({
    workspaceRoot: process.cwd(),
    agentRoot: `${process.cwd()}\\agent`,
    systemPromptPath: `${process.cwd()}\\agent\\prompts\\farmer_system_prompt.md`,
    skillPath: `${process.cwd()}\\agent\\skills\\kisansathi\\SKILL.md`,
    pluginRoot: `${process.cwd()}\\codex\\plugins\\kisansathi`,
    pluginLauncher: `${process.cwd()}\\codex\\plugins\\kisansathi\\run_server.py`,
    backendUrl: 'http://127.0.0.1:8001',
    farmerId: 'test-farmer',
    listMcpServerNames: options.listMcpServerNames || (() => ['gmail', 'railway', 'node_repl']),
    spawnProcess: (command, args, spawnOptions) => {
      launches.push({ command, args, spawnOptions });
      const child = new FakeProcess(options);
      child.unexpectedMcp = options.unexpectedMcp;
      processes.push(child);
      return child;
    },
  });
  return { harness, processes, launches };
}

test('starts a thread with the farmer lifecycle system prompt and sends a text turn through JSONL', async () => {
  const { harness, processes, launches } = makeHarness();
  const ready = [];
  harness.on('event', (event) => ready.push(event));
  assert.deepEqual(await harness.start({ fieldId: 'field-1', language: 'hi' }), { threadId: 'thread-1', reused: false });
  assert.deepEqual(await harness.sendText('Check soil moisture', { field_id: 'field-1' }), { turnId: 'turn-1' });
  assert.equal(ready.some((event) => event.kind === 'ready' && event.threadId === 'thread-1'), true);
  assert.equal(processes[0].messages.some((message) => message.method === 'thread/start'), true);
  const instructions = processes[0].messages.find((message) => message.method === 'thread/start').params.baseInstructions;
  assert.match(instructions, /get_crop_options/);
  assert.match(instructions, /best-supported option/);
  assert.match(instructions, /Never rely on the photo or CNN result alone/);
  assert.match(instructions, /get_crop_stage_action_proposals/);
  assert.match(instructions, /list_reminders/);
  assert.match(instructions, /[Dd]o not claim background monitoring or delivery while the app is closed/);
  assert.match(instructions, /compare_sale_routes` is available only as a read-only ranking/);
  assert.match(instructions, /official Indian agriculture, ICAR, state agricultural university, or extension advisory/);
  assert.match(instructions, /desktop runs Codex in full-access mode/);
  assert.match(instructions, /selected field field-1; display language hi/);
  assert.equal(launches[0].args.includes('web_search="live"'), true);
  for (const flag of [
    'features.shell_tool=true', 'features.unified_exec=true', 'features.apps=true',
    'features.plugins=true', 'features.multi_agent=true', 'features.code_mode_host=true',
    'features.browser_use=true', 'features.in_app_browser=true',
    'features.computer_use=true', 'features.hooks=true',
    'features.skill_mcp_dependency_install=true',
  ]) {
    assert.equal(launches[0].args.includes(flag), true);
  }
  for (const server of ['gmail', 'railway', 'node_repl']) {
    assert.equal(launches[0].args.includes(`mcp_servers.${server}.enabled=false`), false);
  }
  assert.deepEqual(processes[0].messages.find((message) => message.method === 'thread/start').params.sandboxPolicy, { type: 'dangerFullAccess' });
  assert.equal(processes[0].messages.at(-1).method, 'turn/start');
  assert.deepEqual(processes[0].messages.at(-1).params.sandboxPolicy, { type: 'dangerFullAccess' });
  harness.close();
});

test('starts with additional configured MCP tools available', async () => {
  const { harness } = makeHarness({ unexpectedMcp: true });
  assert.deepEqual(await harness.start(), { threadId: 'thread-1', reused: false });
  assert.equal(harness.status().running, true);
  harness.close();
});

test('keeps the full-access session open when another MCP server becomes ready', async () => {
  const { harness, processes } = makeHarness();
  await harness.start();
  processes[0].stdout.emit('data', `${JSON.stringify({ method: 'mcpServer/startupStatus/updated', params: { name: 'gmail', status: 'ready' } })}\n`);
  assert.equal(harness.status().running, true);
  harness.close();
});

test('resumes with additional configured MCP tools available', async () => {
  const { harness } = makeHarness({ unexpectedMcp: true });
  assert.deepEqual(await harness.resume('saved-thread'), { threadId: 'saved-thread', resumed: true });
  assert.equal(harness.status().running, true);
  harness.close();
});

test('refuses conflicting or unsafe inherited MCP names', () => {
  assert.throws(() => mcpDenyArgs(['kisansathi']), /conflicting/);
  assert.throws(() => mcpDenyArgs(['unsafe.name']), /cannot be safely disabled/);
});

test('resumes a saved thread and surfaces malformed app-server output', async () => {
  const { harness, processes } = makeHarness();
  const events = [];
  harness.on('event', (event) => events.push(event));
  assert.deepEqual(await harness.resume('saved-thread'), { threadId: 'saved-thread', resumed: true });
  assert.match(processes[0].messages.find((message) => message.method === 'thread/resume').params.baseInstructions, /get_crop_options/);
  processes[0].stdout.emit('data', 'not-json\n');
  assert.equal(events.some((event) => event.kind === 'diagnostic'), true);
  harness.close();
});

test('answers Codex approval requests without exposing the child process', async () => {
  const { harness, processes } = makeHarness();
  const requests = [];
  harness.on('event', (event) => requests.push(event));
  await harness.start();
  processes[0].emitServerRequest();
  const request = requests.find((event) => event.kind === 'approval');
  assert.equal(request.requestId, 77);
  harness.respond(request.requestId, { decision: 'accept' });
  assert.deepEqual(processes[0].messages.at(-1), { id: 77, result: { decision: 'accept' } });
  assert.throws(() => harness.respond(request.requestId, { decision: 'accept' }), /no longer pending/);
  harness.close();
});

test('surfaces coding, file-change, and permission approvals in full-access mode', async () => {
  const { harness, processes } = makeHarness();
  const events = [];
  harness.on('event', (event) => events.push(event));
  await harness.start();
  processes[0].stdout.emit('data', `${JSON.stringify({ id: 81, method: 'item/commandExecution/requestApproval', params: { command: 'powershell' } })}\n`);
  processes[0].stdout.emit('data', `${JSON.stringify({ id: 82, method: 'item/fileChange/requestApproval', params: {} })}\n`);
  processes[0].stdout.emit('data', `${JSON.stringify({ id: 83, method: 'item/permissions/requestApproval', params: {} })}\n`);
  assert.deepEqual(events.filter((event) => event.kind === 'approval').map((event) => event.requestId), [81, 82, 83]);
  harness.respond(81, { decision: 'accept' });
  harness.respond(82, { decision: 'accept' });
  harness.respond(83, { permissions: { filesystem: 'read-write' } });
  assert.deepEqual(processes[0].messages.at(-1), { id: 83, result: { permissions: { filesystem: 'read-write' } } });
  harness.close();
});

test('rejects an in-flight request and can recover after app-server exit', async () => {
  const first = makeHarness({ respondTurns: false });
  await first.harness.start();
  const pendingTurn = first.harness.sendText('wait for response');
  first.processes[0].stop(2);
  await assert.rejects(pendingTurn, /Codex app-server stopped/);
  assert.equal(first.harness.status().running, false);

  const second = makeHarness();
  assert.deepEqual(await second.harness.start(), { threadId: 'thread-1', reused: false });
  second.harness.close();
});
