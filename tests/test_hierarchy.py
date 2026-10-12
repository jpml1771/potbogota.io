import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract_pot_decreto_555 import restore_hierarchy


def fixture():
    starts = {1: 1, 2: 2, 102: 3, 392: 4, 478: 5, 485: 6, 565: 7, 572: 8}
    markup = []
    articles = []
    for number in range(1, 609):
        if number in starts:
            book = starts[number]
            markup.append(f'<h2>LIBRO <span class="ancla" id="L.{book}"></span>{book}</h2><h2>BOOK {book}</h2>')
        if number == 2:
            markup.append('<p><span class="ancla" id="L.2.T.1"></span></p><h2>TÍTULO 1</h2><h2>STRATEGY</h2>')
            markup.append('<h2>CAPÍTULO <span class="ancla" id="L.2.T.1.C.U"></span>ÚNICO<span class="ancla" id="L.2.T.1.C.1"></span></h2><h2>CHAPTER</h2>')
        if number == 47:
            markup.append('<h3>SECCIÓN <span class="ancla" id="L.2.T.1.C.U.S.2"></span>2</h3><h3>SECTION</h3>')
            markup.append('<h3>SUBSECCIÓN <span class="ancla" id="L.2.T.1.C.U.S.2.SS.2"></span>2</h3><h3>SUBSECTION</h3>')
        if number == 508:
            markup.append('<p>CAPÍTULO <span class="ancla" id="L.6.C.2.sic"></span>II (sic)</p><p>FINANCING</p>')
        markup.append(f'<p><b>Artículo {number}.</b> TEXT {number}</p>')
        if number == 222:
            markup.append('<p><b>Artículo 222A.</b> LETTERED ARTICLE</p>')
        articles.append({'numero': number, 'id': f'art-{number}', 'titulo': f'Title {number}',
            'jerarquia': {'libro_id': 'wrong'}, 'contenido_html': '<p>Clause</p><table><td colspan="2">Value</td></table>',
            'texto_plano': 'Clause Value', 'nota_url': None, 'nota_reglamentaria': None,
            'citas_articulos': [], 'menciona_anexo_5': False})
    return ''.join(markup), {'meta': {}, 'articulos': articles}


class HierarchyTests(unittest.TestCase):
    def setUp(self):
        source, baseline = fixture()
        self.before = copy.deepcopy(baseline)
        self.complete, self.index, self.tree = restore_hierarchy(source, baseline)

    def test_all_eight_books_and_boundaries(self):
        self.assertEqual(len(self.tree['libros']), 8)
        for number, book in [(1, 'L.1'), (101, 'L.2'), (102, 'L.3'), (477, 'L.4'),
                             (478, 'L.5'), (564, 'L.6'), (565, 'L.7'), (571, 'L.7'),
                             (572, 'L.8'), (608, 'L.8')]:
            self.assertEqual(self.complete['articulos'][number - 1]['jerarquia']['libro_id'], book)

    def test_preserves_every_non_hierarchy_field(self):
        for before, after in zip(self.before['articulos'], self.complete['articulos']):
            self.assertEqual({k: v for k, v in before.items() if k != 'jerarquia'},
                             {k: v for k, v in after.items() if k != 'jerarquia'})

    def test_subsections_are_distinct_and_parent_aliases_do_not_duplicate(self):
        hierarchy = self.complete['articulos'][46]['jerarquia']
        self.assertEqual(hierarchy['seccion_id'], 'L.2.T.1.C.U.S.2')
        self.assertEqual(hierarchy['subseccion_id'], 'L.2.T.1.C.U.S.2.SS.2')
        self.assertEqual(self.tree['aliases']['L.2.T.1.C.1'], 'L.2.T.1.C.U')
        self.assertEqual(len(self.tree['libros'][1]['children'][0]['children']), 1)

    def test_parent_state_resets_and_sic_is_preserved(self):
        hierarchy = self.complete['articulos'][571]['jerarquia']
        self.assertEqual(hierarchy['ruta'], ['L.8'])
        self.assertIsNone(hierarchy['titulo_id'])
        self.assertIn('(sic)', self.complete['articulos'][507]['jerarquia']['capitulo_nombre'])

    def test_lettered_labels_are_reported_not_silently_added(self):
        self.assertEqual(len(self.index), 608)
        self.assertTrue(any('222A' in warning for warning in self.tree['advertencias']))


if __name__ == '__main__':
    unittest.main()
