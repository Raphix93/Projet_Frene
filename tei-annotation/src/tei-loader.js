import {
  setDocumentState
} from './document-state.js';

const TEI_NAMESPACE =
  'http://www.tei-c.org/ns/1.0';

export async function loadConfiguredTei(
  configUrl = './config.json'
) {
  const config = await fetchJson(configUrl);

  validateConfig(config);

  const teiUrl = new URL(
    config.document.url,
    window.location.href
  );

  const response = await fetch(teiUrl, {
    cache: 'no-store'
  });

  if (!response.ok) {
    throw new Error(
      `Impossible de charger la TEI (${response.status}). ` +
      `URL : ${teiUrl}`
    );
  }

  const xml = await response.text();
  const sha256 = await computeSha256(xml);
  const xmlDocument = parseXml(xml);
  const body = findTeiBody(xmlDocument);

  if (!body) {
    throw new Error(
      'La TEI ne contient aucun élément <text><body>.'
    );
  }

  const fragment = renderTeiBody(body);
  const bodyText = normalizeText(body.textContent ?? '');

  setDocumentState({
    config,
    xml,
    sha256,
    bodyText
  });

  return {
    config,
    xml,
    sha256,
    bodyText,
    fragment,
    teiUrl: teiUrl.href
  };
}

async function fetchJson(url) {
  const response = await fetch(url, {
    cache: 'no-store'
  });

  if (!response.ok) {
    throw new Error(
      `Impossible de charger ${url} (${response.status}).`
    );
  }

  return response.json();
}

function validateConfig(config) {
  const documentConfig = config?.document;

  if (
    !documentConfig?.id ||
    !documentConfig?.title ||
    !documentConfig?.url
  ) {
    throw new Error(
      'config.json doit définir document.id, ' +
      'document.title et document.url.'
    );
  }

  if (
    documentConfig.scope &&
    documentConfig.scope !== 'text/body'
  ) {
    throw new Error(
      'La portée prise en charge est uniquement "text/body".'
    );
  }
}

function parseXml(xml) {
  const parser = new DOMParser();
  const document = parser.parseFromString(
    xml,
    'application/xml'
  );

  const parserError = document.querySelector(
    'parsererror'
  );

  if (parserError) {
    throw new Error(
      `La TEI est invalide : ${parserError.textContent}`
    );
  }

  return document;
}

function findTeiBody(document) {
  return (
    document.getElementsByTagNameNS(
      TEI_NAMESPACE,
      'body'
    )[0] ??
    document.querySelector('text > body')
  );
}

/*
 * Conversion volontairement légère :
 * - le texte et la structure du body sont conservés ;
 * - les éléments deviennent des éléments HTML personnalisés `tei-*` ;
 * - le sourceDoc n'est jamais parcouru, puisqu'on part uniquement du body.
 */
function renderTeiBody(body) {
  const fragment =
    window.document.createDocumentFragment();

  for (const child of body.childNodes) {
    fragment.append(convertNode(child));
  }

  return fragment;
}

function convertNode(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    return window.document.createTextNode(
      node.nodeValue ?? ''
    );
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return window.document.createTextNode('');
  }

  const localName =
    node.localName?.toLowerCase() ?? 'node';

  const element =
    window.document.createElement(`tei-${localName}`);

  for (const attribute of node.attributes) {
    const name =
      attribute.name === 'xml:id'
        ? 'data-xml-id'
        : `data-tei-${attribute.localName}`;

    element.setAttribute(name, attribute.value);
  }

  for (const child of node.childNodes) {
    element.append(convertNode(child));
  }

  return element;
}

async function computeSha256(value) {
  if (!window.crypto?.subtle) {
    throw new Error(
      'Le calcul SHA-256 nécessite un contexte sécurisé ' +
      '(localhost ou HTTPS).'
    );
  }

  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest(
    'SHA-256',
    data
  );

  return [...new Uint8Array(digest)]
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('');
}

function normalizeText(value) {
  return value
    .replace(/\r\n?/g, '\n')
    .replace(/[ \t]+\n/g, '\n')
    .trim();
}
