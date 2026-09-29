const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('kisanHarness', {
  farmerId: ipcRenderer.sendSync('kisansathi:farmer-id'),
  backendUrl: ipcRenderer.sendSync('kisansathi:backend-url'),
  session: { start: (options) => ipcRenderer.invoke('kisansathi:session-start', options), resume: (threadId) => ipcRenderer.invoke('kisansathi:session-resume', threadId), restart: (options) => ipcRenderer.invoke('kisansathi:session-restart', options), status: () => ipcRenderer.invoke('kisansathi:status') },
  chat: { sendText: (text, metadata) => ipcRenderer.invoke('kisansathi:send-text', text, metadata), sendImage: (bytes, mimeType, prompt, metadata) => ipcRenderer.invoke('kisansathi:send-image', bytes, mimeType, prompt, metadata), interrupt: () => ipcRenderer.invoke('kisansathi:interrupt') },
  notifications: { showAlert: (alert) => ipcRenderer.invoke('kisansathi:show-alert-notification', alert) },
  voice: { transcribe: (audio, languageCode, mimeType) => ipcRenderer.invoke('kisansathi:voice-transcribe', audio, languageCode, mimeType), translate: (body) => ipcRenderer.invoke('kisansathi:voice-translate', body), synthesize: (body) => ipcRenderer.invoke('kisansathi:voice-synthesize', body) },
  approval: { respond: (requestId, result) => ipcRenderer.invoke('kisansathi:respond', requestId, result) },
  clarification: { respond: (requestId, result) => ipcRenderer.invoke('kisansathi:respond', requestId, result) },
  onEvent: (listener) => { const wrapped = (_event, payload) => listener(payload); ipcRenderer.on('kisansathi:codex-event', wrapped); return () => ipcRenderer.removeListener('kisansathi:codex-event', wrapped); },
});
