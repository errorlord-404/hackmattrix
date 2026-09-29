import { I18nextProvider, useTranslation } from 'react-i18next'
import i18n from '../i18n/index.js'

export function LanguageProvider({ children }) {
  return <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
}

// The hook and provider are intentionally colocated for the app's i18n boundary.
// eslint-disable-next-line react-refresh/only-export-components
export function useLanguage() {
  const { t, i18n: instance } = useTranslation()
  const language = ['en', 'hi', 'mr'].includes(instance.language) ? instance.language : 'en'
  const setLanguage = (nextLanguage) => { const safeLanguage = ['en', 'hi', 'mr'].includes(nextLanguage) ? nextLanguage : 'en'; instance.changeLanguage(safeLanguage); localStorage.setItem('kisansathi-language', safeLanguage); document.documentElement.lang = safeLanguage }
  const locale = language === 'hi' ? 'hi-IN' : language === 'mr' ? 'mr-IN' : 'en-IN'
  return { language, setLanguage, isHindi: language === 'hi', isMarathi: language === 'mr', t, formatDate: (value, options = { day: 'numeric', month: 'short', year: 'numeric' }) => new Intl.DateTimeFormat(locale, options).format(new Date(value)) }
}
