import { defineStore } from 'pinia';
import { computed, ref, watch } from 'vue';

function saved(key: string, choices: string[], fallback: string) {
  try { const value = localStorage.getItem(`vcw-${key}`); return value && choices.includes(value) ? value : fallback; }
  catch { return fallback; }
}
export const usePreferencesStore = defineStore('preferences', () => {
  const language = ref(saved('language', ['zh', 'en'], 'zh'));
  const theme = ref(saved('theme', ['light', 'dark', 'system'], 'light'));
  const level = ref(saved('level', ['all', 'beginner', 'intermediate', 'advanced'], 'all'));
  const fontSize = ref(saved('font-size', ['normal', 'large'], 'normal'));
  const directoryMode = ref(saved('directory-mode', ['expanded', 'collapsed', 'fixed'], 'expanded'));
  const english = computed(() => language.value === 'en');
  for (const [key, value] of [['language', language], ['theme', theme], ['level', level], ['font-size', fontSize], ['directory-mode', directoryMode]] as const) {
    watch(value, next => { try { localStorage.setItem(`vcw-${key}`, next); } catch { /* Keep the preference for this session. */ } });
  }
  const text = (zh: string, en: string) => english.value ? en : zh;
  function reset() { language.value = 'zh'; theme.value = 'light'; level.value = 'all'; fontSize.value = 'normal'; directoryMode.value = 'expanded'; }
  return { language, theme, level, fontSize, directoryMode, english, text, reset };
});
