import copy
from collections import Counter
import json
from pathlib import Path
import re
import unittest
from lxml import html
from audit_pot_content import sanitize, source_blocks, split_header, table_signature
from extract_pot_decreto_555 import ARTICLE, article_key

ROOT = Path(__file__).resolve().parents[1]


class ContentTests(unittest.TestCase):
    def test_split_title_keeps_initial_letter_and_first_clause(self):
        header = html.fromstring('<p><b>Artículo</b><b>4. P</b><b>rincipios rectores.</b><span> La primera cláusula.</span></p>')
        title, body, _ = split_header(header)
        self.assertEqual(title, 'Principios rectores')
        self.assertEqual(body.text_content().strip(), 'La primera cláusula.')

    def test_notes_before_title_and_nested_title(self):
        header = html.fromstring('<p><b>Artículo</b><span><b>263.</b><a href="?i=150477">Reglamentado por el Decreto 506 de 2023.</a></span><span><b>Reconocimiento.</b> Cláusula <a href="?i=339">388</a>.</span></p>')
        title, body, _ = split_header(header)
        self.assertEqual(title, 'Reconocimiento')
        self.assertEqual(body.text_content().strip(), 'Cláusula 388.')
        self.assertEqual(body.xpath('.//a/@href'), ['?i=339'])

    def test_repeated_source_title_remains_in_body(self):
        header = html.fromstring('<p><b>Artículo 30. Gestión.</b><span> <b>Gestión.</b> Texto.</span></p>')
        title, body, _ = split_header(header)
        self.assertEqual(title, 'Gestión')
        self.assertEqual(body.text_content().strip(), 'Gestión. Texto.')

    def test_merged_cells_nested_tables_and_words_survive_cleanup(self):
        source = html.fromstring('<div><table style="color:red"><tr><td rowspan="2" colspan="3"><p>Uno <b> </b>dos.</p><table><tr><td>X</td></tr></table></td></tr><tr><td>Y</td></tr></table></div>')
        after = sanitize(source)
        self.assertEqual(source.text_content(), after.text_content())
        self.assertEqual(table_signature(source), table_signature(after))
        self.assertFalse(after.xpath('.//@style'))

    @unittest.skipUnless((ROOT/'official-sisjur-555.html').exists(), 'Run with the saved official HTML for the full source audit')
    def test_all_source_words_and_tables_match_generated_articles(self):
        # Independently compare every source word, including titles and notes.
        # Notes may move above the clause, so compare their multiplicities too.
        document = html.fromstring((ROOT/'official-sisjur-555.html').read_bytes().decode('cp1252'))
        complete = json.loads((ROOT/'data/decreto_555_completo.json').read_text(encoding='utf-8'))
        generated = {a['numero']: a for a in complete['articulos']}
        ranges, current, heading = {}, None, False
        for block in source_blocks(document):
            text = ' '.join(block.text_content().split())
            match = ARTICLE.match(text)
            if match:
                current, heading = article_key(match), False
                ranges[current] = [block]
            elif re.match(r'^PUBL[ÍI]QUESE Y C[ÚU]MPLASE', text):
                break
            elif current is not None:
                if block.xpath('.//span[starts-with(@id,"L.")]'):
                    heading = True
                if not heading:
                    ranges[current].append(block)
        self.assertEqual(list(ranges), [a['numero'] for a in complete['articulos']])
        words = lambda text: Counter(re.findall(r'\w+', text, re.UNICODE))
        for key, blocks in ranges.items():
            with self.subTest(article=key):
                source_text = ARTICLE.sub('', ' '.join(b.text_content() for b in blocks), count=1)
                article = generated[key]
                body = html.fragment_fromstring(article['contenido_html'], create_parent='div')
                output_text = ' '.join([article['titulo'], *[b.text_content() for b in body], *[n['texto'] for n in article['notas_reglamentarias']]])
                self.assertEqual(words(source_text), words(output_text))
                source_container = html.Element('div')
                for block in blocks:
                    source_container.append(copy.deepcopy(block))
                self.assertEqual(table_signature(source_container), table_signature(body))


if __name__ == '__main__':
    unittest.main()
