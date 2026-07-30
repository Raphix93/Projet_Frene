import { setDocumentState } from './document-state.js';

const TEI_NS = 'http://www.tei-c.org/ns/1.0';

export async function loadConfiguredTei(configUrl = './config.json') {
  const config = await fetchJson(configUrl);
  validateConfig(config);

  const teiUrl = new URL(config.document.url, window.location.href);
  const response = await fetch(teiUrl, { cache: 'no-store' });

  if (!response.ok) {
    throw new Error(
      `Impossible de charger la TEI (${response.status}) : ${teiUrl.href}`
    );
  }

  const xml = await response.text();
  const xmlDocument = parseXml(xml);
  const body = findBody(xmlDocument);

  if (!body) {
    throw new Error('Aucun élément TEI <text><body> trouvé.');
  }

  const sha256 = await computeSha256(xml);
  const fragment = renderBodyAsHtml(body);
  const bodyText = normalizeText(body.textContent ?? '');

  setDocumentState({ config, xml, sha256, bodyText });

  return { config, xml, sha256, bodyText, fragment };
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Impossible de charger ${url} (${response.status}).`);
  }
  return response.json();
}

function validateConfig(config) {
  if (!config?.document?.id || !config?.document?.title || !config?.document?.url) {
    throw new Error(
      'config.json doit définir document.id, document.title et document.url.'
    );
  }

  if (config.document.scope && config.document.scope !== 'text/body') {
    throw new Error('La portée prise en charge est uniquement "text/body".');
  }
}

function parseXml(xml) {
  const document = new DOMParser().parseFromString(xml, 'application/xml');
  const error = document.querySelector('parsererror');

  if (error) {
    throw new Error(`TEI XML invalide : ${error.textContent.trim()}`);
  }

  return document;
}

function findBody(document) {
  return (
    document.getElementsByTagNameNS(TEI_NS, 'body')[0] ??
    document.querySelector('text > body')
  );
}

/*
 * Le rendu utilise volontairement des éléments HTML standards.
 * Recogito annote ainsi un DOM simple et stable.
 * Le teiHeader et sourceDoc sont absents car seul body est parcouru.
 */
function renderBodyAsHtml(body) {
  const fragment = document.createDocumentFragment();

  for (const child of body.childNodes) {
    const rendered = renderNode(child);
    if (rendered) fragment.append(rendered);
  }

  return fragment;
}

function renderNode(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    return document.createTextNode(node.nodeValue ?? '');
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }

  const name = (node.localName ?? '').toLowerCase();

  if (name === 'lb') {
    return document.createElement('br');
  }

  if (name === 'pb') {
    const separator = document.createElement('div');
    separator.className = 'tei-page-break';
    separator.dataset.teiElement = 'pb';
    copyTeiAttributes(node, separator);

    const page = node.getAttribute('n') || node.getAttribute('corresp') || '';
    separator.textContent = page ? `Page ${page.replace(/^#/, '')}` : 'Changement de page';
    return separator;
  }

  const tagName = htmlTagFor(name);
  const element = document.createElement(tagName);
  element.dataset.teiElement = name;
  copyTeiAttributes(node, element);

  for (const child of node.childNodes) {
    const rendered = renderNode(child);
    if (rendered) element.append(rendered);
  }

  return element;
}

function htmlTagFor(name) {
  const map = {
    div: 'section',
    p: 'p',
    ab: 'p',
    head: 'h2',
    list: 'ul',
    item: 'li',
    quote: 'blockquote',
    q: 'q',
    note: 'aside',
    persname: 'span',
    placename: 'span',
    orgname: 'span',
    date: 'time',
    choice: 'span',
    orig: 'span',
    reg: 'span',
    sic: 'span',
    corr: 'span',
    hi: 'span'
  };

  return map[name] ?? 'span';
}

function copyTeiAttributes(source, target) {
  for (const attribute of source.attributes) {
    const safeName = attribute.name
      .replace(':', '-')
      .replace(/[^a-zA-Z0-9_-]/g, '-');

    target.dataset[`tei${toDatasetKey(safeName)}`] = attribute.value;
  }
}

function toDatasetKey(value) {
  return value
    .split('-')
    .filter(Boolean)
    .map(part => part[0].toUpperCase() + part.slice(1))
    .join('');
}

async function computeSha256(value) {
  if (!window.crypto?.subtle) {
    throw new Error('SHA-256 nécessite localhost ou HTTPS.');
  }

  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest('SHA-256', bytes);

  return [...new Uint8Array(digest)]
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('');
}

function normalizeText(value) {
  return value.replace(/\r\n?/g, '\n').replace(/[ \t]+\n/g, '\n').trim();
}
