"""Extract article bodies from the official DOM, preserving table structure."""
import copy
import hashlib
import re
from urllib.parse import urljoin
from lxml import html
from extract_pot_decreto_555 import ARTICLE, LEVELS, SOURCE_URL, article_key, clean_text, parse_structure
from restore_legal_links import header_notes, inner_html, normalize_text

LETTERED = {'222A', '289A', '390A', '459A', '471A'}
BLOCKS = {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table'}
ATTRIBUTES = {'href', 'src', 'alt', 'title', 'colspan', 'rowspan', 'scope', 'start', 'value'}


def text_parts(element):
    """Yield text nodes with their actual formatting parent (tails are outside)."""
    for text in element.xpath('.//text()'):
        owner = text.getparent().getparent() if text.is_tail else text.getparent()
        yield text, owner


def split_header(header):
    raw = header.text_content()
    label = ARTICLE.match(raw)
    if not label:
        raise ValueError('Invalid article header')
    offset, title_start, title_end = 0, None, None
    for text, owner in text_parts(header):
        end = offset + len(text)
        part_start = max(offset, label.end())
        part = str(text)[part_start-offset:] if end > label.end() else ''
        ancestors = [owner, *owner.iterancestors()] if owner is not None else []
        bold = any(x.tag in ('b', 'strong') for x in ancestors)
        linked = any(x.tag == 'a' and x.get('href') for x in ancestors)
        if part.strip() and not linked:
            if title_start is None and bold and part.strip(' .\xa0\n\r\t'):
                title_start, title_end = part_start, end
            elif title_start is not None:
                if bold:
                    # SISJUR repeats the title in the body of articles 30/398.
                    # Keep the first heading and retain the repeated wording in the body.
                    if normalize_text(part).strip(' .') == normalize_text(raw[title_start:title_end]).strip(' .'):
                        break
                    title_end = end
                else:
                    break
        offset = end
    if title_start is None:
        raise ValueError(f'No bold source title: {clean_text(header)[:120]}')
    title = normalize_text(raw[title_start:title_end]).strip(' .')
    # Trim the prefix by character offsets, preserving all remaining inline DOM.
    body = copy.deepcopy(header)
    remaining = title_end
    for text, _ in list(text_parts(body)):
        value = str(text)
        keep = value[min(remaining, len(value)):]
        remaining = max(0, remaining - len(value))
        if text.is_tail:
            text.getparent().tail = keep
        else:
            text.getparent().text = keep
    # Header regulatory notes are rendered separately; leave ordinary body links.
    note_targets = {note['href_fuente'] for note in header_notes(header)}
    for link in list(body.xpath('.//a[@href]')):
        if link.get('href') in note_targets:
            link.drop_tree()
    for text, _ in list(text_parts(body)):
        if str(text).strip():
            cleaned = re.sub(r'^[\s.]+', '', str(text))
            if text.is_tail:
                text.getparent().tail = cleaned
            else:
                text.getparent().text = cleaned
            if cleaned.strip():
                break
    return title, body, label


def sanitize(element):
    clone = copy.deepcopy(element)
    clone.tail = None
    for node in list(clone.iter()):
        if not isinstance(node.tag, str):
            if node.getparent() is not None:
                node.getparent().remove(node)
            continue
        if node.tag in ('script', 'style', 'object'):
            node.drop_tree()
            continue
        for key in list(node.attrib):
            if key not in ATTRIBUTES and not (node.tag == 'img' and key in ('width', 'height')):
                del node.attrib[key]
        if node.tag == 'img' and node.get('src'):
            node.set('src', urljoin(SOURCE_URL, node.get('src')))
    # Empty Word blocks carry no legal text and caused the previous spacing bug.
    for node in reversed(list(clone.iter())):
        if node.tag in ('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'b', 'strong', 'i') and not clean_text(node) and not node.xpath('.//img|.//table'):
            if node.getparent() is not None:
                node.drop_tag()
    return clone


def source_blocks(document):
    """Walk Word sections, retaining whole tables rather than duplicating cells."""
    def walk(node):
        for child in node:
            if child.tag in BLOCKS:
                yield child
            else:
                yield from walk(child)
    for section in document.xpath('//div[starts-with(@class,"WordSection") and not(ancestor::div[starts-with(@class,"WordSection")])]'):
        yield from walk(section)


def table_signature(element):
    return [[[(cell.tag, cell.get('rowspan', '1'), cell.get('colspan', '1'), clean_text(cell))
              for cell in row if cell.tag in ('td', 'th')]
             for row in table.xpath('./tr|./thead/tr|./tbody/tr|./tfoot/tr')]
            for table in element.xpath('.//table')]


def extract_content(source, baseline):
    roots, nodes, paths, aliases, warnings = parse_structure(source, include_lettered=True)
    document = html.fromstring(source)
    old = {a['numero']: a for a in baseline['articulos']}
    articles, audit_rows = [], []
    current, fragments, raw_fragments, in_heading = None, [], [], False

    def finish():
        if current is None:
            return
        article, title = current
        container = html.Element('div')
        expected = html.Element('div')
        for block in raw_fragments:
            expected.append(copy.deepcopy(block))
        for block in fragments:
            cleaned = sanitize(block)
            if clean_text(cleaned) or cleaned.xpath('.//img|.//table') or cleaned.tag == 'table':
                container.append(cleaned)
        body_text = normalize_text(' '.join(block.text_content() for block in container))
        expected_text = normalize_text(' '.join(block.text_content() for block in expected))
        if body_text != expected_text:
            raise ValueError(f'Body text changed while cleaning article {article["numero"]}: {expected_text[:600]!r} / {body_text[:600]!r}')
        if table_signature(container) != table_signature(expected):
            raise ValueError(f'Table structure changed in article {article["numero"]}')
        article['contenido_html'] = inner_html(container)
        article['texto_plano'] = normalize_text(title + ' ' + body_text)
        article['citas_articulos'] = list(dict.fromkeys(
            f'{int(m[1])}{(m[2] or "").replace("-", "").replace(" ", "").upper()}' if m[2] else int(m[1])
            for m in re.finditer(r'art[íi]culos?\s+(\d+)([A-Z]\b|\s*-\s*[A-Z]\b)?', article['texto_plano'], re.I)))
        article['menciona_anexo_5'] = bool(re.search(r'anexo\s*(?:no\.?\s*)?5\b|manual de normas comunes', article['texto_plano'], re.I))
        before = old.get(article['numero'])
        old_fragment = html.fragment_fromstring(before['contenido_html'], create_parent='div') if before else html.Element('div')
        audit_rows.append({'numero': article['numero'], 'etiqueta': article['etiqueta'],
            'titulo_anterior': before['titulo'] if before else None, 'titulo': title,
            'titulo_corregido': bool(before and normalize_text(before['titulo']).strip(' .') != title),
            'tablas': len(container.xpath('.//table')), 'celdas_combinadas': len(container.xpath('.//td[@rowspan or @colspan]|.//th[@rowspan or @colspan]')),
            'estructura_tablas_corregida': bool(before and table_signature(old_fragment) != table_signature(container)),
            'texto_cuerpo_coincide': True, 'tablas_coinciden': True,
            'cuerpo_sha256': hashlib.sha256(normalize_text(container.text_content()).encode()).hexdigest()})
        articles.append(article)

    for block in source_blocks(document):
        text = clean_text(block)
        match = ARTICLE.match(text)
        if match:
            finish()
            key = article_key(match)
            title, body, raw_label = split_header(block)
            source_label = re.sub(r'\s+', '', raw_label[1] + (raw_label[2] or '')).upper()
            hierarchy = {f'{level}_{suffix}': None for level in LEVELS for suffix in ('id', 'nombre')}
            for node_id in paths[key]:
                node = nodes[node_id]
                hierarchy[f'{node["tipo"]}_id'] = node_id
                hierarchy[f'{node["tipo"]}_nombre'] = node['nombre']
            hierarchy['ruta'] = paths[key]
            anchors = block.xpath('.//span[contains(concat(" ",normalize-space(@class)," ")," ancla ")]/@id')
            current = ({'numero': key, 'etiqueta': source_label, 'id': f'art-{key}', 'titulo': title,
                'jerarquia': hierarchy, 'fuente_url': SOURCE_URL + '#' + (anchors[0] if anchors else str(key))}, title)
            fragments, raw_fragments, in_heading = [body], [body], False
        elif current:
            if re.match(r'^PUBL[ÍI]QUESE Y C[ÚU]MPLASE', text):
                finish()
                current = None
                break
            if block.xpath('.//span[starts-with(@id,"L.")]'):
                in_heading = True
            if not in_heading:
                fragments.append(block)
                raw_fragments.append(block)
    else:
        finish()
    keys = [a['numero'] for a in articles]
    if [key for key in keys if isinstance(key, int)] != list(range(1,609)) or {key for key in keys if isinstance(key,str)} != LETTERED or len(keys) != 613:
        raise ValueError(f'Unexpected source article sequence ({len(keys)} articles)')
    if set(keys) != set(paths):
        raise ValueError('Article bodies and hierarchy disagree')
    complete = {'meta': {**baseline['meta'], 'total_articulos': len(articles), 'total_libros': len(roots),
                        'fuente_url': SOURCE_URL, 'jerarquia_version': 3, 'contenido_version': 1}, 'articulos': articles}
    index = [{key: a[key] for key in ('numero','etiqueta','id','titulo','menciona_anexo_5')} |
             {'libro': a['jerarquia']['libro_nombre'], 'libro_id': a['jerarquia']['libro_id'], 'ruta': a['jerarquia']['ruta'], 'citas': a['citas_articulos']}
             for a in articles]
    tree = {'version': 3, 'libros': roots, 'aliases': aliases, 'advertencias': warnings}
    audit = {'fuente_url': SOURCE_URL, 'total_articulos': len(articles), 'articulos_con_letra': [a['etiqueta'] for a in articles if isinstance(a['numero'], str)],
        'titulos_corregidos': sum(row['titulo_corregido'] for row in audit_rows),
        'articulos_con_tablas_corregidas': sum(row['estructura_tablas_corregida'] for row in audit_rows),
        'total_tablas': sum(row['tablas'] for row in audit_rows),
        'total_celdas_combinadas': sum(row['celdas_combinadas'] for row in audit_rows),
        'articulos': audit_rows, 'alcance': 'Fidelidad al HTML de SISJUR; no determina la vigencia legal.'}
    return complete, index, tree, audit
