"""Pasa por el embudo las propuestas de cada corrida de evaluación y resume por versión."""
import json, sys, shutil, glob, statistics as st
from pathlib import Path
sys.path.insert(0, '/home/claude/faltante-gh')
from harness import correr as c
from harness.embudo import recorrer
S = Path(sys.argv[1]); SER = c.SERENDIPIA
filas, faltan = [], set()
for f in sorted(S.glob('eval/eval-*.json')):
    version, corrida = f.stem.rsplit('_', 1)
    tmp = SER / f"divergente_eval{corrida}.json"; shutil.copy(f, tmp)
    try:
        rs = [recorrer(p) for p in c.propuestas(f"eval{corrida}")]
    finally:
        tmp.unlink()
    llm = [r for r in rs if r['metodo'] == 'llm']
    pasa = lambda r, ch: any(x['chequeo'] == ch and x['pasa'] for x in r['recorrido'])
    faltan |= {r['busqueda_ml'] for r in llm if r['motivo'].startswith('falta capturar')}
    distintas = lambda xs: len({r['busqueda_ml'] for r in xs})
    filas.append({'version': version, 'corrida': corrida, 'propuestas': len(llm),
                  'c1_c3': distintas([r for r in llm if pasa(r, 'C3 demanda')]),
                  'c4': distintas([r for r in llm if pasa(r, 'C4 hueco')]),
                  'c5': distintas([r for r in llm if pasa(r, 'C5 la eligen')]),
                  'c6_o_condicional': distintas([r for r in llm if r['estado'] != 'descartada']),
                  'falta_capturar': sum(r['motivo'].startswith('falta capturar') for r in llm),
                  'sobrevivientes': sorted({r['que_traer'][:70] for r in llm if pasa(r, 'C5 la eligen')})})
    if version == 'eval-personas-cruzan' and not any(x.get('base') for x in filas):
        b = [r for r in rs if r['metodo'] in ('B1', 'B2')]
        for m in ('B1', 'B2'):
            bb = [r for r in b if r['metodo'] == m]
            filas.append({'version': m, 'corrida': '-', 'base': True, 'propuestas': len(bb), 'c1_c3': distintas([r for r in bb if pasa(r, 'C3 demanda')]),
                          'c4': distintas([r for r in bb if pasa(r, 'C4 hueco')]), 'c5': distintas([r for r in bb if pasa(r, 'C5 la eligen')]),
                          'c6_o_condicional': distintas([r for r in bb if r['estado'] != 'descartada']), 'falta_capturar': sum(r['motivo'].startswith('falta capturar') for r in bb), 'sobrevivientes': []})
json.dump({'filas': filas, 'faltan': sorted(faltan)}, open(S / 'eval/resumen.json', 'w'), ensure_ascii=False, indent=1)
for x in filas:
    print(f"{x['version']:22} {x['corrida']:12} prop={x['propuestas']:3} C1-C3={x['c1_c3']:3} C4={x['c4']:2} C5={x['c5']:2} C6={x['c6_o_condicional']:2} faltan={x['falta_capturar']}")
print('búsquedas por capturar:', len(faltan))
