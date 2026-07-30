import { createTextAnnotator } from '@recogito/text-annotator';
import '@recogito/text-annotator/text-annotator.css';

const COLORS = {
  person: '#DBEAFE',
  place: '#DCFCE7',
  date: '#FEF3C7',
  normalization: '#FEE2E2',
  correction: '#EDE9FE'
};

const LABELS = {
  person: 'Personne',
  place: 'Lieu',
  date: 'Date',
  normalization: 'Normalisation',
  correction: 'Correction libre'
};

let annotator = null;
let activeAnnotation = null;
let isNewAnnotation = false;
let lastPointerPosition = null;
let activeTextActionType = null;

export function initAnnotator() {
  const transcription = document.querySelector('#transcription');
  const contextMenu = document.querySelector('#context-menu');
  const uriButton = document.querySelector(
    '#add-uri'
  );
  const deleteButton = document.querySelector(
    '#delete-annotation'
  );

  if (
    !transcription ||
    !contextMenu ||
    !uriButton ||
    !deleteButton
  ) {
    console.error(
      'Impossible d’initialiser l’interface d’annotation.'
    );

    return;
  }

  annotator = createTextAnnotator(transcription, {
    style: getAnnotationStyle
  });

  /*
   * Mémorise la position du clic afin de placer le menu
   * près d’une annotation existante.
   */
  transcription.addEventListener('pointerdown', event => {
    lastPointerPosition = {
      x: event.clientX,
      y: event.clientY
    };
  });

  /*
   * Une nouvelle sélection vient de créer une annotation.
   */
  annotator.on('createAnnotation', annotation => {
    activeAnnotation = annotation;
    isNewAnnotation = true;

    const selectionRectangle = getSelectionRectangle();

    if (!selectionRectangle) {
      removeAbandonedNewAnnotation();
      return;
    }

    openContextMenu(selectionRectangle);
  });

  /*
   * L’utilisateur clique sur une annotation existante.
   */
  annotator.on('selectionChanged', annotations => {
    if (!Array.isArray(annotations) || annotations.length === 0) {
      if (!isNewAnnotation) {
        activeAnnotation = null;
        closeContextMenu();
      }

      return;
    }

    const selectedAnnotation = annotations[0];

    /*
     * Empêche cet événement de remplacer immédiatement
     * l’état d’une annotation qui vient d’être créée.
     */
    if (
      isNewAnnotation &&
      activeAnnotation?.id === selectedAnnotation.id
    ) {
      return;
    }

    activeAnnotation = selectedAnnotation;
    isNewAnnotation = false;

    openContextMenu(getPointerRectangle());
  });

  annotator.on('updateAnnotation', updateCounters);
  annotator.on('deleteAnnotation', updateCounters);

  contextMenu.addEventListener(
    'click',
    handleContextMenuClick
  );

  uriButton.addEventListener(
    'click',
    openUriDialog
  );

  deleteButton.addEventListener(
    'click',
    deleteActiveAnnotation
  );

  document.addEventListener(
    'pointerdown',
    handleDocumentPointerDown
  );

  document.addEventListener(
    'keydown',
    handleKeyboardNavigation
  );

  window.addEventListener('resize', closeContextMenu);

  window.addEventListener(
    'scroll',
    closeContextMenu,
    { passive: true }
  );

  setupCorrectionDialog();
  setupUriDialog();
  updateCounters();

  console.log('Frêne Annotator initialisé');

  return {
    getAnnotations() {
        return makeAnnotationsSerializable(
            annotator.getAnnotations()
         );
    },

    setAnnotations(annotations) {
        annotator.setAnnotations(
            JSON.parse(JSON.stringify(annotations)),
            true
        );

        activeAnnotation = null;
        isNewAnnotation = false;

        closeContextMenu();
        clearBrowserSelection();
        updateCounters();
    },

    clearAnnotations() {
      annotator.clearAnnotations();

      activeAnnotation = null;
      isNewAnnotation = false;

      closeContextMenu();
      clearBrowserSelection();
      updateCounters();
    }
  };
}

function getAnnotationType(annotation) {
  const typeBody = annotation?.bodies?.find(
    body => body.purpose === 'tagging'
  );

  return typeBody?.value ?? null;
}

function getReplacementText(annotation, type) {
  const purpose =
    type === 'normalization'
      ? 'normalizing'
      : 'correcting';

  const replacementBody = annotation?.bodies?.find(
    body => body.purpose === purpose
  );

  return replacementBody?.value ?? '';
}

function getAnnotationUri(annotation) {
  const uriBody = annotation?.bodies?.find(
    body => body.purpose === 'linking'
  );

  return uriBody?.value ?? '';
}

function isUriCompatibleType(type) {
  return type === 'person' || type === 'place';
}

function normalizeWikidataUri(value) {
  const trimmedValue = value.trim();

  if (/^Q\d+$/i.test(trimmedValue)) {
    return (
      'https://www.wikidata.org/entity/' +
      trimmedValue.toUpperCase()
    );
  }

  return trimmedValue;
}

function isValidUri(value) {
  try {
    const uri = new URL(value);

    return (
      uri.protocol === 'https:' ||
      uri.protocol === 'http:'
    );
  } catch {
    return false;
  }
}

function getAnnotationStyle(annotation, state = {}) {
  const type = getAnnotationType(annotation);

  return {
    fill: COLORS[type] ?? '#DDE7F0',
    fillOpacity:
      state.hovered || state.selected
        ? 0.95
        : 0.75,
    underlineColor: 'transparent',
    underlineThickness: 0
  };
}

function handleContextMenuClick(event) {
  const typeButton = event.target.closest(
    'button[data-type]'
  );

  if (!typeButton || !activeAnnotation) {
    return;
  }

  const type = typeButton.dataset.type;

  if (!Object.hasOwn(LABELS, type)) {
    return;
  }

  if (
    type === 'normalization' ||
    type === 'correction'
  ) {
    activeTextActionType = type;
    closeContextMenu();
    openCorrectionDialog(type);
    return;
  }

  saveAnnotationType(type);
}

function saveAnnotationType(type, replacementText = '') {
  if (!activeAnnotation || !annotator) {
    return;
  }

  const preservedBodies = (
    activeAnnotation.bodies ?? []
  ).filter(body => {
    return (
      body.purpose !== 'tagging' &&
      body.purpose !== 'normalizing' &&
      body.purpose !== 'correcting'
    );
  });

  const newBodies = [
    ...preservedBodies,
    {
      id: crypto.randomUUID(),
      annotation: activeAnnotation.id,
      purpose: 'tagging',
      value: type
    }
  ];

  if (type === 'normalization' && replacementText) {
    newBodies.push({
      id: crypto.randomUUID(),
      annotation: activeAnnotation.id,
      purpose: 'normalizing',
      value: replacementText
    });
  }

  if (type === 'correction' && replacementText) {
    newBodies.push({
      id: crypto.randomUUID(),
      annotation: activeAnnotation.id,
      purpose: 'correcting',
      value: replacementText
    });
  }

  const updatedAnnotation = {
    ...activeAnnotation,
    bodies: newBodies
  };

  annotator.updateAnnotation(updatedAnnotation);

  activeTextActionType = null;
  finishCurrentAction();
}

function saveAnnotationUri(uri) {
  if (!activeAnnotation || !annotator) {
    return;
  }

  const currentType =
    getAnnotationType(activeAnnotation);

  if (!isUriCompatibleType(currentType)) {
    return;
  }

  const preservedBodies = (
    activeAnnotation.bodies ?? []
  ).filter(body => body.purpose !== 'linking');

  const updatedAnnotation = {
    ...activeAnnotation,
    bodies: [
      ...preservedBodies,
      {
        id: crypto.randomUUID(),
        annotation: activeAnnotation.id,
        purpose: 'linking',
        value: uri
      }
    ]
  };

  annotator.updateAnnotation(updatedAnnotation);
  finishCurrentAction();
}

function deleteActiveAnnotation() {
  if (!activeAnnotation || !annotator) {
    return;
  }

  const annotationId = activeAnnotation.id;

  activeAnnotation = null;
  isNewAnnotation = false;

  closeContextMenu();

  annotator.removeAnnotation(annotationId);

  clearBrowserSelection();
  updateCounters();
}

function finishCurrentAction() {
  activeAnnotation = null;
  isNewAnnotation = false;

  closeContextMenu();
  clearBrowserSelection();
  updateCounters();
}

function openContextMenu(anchorRectangle) {
  const menu = document.querySelector('#context-menu');
  const title = document.querySelector('#context-menu-title');
  const uriButton = document.querySelector(
    '#add-uri'
  );
  const deleteButton = document.querySelector(
    '#delete-annotation'
  );
  const separator = document.querySelector(
    '#context-menu-separator'
  );

  if (
    !menu ||
    !title ||
    !uriButton ||
    !deleteButton ||
    !separator ||
    !activeAnnotation
  ) {
    return;
  }

  const currentType = getAnnotationType(activeAnnotation);
  const isExistingAnnotation =
    !isNewAnnotation && Boolean(currentType);

  if (isExistingAnnotation) {
    title.textContent =
      `Annotation : ${LABELS[currentType] ?? 'Type inconnu'}`;

    const canAddUri =
      isUriCompatibleType(currentType);

    const existingUri =
      getAnnotationUri(activeAnnotation);

    uriButton.hidden = !canAddUri;
    uriButton.textContent = existingUri
      ? 'Modifier l’URI'
      : 'Ajouter un URI';

    deleteButton.hidden = false;
    separator.hidden = false;
  } else {
    title.textContent = 'Annoter comme';

    uriButton.hidden = true;
    deleteButton.hidden = true;
    separator.hidden = true;
  }

  menu
    .querySelectorAll('button[data-type]')
    .forEach(button => {
      const isCurrentType =
        button.dataset.type === currentType;

      button.classList.toggle(
        'current-type',
        isCurrentType
      );

      button.setAttribute(
        'aria-checked',
        String(isCurrentType)
      );
    });

  positionMenuInsideApplication(
    menu,
    anchorRectangle
  );
}

function closeContextMenu() {
  const menu = document.querySelector('#context-menu');

  if (menu) {
    menu.hidden = true;
  }
}

function positionMenuInsideApplication(
  menu,
  anchorRectangle
) {
  const application = document.querySelector(
    '.app-container'
  );

  if (!application || !anchorRectangle) {
    return;
  }

  const applicationRectangle =
    application.getBoundingClientRect();

  const padding = 12;
  const gap = 10;

  /*
   * Limites correspondant à la partie visible
   * de l’application.
   */
  const visibleLeft = Math.max(
    applicationRectangle.left,
    0
  );

  const visibleRight = Math.min(
    applicationRectangle.right,
    window.innerWidth
  );

  const visibleTop = Math.max(
    applicationRectangle.top,
    0
  );

  const visibleBottom = Math.min(
    applicationRectangle.bottom,
    window.innerHeight
  );

  menu.hidden = false;

  /*
   * Il faut rendre le menu visible avant de mesurer
   * sa largeur et sa hauteur.
   */
  const menuRectangle = menu.getBoundingClientRect();
  const menuWidth = menuRectangle.width;
  const menuHeight = menuRectangle.height;

  let left =
    anchorRectangle.left +
    anchorRectangle.width / 2 -
    menuWidth / 2;

  const minimumLeft = visibleLeft + padding;
  const maximumLeft =
    visibleRight - menuWidth - padding;

  if (maximumLeft >= minimumLeft) {
    left = clamp(
      left,
      minimumLeft,
      maximumLeft
    );
  } else {
    left = Math.max(padding, minimumLeft);
  }

  let top = anchorRectangle.bottom + gap;

  const minimumTop = visibleTop + padding;
  const maximumTop =
    visibleBottom - menuHeight - padding;

  /*
   * En cas de manque de place sous la sélection,
   * le menu est placé au-dessus.
   */
  if (top > maximumTop) {
    top =
      anchorRectangle.top -
      menuHeight -
      gap;
  }

  if (maximumTop >= minimumTop) {
    top = clamp(
      top,
      minimumTop,
      maximumTop
    );
  } else {
    /*
     * Cas d’une fenêtre très petite :
     * le menu reste au moins visible en haut.
     */
    top = Math.max(padding, visibleTop + padding);
  }

  menu.style.left = `${Math.round(left)}px`;
  menu.style.top = `${Math.round(top)}px`;
}

function getSelectionRectangle() {
  const selection = window.getSelection();

  if (
    !selection ||
    selection.rangeCount === 0 ||
    selection.isCollapsed
  ) {
    return null;
  }

  const rectangle = selection
    .getRangeAt(0)
    .getBoundingClientRect();

  if (rectangle.width === 0 && rectangle.height === 0) {
    return null;
  }

  return rectangle;
}

function getPointerRectangle() {
  if (lastPointerPosition) {
    return createPointRectangle(
      lastPointerPosition.x,
      lastPointerPosition.y
    );
  }

  const application = document.querySelector(
    '.app-container'
  );

  if (!application) {
    return createPointRectangle(
      window.innerWidth / 2,
      100
    );
  }

  const rectangle = application.getBoundingClientRect();

  return createPointRectangle(
    rectangle.left + rectangle.width / 2,
    Math.max(rectangle.top + 100, 100)
  );
}

function createPointRectangle(x, y) {
  return {
    left: x,
    right: x,
    top: y,
    bottom: y,
    width: 0,
    height: 0
  };
}

function setupCorrectionDialog() {
  const dialog = document.querySelector(
    '#correction-dialog'
  );
  const form = document.querySelector(
    '#correction-form'
  );
  const cancelButton = document.querySelector(
    '#cancel-correction'
  );

  if (!dialog || !form || !cancelButton) {
    console.error(
      'La fenêtre de saisie est introuvable.'
    );
    return;
  }

  form.addEventListener('submit', event => {
    event.preventDefault();

    const correctedInput = document.querySelector(
      '#corrected-text'
    );

    if (!correctedInput || !activeTextActionType) {
      return;
    }

    const replacementText =
      correctedInput.value.trim();

    if (!replacementText) {
      correctedInput.focus();
      return;
    }

    dialog.close();

    saveAnnotationType(
      activeTextActionType,
      replacementText
    );
  });

  cancelButton.addEventListener(
    'click',
    cancelCorrection
  );

  dialog.addEventListener('cancel', event => {
    event.preventDefault();
    cancelCorrection();
  });
}

function openCorrectionDialog(type) {
  const dialog = document.querySelector(
    '#correction-dialog'
  );
  const dialogTitle = document.querySelector(
    '#correction-dialog-title'
  );
  const fieldLabel = document.querySelector(
    '#replacement-text-label'
  );
  const originalText = document.querySelector(
    '#original-text'
  );
  const correctedInput = document.querySelector(
    '#corrected-text'
  );

  if (
    !dialog ||
    !dialogTitle ||
    !fieldLabel ||
    !originalText ||
    !correctedInput ||
    !activeAnnotation
  ) {
    return;
  }

  const isNormalization =
    type === 'normalization';

  dialogTitle.textContent = isNormalization
    ? 'Normaliser le texte'
    : 'Corriger librement le texte';

  fieldLabel.textContent = isNormalization
    ? 'Forme normalisée'
    : 'Texte corrigé';

  originalText.textContent =
    getSelectedAnnotationText(activeAnnotation);

  correctedInput.value =
    getReplacementText(activeAnnotation, type);

  dialog.showModal();

  requestAnimationFrame(() => {
    correctedInput.focus();
    correctedInput.select();
  });
}

function cancelCorrection() {
  const dialog = document.querySelector(
    '#correction-dialog'
  );

  if (dialog?.open) {
    dialog.close();
  }

  activeTextActionType = null;

  /*
   * Une nouvelle annotation sans type ne doit pas
   * rester dans la transcription après une annulation.
   */
  if (isNewAnnotation && activeAnnotation) {
    removeAbandonedNewAnnotation();
    return;
  }

  finishCurrentAction();
}

function getSelectedAnnotationText(annotation) {
  const selectors = annotation?.target?.selector;

  if (Array.isArray(selectors)) {
    const quoteSelector = selectors.find(selector => {
      return (
        typeof selector?.quote === 'string' ||
        typeof selector?.exact === 'string' ||
        selector?.type === 'TextQuoteSelector'
      );
    });

    return (
      quoteSelector?.quote ??
      quoteSelector?.exact ??
      ''
    );
  }

  return (
    selectors?.quote ??
    selectors?.exact ??
    ''
  );
}

function setupUriDialog() {
  const dialog = document.querySelector(
    '#uri-dialog'
  );
  const form = document.querySelector(
    '#uri-form'
  );
  const cancelButton = document.querySelector(
    '#cancel-uri'
  );
  const removeButton = document.querySelector(
    '#remove-uri'
  );

  if (
    !dialog ||
    !form ||
    !cancelButton ||
    !removeButton
  ) {
    console.error(
      'La fenêtre de saisie de l’URI est introuvable.'
    );
    return;
  }

  form.addEventListener('submit', event => {
    event.preventDefault();

    const uriInput = document.querySelector(
      '#annotation-uri'
    );
    const errorMessage = document.querySelector(
      '#uri-error'
    );

    if (!uriInput || !errorMessage) {
      return;
    }

    const uri = normalizeWikidataUri(
      uriInput.value
    );

    if (!isValidUri(uri)) {
      errorMessage.textContent =
        'Saisissez une URI valide ou un identifiant Wikidata, par exemple Q39.';
      errorMessage.hidden = false;
      uriInput.focus();
      return;
    }

    errorMessage.hidden = true;
    dialog.close();
    saveAnnotationUri(uri);
  });

  cancelButton.addEventListener(
    'click',
    cancelUriDialog
  );

  removeButton.addEventListener('click', () => {
    removeAnnotationUri();
  });

  dialog.addEventListener('cancel', event => {
    event.preventDefault();
    cancelUriDialog();
  });
}

function openUriDialog() {
  const dialog = document.querySelector(
    '#uri-dialog'
  );
  const uriInput = document.querySelector(
    '#annotation-uri'
  );
  const removeButton = document.querySelector(
    '#remove-uri'
  );
  const errorMessage = document.querySelector(
    '#uri-error'
  );

  if (
    !dialog ||
    !uriInput ||
    !removeButton ||
    !errorMessage ||
    !activeAnnotation
  ) {
    return;
  }

  const currentType =
    getAnnotationType(activeAnnotation);

  if (!isUriCompatibleType(currentType)) {
    return;
  }

  const existingUri =
    getAnnotationUri(activeAnnotation);

  closeContextMenu();

  uriInput.value = existingUri;
  removeButton.hidden = !existingUri;
  errorMessage.hidden = true;
  errorMessage.textContent = '';

  dialog.showModal();

  requestAnimationFrame(() => {
    uriInput.focus();
    uriInput.select();
  });
}

function cancelUriDialog() {
  const dialog = document.querySelector(
    '#uri-dialog'
  );

  if (dialog?.open) {
    dialog.close();
  }

  finishCurrentAction();
}

function removeAnnotationUri() {
  if (!activeAnnotation || !annotator) {
    return;
  }

  const dialog = document.querySelector(
    '#uri-dialog'
  );

  const updatedAnnotation = {
    ...activeAnnotation,
    bodies: (
      activeAnnotation.bodies ?? []
    ).filter(body => body.purpose !== 'linking')
  };

  if (dialog?.open) {
    dialog.close();
  }

  annotator.updateAnnotation(updatedAnnotation);
  finishCurrentAction();
}

function handleDocumentPointerDown(event) {
  const menu = document.querySelector('#context-menu');
  const correctionDialog = document.querySelector(
    '#correction-dialog'
  );
  const uriDialog = document.querySelector(
    '#uri-dialog'
  );

  if (
    !menu ||
    menu.hidden ||
    correctionDialog?.open ||
    uriDialog?.open
  ) {
    return;
  }

  /*
   * Un clic dans le menu ne doit pas le fermer
   * avant l’exécution du bouton.
   */
  if (menu.contains(event.target)) {
    return;
  }

  /*
   * Un clic ailleurs ferme le menu.
   * Une nouvelle annotation encore non typée est retirée.
   */
  if (isNewAnnotation && activeAnnotation) {
    removeAbandonedNewAnnotation();
    return;
  }

  activeAnnotation = null;
  isNewAnnotation = false;

  closeContextMenu();
}

function handleKeyboardNavigation(event) {
  if (event.key !== 'Escape') {
    return;
  }

  const correctionDialog = document.querySelector(
    '#correction-dialog'
  );
  const uriDialog = document.querySelector(
    '#uri-dialog'
  );
  const menu = document.querySelector('#context-menu');

  if (
    correctionDialog?.open ||
    uriDialog?.open
  ) {
    return;
  }

  if (!menu || menu.hidden) {
    return;
  }

  if (isNewAnnotation && activeAnnotation) {
    removeAbandonedNewAnnotation();
    return;
  }

  finishCurrentAction();
}

function removeAbandonedNewAnnotation() {
  if (!activeAnnotation || !annotator) {
    finishCurrentAction();
    return;
  }

  const annotationId = activeAnnotation.id;

  activeAnnotation = null;
  isNewAnnotation = false;

  closeContextMenu();

  annotator.removeAnnotation(annotationId);

  clearBrowserSelection();
  updateCounters();
}

function clearBrowserSelection() {
  window.getSelection()?.removeAllRanges();
}

function updateCounters() {
  if (!annotator) {
    return;
  }

  const counts = {
    person: 0,
    place: 0,
    date: 0,
    normalization: 0,
    correction: 0
  };

  annotator.getAnnotations().forEach(annotation => {
    const type = getAnnotationType(annotation);

    if (type && Object.hasOwn(counts, type)) {
      counts[type] += 1;
    }
  });

  setCounterValue('person-count', counts.person);
  setCounterValue('place-count', counts.place);
  setCounterValue('date-count', counts.date);
  setCounterValue(
    'normalization-count',
    counts.normalization
  );
  setCounterValue(
    'correction-count',
    counts.correction
  );
}

function setCounterValue(elementId, value) {
  const element = document.querySelector(
    `#${elementId}`
  );

  if (element) {
    element.textContent = String(value);
  }
}

function clamp(value, minimum, maximum) {
  return Math.min(
    Math.max(value, minimum),
    maximum
  );
}

function makeAnnotationsSerializable(annotations) {
  return annotations.map(annotation => ({
    id: annotation.id,

    bodies: (annotation.bodies ?? []).map(body => ({
      ...body
    })),

    target: {
      ...copyTargetMetadata(annotation.target),

      selector: (annotation.target?.selector ?? []).map(
        selector => ({
          quote: selector.quote ?? '',
          start: selector.start,
          end: selector.end
        })
      )
    }
  }));
}

function copyTargetMetadata(target = {}) {
  const {
    selector,
    range,
    ...metadata
  } = target;

  return metadata;
}
