"""Build the first integrated Anexo 5 reading edition from the archived Word HTML.

Preserve its wording and headings; use the corresponding full-resolution images
from the official PDF. The archived source and official PDF remain untouched.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from lxml import html
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'archive/anexo_no._5_manual_comunes_tramientos_urbanisticos_.html'
OUTPUT = ROOT / 'anexos/anexo_05_actualizacion'
PDF = OUTPUT / 'anexo_05_actualizacion_dic_2022.pdf'
ALLOWED = {'p', 'br', 'b', 'strong', 'i', 'em', 'u', 'sup', 'sub', 'table',
           'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'ul', 'ol', 'li', 'img'}


def text(element):
    return ' '.join(element.text_content().split())


def clean(element, image_sources, heading):
    result = deepcopy(element)
    for comment in result.xpath('.//comment()'):
        comment.drop_tree()
    for node in list(result.iter()):
        if not isinstance(node.tag, str):
            continue
        if node.tag == 'img':
            source = node.get('src')
            node.attrib.clear()
            node.set('src', image_sources[source])
            node.set('alt', heading)
            node.set('loading', 'lazy')
            node.set('decoding', 'async')
        else:
            keep = {key: value for key, value in node.attrib.items()
                    if node.tag in {'td', 'th'} and key in {'colspan', 'rowspan'}}
            node.attrib.clear()
            node.attrib.update(keep)
        if node is not result and node.tag not in ALLOWED:
            node.drop_tag()
    return html.tostring(result, encoding='unicode', method='html')


def main():
    raw = SOURCE.read_bytes()
    document = html.fromstring(raw)
    body = document.xpath('//body')[0]
    image_elements = body.xpath('.//img')
    pdf = PdfReader(PDF)
    pdf_images = [(page_number, image) for page_number, page in enumerate(pdf.pages, 1)
                  for image in page.images]
    if len(image_elements) != len(pdf_images) or len(pdf_images) != 44:
        raise ValueError('Review the correspondence of the HTML and PDF illustrations')
    (OUTPUT / 'images').mkdir(exist_ok=True)
    image_sources = {}
    image_pages = {}
    for number, (element, (page, image)) in enumerate(zip(image_elements, pdf_images), 1):
        filename = f'figura-{number:02}{Path(image.name).suffix.lower()}'
        (OUTPUT / 'images' / filename).write_bytes(image.data)
        url = f'anexos/anexo_05_actualizacion/images/{filename}'
        image_sources[element.get('src')] = url
        image_pages[url] = page

    nodes, tree, stack = [], [], []
    originals = []
    for element in body.xpath('.//h1|.//h2|.//h3|.//h4|.//h5|.//h6|.//p|.//table'):
        if element.xpath('ancestor::table'):
            continue
        value = text(element)
        if re.fullmatch(r'h[1-6]', element.tag):
            level = int(element.tag[1])
            while stack and stack[-1]['level'] >= level:
                stack.pop()
            chapter = re.match(r'^\d+\.\s*(CAPÍTULO\s+\d+)\.\s*(.*)', value, re.I)
            prefix = re.match(r'^(\d+(?:\.\d+)*\.?|[A-Z](?:\.\d+)*\.)\s+(.*)', value)
            label, title = chapter.groups() if chapter else prefix.groups() if prefix else ('', value)
            node = {'id': f'anexo5-sec-{len(nodes)+1:03}', 'level': level,
                    'label': label, 'title': title, 'heading': value,
                    'parent': stack[-1]['id'] if stack else None,
                    'path': [parent['id'] for parent in stack], 'children': [], 'html': ''}
            if stack:
                stack[-1]['children'].append(node['id'])
            else:
                tree.append(node['id'])
            nodes.append(node)
            stack.append(node)
        elif stack and (value or element.xpath('.//img') or element.tag == 'table'):
            originals.append(element)
            stack[-1]['html'] += clean(element, image_sources, stack[-1]['heading'])

    # Text and all merged cell spans must survive the cleanup unchanged.
    combined = html.fromstring('<div>' + ''.join(node['html'] for node in nodes) + '</div>')
    words = lambda value: Counter(re.findall(r'\w+', value, re.UNICODE))
    if words(' '.join(text(el) for el in originals)) != words(text(combined)):
        raise ValueError('Reader cleanup changed the source wording')
    signature = lambda tables: [[[(cell.tag, cell.get('rowspan', '1'), cell.get('colspan', '1'), text(cell))
                                  for cell in row.xpath('./td|./th')]
                                 for row in table.xpath('./tr|./tbody/tr|./thead/tr|./tfoot/tr')]
                                for table in tables]
    if signature(body.xpath('.//table')) != signature(combined.xpath('.//table')):
        raise ValueError('Reader cleanup changed the source tables')
    record = {'title': 'Manual de Normas Comunes a los Tratamientos Urbanísticos',
              'edition': 'Actualización 2022', 'source_html_sha256': hashlib.sha256(raw).hexdigest(),
              'source_pdf_sha256': hashlib.sha256(PDF.read_bytes()).hexdigest(),
              'pdf_url': 'anexos/anexo_05_actualizacion/anexo_05_actualizacion_dic_2022.pdf',
              'editorial_headings_preserved': True, 'total_tables': len(body.xpath('.//table')),
              'total_images': len(image_elements), 'image_pages': image_pages,
              'roots': tree, 'nodes': nodes}
    (OUTPUT / 'reader.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Built {len(nodes)} headings, {len(tree)} chapters, {record["total_tables"]} tables, and {len(image_elements)} full-resolution images.')


if __name__ == '__main__':
    main()
