import { useAIConversation } from '../../context/AIConversationContext.jsx';
import { FeatureRouteShell } from '../../components/layout/FeatureRouteShell.jsx';
export function ConversationRoute() {
  const { state } = useAIConversation();
  return <FeatureRouteShell eyebrow="Advisor" title="Conversation" description="Provider output is untrusted until the server policy and approval boundary accepts it."><div data-testid="web-ai-stream-resume">{state.status === 'degraded' ? 'Advisor unavailable; no farm action was taken.' : `${state.messages.length} conversation items`}</div>{state.pendingApproval && <p role="status">Approval is required before this write.</p>}</FeatureRouteShell>;
}
