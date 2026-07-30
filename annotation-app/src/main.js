import './style.css';
import { initAnnotator } from './annotator.js';
import { initAnnotationsIO } from './annotations-io.js';
import { loadConfiguredTei } from './tei-loader.js';

const app = document.querySelector('#app');

app.innerHTML = `
  <div class="app-container">
    <header class="site-header">
      <div class="site-title">
        <h1 id="application-title">Projet Frêne</h1>
        <p id="document-title">Chargement de la TEI…</p>
      </div>

      <div class="app-menu-container">
        <button id="app-menu-button" class="app-menu-button" type="button"
          aria-label="Ouvrir le menu" aria-expanded="false" disabled>☰</button>

        <div id="app-menu" class="app-menu" hidden>
          <button id="import-annotations" type="button">Importer les annotations</button>
          <button id="export-annotations" type="button">Exporter les annotations</button>
          <div class="app-menu-separator"></div>
          <button id="clear-annotations" type="button" class="danger-menu-button">
            Effacer toutes les annotations
          </button>
        </div>

        <input id="annotations-file-input" type="file"
          accept=".json,application/json" hidden>
      </div>
    </header>

    <section class="document-status">
      <span>Fichier : <strong id="document-file">—</strong></span>
      <span>Portée : <strong>text/body</strong></span>
      <span>SHA-256 : <code id="document-sha">—</code></span>
    </section>

    <div id="application-message" class="application-message"
      role="status" aria-live="polite" hidden></div>

    <main id="transcription" class="transcription"
      aria-label="Transcription à annoter" aria-busy="true">
      <p class="loading">Chargement du véritable texte TEI…</p>
    </main>

    <footer class="annotation-counts">
      ${counter('person', 'Personnes')}
      ${counter('place', 'Lieux')}
      ${counter('date', 'Dates')}
      ${counter('normalization', 'Normalisations')}
      ${counter('correction', 'Corrections libres')}
    </footer>
  </div>

  <div id="context-menu" class="context-menu" role="menu" hidden>
    <div id="context-menu-title" class="context-menu-title">Annoter comme</div>
    ${menuItem('person', 'Personne')}
    ${menuItem('place', 'Lieu')}
    ${menuItem('date', 'Date')}
    ${menuItem('normalization', 'Normalisation')}
    ${menuItem('correction', 'Correction libre')}
    <div id="context-menu-separator" class="context-menu-separator" hidden></div>
    <button id="delete-annotation" class="delete-annotation"
      type="button" role="menuitem" hidden>Supprimer l’annotation</button>
  </div>

  <dialog id="correction-dialog" class="correction-dialog">
    <form id="correction-form">
      <h2 id="correction-dialog-title">Modifier le texte</h2>
      <p>Texte original : <strong id="original-text"></strong></p>
      <label id="replacement-text-label" for="corrected-text">
        Texte de remplacement
      </label>
      <input id="corrected-text" type="text" required autocomplete="off">
      <div class="dialog-actions">
        <button id="cancel-correction" type="button" class="secondary-button">
          Annuler
        </button>
        <button type="submit">Enregistrer</button>
      </div>
    </form>
  </dialog>
`;

start();

async function start() {
  const transcription = document.querySelector('#transcription');

  try {
    const data = await loadConfiguredTei();

    transcription.replaceChildren(data.fragment);
    transcription.setAttribute('aria-busy', 'false');

    document.querySelector('#application-title').textContent =
      data.config.application?.name ?? 'Projet Frêne';
    document.querySelector('#document-title').textContent =
      data.config.document.title;
    document.querySelector('#document-file').textContent =
      data.config.document.file ?? data.config.document.url.split('/').pop();
    document.querySelector('#document-sha').textContent =
      `${data.sha256.slice(0, 12)}…`;

    // Attend un cycle de rendu complet avant Recogito.
    await new Promise(resolve =>
      requestAnimationFrame(() => requestAnimationFrame(resolve))
    );

    const api = initAnnotator();

    if (!api) {
      throw new Error(
        'Initialisation de l’annotateur impossible. Consulte la console F12.'
      );
    }

    initAnnotationsIO(api);
    document.querySelector('#app-menu-button').disabled = false;
    showMessage('TEI chargée : le véritable <text><body> est prêt à être annoté.');
  } catch (error) {
    console.error(error);
    transcription.setAttribute('aria-busy', 'false');
    transcription.innerHTML = `
      <div class="load-error">
        <h2>Chargement impossible</h2>
        <p>${escapeHtml(error.message)}</p>
        <p>Ouvre la console avec <kbd>F12</kbd> pour voir le détail technique.</p>
      </div>
    `;
    showMessage(error.message, true);
  }
}

function counter(type, label) {
  return `<span><i class="legend ${type}"></i>${label} :
    <strong id="${type}-count">0</strong></span>`;
}

function menuItem(type, label) {
  return `<button type="button" data-type="${type}" role="menuitem">
    <i class="menu-dot ${type}"></i>${label}</button>`;
}

function showMessage(text, error = false) {
  const element = document.querySelector('#application-message');
  element.textContent = text;
  element.hidden = false;
  element.classList.toggle('error', error);
}

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = String(value);
  return div.innerHTML;
}
