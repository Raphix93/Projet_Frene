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
  const deleteButton = document.querySelector('#delete-annotation');

  if (!transcription || !contextMenu || !deleteButton) {
    console.error('Éléments requis absents.', {
      transcription: Boolean(transcription),
      contextMenu: Boolean(contextMenu),
      deleteButton: Boolean(deleteButton)
    });
    return null;
  }

  if (!transcription.textContent.trim()) {
    console.error('Le body TEI rendu est vide.');
    return null;
  }

  try {
    annotator = createTextAnnotator(transcription, {
      style: getAnnotationStyle
    });
  } catch (error) {
    console.error('Erreur Recogito :', error);
    throw new Error(`Recogito : ${error.message}`);
  }

  if (!annotator) {
    console.error('createTextAnnotator n’a retourné aucune instance.');
    return null;
  }

  transcription.addEventListener('pointerdown', event => {
    lastPointerPosition = { x: event.clientX, y: event.clientY };
  });

  annotator.on('createAnnotation', annotation => {
    activeAnnotation = annotation;
    isNewAnnotation = true;

    const rectangle = getSelectionRectangle();

    if (!rectangle) {
      removeAbandonedNewAnnotation();
      return;
    }

    openContextMenu(rectangle);
  });

  annotator.on('selectionChanged', annotations => {
    if (!Array.isArray(annotations) || annotations.length === 0) {
      if (!isNewAnnotation) {
        activeAnnotation = null;
        closeContextMenu();
      }
      return;
    }

    const selected = annotations[0];

    if (isNewAnnotation && activeAnnotation?.id === selected.id) {
      return;
    }

    activeAnnotation = selected;
    isNewAnnotation = false;
    openContextMenu(getPointerRectangle());
  });

  annotator.on('updateAnnotation', updateCounters);
  annotator.on('deleteAnnotation', updateCounters);

  contextMenu.addEventListener('click', handleContextMenuClick);
  deleteButton.addEventListener('click', deleteActiveAnnotation);
  document.addEventListener('pointerdown', handleDocumentPointerDown);
  document.addEventListener('keydown', handleKeyboardNavigation);
  window.addEventListener('resize', closeContextMenu);
  window.addEventListener('scroll', closeContextMenu, { passive: true });

  setupCorrectionDialog();
  updateCounters();

  return {
    getAnnotations() {
      return makeAnnotationsSerializable(annotator.getAnnotations());
    },

    setAnnotations(annotations) {
      annotator.setAnnotations(JSON.parse(JSON.stringify(annotations)), true);
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
  return annotation?.bodies?.find(body => body.purpose === 'tagging')?.value ?? null;
}

function getReplacementText(annotation, type) {
  const purpose = type === 'normalization' ? 'normalizing' : 'correcting';
  return annotation?.bodies?.find(body => body.purpose === purpose)?.value ?? '';
}

function getAnnotationStyle(annotation, state = {}) {
  const type = getAnnotationType(annotation);

  return {
    fill: COLORS[type] ?? '#DDE7F0',
    fillOpacity: state.hovered || state.selected ? 0.95 : 0.75,
    underlineColor: 'transparent',
    underlineThickness: 0
  };
}

function handleContextMenuClick(event) {
  const typeButton = event.target.closest('button[data-type]');
  if (!typeButton || !activeAnnotation) return;

  const type = typeButton.dataset.type;
  if (!Object.hasOwn(LABELS, type)) return;

  if (type === 'normalization' || type === 'correction') {
    activeTextActionType = type;
    closeContextMenu();
    openCorrectionDialog(type);
    return;
  }

  saveAnnotationType(type);
}

function saveAnnotationType(type, replacementText = '') {
  if (!activeAnnotation || !annotator) return;

  const preservedBodies = (activeAnnotation.bodies ?? []).filter(body =>
    body.purpose !== 'tagging' &&
    body.purpose !== 'normalizing' &&
    body.purpose !== 'correcting'
  );

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

  annotator.updateAnnotation({ ...activeAnnotation, bodies: newBodies });
  activeTextActionType = null;
  finishCurrentAction();
}

function deleteActiveAnnotation() {
  if (!activeAnnotation || !annotator) return;

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
  const deleteButton = document.querySelector('#delete-annotation');
  const separator = document.querySelector('#context-menu-separator');

  if (!menu || !title || !deleteButton || !separator || !activeAnnotation) return;

  const currentType = getAnnotationType(activeAnnotation);
  const existing = !isNewAnnotation && Boolean(currentType);

  title.textContent = existing
    ? `Annotation : ${LABELS[currentType] ?? 'Type inconnu'}`
    : 'Annoter comme';

  deleteButton.hidden = !existing;
  separator.hidden = !existing;

  menu.querySelectorAll('button[data-type]').forEach(button => {
    const current = button.dataset.type === currentType;
    button.classList.toggle('current-type', current);
    button.setAttribute('aria-checked', String(current));
  });

  positionMenuInsideApplication(menu, anchorRectangle);
}

function closeContextMenu() {
  const menu = document.querySelector('#context-menu');
  if (menu) menu.hidden = true;
}

function positionMenuInsideApplication(menu, anchor) {
  const application = document.querySelector('.app-container');
  if (!application || !anchor) return;

  const appRect = application.getBoundingClientRect();
  const padding = 12;
  const gap = 10;
  const visibleLeft = Math.max(appRect.left, 0);
  const visibleRight = Math.min(appRect.right, window.innerWidth);
  const visibleTop = Math.max(appRect.top, 0);
  const visibleBottom = Math.min(appRect.bottom, window.innerHeight);

  menu.hidden = false;

  const menuRect = menu.getBoundingClientRect();
  let left = anchor.left + anchor.width / 2 - menuRect.width / 2;
  let top = anchor.bottom + gap;

  left = clamp(left, visibleLeft + padding, Math.max(visibleLeft + padding, visibleRight - menuRect.width - padding));

  if (top + menuRect.height > visibleBottom - padding) {
    top = anchor.top - menuRect.height - gap;
  }

  top = clamp(top, visibleTop + padding, Math.max(visibleTop + padding, visibleBottom - menuRect.height - padding));

  menu.style.left = `${Math.round(left)}px`;
  menu.style.top = `${Math.round(top)}px`;
}

function getSelectionRectangle() {
  const selection = window.getSelection();

  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
    return null;
  }

  const rectangle = selection.getRangeAt(0).getBoundingClientRect();

  return rectangle.width === 0 && rectangle.height === 0 ? null : rectangle;
}

function getPointerRectangle() {
  if (lastPointerPosition) {
    return createPointRectangle(lastPointerPosition.x, lastPointerPosition.y);
  }

  const application = document.querySelector('.app-container');
  const rectangle = application?.getBoundingClientRect();

  return rectangle
    ? createPointRectangle(rectangle.left + rectangle.width / 2, Math.max(rectangle.top + 100, 100))
    : createPointRectangle(window.innerWidth / 2, 100);
}

function createPointRectangle(x, y) {
  return { left: x, right: x, top: y, bottom: y, width: 0, height: 0 };
}

function setupCorrectionDialog() {
  const dialog = document.querySelector('#correction-dialog');
  const form = document.querySelector('#correction-form');
  const cancelButton = document.querySelector('#cancel-correction');

  if (!dialog || !form || !cancelButton) {
    console.error('La fenêtre de saisie est introuvable.');
    return;
  }

  form.addEventListener('submit', event => {
    event.preventDefault();

    const input = document.querySelector('#corrected-text');
    if (!input || !activeTextActionType) return;

    const replacementText = input.value.trim();
    if (!replacementText) {
      input.focus();
      return;
    }

    dialog.close();
    saveAnnotationType(activeTextActionType, replacementText);
  });

  cancelButton.addEventListener('click', cancelCorrection);

  dialog.addEventListener('cancel', event => {
    event.preventDefault();
    cancelCorrection();
  });
}

function openCorrectionDialog(type) {
  const dialog = document.querySelector('#correction-dialog');
  const title = document.querySelector('#correction-dialog-title');
  const label = document.querySelector('#replacement-text-label');
  const original = document.querySelector('#original-text');
  const input = document.querySelector('#corrected-text');

  if (!dialog || !title || !label || !original || !input || !activeAnnotation) return;

  const normalization = type === 'normalization';

  title.textContent = normalization ? 'Normaliser le texte' : 'Corriger librement le texte';
  label.textContent = normalization ? 'Forme normalisée' : 'Texte corrigé';
  original.textContent = getSelectedAnnotationText(activeAnnotation);
  input.value = getReplacementText(activeAnnotation, type);

  dialog.showModal();
  requestAnimationFrame(() => {
    input.focus();
    input.select();
  });
}

function cancelCorrection() {
  const dialog = document.querySelector('#correction-dialog');
  if (dialog?.open) dialog.close();

  activeTextActionType = null;

  if (isNewAnnotation && activeAnnotation) {
    removeAbandonedNewAnnotation();
    return;
  }

  finishCurrentAction();
}

function getSelectedAnnotationText(annotation) {
  const selectors = annotation?.target?.selector;

  if (Array.isArray(selectors)) {
    const selector = selectors.find(item =>
      typeof item?.quote === 'string' ||
      typeof item?.exact === 'string' ||
      item?.type === 'TextQuoteSelector'
    );

    return selector?.quote ?? selector?.exact ?? '';
  }

  return selectors?.quote ?? selectors?.exact ?? '';
}

function handleDocumentPointerDown(event) {
  const menu = document.querySelector('#context-menu');
  const dialog = document.querySelector('#correction-dialog');

  if (!menu || menu.hidden || dialog?.open || menu.contains(event.target)) return;

  if (isNewAnnotation && activeAnnotation) {
    removeAbandonedNewAnnotation();
    return;
  }

  activeAnnotation = null;
  isNewAnnotation = false;
  closeContextMenu();
}

function handleKeyboardNavigation(event) {
  if (event.key !== 'Escape') return;

  const dialog = document.querySelector('#correction-dialog');
  const menu = document.querySelector('#context-menu');

  if (dialog?.open || !menu || menu.hidden) return;

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
  if (!annotator) return;

  const counts = {
    person: 0,
    place: 0,
    date: 0,
    normalization: 0,
    correction: 0
  };

  annotator.getAnnotations().forEach(annotation => {
    const type = getAnnotationType(annotation);
    if (type && Object.hasOwn(counts, type)) counts[type] += 1;
  });

  Object.entries(counts).forEach(([type, value]) => {
    const element = document.querySelector(`#${type}-count`);
    if (element) element.textContent = String(value);
  });
}

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function makeAnnotationsSerializable(annotations) {
  return annotations.map(annotation => ({
    id: annotation.id,
    bodies: (annotation.bodies ?? []).map(body => ({ ...body })),
    target: {
      ...copyTargetMetadata(annotation.target),
      selector: (annotation.target?.selector ?? []).map(selector => ({
        quote: selector.quote ?? selector.exact ?? '',
        exact: selector.exact ?? selector.quote ?? '',
        prefix: selector.prefix ?? '',
        suffix: selector.suffix ?? '',
        start: selector.start,
        end: selector.end
      }))
    }
  }));
}

function copyTargetMetadata(target = {}) {
  const { selector, range, ...metadata } = target;
  return metadata;
}
