# POT Bogotá

Static reader for Decreto Distrital 555 de 2021, using the official SISJUR source:
https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=119582

## Hierarchy and regeneration

The document has eight books. Its possible levels are Libro, Título, Capítulo,
Subcapítulo, Sección, Subsección, and Artículo; branches may skip levels.
`data/decreto_555_arbol.json` contains the nested heading tree and source hash.
Each article's `jerarquia.ruta` lists its ordered heading IDs. Numeric article
IDs and existing `#art-N` links are preserved. Heading IDs also support links.

Install Python dependencies and regenerate from a saved official HTML file:

```sh
python -m pip install -r requirements.txt
python extract_pot_decreto_555.py --source sisjur_pot_555.html
```

Alternatively use `--download` to retrieve the exact official URL. The source
defaults to Windows-1252; use `--encoding` for a differently encoded saved file.
Use `--output-dir` to stage generated files for review before replacing `data`.
The complete database, index, hierarchy tree and eight book snapshots are
generated together. No local Windows paths or Antigravity folders are required.

This hierarchy pass deliberately preserves every non-hierarchy article field
from the existing complete JSON. It is not a full content re-extraction or
verification of legal wording. The UI suppresses exact known structural heading
blocks that the legacy parser misplaced inside the preceding article, then
renders them at their correct location using the tree.

## Known content review items

The inspected SISJUR source includes lettered labels 222A, 390A, 459A and 471A.
The legacy database has only numeric articles 1–608; those source labels require
a separate content audit. The hierarchy parser reports them and preserves the
baseline content rather than silently splitting or renumbering it. Source
annotations and regulatory table extraction also remain separate review items.

## Local preview and tests

```sh
python -m http.server 8000
python -m unittest discover -s tests -p 'test_*.py'
node tests/test_reader.cjs
```

Open http://localhost:8000 for the reader. GitHub Pages publishes `main`.
