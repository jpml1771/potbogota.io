"""
Extractor y normalizador completo del Decreto Distrital 555 de 2021 (POT de Bogotá)
Desde la versión oficial de SISJUR (Secretaría Jurídica Distrital)
Genera:
  - data/decreto_555_completo.json (Los 608 artículos con texto limpio, tablas, notas y citas)
  - data/decreto_555_indice.json (Índice ligero para búsqueda instantánea en cliente)
  - data/decreto_555_arbol.json (Estructura jerárquica Libros > Títulos > Capítulos > Artículos)
"""

import os
import re
import json
import html as html_lib

def main():
    repo_dir = r'd:\OneDrive\08_ETOM\07_POT\POT_DIGITAL\potbogota.io'
    scratch_dir = r'C:\Users\Juam Pablo\.gemini\antigravity-ide\brain\4f33cac9-4194-420a-bc56-4938b3b19d50\scratch'
    html_path = os.path.join(scratch_dir, 'sisjur_pot_555.html')
    data_dir = os.path.join(repo_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    print(f"Leyendo archivo fuente: {html_path}...")
    with open(html_path, 'r', encoding='windows-1252', errors='replace') as f:
        html = f.read()

    print(f"Archivo cargado: {len(html)} caracteres. Parseando estructura...")

    # 1. Parsear anclas estructurales (Libros, Títulos, Capítulos, etc.)
    ancla_pattern = re.compile(r'<span[^>]*class="ancla"[^>]*id="([^"]+)"[^>]*></span>', re.I)
    
    # Nombres amigables conocidos para los Libros
    libros_nombres = {
        'L.1': 'Libro I - Estructura y Adopción del Plan',
        'L.2': 'Libro II - Componente General',
        'L.3': 'Libro III - Componente Urbano',
        'L.4': 'Libro IV - Componente Rural',
        'L.5': 'Libro V - Instrumentos de Planeación',
        'L.6': 'Libro VI - Instrumentos de Gestión, Financiación y Gobernanza'
    }

    structures = []
    for m in ancla_pattern.finditer(html):
        aid = m.group(1)
        if any(aid.startswith(p) for p in ['L.1', 'L.2', 'L.3', 'L.4', 'L.5', 'L.6']):
            start = max(0, m.start() - 250)
            end = min(len(html), m.end() + 350)
            snippet = html[start:end]
            clean = re.sub(r'<[^>]+>', ' ', snippet)
            clean = ' '.join(clean.split())
            clean = html_lib.unescape(clean)

            # Intentar obtener título limpio
            title = clean
            # Normalizar nombre
            if aid in libros_nombres:
                nombre = libros_nombres[aid]
            else:
                nombre = clean[:120]

            structures.append({
                'id': aid,
                'pos': m.start(),
                'raw_text': clean,
                'nombre': nombre
            })

    structures.sort(key=lambda s: s['pos'])
    print(f"Estructuras encontradas: {len(structures)}")

    def get_hierarchy_at(pos):
        cur_libro = None
        cur_titulo = None
        cur_capitulo = None
        cur_subcap = None
        cur_seccion = None

        for s in structures:
            if s['pos'] > pos:
                break
            aid = s['id']
            parts = aid.split('.')
            if len(parts) == 2 and parts[0] == 'L':
                cur_libro = s
                cur_titulo = None
                cur_capitulo = None
                cur_subcap = None
                cur_seccion = None
            elif 'T' in parts:
                if 'C' not in parts:
                    cur_titulo = s
                    cur_capitulo = None
                    cur_subcap = None
                    cur_seccion = None
            if 'C' in parts and 'SC' not in parts and 'S' not in parts:
                cur_capitulo = s
                cur_subcap = None
                cur_seccion = None
            if 'SC' in parts and 'S' not in parts:
                cur_subcap = s
                cur_seccion = None
            if 'S' in parts:
                cur_seccion = s

        return {
            'libro_id': cur_libro['id'] if cur_libro else 'L.1',
            'libro_nombre': libros_nombres.get(cur_libro['id'] if cur_libro else 'L.1', 'Libro I'),
            'titulo_id': cur_titulo['id'] if cur_titulo else None,
            'titulo_nombre': cur_titulo['nombre'] if cur_titulo else None,
            'capitulo_id': cur_capitulo['id'] if cur_capitulo else None,
            'capitulo_nombre': cur_capitulo['nombre'] if cur_capitulo else None,
            'subcapitulo_id': cur_subcap['id'] if cur_subcap else None,
            'seccion_id': cur_seccion['id'] if cur_seccion else None,
        }

    # 2. Localizar los 608 artículos secuenciales
    art_pattern = re.compile(
        r'(?:Art[íi]culo|ART[ÍI]CULO)'
        r'(?:<[^>]+>|\s|&nbsp;)*?'
        r'(?:<span[^>]*class="ancla"[^>]*id="(\d+)"[^>]*></span>)?'
        r'(?:<[^>]+>|\s|&nbsp;)*?'
        r'(\d+)'
        r'(?:<[^>]+>|\s|&nbsp;)*?'
        r'[\.:\-\)]',
        re.I
    )

    articles_pos = []
    expected_num = 1
    for m in art_pattern.finditer(html):
        num = int(m.group(2))
        if num == expected_num:
            articles_pos.append({
                'num': num,
                'start': m.start(),
                'match_end': m.end()
            })
            expected_num += 1
            if expected_num > 608:
                break

    print(f"Artículos detectados secuencialmente: {len(articles_pos)} de 608")
    if len(articles_pos) != 608:
        raise ValueError(f"Se esperaban 608 artículos, pero se detectaron {len(articles_pos)}")

    for i in range(len(articles_pos)):
        cur = articles_pos[i]
        if i + 1 < len(articles_pos):
            cur['end'] = articles_pos[i + 1]['start']
        else:
            cur['end'] = len(html)

    # 3. Procesar y limpiar cada artículo
    todos_articulos = []
    indice_articulos = []

    for art_info in articles_pos:
        num = art_info['num']
        raw = html[art_info['match_end']:art_info['end']]
        
        # Jerarquía activa
        hier = get_hierarchy_at(art_info['start'])

        # Nota reglamentaria si existe
        nota_reg = None
        nota_url = None
        note_m = re.search(r'<a\s+href="([^"]+)">\s*((?:Reglamentado|Modificado|Adicionado)[^<]+)\s*</a>', raw[:1200], re.I)
        if note_m:
            nota_url = note_m.group(1).strip()
            nota_reg = note_m.group(2).strip()

        # Extraer título
        first_b = re.search(r'<b[^>]*>(.*?)</b>', raw[:1200], re.DOTALL | re.I)
        title = ""
        title_end_pos = 0
        if first_b:
            t_raw = re.sub(r'<[^>]+>', ' ', first_b.group(1)).strip()
            t_clean = ' '.join(t_raw.split())
            t_clean = html_lib.unescape(t_clean).strip(' .\t\r\n')
            if len(t_clean) <= 1:
                second_b = re.search(r'<b[^>]*>(.*?)</b>', raw[first_b.end():1500], re.DOTALL | re.I)
                if second_b:
                    t_raw = re.sub(r'<[^>]+>', ' ', second_b.group(1)).strip()
                    t_clean = ' '.join(t_raw.split())
                    t_clean = html_lib.unescape(t_clean).strip(' .\t\r\n')
                    title = t_clean
                    title_end_pos = first_b.end() + second_b.end()
            else:
                title = t_clean
                title_end_pos = first_b.end()

        # Limpiar cuerpo del artículo
        body_raw = raw[title_end_pos:] if title_end_pos > 0 else raw

        # Quitar basura de Word y SISJUR
        cleaned = re.sub(r'<\?xml[^>]*>', '', body_raw)
        cleaned = re.sub(r'<!--\[if[^\]]*\]>.*?<!\[endif\]-->', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<!\[if[^\]]*\]>.*?<!\[endif\]>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<o:p>.*?</o:p>', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<span[^>]*class="ancla"[^>]*></span>', '', cleaned)
        cleaned = re.sub(r'class="Mso\w+"', '', cleaned)
        cleaned = re.sub(r'style="[^"]*"', '', cleaned)
        cleaned = re.sub(r'lang="[^"]*"', '', cleaned)
        cleaned = re.sub(r'align="[^"]*"', '', cleaned)
        cleaned = re.sub(r'face="[^"]*"', '', cleaned)
        cleaned = re.sub(r'<font[^>]*>', '', cleaned)
        cleaned = re.sub(r'</font>', '', cleaned)
        cleaned = re.sub(r'<span\s*>\s*</span>', '', cleaned)

        # Quitar párrafos vacíos sucesivos
        cleaned = re.sub(r'<p\s*>\s*(&nbsp;|\s)*</p>', '', cleaned)

        # Arreglar tablas
        cleaned = re.sub(r'<table[^>]*>', '<div class="table-wrapper my-4 overflow-x-auto"><table class="pot-table min-w-full text-sm border border-slate-200">', cleaned)
        cleaned = re.sub(r'</table>', '</table></div>', cleaned)
        cleaned = re.sub(r'<td[^>]*>', '<td class="border border-slate-200 px-3 py-2 text-left align-top">', cleaned)
        cleaned = re.sub(r'<th[^>]*>', '<th class="border border-slate-200 bg-slate-100 font-bold px-3 py-2 text-left">', cleaned)

        # Convertir párrafos a limpios
        cleaned = re.sub(r'<p\s*>', '<p class="mb-3 leading-relaxed text-slate-700">', cleaned)

        # Detectar citas a otros artículos
        # Ej: "artículo 384", "artículos 190 y 191"
        citas = []
        for ref_m in re.finditer(r'art[íi]culos?\s+(\d+)', cleaned, re.I):
            ref_num = int(ref_m.group(1))
            if 1 <= ref_num <= 608 and ref_num != num:
                citas.append(ref_num)
        citas = sorted(list(set(citas)))

        # Detectar si cita al Anexo 5 / Manual de Normas Comunes
        menciona_anexo_5 = bool(re.search(r'Anexo\s+(?:No\.?\s*)?5|Manual\s+de\s+Normas\s+Comunes', cleaned, re.I))

        # Texto plano para búsqueda ultra rápida
        texto_plano = re.sub(r'<[^>]+>', ' ', f"{title} {cleaned}")
        texto_plano = ' '.join(texto_plano.split())
        texto_plano = html_lib.unescape(texto_plano)

        art_doc = {
            'numero': num,
            'id': f"art-{num}",
            'titulo': title,
            'nota_reglamentaria': nota_reg,
            'nota_url': nota_url,
            'jerarquia': hier,
            'contenido_html': cleaned.strip(),
            'citas_articulos': citas,
            'menciona_anexo_5': menciona_anexo_5,
            'texto_plano': texto_plano
        }

        todos_articulos.append(art_doc)

        # Entrada para el índice ligero
        indice_articulos.append({
            'numero': num,
            'id': f"art-{num}",
            'titulo': title,
            'libro': hier['libro_nombre'],
            'menciona_anexo_5': menciona_anexo_5,
            'citas': citas
        })

    # 4. Guardar los archivos generados
    completo_path = os.path.join(data_dir, 'decreto_555_completo.json')
    indice_path = os.path.join(data_dir, 'decreto_555_indice.json')
    arbol_path = os.path.join(data_dir, 'decreto_555_arbol.json')

    print(f"Guardando {completo_path}...")
    with open(completo_path, 'w', encoding='utf-8') as f:
        json.dump({
            'meta': {
                'titulo': 'Plan de Ordenamiento Territorial de Bogotá D.C. - Decreto Distrital 555 de 2021',
                'fuente_oficial': 'Alcaldía Mayor de Bogotá D.C. - Secretaría Jurídica Distrital (SISJUR)',
                'total_articulos': len(todos_articulos)
            },
            'articulos': todos_articulos
        }, f, ensure_ascii=False, indent=2)

    print(f"Guardando {indice_path}...")
    with open(indice_path, 'w', encoding='utf-8') as f:
        json.dump(indice_articulos, f, ensure_ascii=False, indent=2)

    # 5. Generar árbol para el menú lateral
    # Agrupado por Libro -> Capítulo -> Artículos
    libros_dict = {}
    for a in todos_articulos:
        l_id = a['jerarquia']['libro_id']
        l_name = a['jerarquia']['libro_nombre']
        if l_id not in libros_dict:
            libros_dict[l_id] = {
                'id': l_id,
                'nombre': l_name,
                'articulos': []
            }
        libros_dict[l_id]['articulos'].append({
            'numero': a['numero'],
            'id': a['id'],
            'titulo': a['titulo'],
            'menciona_anexo_5': a['menciona_anexo_5']
        })

    print(f"Guardando {arbol_path}...")
    with open(arbol_path, 'w', encoding='utf-8') as f:
        json.dump(list(libros_dict.values()), f, ensure_ascii=False, indent=2)

    # Resumen final
    anexo_citas_total = sum(1 for a in todos_articulos if a['menciona_anexo_5'])
    tamanio_mb = os.path.getsize(completo_path) / (1024 * 1024)
    print("\n" + "="*50)
    print("¡EXTRACCIÓN EXITOSA DEL DECRETO 555 DE 2021!")
    print(f"- Total artículos procesados: {len(todos_articulos)} (1 al 608)")
    print(f"- Artículos que citan al Anexo 5: {anexo_citas_total}")
    print(f"- Tamaño del JSON completo limpio: {tamanio_mb:.2f} MB (antes 4.58 MB de HTML sucio)")
    print(f"- Tamaño del índice ligero: {os.path.getsize(indice_path)/1024:.1f} KB")
    print("="*50)

if __name__ == '__main__':
    main()
