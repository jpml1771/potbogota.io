"""Restore the official source's legal hyperlinks and reference-note placement."""
import copy
from html import escape
import re
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from lxml import html

SOURCE_URL = 'https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=119582'
OFFICIAL_HOSTS = {'www.alcaldiabogota.gov.co', 'alcaldiabogota.gov.co',
                  'www.bogotajuridica.gov.co', 'bogotajuridica.gov.co', 'sisjur.bogotajuridica.gov.co'}
REGULATORY = re.compile(r'^(Reglamentado|Modificado|Adicionado|Corregido|Derogado)\b', re.I)
ARTICLE = re.compile(r'^Art[íi]culo\s*(\d+)([A-Z]?)\s*[.:\-)]', re.I)


def normalize_text(text):
    return ' '.join(text.split())


def normalize_url(href, context=''):
    href = href.strip()
    # The source incorrectly uses a self-fragment for a reference explicitly
    # naming DUS 670/2025. Its own introductory links identify SISJUR i=191905.
    if href == '#1365' and re.search(r'670\s+de\s+2025', context, re.I):
        return 'https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=191905#1365'
    resolved = urljoin(SOURCE_URL, href)
    parts = urlsplit(resolved)
    parts = parts._replace(fragment=re.sub(r'\s+', '', unquote(parts.fragment)))
    if (re.fullmatch(r'27\.p\.[345]', parts.fragment)
            and re.search(r'Ley\s+388\s+de\s+1997', context, re.I)
            and (href.startswith('#') or re.search(r'(?:^|&)i=119582(?:&|$)', parts.query))):
        # The paragraph names Ley 388/1997, identified elsewhere in the same
        # official source as i=339; the bare fragment incorrectly targets POT.
        return f'https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=339#{parts.fragment}'
    if parts.scheme not in ('http', 'https'):
        raise ValueError(f'Unsupported legal-link scheme: {href}')
    if parts.hostname in OFFICIAL_HOSTS and re.search(r'/(?:normas/)?Norma1\.jsp$', parts.path, re.I):
        return urlunsplit(('https', 'www.alcaldiabogota.gov.co', '/sisjur/normas/Norma1.jsp', parts.query, parts.fragment))
    return urlunsplit(parts)


def inner_html(element):
    return escape(element.text or '') + ''.join(html.tostring(child, encoding='unicode') for child in element)


def normalize_fragment(fragment, corrections):
    for anchor in fragment.xpath('.//a[@href]'):
        before = anchor.get('href')
        context = normalize_text(anchor.getparent().text_content())
        # In some source paragraphs the two halves of the citation live in
        # separate spans, so use the full paragraph to identify its document.
        paragraph = anchor
        while paragraph.getparent() is not None and paragraph.tag != 'p':
            paragraph = paragraph.getparent()
        if paragraph.tag == 'p':
            context = normalize_text(paragraph.text_content())
        after = normalize_url(before, context)
        anchor.set('href', after)
        anchor.set('target', '_blank')
        anchor.set('rel', 'noopener noreferrer')
        if before != after:
            corrections.add((before, after))


def header_notes(paragraph):
    # Adjacent links sometimes split a word ("R" / "eglamentado...") or a
    # citation across multiple spans. Join only consecutive identical targets.
    groups = []
    for anchor in paragraph.xpath('.//a[@href]'):
        text = normalize_text(anchor.text_content())
        href = anchor.get('href')
        if groups and groups[-1]['href_fuente'] == href:
            separator = '' if len(groups[-1]['texto']) == 1 else ' '
            groups[-1]['texto'] += separator + text
        else:
            groups.append({'texto': text, 'href_fuente': href})
    context = normalize_text(paragraph.text_content())
    return [{**group, 'url': normalize_url(group['href_fuente'], context)}
            for group in groups if REGULATORY.match(group['texto'])]


def restore_links(source, complete, tree):
    document = html.fromstring(source)
    nodes = {}
    def register(node):
        nodes[node['id']] = node
        node['notas_html'] = []
        for child in node['children']:
            register(child)
    for node in tree['libros']:
        register(node)

    state = None
    previous_article = None
    expected = 1
    heading_notes = []
    source_notes = {}
    corrections = set()
    for block in document.xpath('//p|//h1|//h2|//h3|//h4|//h5|//h6'):
        text = normalize_text(block.text_content())
        for anchor in block.xpath('.//span[@class="ancla"]'):
            source_id = anchor.get('id')
            canonical = tree['aliases'].get(source_id, source_id)
            if canonical in nodes:
                state = ('heading', canonical)
        match = ARTICLE.match(text)
        if match and not match[2] and int(match[1]) == expected:
            source_notes[expected] = header_notes(block)
            state = ('article', expected)
            previous_article = expected
            expected += 1
        if expected > 1:
            for anchor in block.xpath('.//a[@href]'):
                before = anchor.get('href')
                after = normalize_url(before, text)
                if before != after:
                    corrections.add((before, after))
        if state and state[0] == 'heading' and block.xpath('.//a[@href]') and re.match(r'^(Ver|Reglamentado|Modificado|Adicionado|Corregido|Derogado)\b', text, re.I):
            clone = copy.deepcopy(block)
            clone.tail = None
            for element in clone.iter():
                for attribute in ('style', 'class', 'lang', 'align'):
                    element.attrib.pop(attribute, None)
            normalize_fragment(clone, corrections)
            markup = html.tostring(clone, encoding='unicode')
            nodes[state[1]]['notas_html'].append(markup)
            heading_notes.append((state[1], text, previous_article))
    if expected != 609:
        raise ValueError('Expected all 608 article headers before restoring links')

    moved = []
    link_count = 0
    for article in complete['articulos']:
        fragment = html.fragment_fromstring(article['contenido_html'], create_parent='div')
        for block in list(fragment.xpath('.//p')):
            text = normalize_text(block.text_content())
            matching = next((node_id for node_id, note_text, _ in heading_notes if note_text == text), None)
            if matching:
                # Only move the exact standalone source note, never a clause
                # containing a mention of the same agreement or decree.
                block.drop_tree()
                moved.append({'articulo_anterior': article['numero'], 'encabezado_correcto': matching, 'texto': text})
        normalize_fragment(fragment, corrections)
        link_count += len(fragment.xpath('.//a[@href]'))
        article['contenido_html'] = inner_html(fragment)
        notes = source_notes[article['numero']]
        article['notas_reglamentarias'] = notes
        article['nota_reglamentaria'] = notes[0]['texto'] if notes else None
        article['nota_url'] = notes[0]['url'] if notes else None
        inherited_notes = [normalize_text(html.fragment_fromstring(markup, create_parent='div').text_content())
                           for node_id in article['jerarquia']['ruta']
                           for markup in nodes[node_id]['notas_html']]
        article['texto_plano'] = normalize_text(' '.join([article['titulo'], fragment.text_content(),
                                                        *[note['texto'] for note in notes], *inherited_notes]))
        link_count += len(notes)
    heading_link_count = sum(len(html.fragment_fromstring(note, create_parent='div').xpath('.//a[@href]'))
                             for node in nodes.values() for note in node['notas_html'])
    complete['meta']['enlaces_version'] = 1
    placements = [{'articulo_anterior': previous, 'encabezado_correcto': node_id, 'texto': text}
                  for node_id, text, previous in heading_notes]
    audit = {'fuente_url': SOURCE_URL, 'total_enlaces_renderizados': link_count + heading_link_count,
             'notas_de_encabezado': len(heading_notes), 'notas_reubicadas': placements,
             'urls_normalizadas': [{'href_fuente': before, 'url': after} for before, after in sorted(corrections)],
             'alcance': 'Enlaces y anotaciones del texto articulado; no incluye el preámbulo ni verifica la vigencia legal.'}
    return audit
