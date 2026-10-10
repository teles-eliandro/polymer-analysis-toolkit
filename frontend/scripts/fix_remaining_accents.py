#!/usr/bin/env python3
"""Quarta passagem: os ultimos valores sem acento, com lista de palavras completa.

Tres passagens anteriores usaram listas de palavras que cresceram a cada rodada,
e cada rodada revelou que a anterior tinha buracos -- na terceira faltava
"numero", na segunda faltava "media". Uma lista de palavras num auditor de
acentos e um scanner incompleto por construcao: ela so encontra o que ja se
sabia procurar.

A solucao aqui e a mesma que funciona nos testes de paridade: rodar ate a
rodada seguinte reportar ZERO *e* conferir que os acertos restantes sao falsos
positivos por inspecao. Os falsos positivos conhecidos estao listados abaixo,
para que a proxima pessoa nao os "corrija" de novo.
"""
from __future__ import annotations

import sys

PATH = "src/i18n/I18nContext.jsx"

FIXES: list[tuple[str, str, int]] = [
    # --- português --------------------------------------------------------
    ("Massa molar media em massa.", "Massa molar média em massa.", 1),
    ("Massa molar media em numero.", "Massa molar média em número.", 1),
    ("Numero de cadeias de massa molar Mi.", "Número de cadeias de massa molar Mi.", 1),
    ("'numero de cadeias de massa molar Mi'", "'número de cadeias de massa molar Mi'", 1),
    ("massa molar media viscosimetrica (g/mol)", "massa molar média viscosimétrica (g/mol)", 1),
    (
        "Mv fica entre Mn e Mw e se aproxima de Mw quando a esta perto de 1. "
        "Usar K e a de outro solvente ou temperatura da uma massa molar "
        "sistematicamente errada que parece perfeitamente razoavel.",
        "Mv fica entre Mn e Mw e se aproxima de Mw quando a está perto de 1. "
        "Usar K e a de outro solvente ou temperatura dá uma massa molar "
        "sistematicamente errada que parece perfeitamente razoável.",
        1,
    ),
    # --- espanhol ---------------------------------------------------------
    (
        "Masa molar leida en la curva de calibracion en el volumen de elucion dado.",
        "Masa molar leída en la curva de calibración en el volumen de elución dado.",
        1,
    ),
    ("Medias numerica y ponderal", "Medias numérica y ponderal", 1),
    (
        "Mn es la media simple entre cadenas, Mw pondera cada cadena por su "
        "masa. Mw es siempre mayor o igual que Mn; si un resultado lo viola, el "
        "error esta en los datos o en la aritmetica, no en el polimero.",
        "Mn es la media simple entre cadenas, Mw pondera cada cadena por su "
        "masa. Mw es siempre mayor o igual que Mn; si un resultado lo viola, el "
        "error está en los datos o en la aritmética, no en el polímero.",
        1,
    ),
    ("constante especifica del polimero, disolvente y temperatura", "constante específica del polímero, disolvente y temperatura", 1),
    ("Calibracion en SEC", "Calibración en SEC", 1),
    (
        "La curva de calibracion convierte el volumen de elucion en masa molar "
        "usando estandares de otro polimero, salvo que los estandares sean del "
        "mismo material que la muestra. Por eso un resultado de SEC convencional "
        "es una masa molar relativa, y por eso debe informarse el estandar de "
        "calibracion.",
        "La curva de calibración convierte el volumen de elución en masa molar "
        "usando estándares de otro polímero, salvo que los estándares sean del "
        "mismo material que la muestra. Por eso un resultado de SEC convencional "
        "es una masa molar relativa, y por eso debe informarse el estándar de "
        "calibración.",
        1,
    ),
]

#: Acertos do auditor que NAO sao defeitos: a palavra nao leva acento.
#: Documentados para que a proxima rodada do auditor nao os trate como pendencias
#: nem os "corrija" -- acentuar "energia" em portugues esta errado.
NAO_SAO_DEFEITOS = {
    "energia",       # pt e es: sem acento
    "tangente",      # pt e es: sem acento
    "tolerancia",    # es: sem acento (pt "tolerância" leva)
    "sistematicamente",  # pt e es: sem acento
    "reticulada",    # pt: sem acento
    "elasticamente", # pt: sem acento
    "viscosimetria", # pt: sem acento
    "longitud",      # es: sem acento
    "velocidad",     # es: sem acento
    "media",         # es: sem acento (pt "média" leva -- por isso as listas sao separadas por idioma)
}


def main() -> int:
    text = open(PATH, encoding="utf-8").read()
    applied = 0
    problems: list[str] = []
    for old, new, expected in FIXES:
        n = text.count(old)
        if n == expected:
            text = text.replace(old, new)
            applied += 1
        elif n == 0 and text.count(new) >= expected:
            continue
        else:
            problems.append(f"{n} ocorrencia(s), esperava {expected}: {old[:65]!r}")
    # Escopo por LINHA, nao por texto: ``mol.f.mz.name`` e "Media z" nos dois
    # blocos, e em espanhol "media" nao leva acento. Uma substituicao global
    # acentuaria o espanhol tambem -- o tipo de "correcao" que cria o defeito
    # oposto. So a linha do bloco portugues muda.
    lines = text.split("\n")
    alvo = "'mol.f.mz.name': 'Media z',"
    idx = [i for i, ln in enumerate(lines) if ln.strip() == alvo]
    if len(idx) == 2:
        pt_line = idx[0] if idx[0] < 820 else idx[1]
        lines[pt_line] = lines[pt_line].replace("'Media z'", "'Média z'")
        text = "\n".join(lines)
        applied += 1
        print(f"  'Media z' acentuado apenas na linha {pt_line + 1} (bloco pt); "
              f"a linha {idx[1] - idx[0] + pt_line + 1} (es) mantida -- 'media' nao leva acento em espanhol")
    elif text.count("'Média z'") == 1:
        pass  # ja aplicado
    else:
        problems.append(f"esperava 2 ocorrencias de {alvo!r} para escopar por linha, achei {len(idx)}")
    if problems:
        print("FALHOU:")
        for p in problems:
            print("  ", p)
        return 1
    open(PATH, "w", encoding="utf-8").write(text)
    print(f"alteracoes aplicadas: {applied} de {len(FIXES)}")
    print(f"falsos positivos documentados: {len(NAO_SAO_DEFEITOS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
