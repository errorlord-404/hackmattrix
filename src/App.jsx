import { RouterProvider } from 'react-router-dom'
import { router } from './routes/index.jsx'
import { LanguageProvider } from './hooks/useLanguage.jsx'
import { FarmDataProvider } from './context/FarmDataContext.jsx'
import { AIConversationProvider } from './context/AIConversationContext.jsx'

function App() {
  return <LanguageProvider>
            <FarmDataProvider>
              <AIConversationProvider>
                <RouterProvider router={router} />
              </AIConversationProvider>
            </FarmDataProvider>
          </LanguageProvider>
}

export default App
