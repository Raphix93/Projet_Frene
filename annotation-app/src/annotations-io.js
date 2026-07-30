import { getDocumentState } from './document-state.js';

export function initAnnotationsIO(api) {
  const importButton = required('import-annotations');
  const exportButton = required('export-annotations');
  const clearButton = required('clear-annotations');
  const input = required('annotations-file-input');
  const menuButton = required('app-menu-button');
  const menu = required('app-menu');

  menuButton.addEventListener('click', event => {
    event.stopPropagation();
    menu.hidden = !menu.hidden;
    menuButton.setAttribute('aria-expanded', String(!menu.hidden));
  });

  document.addEventListener('click', event => {
    if (!menu.hidden && !menu.contains(event.target) && event.target !== menuButton) {
      menu.hidden = true;
      menuButton.setAttribute('aria-expanded', 'false');
    }
  });

  importButton.addEventListener('click', () => input.click());
  exportButton.addEventListener('click', () => exportAnnotations(api));
  clearButton.addEventListener('click', () => {
    if (window.confirm('Effacer toutes les annotations ?')) {
      api.clearAnnotations();
      message('Toutes les annotations ont été effacées.');
    }
  });

  input.addEventListener('change', async event => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const payload = JSON.parse(await file.text());
      validatePayload(payload);

      const state = getDocumentState();
      const expected = `sha256:${state.sha256}`;

      if (payload.document.sha256 && payload.document.sha256 !== expected) {
        throw new Error('Ce JSON correspond à une autre version de la TEI.');
      }

      api.setAnnotations(payload.annotations);
      message(`${payload.annotations.length} annotation(s) importée(s).`);
    } catch (error) {
      message(error.message, true);
    } finally {
      input.value = '';
    }
  });
}

function exportAnnotations(api) {
  const state = getDocumentState();
  const config = state.config;
  const annotations = api.getAnnotations();

  const payload = {
    format: 'frene-annotations',
    version: '2.0',
    generator: {
      application: config.application?.name ?? 'annotation-app',
      version: config.application?.version ?? '2.0.0'
    },
    document: {
      id: config.document.id,
      title: config.document.title,
      file: config.document.file ?? config.document.url.split('/').pop(),
      url: config.document.url,
      scope: 'text/body',
      sha256: `sha256:${state.sha256}`,
      textLength: state.bodyText.length
    },
    exportedAt: new Date().toISOString(),
    annotationCount: annotations.length,
    annotations
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: 'application/json;charset=utf-8'
  });

  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.href = url;
  link.download = `${config.document.id}.annotations.json`;
  link.click();

  URL.revokeObjectURL(url);
  message(`${annotations.length} annotation(s) exportée(s).`);
}

function validatePayload(payload) {
  if (
    payload?.format !== 'frene-annotations' ||
    payload?.document?.scope !== 'text/body' ||
    !Array.isArray(payload?.annotations)
  ) {
    throw new Error('Format JSON non reconnu.');
  }
}

function required(id) {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Élément #${id} introuvable.`);
  return element;
}

function message(text, error = false) {
  const element = required('application-message');
  element.textContent = text;
  element.hidden = false;
  element.classList.toggle('error', error);
}
