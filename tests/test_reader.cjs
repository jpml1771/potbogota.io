const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const page = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const articles = JSON.parse(fs.readFileSync(path.join(root, 'data/decreto_555_completo.json'), 'utf8')).articulos;
const index = JSON.parse(fs.readFileSync(path.join(root, 'data/decreto_555_indice.json'), 'utf8'));
const tree = JSON.parse(fs.readFileSync(path.join(root, 'data/decreto_555_arbol.json'), 'utf8')).libros;
const ids = new Map();
class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {};
    this.events = {}; this.className = ''; this.attributes = {}; this.style = {};
    this.value = ''; this.textContent = ''; this.open = false;
    this.classList = {
      contains: name => this.className.split(/\s+/).includes(name),
      add: (...names) => { this.className = [...new Set([...this.className.split(/\s+/), ...names])].join(' '); },
      remove: (...names) => { this.className = this.className.split(/\s+/).filter(n => !names.includes(n)).join(' '); },
      toggle: (name, on) => { if (on) this.classList.add(name); else this.classList.remove(name); }
    };
    if (tag === 'template') this.content = { querySelectorAll: () => [] };
  }
  set id(value) { this._id = value; ids.set(value, this); }
  get id() { return this._id; }
  set innerHTML(value) {
    const remove = el => { if (el.id) ids.delete(el.id); el.children.forEach(remove); };
    this.children.forEach(remove); this.children = []; this._html = value;
  }
  get innerHTML() { return this._html || ''; }
  get outerHTML() {
    const attributes = ['href', 'target', 'rel'].filter(name => this[name]).map(name => ` ${name}="${this[name]}"`).join('');
    return `<${this.tagName.toLowerCase()}${attributes}>${this._html || this.textContent || this.children.map(child => child.outerHTML).join('')}</${this.tagName.toLowerCase()}>`;
  }
  append(...nodes) { nodes.forEach(node => this.appendChild(node)); }
  appendChild(node) {
    if (node.tagName === 'FRAGMENT') return node.children.forEach(child => this.appendChild(child));
    node.parentElement = this; this.children.push(node);
  }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(name, callback) { this.events[name] = callback; }
  scrollIntoView(options) { this.scrolled = true; this.scrollOptions = options; }
  scrollBy() {}
  scrollTo(options) { this.scrollTop = options.top; }
  contains(other) { return this === other || this.children.some(child => child.contains(other)); }
  querySelectorAll(selector) {
    const descendants = [];
    const visit = node => { node.children.forEach(child => { descendants.push(child); visit(child); }); };
    visit(this);
    return descendants.filter(node => node.tagName === selector.toUpperCase());
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  getBoundingClientRect() { return { top: this.top || 0, bottom: this.bottom || 100 }; }
}
for (const match of page.matchAll(/\bid="([^"]+)"/g)) new Element().id = match[1];
const pills = [...page.matchAll(/<button data-libro="([^"]+)"/g)].map(match => {
  const pill = new Element('button'); pill.dataset.libro = match[1]; return pill;
});
const document = {
  getElementById: id => ids.get(id) || null,
  createElement: tag => new Element(tag),
  createTreeWalker: () => ({ nextNode: () => null }),
  createDocumentFragment: () => new Element('fragment'),
  addEventListener() {},
  querySelectorAll(selector) {
    if (selector === '.libro-filter-pill') return pills;
    if (selector === '#articles-nav-list details') return ids.get('articles-nav-list').querySelectorAll('details');
    if (selector === '.pot-nav-heading.is-current') return [...ids.values()].filter(el => el.classList.contains('pot-nav-heading') && el.classList.contains('is-current'));
    if (selector.startsWith('.art-ref-chip')) return [];
    if (selector === '.art-nav-item.active') return [...ids.values()].filter(el => el.classList.contains('art-nav-item') && el.classList.contains('active'));
    if (selector === '.pot-article-card') return [...ids.values()].filter(el => el.classList.contains('pot-article-card'));
    if (selector === '.pot-structure-heading') return [...ids.values()].filter(el => el.classList.contains('pot-structure-heading'));
    return [];
  },
  querySelector: () => pills[0]
};
const context = vm.createContext({ document, articles, index, tree, console, NodeFilter: { SHOW_TEXT: 4 },
  window: { innerWidth: 1200, location: { hash: '', pathname: '/potbogota.io/', search: '' }, addEventListener() {} },
  history: {
    pushState(a, b, hash) { context.window.location.hash = hash; },
    replaceState(a, b, target) { context.window.location.hash = target.startsWith('#') ? target : ''; }
  },
  navigator: { clipboard: { writeText(value) { context.copied = value; return { then() {} }; } } }, setTimeout() {}, clearTimeout() {}, requestAnimationFrame(callback) { callback(); } });
const script = page.slice(page.lastIndexOf('<script>') + 8, page.lastIndexOf('</script>'));
new vm.Script(script).runInContext(context);
vm.runInContext(`potIndex=index;potTree=tree;fullDatabase=articles;
  const register=node=>{potStructureMap[node.id]=node;node.children.forEach(register)};
  potTree.forEach(register);articles.forEach(a=>{potArticlesMap[a.numero]=a;potArticlesMap[a.id]=a});
  setupEventListeners();renderSidebar(potIndex);renderArticles();`, context);
const cards = () => ids.get('articles-feed').children.filter(el => el.classList.contains('pot-article-card'));
assert.equal(cards().length, 613);
assert.equal(pills.length, 9);
const restoredNotes = vm.runInContext('renderLegalNotes(potArticlesMap[263])', context);
assert(restoredNotes.includes('Decreto Único Sectorial 670 de 2025'));
assert(restoredNotes.includes('i=191905#1365'));
assert(restoredNotes.includes('target="_blank"'));
const openGroups = () => document.querySelectorAll('#articles-nav-list details').filter(group => group.open).map(group => group.id);
assert.deepEqual(openGroups(), []);
for (const pill of pills) {
  pill.events.click();
  const expected = articles.filter(a => pill.dataset.libro === 'all' || a.jerarquia.libro_id === pill.dataset.libro);
  assert.deepEqual(cards().map(el => el.id), expected.map(a => a.id));
  assert.equal([...ids.keys()].filter(id => id.startsWith('nav-art-')).length, expected.length);
  assert.deepEqual(openGroups(), pill.dataset.libro === 'all' ? [] : ['nav-group-' + pill.dataset.libro]);
  assert.equal(ids.get('articles-nav-list').scrollTop, 0);
  assert.equal(ids.get('content-pane').scrollTop, 0);
}
// Following an article must never force closed branches open.
vm.runInContext('navigateToArticle(47)', context);
assert.equal(cards().length, 613);
assert.equal(ids.get('art-47').scrolled, true);
assert.equal(ids.get('art-47').scrollOptions.behavior, 'instant');
assert.deepEqual(openGroups(), []);
assert(ids.get('breadcrumb-libro').textContent.includes('SUBSECCIÓN 2'));
const chapter = ids.get('nav-group-L.3.C.5');
chapter.children[0].events.click({ preventDefault() {} });
assert.equal(ids.get('L.3.C.5').scrolled, true);
assert.equal(context.window.location.hash, '#L.3.C.5');
assert.deepEqual(openGroups(), ['nav-group-L.3', 'nav-group-L.3.C.5']);
const firstSubchapter = ids.get('nav-group-L.3.C.5.SC.1');
const secondSubchapter = ids.get('nav-group-L.3.C.5.SC.2');
secondSubchapter.children[0].events.click({ preventDefault() {} });
assert(secondSubchapter.open);
firstSubchapter.children[0].events.click({ preventDefault() {} });
assert(firstSubchapter.open);
assert(!secondSubchapter.open);
assert.deepEqual(openGroups(), ['nav-group-L.3', 'nav-group-L.3.C.5', 'nav-group-L.3.C.5.SC.1']);
firstSubchapter.children[0].events.click({ preventDefault() {} });
assert(!firstSubchapter.open);
// When positioned on a new title, track its first article, not the previous one.
document.querySelectorAll('.pot-article-card').forEach(card => card.top = Number(card.dataset.numero) < 6 ? -1000 : 1000);
let passedTitle = false;
document.querySelectorAll('.pot-structure-heading').forEach(heading => {
  heading.top = passedTitle ? 1000 : -1000;
  if (heading.id === 'L.2.T.2') { heading.top = 110; passedTitle = true; }
});
vm.runInContext('syncNavigationToScroll()', context);
assert.equal(ids.get('breadcrumb-art').textContent, 'Artículo 6');
assert.deepEqual(openGroups(), ['nav-group-L.3', 'nav-group-L.3.C.5']);
// Search filters article headings, ignoring accents and capitalization.
vm.runInContext("searchQuery='construccion';renderSidebar(potIndex);renderArticles()", context);
const withoutAccents = cards().map(el => el.id);
assert(withoutAccents.length > 0);
vm.runInContext("searchQuery='CONSTRUCCIÓN';renderSidebar(potIndex);renderArticles()", context);
assert.deepEqual(cards().map(el => el.id), withoutAccents);
assert.equal([...ids.keys()].filter(id => id.startsWith('nav-art-')).length, cards().length);
vm.runInContext("searchQuery='area minima';renderSidebar(potIndex);renderArticles()", context);
assert(cards().some(el => el.id === 'art-384'));
for (const query of ['384', 'articulo 384', 'Artículo 384']) {
  context.numberQuery = query;
  vm.runInContext('searchQuery=numberQuery;renderSidebar(potIndex);renderArticles()', context);
  assert.deepEqual(cards().map(el => el.id), ['art-384']);
}
// A phrase that only appears in the body must not include that article.
context.bodyQuery = articles[255].texto_plano.slice(400, 450);
vm.runInContext('searchQuery=bodyQuery;renderSidebar(potIndex);renderArticles()', context);
assert.equal(cards().length, 0);
assert.equal([...ids.keys()].filter(id => id.startsWith('nav-art-')).length, cards().length);
context.window.location.hash = '#art-608';
vm.runInContext('handleInitialRoute()', context);
assert.equal(ids.get('art-608').scrolled, true);
assert.equal(ids.get('nav-group-L.8').open, false);
assert.equal(ids.get('breadcrumb-art').textContent, 'Artículo 608');
assert.equal(ids.get('art-608').scrollOptions.behavior, 'instant');
assert(!page.includes("behavior: 'smooth'"));
// Lettered articles keep their source label and sit between numeric neighbors.
// SISJUR places 222A between 221 and 222; preserve that source order.
for (const [before, lettered, after] of [[221,'222A',222],[289,'289A',290],[390,'390A',391],[459,'459A',460],[471,'471A',472]]) {
  vm.runInContext(`navigateToArticle(${before})`, context);
  ids.get('next-art-btn').events.click();
  assert.equal(context.window.location.hash, `#art-${lettered}`);
  assert.equal(ids.get('breadcrumb-art').textContent, `Artículo ${lettered === '289A' ? '289-A' : lettered}`);
  ids.get('next-art-btn').events.click();
  assert.equal(context.window.location.hash, `#art-${after}`);
  ids.get('prev-art-btn').events.click();
  assert.equal(context.window.location.hash, `#art-${lettered}`);
}
vm.runInContext("searchQuery='289-A';renderSidebar(potIndex);renderArticles()", context);
assert.deepEqual(cards().map(el => el.id), ['art-289A']);
assert.equal([...ids.keys()].filter(id => id.startsWith('nav-art-')).length, cards().length);
for (const key of ['222A','289-A','390A','459A','471A']) {
  context.window.location.hash = `#art-${key}`;
  vm.runInContext('handleInitialRoute()', context);
  assert.equal(ids.get('art-' + key.replace('-','')).scrolled, true);
  assert.equal(context.window.location.hash, `#art-${key}`); // routing must not push another history entry
  context.previewKey = key;
  vm.runInContext('showQuickPreview(previewKey)', context);
  assert.equal(ids.get('preview-badge').textContent, `ARTÍCULO ${key}`);
}
context.window.location.origin = 'https://jpml1771.github.io';
vm.runInContext("window.copyArticleLink('289-A')", context);
assert.equal(context.copied, 'https://jpml1771.github.io/potbogota.io/#art-289A');
vm.runInContext("window.copyArticleCitation('289A')", context);
assert(context.copied.includes('Artículo 289-A:'));
assert(ids.get('art-289A').innerHTML.includes("copyArticleLink('289A')"));
vm.runInContext('navigateToArticle(608)', context);
assert.equal(ids.get('nav-counter').textContent, '613 / 613');
console.log('PASS: eight book filters, sidebar behavior, search consistency, article/heading routes, five lettered articles, previous/next sequence, previews, copied links and citations.');
