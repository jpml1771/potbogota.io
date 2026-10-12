"""Restore the official POT hierarchy while preserving existing article wording.

python extract_pot_decreto_555.py --source sisjur_pot_555.html
python extract_pot_decreto_555.py --download
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen
from lxml import html

SOURCE_URL = "https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=119582"
LEVELS = ("libro", "titulo", "capitulo", "subcapitulo", "seccion", "subseccion")
LABEL_LEVEL = dict(zip(("LIBRO", "TÍTULO", "CAPÍTULO", "SUBCAPÍTULO", "SECCIÓN", "SUBSECCIÓN"), LEVELS))
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6"}
HEADING = re.compile(r"^(LIBRO|TÍTULO|CAPÍTULO|SUBCAPÍTULO|SECCIÓN|SUBSECCIÓN)\s+(ÚNICO|\d+|[IVXLCDM]+)(?:\s*\(sic\))?", re.I)
ARTICLE = re.compile(r"^Art[íi]culo\s*(\d+)([A-Z]?)\s*[.:\-)]", re.I)


def clean_text(element):
    return " ".join(element.text_content().split())


def parse_structure(source):
    """Read real heading blocks, never character windows around HTML anchors."""
    document = html.fromstring(source)
    blocks = document.xpath("//p|//h1|//h2|//h3|//h4|//h5|//h6")
    positions = {block: i for i, block in enumerate(blocks)}
    heading_blocks, aliases, warnings = {}, {}, []
    for anchor in document.xpath('//span[contains(concat(" ", normalize-space(@class), " "), " ancla ")]'):
        source_id = anchor.get("id", "")
        if not re.match(r"^L\.\d+(?:\.|$)", source_id):
            continue
        block = anchor.getparent()
        while block is not None and block.tag not in BLOCK_TAGS:
            block = block.getparent()
        if block is None:
            raise ValueError(f"No heading block for {source_id}")
        i = positions[block]
        while not clean_text(block):
            i += 1
            if i >= len(blocks):
                raise ValueError(f"Empty heading at {source_id}")
            block = blocks[i]
        label_text = re.sub(r"^[a-z]\.\s*", "", clean_text(block), flags=re.I)
        label_text = re.sub(r"^L\s+IBRO", "LIBRO", label_text, flags=re.I)
        match = HEADING.match(label_text)
        if not match:
            raise ValueError(f"Unrecognized heading {source_id}: {label_text!r}")
        label, level = match.group(0), LABEL_LEVEL[match.group(1).upper()]
        if block in heading_blocks:
            canonical = heading_blocks[block]
            aliases[source_id] = canonical["id"]
            canonical["aliases"].append(source_id)
            continue
        title = label_text[match.end():].strip(" .")
        if not title:
            for following in blocks[i + 1:]:
                text = clean_text(following)
                if not text:
                    continue
                if HEADING.match(text) or ARTICLE.match(text) or text.lower().startswith("ver "):
                    raise ValueError(f"Missing heading title at {source_id}")
                title = re.sub(r"^[a-z]\.\s*", "", text, flags=re.I)
                break
        if not title or "<" in title or "style=" in title:
            raise ValueError(f"Invalid title for {source_id}: {title!r}")
        heading_blocks[block] = {"id": source_id, "tipo": level, "etiqueta": label,
            "titulo": title, "nombre": f"{label} — {title}", "aliases": [],
            "children": [], "articulos": [], "position": i}

    article_positions, expected = [], 1
    for i, block in enumerate(blocks):
        match = ARTICLE.match(clean_text(block))
        if not match:
            continue
        if match.group(2):
            warnings.append(f"Source contains article label {match.group(1)}{match.group(2)}; retained in baseline text for separate content review.")
        elif int(match.group(1)) == expected:
            article_positions.append((i, expected))
            expected += 1
    if expected != 609:
        raise ValueError(f"Expected baseline headings 1–608, found 1–{expected - 1}")
    events = [(node["position"], 0, node) for node in heading_blocks.values()]
    events += [(position, 1, number) for position, number in article_positions]
    stack, roots, paths, nodes = {}, [], {}, {}
    for _, kind, value in sorted(events, key=lambda event: (event[0], event[1])):
        if kind == 0:
            node = value
            depth = LEVELS.index(node["tipo"])
            for level in LEVELS[depth:]:
                stack.pop(level, None)
            parent = next((stack[level] for level in reversed(LEVELS[:depth]) if level in stack), None)
            node["parent_id"] = parent["id"] if parent else None
            if parent:
                parent["children"].append(node)
            elif node["tipo"] == "libro":
                roots.append(node)
            else:
                raise ValueError(f"Orphan heading: {node['id']}")
            nodes[node["id"]] = node
            stack[node["tipo"]] = node
        else:
            path = [stack[level]["id"] for level in LEVELS if level in stack]
            if not path or nodes[path[0]]["tipo"] != "libro":
                raise ValueError(f"Article {value} has no book")
            paths[value] = path
            nodes[path[-1]]["articulos"].append(value)
    if [node["id"] for node in roots] != [f"L.{i}" for i in range(1, 9)]:
        raise ValueError("The source must contain all eight official books in order")
    for node in nodes.values():
        node.pop("position")
    return roots, nodes, paths, aliases, warnings


def restore_hierarchy(source, baseline):
    roots, nodes, paths, aliases, warnings = parse_structure(source)
    articles = baseline["articulos"]
    if [a["numero"] for a in articles] != list(range(1, 609)):
        raise ValueError("Baseline must contain exactly articles 1–608 in order")
    for article in articles:
        path = paths[article["numero"]]
        hierarchy = {f"{level}_{suffix}": None for level in LEVELS for suffix in ("id", "nombre")}
        for node_id in path:
            node = nodes[node_id]
            hierarchy[f"{node['tipo']}_id"] = node_id
            hierarchy[f"{node['tipo']}_nombre"] = node["nombre"]
        hierarchy["ruta"] = path
        article["jerarquia"] = hierarchy
    index = [{"numero": a["numero"], "id": a["id"], "titulo": a["titulo"],
              "libro": a["jerarquia"]["libro_nombre"], "libro_id": a["jerarquia"]["libro_id"],
              "ruta": a["jerarquia"]["ruta"], "menciona_anexo_5": a["menciona_anexo_5"],
              "citas": a["citas_articulos"]} for a in articles]
    counts = Counter(a["jerarquia"]["libro_id"] for a in articles)
    if [counts[f"L.{i}"] for i in range(1, 9)] != [1, 100, 290, 86, 7, 80, 7, 37]:
        raise ValueError(f"Unexpected article/book assignments: {dict(counts)}")
    baseline["meta"].update({"total_articulos": len(articles), "total_libros": len(roots),
                             "fuente_url": SOURCE_URL, "jerarquia_version": 2})
    tree = {"version": 2, "libros": roots, "aliases": aliases, "advertencias": warnings}
    return baseline, index, tree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", type=Path, help="Saved official SISJUR HTML")
    group.add_argument("--download", action="store_true", help="Download the official source")
    parser.add_argument("--encoding", default="windows-1252")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--output-dir", type=Path, help="Optional staging directory")
    args = parser.parse_args()
    if args.download:
        with urlopen(SOURCE_URL, timeout=60) as response:
            raw = response.read()
    else:
        raw = args.source.read_bytes()
    baseline = json.loads((args.data_dir / "decreto_555_completo.json").read_text(encoding="utf-8"))
    complete, index, tree = restore_hierarchy(raw.decode(args.encoding), baseline)
    tree["fuente"] = {"url": SOURCE_URL, "sha256": hashlib.sha256(raw).hexdigest(),
                       "verificado_utc": datetime.now(timezone.utc).isoformat()}
    output = args.output_dir or args.data_dir
    output.mkdir(parents=True, exist_ok=True)
    (output / "decreto_555_completo.json").write_text(json.dumps(complete, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for filename, data in [("decreto_555_indice.json", index), ("decreto_555_arbol.json", tree)]:
        (output / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    books_dir = output / "libros"
    books_dir.mkdir(exist_ok=True)
    for number, book in enumerate(tree["libros"], 1):
        articles = [a for a in complete["articulos"] if a["jerarquia"]["libro_id"] == book["id"]]
        snapshot = {"libro_id": book["id"], "nombre": book["nombre"],
                    "total_articulos": len(articles), "articulos": articles}
        (books_dir / f"l_{number}.json").write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Restored {len(index)} articles, {len(tree['libros'])} books; article wording unchanged.")
    for warning in tree["advertencias"]:
        print(f"Review: {warning}")


if __name__ == "__main__":
    main()
