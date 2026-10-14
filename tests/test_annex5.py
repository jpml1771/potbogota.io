"""Check the integrated reading edition against its unchanged source documents."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unittest

from lxml import html
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'anexos/anexo_05_actualizacion'


class Annex5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_bytes = (ROOT / 'archive/anexo_no._5_manual_comunes_tramientos_urbanisticos_.html').read_bytes()
        cls.source = html.fromstring(cls.source_bytes).xpath('//body')[0]
        cls.data = json.loads((FOLDER / 'reader.json').read_text(encoding='utf-8'))
        cls.nodes = cls.data['nodes']
        cls.rendered = html.fromstring('<div>' + ''.join(node['html'] for node in cls.nodes) + '</div>')

    def test_all_source_headings_and_their_hierarchy_survive(self):
        headings = self.source.xpath('.//h1|.//h2|.//h3|.//h4|.//h5|.//h6')
        self.assertEqual([node['heading'] for node in self.nodes],
                         [' '.join(heading.text_content().split()) for heading in headings])
        self.assertEqual(len(self.nodes), 278)
        self.assertEqual(len(self.data['roots']), 5)
        self.assertEqual(len(set(node['id'] for node in self.nodes)), len(self.nodes))
        stack = []
        by_id = {node['id']: node for node in self.nodes}
        for heading, node in zip(headings, self.nodes):
            while stack and stack[-1]['level'] >= int(heading.tag[1]):
                stack.pop()
            self.assertEqual(node['path'], [parent['id'] for parent in stack])
            self.assertEqual(node['parent'], stack[-1]['id'] if stack else None)
            if node['parent']:
                self.assertIn(node['id'], by_id[node['parent']]['children'])
            else:
                self.assertIn(node['id'], self.data['roots'])
            stack.append(node)

    def test_body_wording_is_preserved_without_word_metadata(self):
        source_blocks = self.source.xpath('.//p|.//table')
        text = ' '.join(element.text_content() for element in source_blocks if not element.xpath('ancestor::table'))
        words = lambda value: Counter(re.findall(r'\w+', value, re.UNICODE))
        self.assertEqual(words(text), words(self.rendered.text_content()))
        self.assertFalse(self.rendered.xpath('.//@style|.//@onclick|.//script|.//style|.//xml'))

    def test_every_table_cell_and_merged_span_is_preserved(self):
        before = self.source.xpath('.//table')
        after = self.rendered.xpath('.//table')
        self.assertEqual(len(before), 33)
        self.assertEqual(len(before), len(after))
        for first, second in zip(before, after):
            rows1 = first.xpath('.//tr')
            rows2 = second.xpath('.//tr')
            self.assertEqual(len(rows1), len(rows2))
            for row1, row2 in zip(rows1, rows2):
                cells1 = row1.xpath('./td|./th')
                cells2 = row2.xpath('./td|./th')
                self.assertEqual(len(cells1), len(cells2))
                for cell1, cell2 in zip(cells1, cells2):
                    self.assertEqual(' '.join(cell1.text_content().split()), ' '.join(cell2.text_content().split()))
                    for attribute in ['rowspan', 'colspan']:
                        self.assertEqual(cell1.get(attribute, '1'), cell2.get(attribute, '1'))

    def test_images_are_exact_official_pdf_assets_with_local_urls(self):
        pdf = PdfReader(FOLDER / 'anexo_05_actualizacion_dic_2022.pdf')
        originals = [(number, image) for number, page in enumerate(pdf.pages, 1) for image in page.images]
        images = self.rendered.xpath('.//img')
        self.assertEqual(len(originals), 44)
        self.assertEqual(len(images), len(originals))
        for image, (page, original) in zip(images, originals):
            path = (ROOT / image.get('src')).resolve()
            self.assertTrue(path.is_relative_to((FOLDER / 'images').resolve()))
            self.assertEqual(path.read_bytes(), original.data)
            self.assertEqual(self.data['image_pages'][image.get('src')], page)
            self.assertTrue(image.get('alt'))

    def test_source_hashes_match_the_preserved_documents(self):
        self.assertEqual(self.data['source_html_sha256'], hashlib.sha256(self.source_bytes).hexdigest())
        self.assertEqual(self.data['source_pdf_sha256'], hashlib.sha256((ROOT / self.data['pdf_url']).read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
