import { mount } from 'svelte';
import App from './App.svelte';
import './app.css';
import { initTheme } from './lib/theme';

// Initialize theme BEFORE Svelte mounts so the first paint matches the chosen
// theme (avoids flash-of-unstyled-content). Priority chain:
//   1. localStorage `arrconf-ui:theme` (operator's last explicit choice)
//   2. window.matchMedia('(prefers-color-scheme: dark)')
//   3. light (fallback)
initTheme();

const target = document.getElementById('app');
if (!target) {
  throw new Error('#app target element missing from index.html');
}

const app = mount(App, { target });

export default app;
