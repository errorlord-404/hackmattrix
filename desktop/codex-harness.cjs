const { EventEmitter } = require('node:events');
const { spawn, execFileSync } = require('node:child_process');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs');

const MAX_SKILL_INSTRUCTION_CHARS = 24_000;

/**
 * Private JSONL client for `codex app-server --stdio`.
 * The renderer never receives this object or the child process.
 */
class CodexHarness extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = options;
    this.process = null;
    this.buffer = '';
    this.nextId = 1;
    this.pending = new Map();
    this.approvalRequests = new Set();
    this.tempFiles = new Set();
    this.threadId = null;
    this.turnId = null;
    this.lastStartOptions = null;
    this.lastError = null;
    this.closing = false;
  }

  status() {
    return {
      running: Boolean(this.process && !this.process.killed),
      threadId: this.threadId,
      lastError: this.lastError,
    };
  }

  async start(startOptions = {}) {
    if (this.process && !this.process.killed && this.threadId) {
      return { threadId: this.threadId, reused: true };
    }
    this.lastStartOptions = { ...startOptions };
    this.lastError = null;
    this.closing = false;
    try {
      this.#spawnProcess();
      await this.request('initialize', {
        clientInfo: { name: 'kisansathi-desktop', title: 'KisanSathi Farmer Companion', version: '0.1.0' },
        capabilities: { experimentalApi: true },
      });
      this.notify('initialized', {});
      const systemInstructions = loadSkillInstructions(this.options.systemPromptPath);
      const skillInstructions = systemInstructions ? '' : loadSkillInstructions(this.options.skillPath);
      if (!systemInstructions && !skillInstructions) this.emit('event', { kind: 'diagnostic', text: 'KisanSathi instructions could not be loaded; using the embedded safety fallback.' });
      const response = await this.request('thread/start', {
        cwd: this.options.workspaceRoot,
        approvalPolicy: 'on-request',
        sandboxPolicy: { type: 'dangerFullAccess' },
        baseInstructions: farmerInstructions(startOptions.fieldId, startOptions.language, systemInstructions || skillInstructions, Boolean(systemInstructions)),
      });
      this.threadId = response.thread.id;
      await this.#verifyFarmerTools();
      this.emit('event', { kind: 'ready', threadId: this.threadId });
      return { threadId: this.threadId, reused: false };
    } catch (error) {
      this.lastError = error.message;
      this.close();
      throw error;
    }
  }

  async resume(threadId) {
    if (!threadId) throw new Error('A Codex thread ID is required to resume a session.');
    try {
      if (!this.process || this.process.killed) this.#spawnProcess();
      if (!this.pending.size && !this.threadId) {
        await this.request('initialize', {
          clientInfo: { name: 'kisansathi-desktop', title: 'KisanSathi Farmer Companion', version: '0.1.0' },
          capabilities: { experimentalApi: true },
        });
        this.notify('initialized', {});
      }
      const options = this.lastStartOptions || {};
      const systemInstructions = loadSkillInstructions(this.options.systemPromptPath);
      const skillInstructions = systemInstructions ? '' : loadSkillInstructions(this.options.skillPath);
      if (!systemInstructions && !skillInstructions) this.emit('event', { kind: 'diagnostic', text: 'KisanSathi instructions could not be loaded while resuming; using the embedded safety fallback.' });
      const response = await this.request('thread/resume', {
        threadId,
        baseInstructions: farmerInstructions(options.fieldId, options.language, systemInstructions || skillInstructions, Boolean(systemInstructions)),
      });
      this.threadId = response.thread.id;
      await this.#verifyFarmerTools();
      this.emit('event', { kind: 'ready', threadId: this.threadId, resumed: true });
      return { threadId: this.threadId, resumed: true };
    } catch (error) {
      this.lastError = error.message;
      this.close();
      throw error;
    }
  }

  async restart(startOptions = {}) {
    const options = { ...(this.lastStartOptions || {}), ...(startOptions || {}) };
    this.close();
    return this.start(options);
  }

  async sendText(text, metadata = {}) {
    if (!this.threadId) throw new Error('Start a Codex session before sending a message.');
    return this.#startTurn([{ type: 'text', text, textElements: [] }], metadata);
  }

  async sendImage(filePath, prompt, metadata = {}) {
    if (!this.threadId) throw new Error('Start a Codex session before sending an image.');
    if (!filePath || !fs.existsSync(filePath)) throw new Error('The temporary crop image is no longer available.');
    this.tempFiles.add(filePath);
    return this.#startTurn([{ type: 'text', text: prompt, textElements: [] }, { type: 'localImage', path: filePath }], metadata);
  }

  async interrupt() {
    if (this.threadId && this.turnId) await this.request('turn/interrupt', { threadId: this.threadId, turnId: this.turnId });
  }

  respond(requestId, result) {
    if (requestId == null || !result || typeof result !== 'object') throw new Error('Invalid Codex server response.');
    if (!this.approvalRequests.delete(requestId)) throw new Error('This farmer confirmation is no longer pending.');
    this.write({ id: requestId, result });
  }

  trackTempFile(filePath) { this.tempFiles.add(filePath); }

  close() {
    this.closing = true;
    this.#rejectPending(new Error('Codex harness closed.'));
    this.process?.kill();
    this.process = null;
    this.threadId = null;
    this.turnId = null;
    this.approvalRequests.clear();
    this.#cleanupTempFiles();
  }

  async #startTurn(input, metadata) {
    const response = await this.request('turn/start', {
      threadId: this.threadId,
      clientUserMessageId: randomUUID(),
      input,
      approvalPolicy: 'on-request',
      sandboxPolicy: { type: 'dangerFullAccess' },
      responsesapiClientMetadata: Object.fromEntries(Object.entries(metadata).map(([key, value]) => [key, String(value)])),
    });
    this.turnId = response.turn.id;
    return { turnId: this.turnId };
  }

  async #verifyFarmerTools() {
    const inventory = await this.request('mcpServerStatus/list', { cursor: null, limit: 100, detail: 'toolsAndAuthOnly' });
    if (!Array.isArray(inventory.data) || inventory.nextCursor) throw new Error('Farmer tool inventory could not be verified.');
    const farm = inventory.data.find((server) => server.name === 'kisansathi');
    // Crop-health review depends on this complete read-only evidence set. Refuse
    // to start a farmer session if a stale or partial MCP registration omits it.
    const required = [
      'get_onboarding_status', 'get_profile', 'list_fields', 'get_diagnosis',
      'get_latest_field_observations', 'list_device_health',
      'get_weather_for_field', 'get_weather_alerts_for_field',
    ];
    if (!farm || farm.toolsError || required.some((name) => !farm.tools?.[name])) {
      throw new Error('KisanSathi farm tools did not initialize.');
    }
  }

  #spawnProcess() {
    if (this.process && !this.process.killed) return;
    const command = process.env.CODEX_BINARY || 'codex';
    const python = process.env.KISANSATHI_PYTHON || 'python';
    const pluginArgs = [
      '-c', `mcp_servers.kisansathi.command=${tomlString(python)}`,
      '-c', `mcp_servers.kisansathi.args=[${tomlString(this.options.pluginLauncher)}]`,
      '-c', `mcp_servers.kisansathi.cwd=${tomlString(this.options.pluginRoot)}`,
      '-c', 'mcp_servers.kisansathi.required=true',
      '-c', 'mcp_servers.kisansathi.startup_timeout_sec=10',
      '-c', 'mcp_servers.kisansathi.tool_timeout_sec=30',
      '-c', 'mcp_servers.kisansathi.default_tools_approval_mode="writes"',
      '-c', 'features.shell_tool=true',
      '-c', 'features.unified_exec=true',
      '-c', 'features.apps=true',
      '-c', 'features.plugins=true',
      '-c', 'features.multi_agent=true',
      '-c', 'features.code_mode_host=true',
      '-c', 'features.browser_use=true',
      '-c', 'features.in_app_browser=true',
      '-c', 'features.computer_use=true',
      '-c', 'features.hooks=true',
      '-c', 'features.skill_mcp_dependency_install=true',
      '-c', `mcp_servers.kisansathi.env.KISANSATHI_AGENT_ROOT=${tomlString(this.options.agentRoot)}`,
      '-c', `mcp_servers.kisansathi.env.KISANSATHI_BACKEND_URL=${tomlString(this.options.backendUrl)}`,
      '-c', `mcp_servers.kisansathi.env.KISANSATHI_FARMER_ID=${tomlString(this.options.farmerId)}`,
      '-c', 'web_search="live"',
      'app-server', '--stdio',
    ];
    const spawnOptions = {
      cwd: this.options.workspaceRoot,
      env: {
        ...process.env,
        KISANSATHI_AGENT_ROOT: this.options.agentRoot,
        KISANSATHI_BACKEND_URL: this.options.backendUrl,
        KISANSATHI_FARMER_ID: this.options.farmerId,
        LOG_FORMAT: 'json',
      },
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    };
    const spawnProcess = this.options.spawnProcess || defaultSpawn;
    this.process = spawnProcess(command, pluginArgs, spawnOptions);
    this.process.stdout?.setEncoding?.('utf8');
    this.process.stdout?.on('data', (chunk) => this.#read(chunk));
    this.process.stderr?.setEncoding?.('utf8');
    this.process.stderr?.on('data', (line) => this.emit('event', { kind: 'diagnostic', text: line.trim() }));
    this.process.on('error', (error) => this.#fail(error));
    this.process.on('exit', (code) => {
      const error = new Error(`Codex app-server stopped${code == null ? '' : ` (exit ${code})`}.`);
      this.#rejectPending(error);
      this.process = null;
      this.threadId = null;
      this.turnId = null;
      this.approvalRequests.clear();
      this.#cleanupTempFiles();
      if (!this.closing) {
        this.lastError = error.message;
        this.emit('event', { kind: 'unavailable', message: error.message, recoverable: true });
      }
    });
  }

  request(method, params) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      try { this.write({ method, id, params }); } catch (error) { this.pending.delete(id); reject(error); }
    });
  }

  notify(method, params) { this.write({ method, params }); }

  write(message) {
    if (!this.process?.stdin?.writable) throw new Error('Codex app-server is not running.');
    this.process.stdin.write(`${JSON.stringify(message)}\n`);
  }

  #read(chunk) {
    this.buffer += chunk;
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop();
    lines.filter(Boolean).forEach((line) => {
      try { this.#dispatch(JSON.parse(line)); }
      catch { this.emit('event', { kind: 'diagnostic', text: 'Codex app-server emitted invalid JSON.' }); }
    });
  }

  #dispatch(message) {
    if (message.id != null && !message.method) {
      const pending = this.pending.get(message.id);
      if (!pending) return;
      this.pending.delete(message.id);
      if (message.error) pending.reject(new Error(message.error.message || 'Codex request failed.'));
      else pending.resolve(message.result || {});
      return;
    }
    if (message.id != null && message.method) {
      const kind = message.method.includes('requestApproval') ? 'approval' : message.method === 'item/tool/requestUserInput' ? 'clarification' : 'serverRequest';
      if (kind === 'approval' || kind === 'clarification') this.approvalRequests.add(message.id);
      this.emit('event', { kind, requestId: message.id, method: message.method, payload: message.params || {} });
      return;
    }
    const event = normaliseNotification(message.method, message.params || {});
    if (event.kind === 'turnCompleted') { this.#cleanupTempFiles(); this.approvalRequests.clear(); }
    this.emit('event', event);
  }

  #rejectPending(error) {
    for (const pending of this.pending.values()) pending.reject(error);
    this.pending.clear();
  }

  #fail(error) {
    this.lastError = error.message;
    this.#rejectPending(error);
    this.emit('event', { kind: 'unavailable', message: `Could not start Codex: ${error.message}`, recoverable: true });
  }

  #cleanupTempFiles() {
    for (const filePath of this.tempFiles) fs.rm(filePath, { force: true, recursive: true }, () => {});
    this.tempFiles.clear();
  }
}

function defaultSpawn(command, args, options) {
  if (process.platform === 'win32') {
    return spawn('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', `& ${powerShellQuote(command)} ${args.map(powerShellQuote).join(' ')}`], options);
  }
  return spawn(command, args, options);
}

function discoverMcpServerNames(command, cwd) {
  const windows = process.platform === 'win32';
  const executable = windows ? 'powershell.exe' : command;
  const args = windows
    ? ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', `& ${powerShellQuote(command)} mcp list --json`]
    : ['mcp', 'list', '--json'];
  const output = execFileSync(executable, args, {
    cwd, encoding: 'utf8', windowsHide: true, timeout: 15000, maxBuffer: 2_000_000,
  });
  const entries = JSON.parse(output);
  if (!Array.isArray(entries) || entries.some((entry) => typeof entry.name !== 'string')) {
    throw new Error('Could not enumerate inherited Codex MCP servers.');
  }
  return entries.map((entry) => entry.name);
}

function mcpDenyArgs(names) {
  if (!Array.isArray(names)) throw new Error('Could not enumerate inherited Codex MCP servers.');
  if (names.includes('kisansathi')) throw new Error('A conflicting KisanSathi MCP server is already configured.');
  return [...new Set(names)].flatMap((name) => {
    if (!/^[A-Za-z0-9_-]+$/.test(name)) throw new Error('An inherited MCP server name cannot be safely disabled.');
    // CLI overrides form a new config layer; give disabled entries a harmless
    // transport so app-server never attempts to validate an empty shadow table.
    return ['-c', `mcp_servers.${name}.enabled=false`, '-c', `mcp_servers.${name}.command="python"`];
  });
}

function normaliseNotification(method, params) {
  if (method === 'item/agentMessage/delta') return { kind: 'agentMessageDelta', itemId: params.itemId, delta: params.delta || '' };
  if (method === 'item/completed') {
    const item = params.item || {};
    if (item.type === 'agentMessage') return { kind: 'agentMessageCompleted', itemId: item.id, text: itemText(item) };
    if (item.type === 'mcpToolCall') return { kind: 'tool', tool: item.tool, status: item.status, result: item.result, action: toolAction(item.result || item.action), error: item.error, readOnly: item.readOnlyHint };
  }
  if (method === 'item/started' && params.item?.type === 'mcpToolCall') return { kind: 'tool', tool: params.item.tool, status: 'inProgress', action: toolAction(params.item.result || params.item.action), readOnly: params.item.readOnlyHint };
  if (method === 'turn/completed') return { kind: 'turnCompleted', turn: params.turn };
  if (method === 'thread/status/changed') return { kind: 'threadStatus', status: params.status, threadId: params.threadId };
  return { kind: 'raw', method, payload: params };
}

function toolAction(value) {
  if (!value) return undefined;
  if (typeof value === 'object') return value.action || (value.method && value.refresh ? value : undefined);
  if (typeof value !== 'string') return undefined;
  try { return toolAction(JSON.parse(value)); } catch { return undefined; }
}

function itemText(item) {
  if (typeof item.text === 'string') return item.text;
  if (!Array.isArray(item.content)) return '';
  return item.content.map((part) => typeof part === 'string' ? part : part?.text || '').join('');
}

function farmerInstructions(fieldId, language, instructions = '', isSystemPrompt = false) {
  const fallback = `You are KisanSathi, a careful farmer-facing assistant. The active field is ${fieldId || 'not selected'} and the farmer's display language is ${language || 'not selected'}. Use KisanSathi MCP tools for recorded farm facts and actions. Treat tool results as authoritative and preserve source, observation/fetch time, confidence, assumptions, warnings, and unavailable states. Do not invent farm data. For a persistent action, explain the exact change and ask the farmer for explicit confirmation before calling a write tool. Never control pumps, machinery, payments, bookings, purchases, sales, or other physical systems. The desktop converts farmer speech into English before it reaches you. Reply only in clear English. End every response with \`Farmer summary:\` and a self-contained two-to-four-sentence plain-English spoken summary containing the decision, safety warnings, and immediate next step. The desktop translates and speaks only that summary in the farmer's detected language.`;
  if (!instructions) return fallback;
  if (isSystemPrompt) return `${instructions}\n\nSession hint: selected field ${fieldId || 'not selected'}; display language ${language || 'not selected'}. Verify the exact field with farm tools before field-specific advice. The desktop sends you English only: reply in English only, end with the required Farmer summary, and let the desktop translate and speak that summary when providers are available.`;
  return `${fallback}\n\nThe canonical KisanSathi workflow skill below is mandatory. Follow its routing and answer contract. When it links a relative reference, resolve it from agent/skills/kisansathi inside the workspace and read only the relevant section.\n\n${instructions}`;
}

function loadSkillInstructions(skillPath) {
  if (!skillPath) return '';
  try {
    return fs.readFileSync(skillPath, 'utf8').slice(0, MAX_SKILL_INSTRUCTION_CHARS).trim();
  } catch {
    return '';
  }
}

function tomlString(value) { return `'${String(value).replace(/'/g, "''")}'`; }
function powerShellQuote(value) { return `'${String(value).replace(/'/g, "''")}'`; }

module.exports = { CodexHarness, normaliseNotification, itemText, farmerInstructions, loadSkillInstructions, mcpDenyArgs };
