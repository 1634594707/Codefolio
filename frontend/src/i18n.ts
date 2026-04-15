import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import enTranslations from './locales/en.json'
import zhTranslations from './locales/zh.json'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: enTranslations },
      zh: { translation: zhTranslations },
    },
    lng: localStorage.getItem('codefolio-language') ??
         (navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en'),
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already escapes
    },
  })

export default i18n
