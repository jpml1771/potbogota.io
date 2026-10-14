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

`audit_pot_content.py` re-extracts the article text from the source DOM, including
the first clause in each article header. Titles split across bold spans are joined
without losing letters. Full tables retain their rows, cells, `rowspan`, and
`colspan`. Cleanup removes Word styling and empty blocks; it checks body text and
table signatures before accepting the result. Division headings are kept in the
hierarchy, outside the preceding article's body.

The subsequent legal-link stage resolves relative SISJUR URLs, restores regulatory
notes from article headers, and places division notes under their correct heading.

`restore_legal_links.py` handles link restoration. Its audit output is
`data/decreto_555_enlaces_auditoria.json`. Known SISJUR document routes are resolved
to the official HTTPS endpoint while preserving document IDs and article fragments.
The source's bare `#1365` references explicitly naming DUS 670/2025 are resolved
to that document (`i=191905`), identified by the source's own introductory link.
Legal hyperlinks open in a separate tab. Internal article-preview decoration skips
existing links so a reference to another decree cannot be turned into a POT button.
The malformed self-fragments in Article 599 explicitly naming Ley 388/1997 are
likewise resolved to its source-identified document (`i=339`).

## Content audit

The database contains 613 articles: numeric articles 1–608 and source labels
222A, 289-A, 390A, 459A, and 471A. Lettered keys and URLs use `222A`, `289A`, etc.;
`etiqueta` preserves the displayed label, including the hyphen in 289-A. Both
`#art-289A` and `#art-289-A` open that article. Existing numeric URLs are unchanged.
Search, previews, copying, and previous/next navigation support all five additions.
Source order is preserved: SISJUR places 222A between 221 and 222.

`data/decreto_555_contenido_auditoria.json` records the source hash and per-article
checks. The October 13, 2026 audit preserved 99 tables with 689 merged cells and
restored table structure in 44 articles. It corrected 26 titles compared with the
favicon commit, ignoring whitespace-only and trailing-period differences. Repeated
source titles in articles 30/398 remain in the body rather than duplicating the UI
heading. Regulatory header notes appear once, separately from the clause.

The full source regression check independently compares every article's source
word multiplicities (including titles and notes) and exact table cell structure.
Save the official download as `official-sisjur-555.html` to run it; the file is
ignored by Git. Other tests run without it. The audit concerns faithful extraction
of SISJUR's HTML; it does not determine the legal validity of a provision.

## Search

Search filters article titles within the selected book (or the whole decree under
Todos). Accents and capitalization are ignored: `construccion` matches
`Construcción`. A number such as `384` or `Artículo 384` selects that exact article;
lettered numbers such as `289-A` also work. Body text, tables, and regulatory notes
do not cause an article to appear in title search results.

## Official annex documents

The Anexos dropdown mirrors all 25 PDF entries in the official SISJUR attachment
popup, preserving its descriptions and order. Links point directly to SISJUR and
open in a new tab. Both the original December 2021 Anexo 5 and the attachment
labeled as its December 2022 update are included. The previous local Anexo 5
viewer remains in `BK/anexo5_visor_previo/` for the separate version review.

`data/decreto_555_anexos.json` records filenames, document IDs, attachment URLs,
the verification date, and the source hash. To refresh the dropdown, save the
official popup HTML and run:

```sh
python sync_sisjur_annexes.py --source saved-annex-popup.html --verified-date YYYY-MM-DD
```

## Local preview and tests

```sh
python -m http.server 8000
python -m unittest discover -s tests -p 'test_*.py'
node tests/test_reader.cjs
```

Open http://localhost:8000 for the reader. GitHub Pages publishes `main`.
