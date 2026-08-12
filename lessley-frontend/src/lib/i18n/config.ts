import i18n from "i18next"
import { initReactI18next } from "react-i18next"

import en from "./locales/en.json"
import he from "./locales/he.json"

export const SUPPORTED_LANGUAGES = ["en", "he"] as const
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]

export const RTL_LANGUAGES: readonly SupportedLanguage[] = ["he"]

export const LANGUAGE_STORAGE_KEY = "lessley-language"

export function isSupportedLanguage(value: string | null): value is SupportedLanguage {
  return !!value && (SUPPORTED_LANGUAGES as readonly string[]).includes(value)
}

export function getDirection(language: string): "rtl" | "ltr" {
  return (RTL_LANGUAGES as readonly string[]).includes(language) ? "rtl" : "ltr"
}

// This module runs at import time — including from the test setup file, where
// localStorage may be absent. Treat storage as best-effort rather than assuming it.
function readStoredLanguage(): string | null {
  try {
    return globalThis.localStorage?.getItem(LANGUAGE_STORAGE_KEY) ?? null
  } catch {
    return null
  }
}

function storeLanguage(language: SupportedLanguage) {
  try {
    globalThis.localStorage?.setItem(LANGUAGE_STORAGE_KEY, language)
  } catch {
    // Private-mode / storage-disabled browsers: the language still applies for this session.
  }
}

function getInitialLanguage(): SupportedLanguage {
  const stored = readStoredLanguage()
  if (isSupportedLanguage(stored)) return stored
  return "en"
}

const initialLanguage = getInitialLanguage()

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, he: { translation: he } },
  lng: initialLanguage,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  returnNull: false,
})

document.documentElement.lang = initialLanguage
document.documentElement.dir = getDirection(initialLanguage)

export function setLanguage(language: SupportedLanguage) {
  storeLanguage(language)
  document.documentElement.lang = language
  document.documentElement.dir = getDirection(language)
  void i18n.changeLanguage(language)
}

export default i18n
