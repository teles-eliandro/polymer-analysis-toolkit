#!/usr/bin/env python3
"""Restaura os acentos que faltam nos valores espanhois, e os dois restantes em portugues.

O bloco espanhol foi escrito pelo mesmo processo que deixou o portugues sem
acentos: as palavras funcionais ("de", "la", "el") estao certas, e as
significativas ("modulo", "traccion", "tension") perderam o acento. Em espanhol
isso e tao visivel quanto em portugues -- "Modulo de traccion" nao e castelhano.

Mapeamento explicito pelo mesmo motivo do script portugues: "esta"/"esta" e
"mas"/"mas" dependem da leitura, nao de uma regra.
"""
from __future__ import annotations

import sys

PATH = "src/i18n/I18nContext.jsx"

FIXES: list[tuple[str, str]] = [
    # --- o resíduo em português -------------------------------------------
    ("forca aplicada (N)", "força aplicada (N)"),
    # --- espanhol ---------------------------------------------------------
    (
        "Modulo de traccion, la pendiente de la recta ajustada, en MPa.",
        "Módulo de tracción, la pendiente de la recta ajustada, en MPa.",
    ),
    ("Deformacion del punto i dentro de la ventana ajustada.", "Deformación del punto i dentro de la ventana ajustada."),
    ("Tension del punto i dentro de la ventana ajustada, en MPa.", "Tensión del punto i dentro de la ventana ajustada, en MPa."),
    ("Tension de ingenieria, en MPa.", "Tensión de ingeniería, en MPa."),
    ("Deformacion de ingenieria, adimensional.", "Deformación de ingeniería, adimensional."),
    ("Masa molar media en numero.", "Masa molar media en número."),
    ("Numero de cadenas de masa molar Mi.", "Número de cadenas de masa molar Mi."),
    (
        "Modulo de perdida, la respuesta viscosa (disipadora de energia).",
        "Módulo de pérdida, la respuesta viscosa (disipadora de energía).",
    ),
    (
        "Modulo de almacenamiento, la respuesta elastica (acumuladora de energia).",
        "Módulo de almacenamiento, la respuesta elástica (acumuladora de energía).",
    ),
    ("Modulo de almacenamiento en el punto de gel.", "Módulo de almacenamiento en el punto de gel."),
    ("Modulo de perdida en el punto de gel.", "Módulo de pérdida en el punto de gel."),
    ("Modulo de almacenamiento, en Pa.", "Módulo de almacenamiento, en Pa."),
    ("Modulo de perdida, en Pa.", "Módulo de pérdida, en Pa."),
    ("modulo de traccion (MPa)", "módulo de tracción (MPa)"),
    (
        "tension de ingenieria (MPa), fuerza sobre la seccion original",
        "tensión de ingeniería (MPa), fuerza sobre la sección original",
    ),
    ("deformacion de ingenieria (%)", "deformación de ingeniería (%)"),
    (
        "El modulo solo es comparable entre muestras ajustadas en el mismo rango "
        "de deformacion. Un modulo ajustado de 0 a 5 % es sistematicamente menor "
        "que uno ajustado de 0 a 0,5 %, porque la curva se dobla al ceder. El "
        "rango usado se informa junto con el resultado.",
        "El módulo solo es comparable entre muestras ajustadas en el mismo rango "
        "de deformación. Un módulo ajustado de 0 a 5 % es sistemáticamente menor "
        "que uno ajustado de 0 a 0,5 %, porque la curva se dobla al ceder. El "
        "rango usado se informa junto con el resultado.",
    ),
    (
        "Minimos cuadrados en la ventana de deformacion, detectada por la mayor "
        "pendiente local o proporcionada por usted. Una ventana que empiece "
        "despues de la region de acomodo debe elegirse a ojo; la deteccion "
        "automatica puede caer en el hombro de cedencia en una muestra ductil.",
        "Mínimos cuadrados en la ventana de deformación, detectada por la mayor "
        "pendiente local o proporcionada por usted. Una ventana que empiece "
        "después de la región de acomodo debe elegirse a ojo; la detección "
        "automática puede caer en el hombro de cedencia en una muestra dúctil.",
    ),
    ("Tension y deformacion", "Tensión y deformación"),
    (
        "Son valores de ingenieria de principio a fin: se usa el area original y "
        "nunca se actualiza durante el ensayo. La tension real es mayor en una "
        "muestra que estricciona, asi que la resistencia a traccion informada "
        "aqui es conservadora.",
        "Son valores de ingeniería de principio a fin: se usa el área original y "
        "nunca se actualiza durante el ensayo. La tensión real es mayor en una "
        "muestra que estricciona, así que la resistencia a tracción informada "
        "aquí es conservadora.",
    ),
    ("Modulos de almacenamiento y de perdida", "Módulos de almacenamiento y de pérdida"),
    ("modulo de almacenamiento (Pa), la respuesta elastica", "módulo de almacenamiento (Pa), la respuesta elástica"),
    ("modulo de perdida (Pa), la respuesta viscosa", "módulo de pérdida (Pa), la respuesta viscosa"),
    ("desfase entre tension y deformacion (rad)", "desfase entre tensión y deformación (rad)"),
    (
        "Valido solo dentro de la region viscoelastica lineal, donde los modulos "
        "no dependen de la amplitud de deformacion. Un barrido fuera de ella "
        "informa un modulo de almacenamiento menor que parece un cambio de "
        "material y no lo es.",
        "Válido solo dentro de la región viscoelástica lineal, donde los módulos "
        "no dependen de la amplitud de deformación. Un barrido fuera de ella "
        "informa un módulo de almacenamiento menor que parece un cambio de "
        "material y no lo es.",
    ),
    (
        "Se informa solo cuando los dos modulos permanecen dentro de la "
        "tolerancia entre si mientras el modulo de almacenamiento supera al de "
        "perdida. La tolerancia importa: un test de cruce simple se dispara con "
        "ruido en un barrido ruidoso, asi que los dos modulos deben coincidir en "
        "varios puntos consecutivos.",
        "Se informa solo cuando los dos módulos permanecen dentro de la "
        "tolerancia entre sí mientras el módulo de almacenamiento supera al de "
        "pérdida. La tolerancia importa: un test de cruce simple se dispara con "
        "ruido en un barrido ruidoso, así que los dos módulos deben coincidir en "
        "varios puntos consecutivos.",
    ),
    ("numero de cadenas de masa molar Mi", "número de cadenas de masa molar Mi"),
    (
        "Una dispersidad de 1,0 significa que todas las cadenas tienen la misma "
        "longitud, lo que ninguna polimerizacion real alcanza: el minimo teorico "
        "para una polimerizacion anionica viva es de unos 1,02. Valores cercanos "
        "a 2 indican un mecanismo por etapas o dominado por transferencia de "
        "cadena.",
        "Una dispersidad de 1,0 significa que todas las cadenas tienen la misma "
        "longitud, lo que ninguna polimerización real alcanza: el mínimo teórico "
        "para una polimerización aniónica viva es de unos 1,02. Valores cercanos "
        "a 2 indican un mecanismo por etapas o dominado por transferencia de "
        "cadena.",
    ),
    (
        "Un modelo, no una medicion. Se muestra para comparar la forma de una "
        "distribucion medida con una idealizada, y supone que la traza no tiene "
        "ensanchamiento de columna, que ensancha toda traza real.",
        "Un modelo, no una medición. Se muestra para comparar la forma de una "
        "distribución medida con una idealizada, y supone que la traza no tiene "
        "ensanchamiento de columna, que ensancha toda traza real.",
    ),
]


def main() -> int:
    text = open(PATH, encoding="utf-8").read()
    applied = 0
    problems: list[str] = []
    for old, new in FIXES:
        n = text.count(old)
        if n == 1:
            text = text.replace(old, new)
            applied += 1
        elif n == 0:
            if text.count(new) == 1:
                continue
            problems.append(f"NAO ENCONTRADO: {old[:70]!r}")
        else:
            problems.append(f"{n} OCORRENCIAS de {old[:70]!r} -- ambiguo")
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
