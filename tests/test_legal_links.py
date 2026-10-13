import copy
import unittest
from lxml import html
from test_hierarchy import fixture
from extract_pot_decreto_555 import restore_hierarchy
from restore_legal_links import restore_links, normalize_url, normalize_text


class LegalLinkTests(unittest.TestCase):
    def setUp(self):
        source, baseline = fixture()
        self.chapter_note = '<p><a href="../normas/Norma1.jsp?i=139558">Ver Acuerdo 893 de 2023</a></p>'
        source = source.replace('<p><b>Artículo 2.</b>', self.chapter_note + '<p><b>Artículo 2.</b>')
        source = source.replace('<p><b>Artículo 3.</b>', '<p><b>Artículo 3.</b><a href="../normas/Norma1.jsp?i=150477#0">Reglamentado por el Decreto 506 de 2023.</a><a href="#1365">Reglamentado por el art. 1365,</a><a href="#1365">Decreto Único Sectorial 670 de 2025.</a>')
        source = source.replace('<p><b>Artículo 4.</b>', '<p><b>Artículo 4.</b><a href="../normas/Norma1.jsp?i=152442">R</a><a href="../normas/Norma1.jsp?i=152442">eglamentado por el Decreto Distrital 646 de 2023.</a>')
        baseline['articulos'][0]['contenido_html'] += self.chapter_note
        baseline['articulos'][4]['contenido_html'] = '<p>Clause <a href="../normas/Norma1.jsp?i=62512#2.2.6.4.2.6">1077</a>.</p><table><td colspan="2">Value</td></table>'
        self.original = copy.deepcopy(baseline)
        self.source = source
        self.complete, _, self.tree = restore_hierarchy(source, baseline)
        self.audit = restore_links(source, self.complete, self.tree)

    def test_relative_and_legacy_links_keep_document_and_fragment(self):
        url = normalize_url('http://www.bogotajuridica.gov.co/sisjurMantenimiento/normas/Norma1.jsp?i=62512#2.2.6.4.2.6')
        self.assertEqual(url, 'https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=62512#2.2.6.4.2.6')
        self.assertTrue(normalize_url('# 27.p.5').endswith('#27.p.5'))
        self.assertEqual(normalize_url('# 27.p.5', 'parágrafo 5 del artículo 27 de la Ley 388 de 1997'),
                         'https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=339#27.p.5')

    def test_multiple_header_notes_and_split_words_are_restored(self):
        notes = self.complete['articulos'][2]['notas_reglamentarias']
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes[1]['url'], 'https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=191905#1365')
        self.assertEqual(self.complete['articulos'][3]['notas_reglamentarias'][0]['texto'], 'Reglamentado por el Decreto Distrital 646 de 2023.')

    def test_reference_note_stays_with_its_heading(self):
        chapter = self.tree['libros'][1]['children'][0]['children'][0]
        self.assertEqual(chapter['id'], 'L.2.T.1.C.U')
        self.assertIn('Ver Acuerdo 893 de 2023', chapter['notas_html'][0])
        self.assertNotIn('Ver Acuerdo 893 de 2023', self.complete['articulos'][0]['contenido_html'])

    def test_clause_text_and_table_attributes_survive(self):
        before = html.fragment_fromstring(self.original['articulos'][4]['contenido_html'], create_parent='div')
        after = html.fragment_fromstring(self.complete['articulos'][4]['contenido_html'], create_parent='div')
        self.assertEqual(normalize_text(before.text_content()), normalize_text(after.text_content()))
        self.assertEqual(after.xpath('.//td')[0].get('colspan'), '2')
        link = after.xpath('.//a')[0]
        self.assertEqual(link.get('target'), '_blank')
        self.assertIn('noopener', link.get('rel'))

    def test_regeneration_is_idempotent(self):
        before = copy.deepcopy(self.complete)
        restore_links(self.source, self.complete, self.tree)
        self.assertEqual(self.complete, before)

    def test_unsupported_link_schemes_fail(self):
        with self.assertRaises(ValueError):
            normalize_url('javascript:alert(1)')


if __name__ == '__main__':
    unittest.main()
