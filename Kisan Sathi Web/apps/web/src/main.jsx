import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import AuthGate from './components/auth/AuthGate.jsx';
import { AIConversationProvider } from './context/AIConversationContext.jsx';
import { routeComponents, routeFor } from './routes/index.jsx';
import './index.css';

function StandaloneApplication() {
  const route = routeFor(globalThis.location.pathname);
  const RouteComponent = routeComponents[route.id];
  return route.id === 'dashboard' || !RouteComponent ? <App /> : <RouteComponent />;
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthGate>
      <AIConversationProvider>
        <StandaloneApplication />
      </AIConversationProvider>
    </AuthGate>
  </StrictMode>,
);
