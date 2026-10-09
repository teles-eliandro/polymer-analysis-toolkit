"""
Banco de entalpias de fusão de polímeros 100 % cristalinos.

O problema
----------
A cristalinidade por DSC sai de uma razão::

    Xc (%) = (ΔHm medido / ΔHf100) × 100

onde ``ΔHf100`` é a entalpia de fusão do polímero **100 % cristalino**. É o
único denominador possível, e não se mede: nenhuma amostra real é 100 %
cristalina, então o valor vem sempre da literatura, por extrapolação das
entalpias de fusão de uma série de amostras de cristalinidade conhecida (ou
do equilíbrio termodinâmico).

O erro que este módulo existe para evitar
-----------------------------------------
Esse número é **específico do polímero e da forma cristalina**. O polietileno
está em ~290 J/g; o polipropileno, em ~207 J/g; o PLA, em ~93 J/g. Usar 290
para uma amostra de PLA dá uma cristalinidade de ~32 % para uma amostra
totalmente cristalina -- um erro de um fator três, silencioso, que produz um
número plausível e errado. E um formulário que aceita qualquer número sem
dizer de onde ele vem torna esse erro invisível.

Por isso cada entrada aqui carrega a **referência** do valor, a **forma
cristalina** a que ele se refere, e o **grau de confiança** da citação. O
campo do formulário pode então ser preenchido escolhendo um polímero (ou
deixando o nome do arquivo escolher), em vez de digitar um número.

Critério de inclusão
--------------------
Entra aqui só o que se pode citar. Cada valor traz uma referência primária
verificada (DOI conferido) ou uma compilação secundária nomeada. Onde a
literatura diverge, as duas versões entram, cada uma com sua fonte, em vez de
uma média inventada -- uma média de dois números de fontes diferentes não
pertence a nenhuma das duas.

Limite conhecido
----------------
Para copolímeros (PBAT, PHBV) não existe um ``ΔHf100`` único e acordado: o
valor depende da razão entre comonômeros. Essas entradas ficam marcadas, e o
valor reportado é o de uma composição típica, com a ressalva explícita.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CrystallinityReference:
    """A entalpia de fusão de um polímero 100 % cristalino, com a fonte.

    ``value_J_g`` é o valor de referência; ``crystal_form`` diz a que forma
    ele se refere (o polipropileno α e β diferem, e trocar um pelo outro muda
    a cristalinidade calculada); ``source`` é a citação, e ``confidence`` diz
    se ela foi conferida contra o registro bibliográfico ou se é uma
    compilação secundária.
    """

    value_J_g: float
    source: str
    crystal_form: str | None = None
    #: 'verified' quando o DOI foi conferido; 'compilation' quando o valor vem
    #: de uma compilação secundária nomeada; 'divergent' quando a literatura
    #: diverge e este é um dos valores concorrentes.
    confidence: str = "compilation"
    note: str | None = None


@dataclass(frozen=True)
class PolymerEnthalpy:
    """As entalpias de referência de um polímero, com os nomes que o denunciam."""

    key: str
    display_name: str
    #: Nomes pelos quais uma amostra ou um arquivo pode se identificar.
    names: tuple[str, ...]
    references: tuple[CrystallinityReference, ...] = ()
    #: True para copolímeros, cujo valor depende da composição.
    copolymer: bool = False
    note: str | None = None

    @property
    def primary(self) -> CrystallinityReference | None:
        """A referência recomendada -- a primeira, que é a de maior confiança."""
        return self.references[0] if self.references else None


# ---------------------------------------------------------------------------
# O banco
# ---------------------------------------------------------------------------
#
# Valores e citações. Os DOIs foram conferidos contra o registro do Crossref;
# as compilações secundárias (Polymer Handbook, Physical Properties of Polymers
# Handbook, ATHAS) são citadas por edição porque são elas que a literatura
# aplicada cita de fato quando não cita o artigo primário.
ENTHALPY_DB: dict[str, PolymerEnthalpy] = {
    "PE": PolymerEnthalpy(
        key="PE",
        display_name="Polietileno (PE, HDPE/LDPE)",
        names=("pe", "polyethylene", "polietileno", "hdpe", "ldpe", "lldpe", "pe-uhmw"),
        references=(
            CrystallinityReference(
                293.0,
                "B. Wunderlich, F. M. Cormier, 'Heat of fusion of polyethylene', "
                "J. Polym. Sci. A-2 5 (1967) 987-988. doi:10.1002/pol.1967.160050514",
                crystal_form="ortorrômbica",
                confidence="verified",
                note=(
                    "ΔH°m do cristal perfeito, extrapolado. Valor canônico do "
                    "polietileno linear."
                ),
            ),
            CrystallinityReference(
                290.0,
                "J. Brandrup, E. H. Immergut, E. A. Grulke (eds.), Polymer "
                "Handbook, 4th ed., Wiley, 1999, seção VI.",
                crystal_form="ortorrômbica",
                confidence="compilation",
            ),
        ),
        note=(
            "O ΔHf100 é propriedade do cristal, não do grau de ramificação: "
            "LDPE e HDPE têm o mesmo valor (~290 J/g). O LDPE parece ter um "
            "ΔHf100 menor só porque cristaliza menos -- usar um denominador "
            "menor para LDPE dobraria o erro de cristalinidade. Não há "
            "entrada separada para LDPE por esse motivo."
        ),
    ),
    "PP": PolymerEnthalpy(
        key="PP",
        display_name="Polipropileno isotático (PP-α)",
        names=("pp", "polypropylene", "polipropileno", "ipp", "hpp"),
        references=(
            CrystallinityReference(
                207.0,
                "H.-S. Bu, S. Z. D. Cheng, B. Wunderlich, 'Addendum to the "
                "thermal properties of polypropylene', Makromol. Chem., Rapid "
                "Commun. 9 (1988) 75-77. doi:10.1002/marc.1988.030090205",
                crystal_form="α (monoclínica)",
                confidence="verified",
            ),
            CrystallinityReference(
                209.0,
                "J. Brandrup et al., Polymer Handbook, 4th ed., Wiley, 1999.",
                crystal_form="α (monoclínica)",
                confidence="compilation",
            ),
        ),
    ),
    "PP-BETA": PolymerEnthalpy(
        key="PP-BETA",
        display_name="Polipropileno β (PP-β)",
        names=("pp-beta", "ppb", "beta-pp"),
        references=(
            CrystallinityReference(
                168.0,
                "Polymer Handbook, 4th ed.; a forma β do PP tem ΔHf100 menor "
                "que a α e os valores publicados dispersam (168-177 J/g).",
                crystal_form="β (hexagonal)",
                confidence="divergent",
                note=(
                    "A forma β é menos padronizada que a α. Usar o valor da α "
                    "para uma amostra de β subestima a cristalinidade em ~20 %."
                ),
            ),
        ),
    ),
    "PET": PolymerEnthalpy(
        key="PET",
        display_name="Poli(tereftalato de etileno) (PET)",
        names=("pet", "polyethylene terephthalate", "tereftalato"),
        references=(
            CrystallinityReference(
                140.0,
                "H. W. Starkweather, P. Zoller, G. A. Jones, 'The heat of "
                "fusion of poly(ethylene terephthalate)', J. Polym. Sci. "
                "Polym. Phys. 21 (1983) 295-299. doi:10.1002/pol.1983.180210211",
                crystal_form="triclínica",
                confidence="verified",
            ),
            CrystallinityReference(
                125.0,
                "R. C. Roberts, 'Poly(ethylene terephthalate) I - Heat of "
                "fusion', Polymer 10 (1969) 113-116. "
                "doi:10.1016/0032-3861(69)90014-7",
                crystal_form="triclínica",
                confidence="divergent",
                note="Valor anterior, ainda citado; difere do de 1983.",
            ),
        ),
    ),
    "PA6": PolymerEnthalpy(
        key="PA6",
        display_name="Poliamida 6 / Nylon 6 (PA6)",
        names=("pa6", "nylon6", "nylon-6", "polyamide 6", "poliamida 6"),
        references=(
            CrystallinityReference(
                230.0,
                "B. Wunderlich, Macromolecular Physics, Vol. 3: Crystal "
                "Melting, Academic Press, 1980; compilado em Polymer Handbook, "
                "4th ed.",
                crystal_form="α (monoclínica)",
                confidence="compilation",
                note="A forma γ tem ΔHf100 da ordem de 239 J/g.",
            ),
        ),
    ),
    "PA66": PolymerEnthalpy(
        key="PA66",
        display_name="Poliamida 66 / Nylon 66 (PA66)",
        names=("pa66", "nylon66", "nylon-66", "polyamide 66"),
        references=(
            CrystallinityReference(
                255.0,
                "B. Wunderlich, Macromolecular Physics, Vol. 3, Academic "
                "Press, 1980; Polymer Handbook, 4th ed. Algumas compilações "
                "listam 280 J/g.",
                crystal_form="α (triclínica)",
                confidence="divergent",
            ),
        ),
    ),
    "PLA": PolymerEnthalpy(
        key="PLA",
        display_name="Ácido poliláctico (PLA / PLLA)",
        names=("pla", "plla", "pdla", "poly(lactic acid)", "polilactida", "polylactide"),
        references=(
            CrystallinityReference(
                93.0,
                "E. W. Fischer, H. J. Sterzel, G. Wegner, 'Investigation of the "
                "structure of solution grown crystals of lactide copolymers', "
                "Kolloid-Z. Z. Polym. 251 (1973) 980-990. "
                "doi:10.1007/bf01498927",
                crystal_form="α (hélice 10/3)",
                confidence="verified",
                note=(
                    "Valor padrão de literatura para PLLA, amplamente citado. "
                    "O PLA racêmico (PDLLA) é amorfo e não tem ΔHf100 aplicável."
                ),
            ),
            CrystallinityReference(
                106.0,
                "Valor alternativo citado para a forma α do PLLA; ver "
                "Miyata & Masuko, Polymer 39 (1998) 5515.",
                crystal_form="α",
                confidence="divergent",
            ),
        ),
    ),
    "PBT": PolymerEnthalpy(
        key="PBT",
        display_name="Poli(tereftalato de butileno) (PBT)",
        names=("pbt", "polybutylene terephthalate"),
        references=(
            CrystallinityReference(
                145.0,
                "Polymer Handbook, 4th ed.; P. Campbell, R. A. Pethrick, "
                "J. R. White, Polymer Characterization, Chapman & Hall, 1989.",
                crystal_form="α",
                confidence="compilation",
            ),
        ),
    ),
    "PEEK": PolymerEnthalpy(
        key="PEEK",
        display_name="Poli(éter-éter-cetona) (PEEK)",
        names=("peek", "poly(ether ether ketone)"),
        references=(
            CrystallinityReference(
                130.0,
                "D. J. Blundell, B. N. Osborn, 'The morphology of poly(aryl-"
                "ether-ether-ketone)', Polymer 24 (1983) 953-958. "
                "doi:10.1016/0032-3861(83)90144-1",
                crystal_form="ortorrômbica",
                confidence="verified",
            ),
        ),
    ),
    "PCL": PolymerEnthalpy(
        key="PCL",
        display_name="Policaprolactona (PCL)",
        names=("pcl", "polycaprolactone", "policaprolactona"),
        references=(
            CrystallinityReference(
                139.3,
                "Polymer Handbook, 4th ed.; Physical Properties of Polymers "
                "Handbook, 2nd ed. (J. E. Mark, ed., Springer, 2007).",
                crystal_form="ortorrômbica",
                confidence="compilation",
            ),
        ),
    ),
    "PHB": PolymerEnthalpy(
        key="PHB",
        display_name="Poli(hidroxibutirato) (PHB / PHA)",
        names=("phb", "pha", "polyhydroxybutyrate", "poli-hidroxibutirato"),
        references=(
            CrystallinityReference(
                146.0,
                "P. J. Barham, A. Keller, E. L. Otun, P. A. Holmes, "
                "'Crystallization and morphology of a bacterial thermoplastic: "
                "poly-3-hydroxybutyrate', J. Mater. Sci. 19 (1984) 2781-2794. "
                "doi:10.1007/bf01026954",
                crystal_form="ortorrômbica",
                confidence="verified",
            ),
        ),
    ),
    "PHBV": PolymerEnthalpy(
        key="PHBV",
        display_name="Poli(3-hidroxibutirato-co-3-hidroxivalerato) (PHBV)",
        names=("phbv", "phv"),
        references=(
            CrystallinityReference(
                109.0,
                "Copolímero: o valor depende da fração de hidroxivalerato. "
                "Barham et al. (1984) para o PHB puro (146 J/g) é o limite "
                "superior; a literatura reporta 100-130 J/g conforme a "
                "composição.",
                crystal_form="ortorrômbica (HB)",
                confidence="divergent",
            ),
        ),
        copolymer=True,
        note=(
            "Sem ΔHf100 único: o valor cai com o teor de HV. Preencha a "
            "composição e use o valor correspondente."
        ),
    ),
    "PVDF": PolymerEnthalpy(
        key="PVDF",
        display_name="Poli(fluoreto de vinilideno) (PVDF)",
        names=("pvdf", "polyvinylidene fluoride"),
        references=(
            CrystallinityReference(
                104.7,
                "Polymer Handbook, 4th ed.; K. Nakagawa, Y. Ishida, "
                "Kolloid-Z. Z. Polym. 251 (1973) 103. "
                "doi:10.1007/bf01498933",
                crystal_form="α",
                confidence="compilation",
            ),
        ),
    ),
    "PEO": PolymerEnthalpy(
        key="PEO",
        display_name="Poli(óxido de etileno) (PEO / PEG)",
        names=("peo", "peg", "polyethylene oxide", "polyethylene glycol"),
        references=(
            CrystallinityReference(
                196.4,
                "Polymer Handbook, 4th ed.; Physical Properties of Polymers "
                "Handbook, 2nd ed.",
                crystal_form="monoclínica",
                confidence="compilation",
                note="Algumas compilações listam 213 J/g; a divergência é de refino de valor.",
            ),
        ),
    ),
    "PVA": PolymerEnthalpy(
        key="PVA",
        display_name="Poli(álcool vinílico) (PVA / PVOH)",
        names=("pva", "pvoh", "polyvinyl alcohol", "pval"),
        references=(
            CrystallinityReference(
                138.6,
                "Polymer Handbook, 4th ed. A literatura reporta 138-161 J/g "
                "conforme a regularidade estereoquímica.",
                crystal_form="monoclínica",
                confidence="compilation",
            ),
        ),
    ),
    "PTFE": PolymerEnthalpy(
        key="PTFE",
        display_name="Politetrafluoroetileno (PTFE)",
        names=("ptfe", "teflon", "polytetrafluoroethylene"),
        references=(
            CrystallinityReference(
                82.0,
                "B. Wunderlich, Macromolecular Physics, Vol. 3, Academic "
                "Press, 1980; Polymer Handbook, 4th ed.",
                confidence="compilation",
                note="Compilações divergem entre 69 e 82 J/g.",
            ),
        ),
    ),
    "PS-ISO": PolymerEnthalpy(
        key="PS-ISO",
        display_name="Poliestireno isotático (PS-i)",
        names=("ps-iso", "isotactic polystyrene", "psi"),
        references=(
            CrystallinityReference(
                207.0,
                "B. Wunderlich, Macromolecular Physics, Vol. 3, Academic "
                "Press, 1980.",
                crystal_form="isotática",
                confidence="compilation",
            ),
        ),
    ),
    "PS": PolymerEnthalpy(
        key="PS",
        display_name="Poliestireno atático (PS, GPPS/HIPS)",
        names=("ps", "polystyrene", "poliestireno", "gpps", "hips", "sbr"),
        references=(),
        note=(
            "O poliestireno atático é amorfo: não cristaliza, e a "
            "cristalinidade por DSC não se aplica. Um ΔHm medido nesta "
            "amostra é de aditivo ou de outro componente da blenda, não do "
            "PS. Não há ΔHf100 a informar -- e o valor isotático (207 J/g, "
            "PS-ISO) não vale aqui."
        ),
    ),
    "PBAT": PolymerEnthalpy(
        key="PBAT",
        display_name="Poli(adipato-co-tereftalato de butileno) (PBAT)",
        names=("pbat", "ecoflex"),
        references=(
            CrystallinityReference(
                114.0,
                "Copolímero: a literatura reporta 114-144 J/g conforme a razão "
                "BT/BA. Sem valor único acordado.",
                confidence="divergent",
            ),
        ),
        copolymer=True,
        note=(
            "Copolímero aleatório: não existe ΔHf100 universal. O número "
            "depende da fração de tereftalato."
        ),
    ),
}


#: Nomes alternativos, normalizados, que resolvem para uma chave do banco.
#: Mais longo primeiro na consulta, para que ``pa66`` não caia em ``pa6``.
_ALIASES: dict[str, str] = {
    "pe": "PE",
    "polyethylene": "PE",
    "polietileno": "PE",
    "hdpe": "PE",
    "ldpe": "PE",
    "lldpe": "PE",
    "pp": "PP",
    "polypropylene": "PP",
    "polipropileno": "PP",
    "ipp": "PP",
    "pp-beta": "PP-BETA",
    "ppb": "PP-BETA",
    "pet": "PET",
    "polyethylene terephthalate": "PET",
    "pa6": "PA6",
    "nylon6": "PA6",
    "nylon-6": "PA6",
    "pa66": "PA66",
    "nylon66": "PA66",
    "nylon-66": "PA66",
    "pla": "PLA",
    "plla": "PLA",
    "pdla": "PLA",
    "polylactide": "PLA",
    "pbt": "PBT",
    "peek": "PEEK",
    "pcl": "PCL",
    "phb": "PHB",
    "pha": "PHB",
    "phbv": "PHBV",
    "pvdf": "PVDF",
    "peo": "PEO",
    "peg": "PEO",
    "pva": "PVA",
    "pvoh": "PVA",
    "ptfe": "PTFE",
    "teflon": "PTFE",
    "ps-iso": "PS-ISO",
    "pbat": "PBAT",
    "ps": "PS",
    "gpps": "PS",
    "hips": "PS",
    "polystyrene": "PS",
    "poliestireno": "PS",
}


def _normalise(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def lookup(name: str | None) -> PolymerEnthalpy | None:
    """
    Encontra a entrada do banco para um nome de polímero ou de amostra.

    A busca é tolerante na mesma medida que ``reference.resolve``: aceita o
    nome exato e o nome com um qualificador separado por ``-`` ou ``_``
    (``PE-NEW``, ``PLA1-AR``). Devolve ``None`` quando não reconhece, em vez
    de escolher o mais parecido -- um ΔHf100 do polímero errado produz uma
    cristalinidade plausível e errada, que é o único resultado pior que não
    responder.
    """
    if not name:
        return None
    cleaned = _normalise(name)
    for ext in (".tri", ".txt", ".csv", ".dat", ".jws"):
        if cleaned.endswith(ext):
            cleaned = cleaned[: -len(ext)]
    cleaned = cleaned.strip("- ")

    # Um nome de arquivo costuma começar pelo prefixo do instrumento ou da
    # técnica ("JASCO_LDPE-SBC-818", "FTIR_PE-1", "DSC_PLA"), que não é parte
    # do nome do polímero. Removê-lo é o que faz a detecção funcionar a partir
    # do nome do arquivo, que é como o usuário costuma selecionar o material.
    #
    # Separar também no hífen é o que torna isto útil: ``_normalise`` já
    # converteu ``_`` em ``-``, então ``jasco-ldpe-sbc-818`` é um token único
    # se só se dividir por ``_``. Dividir por hífen dá
    # ``['jasco','ldpe','sbc','818']`` e o ``ldpe`` é encontrado.
    tokens = [t for t in re.split(r"[-_\s]+", cleaned) if t]
    if len(tokens) > 1:
        for tok in tokens:
            if tok in _ALIASES:
                return ENTHALPY_DB.get(_ALIASES[tok])

    # Nome exato (incluindo as chaves de alias explícitas).
    if cleaned in _ALIASES:
        return ENTHALPY_DB.get(_ALIASES[cleaned])
    for entry in ENTHALPY_DB.values():
        if cleaned == entry.key.lower() or cleaned in entry.names:
            return entry

    # Qualificador separado: "PE-NEW", "PLA1-AR", "PP3-CRYO".
    head = cleaned.replace("-", " ").split()[0] if cleaned else ""
    candidates: list[str] = []
    for tok in (cleaned, head):
        if tok and tok not in candidates:
            candidates.append(tok)
    # Um índice de corrida no fim ("pla1", "abs2") é comum em export.
    stripped = head.rstrip("0123456789")
    if stripped and stripped != head:
        candidates.append(stripped)
    for tok in candidates:
        if tok in _ALIASES:
            return ENTHALPY_DB.get(_ALIASES[tok])
    return None


def options() -> list[dict[str, object]]:
    """
    A lista para o menu do formulário: valor, forma cristalina e citação.

    Devolve o valor **com a fonte junto**, porque é isso que o campo precisa
    carregar. Um menu que entrega só o número convida a usá-lo sem a citação,
    e o número sozinho não é verificável.
    """
    out: list[dict[str, object]] = []
    for entry in ENTHALPY_DB.values():
        prim = entry.primary
        out.append(
            {
                "key": entry.key,
                "label": entry.display_name,
                "names": list(entry.names),
                "value_J_g": prim.value_J_g if prim else None,
                "crystal_form": prim.crystal_form if prim else None,
                "source": prim.source if prim else None,
                "confidence": prim.confidence if prim else None,
                "copolymer": entry.copolymer,
                "note": entry.note,
                "alternatives": [
                    {
                        "value_J_g": r.value_J_g,
                        "source": r.source,
                        "crystal_form": r.crystal_form,
                        "confidence": r.confidence,
                        "note": r.note,
                    }
                    for r in entry.references[1:]
                ],
            }
        )
    return sorted(out, key=lambda d: str(d["key"]))
