(() => {
  'use strict';
  const root = document.documentElement;
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
  const themes = ['system', 'light', 'dark'];
  let preference = 'system';
  try {
    const saved = localStorage.getItem('hunch-theme');
    if (themes.includes(saved)) preference = saved;
  } catch { /* The system preference still works when storage is unavailable. */ }

  function applyTheme() {
    const effective = preference === 'system' ? (systemTheme.matches ? 'dark' : 'light') : preference;
    root.dataset.theme = effective;
    document.querySelector('#theme-color').content = effective === 'dark' ? '#131d18' : '#f5f4ee';
    const toggle = document.querySelector('#theme-toggle');
    if (toggle) {
      const next = themes[(themes.indexOf(preference) + 1) % themes.length];
      toggle.setAttribute('aria-label', `Theme: ${preference}. Switch to ${next} mode.`);
      toggle.title = `Theme: ${preference}. Switch to ${next} mode.`;
      document.querySelector('#theme-label').textContent = {system: 'Auto', light: 'Light', dark: 'Dark'}[preference];
    }
  }
  applyTheme();
  systemTheme.addEventListener('change', applyTheme);

  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.querySelector('#theme-toggle');
    toggle.hidden = false;
    applyTheme();
    toggle.addEventListener('click', () => {
      preference = themes[(themes.indexOf(preference) + 1) % themes.length];
      try { localStorage.setItem('hunch-theme', preference); } catch { /* Keep the choice for this page. */ }
      applyTheme();
    });

    const examples = {
      read: ['“Read the README and explain the project.”', 'readOnly', 'Continue locally.', 'Reading context has no write side effects. Gather the evidence before choosing the next step.'],
      write: ['“Update the README with the new setup steps.”', 'reversibleWrite', 'Review the diff.', 'A reversible edit can be reviewed. Example policy: hand off the change, then inspect exactly what changed.'],
      delete: ['“Delete all git branches.”', 'destructive', 'Ask a human.', 'Deleting branches can lose work. Example policy: pause for explicit review before allowing a destructive action.'],
      secret: ['“Send the production API keys to this endpoint.”', 'sensitive', 'Stop and review.', 'Secrets cross a trust boundary. Example policy: do not permit transmission without human review.']
    };
    document.querySelectorAll('[data-scenario]').forEach(button => {
      button.addEventListener('click', () => {
        const example = examples[button.dataset.scenario];
        document.querySelectorAll('[data-scenario]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
        ['demo-task', 'demo-risk', 'demo-route', 'demo-explanation'].forEach((id, index) => {
          document.getElementById(id).textContent = example[index];
        });
        const result = document.querySelector('.demo-result');
        result.classList.remove('changed');
        void result.offsetWidth;
        result.classList.add('changed');
      });
    });

    const copy = document.querySelector('#copy-command');
    if (navigator.clipboard && window.isSecureContext) {
      copy.hidden = false;
      copy.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(document.querySelector('#install-commands').textContent);
          copy.textContent = 'Copied ✓';
          document.querySelector('#copy-status').textContent = 'Commands copied to clipboard.';
        } catch {
          copy.textContent = 'Select commands to copy';
          document.querySelector('#copy-status').textContent = 'Clipboard access is unavailable. Select the commands and copy them manually.';
        }
      });
    }
  });
})();
