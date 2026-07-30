import './style.css';

import {
  initAnnotator
} from './annotator.js';

import {
  initAnnotationsIO
} from './annotations-io.js';

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
        <h1>Projet Frêne</h1>
        <p>Journal de Théophile-Rémy Frêne</p>
      </div>

      <div class="app-menu-container">
        <button
          type="button"
          id="app-menu-button"
          class="app-menu-button"
          aria-label="Ouvrir le menu"
          aria-expanded="false"
          aria-controls="app-menu"
        >
          ☰
        </button>

        <div
          id="app-menu"
          class="app-menu"
          hidden
        >
          <button
            type="button"
            id="import-annotations"
          >
            Importer les annotations
          </button>

          <button
            type="button"
            id="export-annotations"
          >
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
    >
      <p>
        Le 12 mars 1754, je partis de Bienne pour me rendre à
        Neuchâtel, où je rencontrai Monsieur Tribolet.
      </p>

      <p>
        Il me parla de Samuel Frêne et de son voyage à Paris.
      </p>
    </main>

    <footer
      class="annotation-counts"
      aria-label="Nombre d’annotations"
    >
      <span class="annotation-count">
        <span
          class="legend-color person-color"
          aria-hidden="true"
        ></span>

        Personnes :
        <strong id="person-count">0</strong>
      </span>

      <span class="annotation-count">
        <span
          class="legend-color place-color"
          aria-hidden="true"
        ></span>

        Lieux :
        <strong id="place-count">0</strong>
      </span>

      <span class="annotation-count">
        <span
          class="legend-color date-color"
          aria-hidden="true"
        ></span>

        Dates :
        <strong id="date-count">0</strong>
      </span>

      <span class="annotation-count">
        <span
          class="legend-color correction-color"
          aria-hidden="true"
        ></span>

        Normalisations :
        <strong id="normalization-count">0</strong>
      </span>

      <span class="annotation-count">
        <span
          class="legend-color"
          style="background: #EDE9FE"
          aria-hidden="true"
        ></span>

        Corrections libres :
        <strong id="correction-count">0</strong>
      </span>
    </footer>

  </div>

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

    <button
      type="button"
      data-type="person"
      role="menuitem"
    >
      <span
        class="menu-dot person-color"
        aria-hidden="true"
      ></span>

      Personne
    </button>

    <button
      type="button"
      data-type="place"
      role="menuitem"
    >
      <span
        class="menu-dot place-color"
        aria-hidden="true"
      ></span>

      Lieu
    </button>

    <button
      type="button"
      data-type="date"
      role="menuitem"
    >
      <span
        class="menu-dot date-color"
        aria-hidden="true"
      ></span>

      Date
    </button>

    <button
      type="button"
      data-type="normalization"
      role="menuitem"
    >
      <span
        class="menu-dot correction-color"
        aria-hidden="true"
      ></span>

      Normalisation
    </button>

    <button
      type="button"
      data-type="correction"
      role="menuitem"
    >
      <span
        class="menu-dot"
        style="background: #EDE9FE"
        aria-hidden="true"
      ></span>

      Correction libre
    </button>

    <div
      id="context-menu-separator"
      class="context-menu-separator"
      hidden
    ></div>

    <button
      type="button"
      id="add-uri"
      role="menuitem"
      hidden
    >
      Ajouter un URI
    </button>

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

  <dialog
    id="uri-dialog"
    class="correction-dialog"
  >
    <form id="uri-form">
      <h2>URI de l’entité</h2>

      <p class="selected-text">
        Ajoutez une URI complète ou un identifiant Wikidata.
      </p>

      <label for="annotation-uri">
        URI ou identifiant Wikidata
      </label>

      <input
        id="annotation-uri"
        name="annotation-uri"
        type="text"
        placeholder="Q39 ou https://www.wikidata.org/entity/Q39"
        autocomplete="off"
        required
      >

      <p
        id="uri-error"
        role="alert"
        hidden
      ></p>

      <div class="dialog-actions">
        <button
          type="button"
          id="remove-uri"
          class="secondary-button"
          hidden
        >
          Retirer l’URI
        </button>

        <button
          type="button"
          id="cancel-uri"
          class="secondary-button"
        >
          Annuler
        </button>

        <button
          type="submit"
          id="save-uri"
          class="primary-button"
        >
          Enregistrer
        </button>
      </div>
    </form>
  </dialog>

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

        <button
          type="submit"
          id="save-correction"
          class="primary-button"
        >
          Enregistrer
        </button>
      </div>
    </form>
  </dialog>
`;

const annotationApi = initAnnotator();

if (!annotationApi) {
  throw new Error(
    'L’annotateur n’a pas pu être initialisé.'
  );
}

initAnnotationsIO(annotationApi);