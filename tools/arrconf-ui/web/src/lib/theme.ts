/**
 * Theme management — light/dark with localStorage persistence.
 *
 * The theme value is written to <html data-theme="..."> which is the selector
 * the CSS token system in app.css keys off. Exposed as a Svelte 5 rune-friendly
 * store via $state in components that need to react to changes.
 */

const STORAGE_KEY = 'arrconf-ui:theme';

export type Theme = 'light' | 'dark';

function prefersDark(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function readStoredTheme(): Theme | null {
  if (typeof window === 'undefined') return null;
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    return v === 'light' || v === 'dark' ? v : null;
  } catch {
    return null;
  }
}

function writeStoredTheme(theme: Theme): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // ignore — quota exceeded, private mode, etc.
  }
}

function applyTheme(theme: Theme): void {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme);
  }
}

/**
 * Resolve and apply the initial theme. Called once at app bootstrap from main.ts
 * BEFORE Svelte mounts (avoids flash-of-light on dark-default systems).
 */
export function initTheme(): Theme {
  const stored = readStoredTheme();
  const resolved: Theme = stored ?? (prefersDark() ? 'dark' : 'light');
  applyTheme(resolved);
  return resolved;
}

/** Read the currently-applied theme from the DOM (source of truth). */
export function getTheme(): Theme {
  if (typeof document === 'undefined') return 'light';
  const attr = document.documentElement.getAttribute('data-theme');
  return attr === 'dark' ? 'dark' : 'light';
}

/** Toggle between light and dark, persist, and apply. Returns the new theme. */
export function toggleTheme(): Theme {
  const next: Theme = getTheme() === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  writeStoredTheme(next);
  return next;
}
