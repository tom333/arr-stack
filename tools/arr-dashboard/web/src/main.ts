import { mount } from 'svelte';
import App from './App.svelte';

const target = document.getElementById('app');
if (!target) {
  throw new Error('#app target element missing from index.html');
}

const app = mount(App, { target });

export default app;
