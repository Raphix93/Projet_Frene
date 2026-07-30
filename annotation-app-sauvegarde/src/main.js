import './style.css';
import './tei-loader.css';

import {
  initAnnotator
} from './annotator.js';

import {
  initAnnotationsIO
} from './annotations-io.js';

import {
  loadConfiguredTei
} from './tei-loader.js';

const app = document.querySelector('#app');

if (!app) {
  throw new Error(
    "L’élément #app est introuvable."
  );
}

app.innerHTML = `
  <div class="app-container">
    <header class="site-header">
      <div class="site-title">
        <h1 id="application-title">Projet Frêne</h1>
        <p id="document-title">
          Chargement de la TEI…
        </p>
      </div>

      <div class="app-menu-container">
        <button
          type="button"
          id="app-menu-button"
          class="app-menu-button"
          aria-label="Ouvrir le menu"
          aria-expanded="false"
          aria-controls="app-menu"
          disabled
        >☰</button>

        <div id="app-menu" class="app-menu" hidden>
          <button type="button" id="import-annotations">
            Importer les annotations
          </button>
          <button type="button" id="export-annotations">
            Exporter les annotations
          </button>
          <div class="app-menu-separator"></div>
          <button
            type="button"
            id="clear-annotations"
            class="danger-menu-button"
          >
            Effacer toutes les annotations
          </button>
        </div>

        <input
          id="annotations-file-input"
          type="file"
          accept=".json,application/json"
          hidden
        >
      </div>
    </header>

    <section
      class="document-status"
      aria-label="Document chargé"
    >
      <span>
        Fichier :
        <strong id="document-file">—</strong>
      </span>
      <span>
        Portée :
        <strong id="document-scope">text/body</strong>
      </span>
      <span>
        SHA-256 :
        <code id="document-sha">—</code>
      </span>
    </section>

    <div
      id="application-message"
      class="application-message"
      role="status"
      aria-live="polite"
      hidden
    ></div>

    <main
      id="transcription"
      class="transcription"
      aria-label="Transcription à annoter"
      aria-busy="true"
    >
      <div class="tei-loading">
        Chargement du véritable texte TEI…
      </div>
    </main>

    <footer
      class="annotation-counts"
      aria-label="Nombre d’annotations"
    >
      ${counter('person', 'person-color', 'Personnes')}
      ${counter('place', 'place-color', 'Lieux')}
      ${counter('date', 'date-color', 'Dates')}
      ${counter(
        'normalization',
        'correction-color',
        'Normalisations'
      )}
      ${counter(
        'correction',
        'free-correction-color',
        'Corrections libres'
      )}
    </footer>
  </div>

  ${contextMenu()}
  ${replacementDialog()}
`;

startApplication();

async function startApplication() {
  const transcription =
    document.querySelector('#transcription');

  try {
    const documentData =
      await loadConfiguredTei();

    transcription.replaceChildren(
      documentData.fragment
    );

    transcription.setAttribute(
      'aria-busy',
      'false'
    );

    updateDocumentHeader(documentData);

    const annotatorApi = initAnnotator();

    if (!annotatorApi) {
      throw new Error(
        'Initialisation de l’annotateur impossible.'
      );
    }

    initAnnotationsIO(annotatorApi);

    document.querySelector(
      '#app-menu-button'
    ).disabled = false;

    showApplicationMessage(
      'TEI chargée. Seul <text><body> est affiché.'
    );
  } catch (error) {
    transcription.setAttribute(
      'aria-busy',
      'false'
    );

    transcription.innerHTML = `
      <div class="tei-load-error">
        <h2>Chargement impossible</h2>
        <p>${escapeHtml(error.message)}</p>
        <p>
          Vérifie <code>public/config.json</code> et la
          présence du fichier dans
          <code>public/data/</code>.
        </p>
      </div>
    `;

    showApplicationMessage(
      error.message,
      true
    );

    console.error(error);
  }
}

function updateDocumentHeader(documentData) {
  const { config, sha256 } = documentData;

  document.querySelector(
    '#application-title'
  ).textContent =
    config.application?.name ??
    'Projet Frêne';

  document.querySelector(
    '#document-title'
  ).textContent =
    config.document.title;

  document.querySelector(
    '#document-file'
  ).textContent =
    config.document.file ??
    config.document.url.split('/').pop();

  document.querySelector(
    '#document-scope'
  ).textContent = 'text/body';

  document.querySelector(
    '#document-sha'
  ).textContent =
    `${sha256.slice(0, 12)}…`;
}

function counter(id, colorClass, label) {
  return `
    <span class="annotation-count">
      <span
        class="legend-color ${colorClass}"
        aria-hidden="true"
      ></span>
      ${label} :
      <strong id="${id}-count">0</strong>
    </span>
  `;
}

function contextMenu() {
  const item = (type, colorClass, label) => `
    <button type="button" data-type="${type}" role="menuitem">
      <span
        class="menu-dot ${colorClass}"
        aria-hidden="true"
      ></span>
      ${label}
    </button>
  `;

  return `
    <div
      id="context-menu"
      class="context-menu"
      role="menu"
      aria-label="Menu d’annotation"
      hidden
    >
      <div
        id="context-menu-title"
        class="context-menu-title"
      >
        Annoter comme
      </div>

      ${item('person', 'person-color', 'Personne')}
      ${item('place', 'place-color', 'Lieu')}
      ${item('date', 'date-color', 'Date')}
      ${item(
        'normalization',
        'correction-color',
        'Normalisation'
      )}
      ${item(
        'correction',
        'free-correction-color',
        'Correction libre'
      )}

      <div
        id="context-menu-separator"
        class="context-menu-separator"
        hidden
      ></div>

      <button
        type="button"
        id="delete-annotation"
        class="delete-annotation"
        role="menuitem"
        hidden
      >
        Supprimer l’annotation
      </button>
    </div>
  `;
}

function replacementDialog() {
  return `
    <dialog
      id="correction-dialog"
      class="correction-dialog"
    >
      <form id="correction-form">
        <h2 id="correction-dialog-title">
          Modifier le texte
        </h2>

        <p class="selected-text">
          Texte original :
          <strong id="original-text"></strong>
        </p>

        <label
          id="replacement-text-label"
          for="corrected-text"
        >
          Texte de remplacement
        </label>

        <input
          id="corrected-text"
          name="corrected-text"
          type="text"
          autocomplete="off"
          required
        >

        <div class="dialog-actions">
          <button
            type="button"
            id="cancel-correction"
            class="secondary-button"
          >
            Annuler
          </button>
          <button type="submit">
            Enregistrer
          </button>
        </div>
      </form>
    </dialog>
  `;
}

function showApplicationMessage(
  message,
  isError = false
) {
  const element = document.querySelector(
    '#application-message'
  );

  element.textContent = message;
  element.hidden = false;
  element.classList.toggle(
    'error',
    isError
  );
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
