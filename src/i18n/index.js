import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './en.json'
import hi from './hi.json'
import mr from './mr.json'
import { translations as legacyTranslations } from '../constants/translations.js'

i18n.use(initReactI18next).init({ resources: { en: { translation: { ...legacyTranslations.en, ...en } }, hi: { translation: { ...legacyTranslations.hi, ...hi } }, mr: { translation: { ...legacyTranslations.en, ...mr } } }, lng: localStorage.getItem('kisansathi-language') || 'en', fallbackLng: 'en', interpolation: { escapeValue: false } })

export default i18n
