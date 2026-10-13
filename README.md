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

The hierarchy stage preserves existing article wording. The subsequent legal-link
stage resolves relative SISJUR URLs, restores all regulatory notes from the source
article headers, and places standalone division notes under their correct heading.
It does not fully re-extract or verify legal wording. The UI suppresses exact known structural heading
blocks that the legacy parser misplaced inside the preceding article, then
renders them at their correct location using the tree.

`restore_legal_links.py` handles link restoration. Its audit output is
`data/decreto_555_enlaces_auditoria.json`. Known SISJUR document routes are resolved
to the official HTTPS endpoint while preserving document IDs and article fragments.
The source's bare `#1365` references explicitly naming DUS 670/2025 are resolved
to that document (`i=191905`), identified by the source's own introductory link.
Legal hyperlinks open in a separate tab. Internal article-preview decoration skips
existing links so a reference to another decree cannot be turned into a POT button.
The malformed self-fragments in Article 599 explicitly naming Ley 388/1997 are
likewise resolved to its source-identified document (`i=339`).

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
