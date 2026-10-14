/* Integrated reading edition; its source wording and editorial headings are retained. */
(() => {
    const ROOT = 'anexo5';
    let active = false;
    let data = null;
    let nodes = new Map();
    let loading = null;
    let generation = 0;
    let current = ROOT;
    let renderedQuery = null;

    async function load() {
        if (data) return;
        if (!loading) {
            loading = fetch('anexos/anexo_05_actualizacion/reader.json').then(response => {
                if (!response.ok) throw new Error('No se pudo cargar el Anexo 5');
                return response.json();
            }).then(result => {
                if (!result.nodes?.length || !result.roots?.length) throw new Error('Anexo incompleto');
                data = result;
                nodes = new Map(data.nodes.map(node => [node.id, node]));
            }).catch(error => { loading = null; throw error; });
        }
        await loading;
    }

    function selectedNodes() {
        const query = normalizeSearchText(searchQuery);
        if (!query) return new Set(data.nodes.map(node => node.id));
        const matches = new Set(data.nodes.filter(node => normalizeSearchText(node.heading).includes(query)).map(node => node.id));
        const selected = new Set();
        data.nodes.forEach(node => {
            if (matches.has(node.id) || node.path.some(id => matches.has(id))) {
                selected.add(node.id);
                node.path.forEach(id => selected.add(id));
            }
        });
        return selected;
    }

    function appendNavigation(container) {
        const group = document.createElement('details');
        group.id = 'nav-group-anexo5';
        group.className = 'pot-nav-group annex-nav-root';
        const summary = document.createElement('summary');
        summary.className = 'pot-nav-heading';
        const link = document.createElement('a');
        link.id = 'nav-anexo5';
        link.className = 'annex-nav-link';
        link.href = '#anexo5';
        const label = document.createElement('span');
        label.className = 'nav-heading-label';
        label.textContent = 'ANEXO 5 · ACTUALIZACIÓN';
        const title = document.createElement('span');
        title.className = 'nav-heading-title';
        title.textContent = 'Manual de Normas Comunes a los Tratamientos Urbanísticos';
        link.append(label, title);
        summary.appendChild(link);
        summary.addEventListener('click', event => {
            event.preventDefault();
            if (group.open && active) group.open = false;
            else navigate(ROOT);
        });
        group.appendChild(summary);
        if (data) {
            const selected = active ? selectedNodes() : new Set(data.nodes.map(node => node.id));
            const appendNode = (id, parent) => {
                if (!selected.has(id)) return;
                const node = nodes.get(id);
                const children = node.children.filter(child => selected.has(child));
                const row = document.createElement(children.length ? 'details' : 'div');
                if (children.length) {
                    row.id = `nav-group-${id}`;
                    row.className = 'pot-nav-group';
                }
                const heading = document.createElement(children.length ? 'summary' : 'div');
                heading.className = 'pot-nav-heading';
                const nodeLink = document.createElement('a');
                nodeLink.id = `nav-${id}`;
                nodeLink.href = `#${id}`;
                nodeLink.className = 'annex-nav-link';
                nodeLink.textContent = `${node.label} ${node.title}`.trim();
                heading.appendChild(nodeLink);
                heading.addEventListener('click', event => {
                    event.preventDefault();
                    if (children.length && row.open && active) row.open = false;
                    else navigate(id);
                });
                row.appendChild(heading);
                if (children.length) {
                    const nested = document.createElement('div');
                    nested.className = 'pot-nav-children';
                    children.forEach(child => appendNode(child, nested));
                    row.appendChild(nested);
                }
                parent.appendChild(row);
            };
            const chapters = document.createElement('div');
            chapters.className = 'pot-nav-children';
            data.roots.forEach(id => appendNode(id, chapters));
            group.appendChild(chapters);
            if (active) {
                group.open = true;
                const target = nodes.get(current);
                [...(target?.path || []), ...(target?.children.length ? [current] : [])].forEach(id => {
                    const branch = group.querySelector(`[id="nav-group-${id}"]`);
                    if (branch) branch.open = true;
                });
                document.getElementById('search-results-counter').textContent = `Anexo 5 · ${selected.size} de ${data.nodes.length} apartados`;
            }
        }
        container.appendChild(group);
    }

    function updateContext(id) {
        current = id;
        const node = nodes.get(id);
        const position = data.nodes.findIndex(item => item.id === id);
        const breadcrumb = document.getElementById('breadcrumb-art');
        breadcrumb.textContent = node ? `${node.label} ${node.title}`.trim() : 'Actualización 2022';
        breadcrumb.dataset.articleId = '';
        breadcrumb.title = breadcrumb.textContent;
        const context = document.getElementById('breadcrumb-libro');
        context.textContent = 'Anexo 5';
        context.title = node ? node.path.map(parent => nodes.get(parent).heading).join(' › ') : data.title;
        document.getElementById('nav-counter').textContent = position < 0 ? 'Anexo 5' : `${position + 1} / ${data.nodes.length}`;
        document.getElementById('prev-art-btn').title = 'Apartado anterior';
        document.getElementById('next-art-btn').title = 'Apartado siguiente';
        document.querySelectorAll('.annex-nav-link.is-current').forEach(link => link.classList.remove('is-current'));
        document.querySelectorAll('.art-nav-item.active, .pot-nav-heading.is-current').forEach(link => link.classList.remove('active', 'is-current'));
        let row = document.getElementById(`nav-${id}`) || document.getElementById('nav-anexo5');
        let parent = row.parentElement;
        while (parent && parent.id !== 'articles-nav-list') {
            if (parent.tagName === 'DETAILS' && !parent.open) row = parent.querySelector('summary');
            parent = parent.parentElement;
        }
        row.classList.add('is-current');
        const list = document.getElementById('articles-nav-list');
        const listRect = list.getBoundingClientRect();
        const rowRect = row.getBoundingClientRect();
        if (rowRect.top < listRect.top + 12) list.scrollBy({ top: rowRect.top - listRect.top - 12, behavior: 'instant' });
        else if (rowRect.bottom > listRect.bottom - 12) list.scrollBy({ top: rowRect.bottom - listRect.bottom + 12, behavior: 'instant' });
    }

    function render() {
        if (!data || !active) return;
        const feed = document.getElementById('articles-feed');
        feed.innerHTML = '';
        document.getElementById('document-hero').hidden = true;
        const intro = document.createElement('section');
        intro.id = ROOT;
        intro.className = 'annex-intro document-heading';
        const edition = document.createElement('p');
        edition.className = 'document-eyebrow';
        edition.textContent = 'ANEXO 5 · ACTUALIZACIÓN 2022';
        const title = document.createElement('h2');
        title.className = 'document-title';
        title.textContent = data.title;
        const sources = document.createElement('div');
        sources.className = 'annex-source-links';
        const pdf = document.createElement('a');
        pdf.href = data.pdf_url;
        pdf.target = '_blank';
        pdf.rel = 'noopener noreferrer';
        pdf.textContent = 'Consultar PDF oficial ↗';
        const back = document.createElement('button');
        back.textContent = 'Volver al POT';
        back.addEventListener('click', () => navigateToArticle(1));
        sources.append(pdf, back);
        intro.append(edition, title, sources);
        feed.appendChild(intro);
        const selected = selectedNodes();
        data.nodes.forEach(node => {
            if (!selected.has(node.id)) return;
            const section = document.createElement('section');
            section.id = node.id;
            section.className = `annex-section annex-level-${node.level}`;
            const heading = document.createElement(node.level === 1 ? 'h2' : 'h3');
            heading.textContent = `${node.label} ${node.title}`.trim();
            const body = document.createElement('div');
            body.className = 'article-content';
            body.innerHTML = node.html;
            body.querySelectorAll('table').forEach(table => {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-wrapper';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            });
            section.append(heading, body);
            feed.appendChild(section);
        });
        if (!selected.size) {
            const empty = document.createElement('p');
            empty.textContent = 'No se encontraron apartados con ese título.';
            feed.appendChild(empty);
        }
        if (renderedQuery !== searchQuery) document.getElementById('content-pane').scrollTo({ top: 0, behavior: 'instant' });
        renderedQuery = searchQuery;
        updateContext(selected.has(current) ? current : ROOT);
    }

    async function navigate(id = ROOT, updateHistory = true) {
        const wasActive = active;
        active = true;
        const request = ++generation;
        current = id;
        if (!wasActive) {
            activeFilterLibro = 'all';
            searchQuery = '';
            document.getElementById('global-search').value = '';
            document.getElementById('clear-search-btn').classList.add('hidden');
            document.querySelectorAll('.libro-filter-pill').forEach(pill => {
                pill.classList.remove('active'); pill.setAttribute('aria-pressed', 'false');
            });
            document.getElementById('global-search').placeholder = 'Buscar títulos en el Anexo 5…';
            document.getElementById('document-hero').hidden = true;
        }
        if (!data) document.getElementById('articles-feed').innerHTML = '<p class="p-6">Cargando Anexo 5…</p>';
        try {
            await load();
            if (!active || request !== generation) return;
            current = nodes.has(id) ? id : ROOT;
            // A permanent link must remain reachable after a previous title search.
            if (current !== ROOT && !selectedNodes().has(current)) {
                searchQuery = '';
                document.getElementById('global-search').value = '';
                document.getElementById('clear-search-btn').classList.add('hidden');
            }
            renderSidebar(potIndex);
            render();
            const branch = document.getElementById(`nav-group-${current}`) || document.getElementById('nav-group-anexo5');
            openNavigationBranch(branch);
            document.getElementById(current).scrollIntoView({ behavior: 'instant', block: 'start' });
            updateContext(current);
            if (updateHistory) history.pushState(null, '', `#${current}`);
            if (window.innerWidth < 768) toggleMobileSidebar(false);
        } catch (error) {
            if (!active || request !== generation) return;
            const feed = document.getElementById('articles-feed');
            feed.innerHTML = '<p class="p-6">No se pudo cargar el Anexo 5. Puedes volver al POT o intentarlo de nuevo.</p>';
            const retry = document.createElement('button');
            retry.textContent = 'Reintentar';
            retry.className = 'annex-retry';
            retry.addEventListener('click', () => navigate(id, updateHistory));
            feed.appendChild(retry);
            console.error(error);
        }
    }

    function leave() {
        if (!active) return false;
        active = false;
        generation++;
        renderedQuery = null;
        document.getElementById('document-hero').hidden = false;
        document.getElementById('global-search').placeholder = 'Buscar artículo o palabra clave…';
        document.getElementById('breadcrumb-art').title = '';
        document.getElementById('prev-art-btn').title = 'Artículo anterior';
        document.getElementById('next-art-btn').title = 'Artículo siguiente';
        searchQuery = '';
        document.getElementById('global-search').value = '';
        document.getElementById('clear-search-btn').classList.add('hidden');
        document.querySelectorAll('.libro-filter-pill').forEach(pill => {
            const selected = pill.dataset.libro === activeFilterLibro;
            pill.classList.toggle('active', selected);
            pill.setAttribute('aria-pressed', String(selected));
        });
        return true;
    }

    function adjacent(direction) {
        if (!data) return;
        const selected = selectedNodes();
        const visible = data.nodes.filter(node => selected.has(node.id));
        const index = visible.findIndex(node => node.id === current);
        const next = index < 0 ? (direction > 0 ? visible[0] : null) : visible[index + direction];
        if (next) navigate(next.id);
    }

    function syncScroll() {
        if (!data || !active) return;
        const line = document.getElementById('sticky-breadcrumb-bar').getBoundingClientRect().bottom + 24;
        let target = ROOT;
        for (const section of document.querySelectorAll('.annex-section')) {
            if (section.getBoundingClientRect().top > line) break;
            target = section.id;
        }
        if (target !== current) updateContext(target);
    }

    window.annex5Reader = {
        get active() { return active; }, appendNavigation, render, navigate, leave, adjacent, syncScroll,
        route(id) {
            if (id === ROOT || /^anexo5-sec-\d{3}$/.test(id)) { navigate(id, false); return true; }
            return false;
        }
    };
})();
