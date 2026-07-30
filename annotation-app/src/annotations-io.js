const EXPORT_FORMAT = 'frene-annotations';
const EXPORT_VERSION = '1.0';
const DOCUMENT_ID = 'Frene_volume_1';
const CONTEXT_LENGTH = 30;

/**
 * Initialise l'import et l'export des annotations.
 *
 * @param {object} annotationApi
 * @param {Function} annotationApi.getAnnotations
 * @param {Function} annotationApi.setAnnotations
 * @param {Function} annotationApi.clearAnnotations
 */
export function initAnnotationsIO(annotationApi) {
  const menuButton = document.querySelector('#app-menu-button');
  const appMenu = document.querySelector('#app-menu');
  const importButton = document.querySelector(
    '#import-annotations'
  );
  const exportButton = document.querySelector(
    '#export-annotations'
  );
  const clearButton = document.querySelector(
    '#clear-annotations'
  );
  const fileInput = document.querySelector(
    '#annotations-file-input'
  );

  if (
    !menuButton ||
    !appMenu ||
    !importButton ||
    !exportButton ||
    !clearButton ||
    !fileInput
  ) {
    console.error(
      'Impossible d’initialiser les fonctions d’import-export.'
    );

    return;
  }

  menuButton.addEventListener('click', event => {
    event.stopPropagation();

    const isOpen = !appMenu.hidden;

    appMenu.hidden = isOpen;

    menuButton.setAttribute(
      'aria-expanded',
      String(!isOpen)
    );
  });

  exportButton.addEventListener('click', async () => {
    closeAppMenu();

    try {
      await exportAnnotations(annotationApi);
    } catch (error) {
      console.error(error);

      showMessage(
        'L’export des annotations a échoué.',
        'error'
      );
    }
  });

  importButton.addEventListener('click', () => {
    closeAppMenu();

    fileInput.value = '';
    fileInput.click();
  });

  fileInput.addEventListener('change', async event => {
    const [file] = event.target.files;

    if (!file) {
      return;
    }

    try {
      await importAnnotations(file, annotationApi);
    } catch (error) {
      console.error(error);

      showMessage(
        error.message ||
          'Le fichier d’annotations est invalide.',
        'error'
      );
    } finally {
      fileInput.value = '';
    }
  });

  clearButton.addEventListener('click', () => {
    closeAppMenu();

    const annotations = annotationApi.getAnnotations();

    if (annotations.length === 0) {
      showMessage(
        'Il n’y a aucune annotation à supprimer.',
        'info'
      );

      return;
    }

    const confirmed = window.confirm(
      'Supprimer toutes les annotations de la transcription ?'
    );

    if (!confirmed) {
      return;
    }

    annotationApi.clearAnnotations();

    showMessage(
      'Toutes les annotations ont été supprimées.',
      'success'
    );
  });

  document.addEventListener('pointerdown', event => {
    if (
      appMenu.hidden ||
      appMenu.contains(event.target) ||
      menuButton.contains(event.target)
    ) {
      return;
    }

    closeAppMenu();
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !appMenu.hidden) {
      closeAppMenu();
      menuButton.focus();
    }
  });
}

async function exportAnnotations(annotationApi) {
  const transcription = getTranscriptionElement();
  const documentText = getDocumentText(transcription);
  const documentHash = await createTextHash(documentText);

  const rawAnnotations =
    annotationApi.getAnnotations();

  const annotations = rawAnnotations.map(annotation => {
    return enrichAnnotation(
      annotation,
      documentText
    );
  });

  const exportData = {
    format: EXPORT_FORMAT,
    version: EXPORT_VERSION,

    document: {
      id: DOCUMENT_ID,
      title: 'Journal de Théophile-Rémy Frêne',
      textLength: documentText.length,
      textHash: `sha256:${documentHash}`
    },

    exportedAt: new Date().toISOString(),

    annotationCount: annotations.length,

    annotations
  };

  const json = JSON.stringify(
    exportData,
    null,
    2
  );

  const blob = new Blob(
    [json],
    {
      type: 'application/json;charset=utf-8'
    }
  );

  const filename = createExportFilename();

  downloadBlob(blob, filename);

  showMessage(
    `${annotations.length} annotation(s) exportée(s).`,
    'success'
  );
}

async function importAnnotations(
  file,
  annotationApi
) {
  validateFileType(file);

  const fileContent = await file.text();

  let importedData;

  try {
    importedData = JSON.parse(fileContent);
  } catch {
    throw new Error(
      'Le fichier sélectionné ne contient pas un JSON valide.'
    );
  }

  validateExportStructure(importedData);

  const transcription = getTranscriptionElement();
  const currentText = getDocumentText(transcription);
  const currentHash = await createTextHash(currentText);

  const expectedHash =
    importedData.document.textHash;

  const actualHash =
    `sha256:${currentHash}`;

  if (expectedHash !== actualHash) {
    throw new Error(
      [
        'Le texte actuel ne correspond pas au texte',
        'sur lequel ces annotations ont été créées.',
        'L’import a été annulé afin de préserver',
        'les positions exactes.'
      ].join(' ')
    );
  }

  validateAnnotations(
    importedData.annotations,
    currentText
  );

  const existingAnnotations =
    annotationApi.getAnnotations();

  let replaceExisting = true;

  if (existingAnnotations.length > 0) {
    replaceExisting = window.confirm(
      [
        'La transcription contient déjà des annotations.',
        '',
        'OK : remplacer les annotations actuelles.',
        'Annuler : abandonner l’import.'
      ].join('\n')
    );

    if (!replaceExisting) {
      showMessage(
        'Import annulé.',
        'info'
      );

      return;
    }
  }

  annotationApi.setAnnotations(
    importedData.annotations
  );

  showMessage(
    `${importedData.annotations.length} annotation(s) importée(s).`,
    'success'
  );
}

function enrichAnnotation(
  annotation,
  documentText
) {
  const clonedAnnotation =
    structuredClone(annotation);

  const selectors =
    clonedAnnotation?.target?.selector;

  if (!Array.isArray(selectors)) {
    return clonedAnnotation;
  }

  clonedAnnotation.target.selector =
    selectors.map(selector => {
      if (
        !Number.isInteger(selector.start) ||
        !Number.isInteger(selector.end)
      ) {
        return selector;
      }

      const start = selector.start;
      const end = selector.end;

      const exact =
        documentText.slice(start, end);

      const prefixStart = Math.max(
        0,
        start - CONTEXT_LENGTH
      );

      const suffixEnd = Math.min(
        documentText.length,
        end + CONTEXT_LENGTH
      );

      return {
        ...selector,

        /*
         * Recogito utilise généralement "quote".
         * Nous ajoutons aussi "exact" pour rendre
         * le fichier plus explicite et plus proche
         * du modèle Web Annotation.
         */
        quote:
          selector.quote ??
          exact,

        exact,

        prefix: documentText.slice(
          prefixStart,
          start
        ),

        suffix: documentText.slice(
          end,
          suffixEnd
        )
      };
    });

  return clonedAnnotation;
}

function validateExportStructure(data) {
  if (!data || typeof data !== 'object') {
    throw new Error(
      'La structure du fichier JSON est invalide.'
    );
  }

  if (data.format !== EXPORT_FORMAT) {
    throw new Error(
      'Ce fichier ne provient pas de Frêne Annotator.'
    );
  }

  if (data.version !== EXPORT_VERSION) {
    throw new Error(
      `Version de fichier non prise en charge : ${data.version}.`
    );
  }

  if (
    !data.document ||
    data.document.id !== DOCUMENT_ID
  ) {
    throw new Error(
      'Ce fichier concerne un autre document.'
    );
  }

  if (
    typeof data.document.textHash !== 'string'
  ) {
    throw new Error(
      'L’empreinte du texte est absente du fichier.'
    );
  }

  if (!Array.isArray(data.annotations)) {
    throw new Error(
      'La liste des annotations est absente.'
    );
  }
}

function validateAnnotations(
  annotations,
  documentText
) {
  const annotationIds = new Set();

  annotations.forEach((annotation, index) => {
    if (
      !annotation ||
      typeof annotation !== 'object'
    ) {
      throw new Error(
        `L’annotation ${index + 1} est invalide.`
      );
    }

    if (
      typeof annotation.id !== 'string' ||
      annotation.id.length === 0
    ) {
      throw new Error(
        `L’annotation ${index + 1} ne possède pas d’identifiant.`
      );
    }

    if (annotationIds.has(annotation.id)) {
      throw new Error(
        `L’identifiant ${annotation.id} est présent plusieurs fois.`
      );
    }

    annotationIds.add(annotation.id);

    validateAnnotationSelectors(
      annotation,
      documentText,
      index
    );
  });
}

function validateAnnotationSelectors(
  annotation,
  documentText,
  annotationIndex
) {
  const selectors =
    annotation?.target?.selector;

  if (
    !Array.isArray(selectors) ||
    selectors.length === 0
  ) {
    throw new Error(
      `L’annotation ${annotationIndex + 1} ne possède pas de position.`
    );
  }

  const positionalSelector = selectors.find(
    selector => {
      return (
        Number.isInteger(selector?.start) &&
        Number.isInteger(selector?.end)
      );
    }
  );

  if (!positionalSelector) {
    throw new Error(
      `La position de l’annotation ${annotationIndex + 1} est absente.`
    );
  }

  const {
    start,
    end
  } = positionalSelector;

  if (
    start < 0 ||
    end <= start ||
    end > documentText.length
  ) {
    throw new Error(
      `La position de l’annotation ${annotationIndex + 1} est hors limites.`
    );
  }

  const expectedText =
    positionalSelector.exact ??
    positionalSelector.quote;

  if (typeof expectedText !== 'string') {
    throw new Error(
      `Le texte de l’annotation ${annotationIndex + 1} est absent.`
    );
  }

  const currentText =
    documentText.slice(start, end);

  if (currentText !== expectedText) {
    throw new Error(
      [
        `L’annotation ${annotationIndex + 1}`,
        `ne correspond pas au texte situé entre`,
        `les positions ${start} et ${end}.`
      ].join(' ')
    );
  }
}

function validateFileType(file) {
  const isJsonMimeType =
    file.type === 'application/json';

  const hasJsonExtension =
    file.name.toLowerCase().endsWith('.json');

  if (!isJsonMimeType && !hasJsonExtension) {
    throw new Error(
      'Sélectionne un fichier portant l’extension .json.'
    );
  }

  const maximumSize = 10 * 1024 * 1024;

  if (file.size > maximumSize) {
    throw new Error(
      'Le fichier dépasse la taille maximale de 10 Mo.'
    );
  }
}

function getTranscriptionElement() {
  const transcription = document.querySelector(
    '#transcription'
  );

  if (!transcription) {
    throw new Error(
      'La transcription est introuvable.'
    );
  }

  return transcription;
}

function getDocumentText(transcription) {
  /*
   * textContent correspond au contenu des nœuds textuels
   * utilisés pour calculer les positions de caractères.
   */
  return transcription.textContent ?? '';
}

async function createTextHash(text) {
  const encodedText =
    new TextEncoder().encode(text);

  const hashBuffer =
    await crypto.subtle.digest(
      'SHA-256',
      encodedText
    );

  return Array.from(
    new Uint8Array(hashBuffer)
  )
    .map(byte =>
      byte.toString(16).padStart(2, '0')
    )
    .join('');
}

function createExportFilename() {
  const date =
    new Date()
      .toISOString()
      .slice(0, 10);

  return `annotations_Frene_volume_1_${date}.json`;
}

function downloadBlob(blob, filename) {
  const objectUrl =
    URL.createObjectURL(blob);

  const link =
    document.createElement('a');

  link.href = objectUrl;
  link.download = filename;

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(objectUrl);
}

function closeAppMenu() {
  const menu = document.querySelector('#app-menu');
  const button = document.querySelector(
    '#app-menu-button'
  );

  if (menu) {
    menu.hidden = true;
  }

  button?.setAttribute(
    'aria-expanded',
    'false'
  );
}

function showMessage(
  message,
  type = 'info'
) {
  const messageBox = document.querySelector(
    '#application-message'
  );

  if (!messageBox) {
    return;
  }

  messageBox.textContent = message;
  messageBox.dataset.type = type;
  messageBox.hidden = false;

  window.clearTimeout(
    showMessage.timeoutId
  );

  showMessage.timeoutId =
    window.setTimeout(() => {
      messageBox.hidden = true;
    }, 4500);
}

showMessage.timeoutId = null;