#!/usr/bin/env python3
"""Terceira passagem: os valores CURTOS que o filtro de tamanho deixou passar.

Os dois scripts anteriores exigiam valores com 18+ caracteres, para nao gastar
tempo com siglas. Isso escondeu os rotulos: 'Modulo de Young' tem 15 e e o nome
que aparece no cabecalho de uma formula. A licao e que um filtro de tamanho num
auditor de texto esconde exatamente o que mais aparece na tela -- rotulos e
titulos sao curtos por natureza.

Cobre tambem o bloco espanhol, que tinha os mesmos defeitos do portugues.
"""
from __future__ import annotations

import sys

PATH = "src/i18n/I18nContext.jsx"

# (antigo, novo, quantas ocorrencias esperar)
FIXES: list[tuple[str, str, int]] = [
    # --- português --------------------------------------------------------
    ("Modulo de Young", "Módulo de Young", 2),  # uma no bloco pt, uma no es
    ("Calibracao em SEC", "Calibração em SEC", 1),
    # --- espanhol ---------------------------------------------------------
    (
        "Energia en la ruptura por unidad de volumen, el area bajo la curva, en MJ/m3.",
        "Energía en la ruptura por unidad de volumen, el área bajo la curva, en MJ/m3.",
        1,
    ),
    (
        "Fraccion en peso en la porcion de la distribucion centrada en M.",
        "Fracción en peso en la porción de la distribución centrada en M.",
        1,
    ),
    ("Ancho de la distribucion log-normal en ln M.", "Ancho de la distribución log-normal en ln M.", 1),
    ("Media de ln M de la distribucion.", "Media de ln M de la distribución.", 1),
    (
        "Tangente de perdida, G'' / G'. Vale exactamente 1 en el cruce.",
        "Tangente de pérdida, G'' / G'. Vale exactamente 1 en el cruce.",
        1,
    ),
    ("'rheo.f.tan.name': 'Tangente de perdida'", "'rheo.f.tan.name': 'Tangente de pérdida'", 1),
    (
        "Velocidad de perdida de masa, en porcentaje por grado Celsius.",
        "Velocidad de pérdida de masa, en porcentaje por grado Celsius.",
        1,
    ),
    (
        "La frecuencia donde el fundido deja de comportarse elasticamente. Se "
        "desplaza con la temperatura, asi que un cruce citado sin su temperatura "
        "no es reproducible.",
        "La frecuencia donde el fundido deja de comportarse elásticamente. Se "
        "desplaza con la temperatura, así que un cruce citado sin su temperatura "
        "no es reproducible.",
        1,
    ),
    (
        "La media z es la que usan la dispersion de luz y la viscosimetria, asi "
        "que compararla con el Mw de la misma traza verifica la forma de la "
        "distribucion, no solo su posicion.",
        "La media z es la que usan la dispersión de luz y la viscosimetría, así "
        "que compararla con el Mw de la misma traza verifica la forma de la "
        "distribución, no solo su posición.",
        1,
    ),
    (
        "Mv queda entre Mn y Mw y se acerca a Mw cuando a esta cerca de 1. Usar K "
        "y a de otro disolvente o temperatura da una masa molar sistematicamente "
        "erronea que parece perfectamente razonable.",
        "Mv queda entre Mn y Mw y se acerca a Mw cuando a está cerca de 1. Usar K "
        "y a de otro disolvente o temperatura da una masa molar sistemáticamente "
        "errónea que parece perfectamente razonable.",
        1,
    ),
    ("Distribucion log-normal", "Distribución log-normal", 1),
]


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
            continue  # já aplicado
        else:
            problems.append(f"{n} ocorrencia(s), esperava {expected}: {old[:65]!r}")
    if problems:
        print("FALHOU:")
        for p in problems:
            print("  ", p)
        return 1
    open(PATH, "w", encoding="utf-8").write(text)
    print(f"alteracoes aplicadas: {applied} de {len(FIXES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
