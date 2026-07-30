import {
  getDocumentState
} from './document-state.js';

export function initAnnotationsIO(annotatorApi) {
  if (!annotatorApi) {
    throw new Error(
      "L'API de l'annotateur est indisponible."
    );
  }

  const importButton = getElement(
    'import-annotations'
  );
  const exportButton = getElement(
    'export-annotations'
  );
  const clearButton = getElement(
    'clear-annotations'
  );
  const fileInput = getElement(
    'annotations-file-input'
  );

  importButton.addEventListener('click', () => {
    fileInput.click();
  });

  exportButton.addEventListener('click', () => {
    exportAnnotations(annotatorApi);
  });

  clearButton.addEventListener('click', () => {
    const confirmed = window.confirm(
      'Effacer toutes les annotations ?'
    );

    if (confirmed) {
      annotatorApi.clearAnnotations();
      showMessage(
        'Toutes les annotations ont été effacées.'
      );
    }
  });

  fileInput.addEventListener(
    'change',
    async event => {
      const [file] = event.target.files ?? [];

      if (!file) {
        return;
      }

      try {
        await importAnnotations(
          file,
          annotatorApi
        );
      } catch (error) {
        showMessage(error.message, true);
      } finally {
        fileInput.value = '';
      }
    }
  );

  setupMenu();
}

function exportAnnotations(annotatorApi) {
  const documentState = getDocumentState();
  const config = documentState.config;
  const annotations =
    annotatorApi.getAnnotations();

  if (!config || !documentState.sha256) {
    throw new Error(
      'La TEI doit être chargée avant l’export.'
    );
  }

  const payload = {
    format: 'frene-annotations',
    version: '2.0',
    generator: {
      application:
        config.application?.name ??
        'annotation-app',
      version:
        config.application?.version ??
        '2.0.0'
    },
    document: {
      id: config.document.id,
      title: config.document.title,
      file:
        config.document.file ??
        fileNameFromUrl(config.document.url),
      url: config.document.url,
      scope: 'text/body',
      sha256: `sha256:${documentState.sha256}`,
      textLength: documentState.bodyText.length
    },
    exportedAt: new Date().toISOString(),
    annotationCount: annotations.length,
    annotations
  };

  const blob = new Blob(
    [JSON.stringify(payload, null, 2)],
    {
      type: 'application/json;charset=utf-8'
    }
  );

  const fileName =
    `${config.document.id}.annotations.json`;

  downloadBlob(blob, fileName);

  showMessage(
    `${annotations.length} annotation(s) exportée(s).`
  );
}

async function importAnnotations(
  file,
  annotatorApi
) {
  const raw = await file.text();
  const payload = JSON.parse(raw);

  validateImport(payload);

  const documentState = getDocumentState();
  const expectedHash =
    `sha256:${documentState.sha256}`;

  if (
    payload.document.sha256 &&
    payload.document.sha256 !== expectedHash
  ) {
    throw new Error(
      'Le JSON correspond à une autre version de la TEI. ' +
      'Import annulé pour éviter des annotations décalées.'
    );
  }

  if (payload.document.scope !== 'text/body') {
    throw new Error(
      'Le JSON ne cible pas la portée text/body.'
    );
  }

  annotatorApi.setAnnotations(
    payload.annotations
  );

  showMessage(
    `${payload.annotations.length} annotation(s) importée(s).`
  );
}

function validateImport(payload) {
  if (
    payload?.format !== 'frene-annotations' ||
    !Array.isArray(payload?.annotations) ||
    !payload?.document
  ) {
    throw new Error(
      'Le fichier ne respecte pas le format attendu.'
    );
  }
}

function setupMenu() {
  const button = getElement('app-menu-button');
  const menu = getElement('app-menu');

  button.addEventListener('click', event => {
    event.stopPropagation();
    const isOpen = !menu.hidden;

    menu.hidden = isOpen;
    button.setAttribute(
      'aria-expanded',
      String(!isOpen)
    );
  });

  document.addEventListener('click', event => {
    if (
      !menu.hidden &&
      !menu.contains(event.target) &&
      event.target !== button
    ) {
      menu.hidden = true;
      button.setAttribute(
        'aria-expanded',
        'false'
      );
    }
  });
}

function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;
  link.download = fileName;
  link.click();

  URL.revokeObjectURL(url);
}

function showMessage(message, isError = false) {
  const element = getElement(
    'application-message'
  );

  element.textContent = message;
  element.hidden = false;
  element.classList.toggle(
    'error',
    isError
  );

  window.setTimeout(() => {
    element.hidden = true;
  }, 5000);
}

function fileNameFromUrl(url) {
  return url.split('/').pop() || 'document.xml';
}

function getElement(id) {
  const element = document.getElementById(id);

  if (!element) {
    throw new Error(
      `Élément #${id} introuvable.`
    );
  }

  return element;
}
