"""As traduções da tabela de entalpias de referência.

Por que este arquivo existe separado de ``crystallinity_ref.py``: o banco de
dados é o registro científico -- valores, citações, DOIs conferidos -- e é
revisado por quem sabe a química. As traduções são outro trabalho, com outro
revisor, e misturá-las ao banco faria com que uma correção de valor e uma
correção de redação aparecessem no mesmo diff.

O português é o idioma de origem: ``crystallinity_ref.py`` continua sendo a
fonte canônica, e é para lá que se olha quando um valor está em dúvida. Este
módulo só acrescenta os idiomas que o banco não carrega.

Três campos são traduzidos, e três não são:

===================  ==========  ============================================
Campo                Traduzir?   Por quê
===================  ==========  ============================================
``display_name``     sim         é o nome do polímero na língua do leitor
``note``             sim         é redação editorial, não uma citação
``crystal_form``     sim         "ortorrômbica" é adjetivo, não notação
``source``           **não**     é a citação literal de um documento
``key``, ``names``   **não**     são identificadores e chaves de busca
``value_J_g``        **não**     é um número
===================  ==========  ============================================

A citação fica como está em todos os idiomas. Traduzir "The reflection of
X-rays by crystals" produziria uma referência que o artigo não usa, e um leitor
que fosse buscar o documento não o encontraria pela tradução. São três idiomas
de interface e um idioma de evidência.

Se uma entrada não tiver tradução, o serializador cai no português em vez de
omitir o campo -- ver ``test_crystallinity_i18n.py``, que falha se qualquer
chave do banco estiver sem ``en`` ou ``es``.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Nomes de exibição
# ---------------------------------------------------------------------------
# Nomes químicos: as formas entre parênteses são as siglas, que não mudam de
# idioma em nenhuma das três versões.

DISPLAY_NAME: dict[str, dict[str, str]] = {
    "PE": {"en": "Polyethylene (PE, HDPE/LDPE)", "es": "Polietileno (PE, HDPE/LDPE)"},
    "PP": {"en": "Isotactic polypropylene (PP-α)", "es": "Polipropileno isotáctico (PP-α)"},
    "PP-BETA": {"en": "Polypropylene β (PP-β)", "es": "Polipropileno β (PP-β)"},
    "PET": {
        "en": "Poly(ethylene terephthalate) (PET)",
        "es": "Poli(tereftalato de etileno) (PET)",
    },
    "PA6": {"en": "Polyamide 6 / Nylon 6 (PA6)", "es": "Poliamida 6 / Nylon 6 (PA6)"},
    "PA66": {"en": "Polyamide 66 / Nylon 66 (PA66)", "es": "Poliamida 66 / Nylon 66 (PA66)"},
    "PLA": {"en": "Polylactic acid (PLA / PLLA)", "es": "Ácido poliláctico (PLA / PLLA)"},
    "PBT": {
        "en": "Poly(butylene terephthalate) (PBT)",
        "es": "Poli(tereftalato de butileno) (PBT)",
    },
    "PEEK": {"en": "Poly(ether ether ketone) (PEEK)", "es": "Poli(éter éter cetona) (PEEK)"},
    "POM": {
        "en": "Poly(oxymethylene) / POM / Acetal (POM)",
        "es": "Poli(oximetileno) / POM / Acetal (POM)",
    },
    "PA11": {"en": "Polyamide 11 / Nylon 11 (PA11)", "es": "Poliamida 11 / Nylon 11 (PA11)"},
    "PA12": {"en": "Polyamide 12 / Nylon 12 (PA12)", "es": "Poliamida 12 / Nylon 12 (PA12)"},
    "PA610": {
        "en": "Polyamide 610 / Nylon 610 (PA610)",
        "es": "Poliamida 610 / Nylon 610 (PA610)",
    },
    "PA612": {
        "en": "Polyamide 612 / Nylon 612 (PA612)",
        "es": "Poliamida 612 / Nylon 612 (PA612)",
    },
    "PA69": {"en": "Polyamide 69 / Nylon 69 (PA69)", "es": "Poliamida 69 / Nylon 69 (PA69)"},
    "PB": {"en": "Polybutene-1 (PB-1 / PB)", "es": "Polibuteno-1 (PB-1 / PB)"},
    "PVC": {"en": "Poly(vinyl chloride) (PVC)", "es": "Poli(cloruro de vinilo) (PVC)"},
    "PCTFE": {
        "en": "Polychlorotrifluoroethylene (PCTFE)",
        "es": "Policlorotrifluoroetileno (PCTFE)",
    },
    "PVF": {"en": "Poly(vinyl fluoride) (PVF)", "es": "Poli(fluoruro de vinilo) (PVF)"},
    "PTrFE": {"en": "Polytrifluoroethylene (PTrFE)", "es": "Politrifluoroetileno (PTrFE)"},
    "PCL": {"en": "Polycaprolactone (PCL)", "es": "Policaprolactona (PCL)"},
    "PHB": {
        "en": "Poly(hydroxybutyrate) (PHB / PHA)",
        "es": "Poli(hidroxibutirato) (PHB / PHA)",
    },
    "PHBV": {
        "en": "Poly(3-hydroxybutyrate-co-3-hydroxyvalerate) (PHBV)",
        "es": "Poli(3-hidroxibutirato-co-3-hidroxivalerato) (PHBV)",
    },
    "PVDF": {
        "en": "Poly(vinylidene fluoride) (PVDF)",
        "es": "Poli(fluoruro de vinilideno) (PVDF)",
    },
    "PEO": {"en": "Poly(ethylene oxide) (PEO / PEG)", "es": "Poli(óxido de etileno) (PEO / PEG)"},
    "PVA": {
        "en": "Poly(vinyl alcohol) (PVA / PVOH)",
        "es": "Poli(alcohol vinílico) (PVA / PVOH)",
    },
    "PTFE": {"en": "Polytetrafluoroethylene (PTFE)", "es": "Politetrafluoroetileno (PTFE)"},
    "PS-ISO": {"en": "Isotactic polystyrene (PS-i)", "es": "Poliestireno isotáctico (PS-i)"},
    "PS": {
        "en": "Atactic polystyrene (PS, GPPS/HIPS)",
        "es": "Poliestireno atáctico (PS, GPPS/HIPS)",
    },
    "PBAT": {
        "en": "Poly(butylene adipate-co-terephthalate) (PBAT)",
        "es": "Poli(adipato-co-tereftalato de butileno) (PBAT)",
    },
}

# ---------------------------------------------------------------------------
# Formas cristalinas
# ---------------------------------------------------------------------------
# Adjetivos e letras gregas. As letras (α, β, γ) não mudam; o que muda é o
# adjetivo do sistema cristalino que as acompanha.

CRYSTAL_FORM: dict[str, dict[str, str]] = {
    "forma I (hexagonal)": {"en": "form I (hexagonal)", "es": "forma I (hexagonal)"},
    "hexagonal (POM estável)": {"en": "hexagonal (stable POM)", "es": "hexagonal (POM estable)"},
    "isotática": {"en": "isotactic", "es": "isotáctica"},
    "monoclínica": {"en": "monoclinic", "es": "monoclínica"},
    "ortorrômbica": {"en": "orthorhombic", "es": "ortorrómbica"},
    "ortorrômbica (HB)": {"en": "orthorhombic (HB)", "es": "ortorrómbica (HB)"},
    "triclínica": {"en": "triclinic", "es": "triclínica"},
    "α": {"en": "α", "es": "α"},
    "α (hélice 10/3)": {"en": "α (10/3 helix)", "es": "α (hélice 10/3)"},
    "α (monoclínica)": {"en": "α (monoclinic)", "es": "α (monoclínica)"},
    "α (triclínica)": {"en": "α (triclinic)", "es": "α (triclínica)"},
    "α' (triclínica)": {"en": "α' (triclinic)", "es": "α' (triclínica)"},
    "β (hexagonal)": {"en": "β (hexagonal)", "es": "β (hexagonal)"},
    "γ (monoclínica)": {"en": "γ (monoclinic)", "es": "γ (monoclínica)"},
}

# ---------------------------------------------------------------------------
# Notas
# ---------------------------------------------------------------------------
# Chaveadas por ``<polímero>`` (nota do polímero) ou ``<polímero>.ref<N>``
# (nota da N-ésima referência daquele polímero).

NOTE: dict[str, dict[str, str]] = {
    "PE.poly": {
        "en": (
            "ΔHf100 is a property of the crystal, not of the degree of "
            "branching: LDPE and HDPE share the same value (~290 J/g). LDPE "
            "appears to have a lower ΔHf100 only because it crystallises less "
            "-- using a smaller denominator for LDPE would double the "
            "crystallinity error. There is no separate LDPE entry for that "
            "reason."
        ),
        "es": (
            "ΔHf100 es una propiedad del cristal, no del grado de ramificación: "
            "LDPE y HDPE comparten el mismo valor (~290 J/g). El LDPE parece "
            "tener un ΔHf100 menor solo porque cristaliza menos -- usar un "
            "denominador menor para LDPE duplicaría el error de cristalinidad. "
            "Por eso no hay una entrada separada para LDPE."
        ),
    },
    "PE.ref0": {
        "en": "ΔH°m of the perfect crystal, extrapolated. The canonical value for linear polyethylene.",
        "es": "ΔH°m del cristal perfecto, extrapolado. Valor canónico del polietileno lineal.",
    },
    "PP-BETA.ref0": {
        "en": "The β form is less standardised than α. Using the α value for a β sample underestimates crystallinity by ~20 %.",
        "es": "La forma β está menos normalizada que la α. Usar el valor de la α para una muestra β subestima la cristalinidad en ~20 %.",
    },
    "PET.ref1": {
        "en": "An earlier value, still cited; it differs from the 1983 one.",
        "es": "Valor anterior, todavía citado; difiere del de 1983.",
    },
    "PA6.ref0": {
        "en": "The γ form has a ΔHf100 of the order of 239 J/g.",
        "es": "La forma γ tiene un ΔHf100 del orden de 239 J/g.",
    },
    "PA66.ref0": {
        "en": "A compilation value, and the most used one in the applied PA66 literature.",
        "es": "Valor de recopilación, y el más usado en la literatura aplicada de PA66.",
    },
    "PA66.ref1": {
        "en": (
            "A real divergence, not an error on one side: TN048 derives from "
            "Wunderlich (kJ/mol per repeat unit) and arrives at 226, while the "
            "applied compilations cite 255. Choosing between them shifts "
            "crystallinity by ~13 %, so the pair is recorded rather than "
            "resolved by averaging. The mean (240) belongs to neither source."
        ),
        "es": (
            "Divergencia real, no error de uno de los lados: la TN048 deriva de "
            "Wunderlich (kJ/mol por unidad repetida) y llega a 226, mientras que "
            "las recopilaciones aplicadas citan 255. Elegir entre ambos cambia la "
            "cristalinidad en ~13 %, así que el par queda registrado en vez de "
            "resolverse por promedio. La media (240) no pertenece a ninguna de "
            "las dos fuentes."
        ),
    },
    "PLA.ref0": {
        "en": "The standard literature value for PLLA, widely cited. Racemic PLA (PDLLA) is amorphous and has no applicable ΔHf100.",
        "es": "Valor estándar de la literatura para PLLA, ampliamente citado. El PLA racémico (PDLLA) es amorfo y no tiene un ΔHf100 aplicable.",
    },
    "POM.ref0": {
        "en": "The largest ΔHf100 among common thermoplastics, and therefore the one most penalised by a wrong denominator: using PE (293) for POM underestimates crystallinity by ~11 %.",
        "es": "El mayor ΔHf100 entre los termoplásticos comunes, y por eso el más penalizado por un denominador erróneo: usar PE (293) para POM subestima la cristalinidad en ~11 %.",
    },
    "PB.ref0": {
        "en": "Form I is the stable one; form II (tetragonal), obtained by fast cooling, has a different ΔHf100. The value of 125 J/g refers to form I.",
        "es": "La forma I es la estable; la forma II (tetragonal), obtenida por enfriamiento rápido, tiene un ΔHf100 distinto. El valor de 125 J/g corresponde a la forma I.",
    },
    "PVC.poly": {
        "en": "Included with an explicit caveat. A non-zero ΔHm in plasticised commercial PVC is almost always from the plasticiser or the stabiliser.",
        "es": "Se incluye con una salvedad explícita. Un ΔHm no nulo en PVC comercial plastificado casi siempre proviene del plastificante o del estabilizante.",
    },
    "PVC.ref0": {
        "en": (
            "Handle this one with care: commercial PVC is amorphous, and a ΔHm "
            "measured on it comes from an additive or a filler, not from the "
            "polymer. The value of 176 J/g applies to syndiotactic PVC, which "
            "does crystallise; using it as the denominator for a commercial PVC "
            "produces a crystallinity with no meaning."
        ),
        "es": (
            "Cuidado con este: el PVC comercial es amorfo, y un ΔHm medido en él "
            "proviene de un aditivo o de una carga, no del polímero. El valor de "
            "176 J/g corresponde al PVC sindiotáctico, que sí cristaliza; usarlo "
            "como denominador de un PVC comercial produce una cristalinidad sin "
            "significado."
        ),
    },
    "PHBV.poly": {
        "en": "No single ΔHf100: the value falls with the HV content. Fill in the composition and use the corresponding value.",
        "es": "Sin un ΔHf100 único: el valor cae con el contenido de HV. Complete la composición y use el valor correspondiente.",
    },
    "PEO.ref0": {
        "en": "Some compilations list 213 J/g; the divergence is one of value refinement.",
        "es": "Algunas recopilaciones listan 213 J/g; la divergencia es un refinamiento del valor.",
    },
    "PVA.ref0": {
        "en": "TN048 uses 161, the upper end of the published range. It applies to PVA of high stereochemical regularity.",
        "es": "La TN048 usa 161, el extremo superior del intervalo publicado. Vale para PVA de alta regularidad estereoquímica.",
    },
    "PVA.ref1": {
        "en": (
            "The lower end of the range. The 15 % spread between 138 and 161 is "
            "not measurement error: commercial PVA has variable degree of "
            "hydrolysis and tacticity, and ΔHf100 follows. Report the degree of "
            "hydrolysis alongside the result."
        ),
        "es": (
            "El límite inferior del intervalo. La dispersión del 15 % entre 138 y "
            "161 no es error de medición: el PVA comercial tiene grado de "
            "hidrólisis y tacticidad variables, y el ΔHf100 los acompaña. Informe "
            "el grado de hidrólisis junto con el resultado."
        ),
    },
    "PTFE.ref0": {
        "en": "Compilations diverge between 69 and 82 J/g.",
        "es": "Las recopilaciones divergen entre 69 y 82 J/g.",
    },
    "PS.poly": {
        "en": (
            "Atactic polystyrene is amorphous: it does not crystallise, and "
            "crystallinity by DSC does not apply. A ΔHm measured on this sample "
            "comes from an additive or from another component of the blend, not "
            "from the PS. There is no ΔHf100 to report -- and the isotactic value "
            "(207 J/g, PS-ISO) does not apply here."
        ),
        "es": (
            "El poliestireno atáctico es amorfo: no cristaliza, y la "
            "cristalinidad por DSC no se aplica. Un ΔHm medido en esta muestra "
            "proviene de un aditivo o de otro componente de la mezcla, no del PS. "
            "No hay ΔHf100 que informar -- y el valor isotáctico (207 J/g, "
            "PS-ISO) no vale aquí."
        ),
    },
    "PBAT.poly": {
        "en": "A random copolymer: no universal ΔHf100 exists. The number depends on the terephthalate fraction.",
        "es": "Copolímero aleatorio: no existe un ΔHf100 universal. El número depende de la fracción de tereftalato.",
    },
}


def display_name(key: str, lang: str, fallback: str) -> str:
    """O nome do polímero em ``lang``, ou ``fallback`` (o português do banco)."""
    entry = DISPLAY_NAME.get(key)
    return (entry or {}).get(lang) or fallback


def crystal_form(form: str | None, lang: str) -> str | None:
    """A forma cristalina em ``lang``; o original quando não há tradução."""
    if form is None:
        return None
    return (CRYSTAL_FORM.get(form) or {}).get(lang) or form


def note(key: str, lang: str, fallback: str | None) -> str | None:
    """A nota de ``key`` em ``lang``, ou ``fallback`` (o português do banco)."""
    if fallback is None:
        return None
    return (NOTE.get(key) or {}).get(lang) or fallback
