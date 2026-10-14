"""Copy the exact document list from SISJUR's Anexos popup into the reader.

python sync_sisjur_annexes.py --source saved-annex-popup.html --verified-date YYYY-MM-DD
"""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit, parse_qs
from lxml import html

SOURCE_URL = 'https://www.alcaldiabogota.gov.co/sisjur/normas/admin_norma_doc.jsp?i=119582'
START = '<!-- SISJUR_ANNEXES_START -->'
END = '<!-- SISJUR_ANNEXES_END -->'


def parse_annexes(raw):
    document = html.fromstring(raw.decode('cp1252'))
    entries, ids = [], set()
    for row in document.xpath('//tr'):
        cells = row.xpath('./td')
        links = row.xpath('.//a[@href]')
        if len(cells) < 2 or not links:
            continue
        url = urljoin(SOURCE_URL, links[0].get('href'))
        parts = urlsplit(url)
        if parts.hostname != 'www.alcaldiabogota.gov.co' or parts.path != '/sisjur/adminverblobawa':
            raise ValueError(f'Unexpected attachment address: {url}')
        file_id = parse_qs(parts.query)['p_NORMFIL_ID'][0]
        if file_id in ids:
            raise ValueError(f'Duplicate source document: {file_id}')
        ids.add(file_id)
        description, filename = [' '.join(cell.text_content().split()) for cell in cells[:2]]
        if not filename.lower().endswith('.pdf'):
            raise ValueError(f'Unexpected attachment format: {filename}')
        if any(urljoin(SOURCE_URL, link.get('href')) != url for link in links):
            raise ValueError(f'Conflicting source links for {file_id}')
        entries.append({'id': file_id, 'descripcion': description, 'archivo': filename, 'url': url})
    if not entries:
        raise ValueError('No PDF documents found in the official popup')
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--verified-date', required=True)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    entries = parse_annexes(raw)
    root = Path(__file__).resolve().parent
    page = (root/'index.html').read_text(encoding='utf-8')
    if page.count(START) != 1 or page.count(END) != 1:
        raise ValueError('The reader must have exactly one annex list placeholder')
    lines = [f'<p class="annex-dropdown-heading">SISJUR · {len(entries)} documentos PDF</p>']
    for entry in entries:
        # Preserve official descriptions and order. The filename provides version
        # information where SISJUR's description alone omits it.
        date = re.search(r'Dic\.?\s*\(?\s*(202\d)', entry['archivo'], re.I)
        detail = f'PDF · diciembre de {date[1]}' if date else 'PDF'
        lines.append(f'<a href="{escape(entry["url"], quote=True)}" target="_blank" rel="noopener noreferrer" '
                     f'title="{escape(entry["archivo"], quote=True)}"><strong>{escape(entry["descripcion"])} '
                     f'<span aria-hidden="true">↗</span></strong><span>{detail}</span></a>')
    before, rest = page.split(START)
    _, after = rest.split(END)
    (root/'index.html').write_text(before + START + '\n' + '\n'.join('                        '+line for line in lines)
                                  + '\n                        ' + END + after, encoding='utf-8')
    record = {'fuente_url': SOURCE_URL, 'verificado_fecha': args.verified_date,
              'fuente_sha256': hashlib.sha256(raw).hexdigest(), 'total_documentos': len(entries), 'documentos': entries}
    (root/'data/decreto_555_anexos.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Copied {len(entries)} official PDF documents, preserving source order.')


if __name__ == '__main__':
    main()
