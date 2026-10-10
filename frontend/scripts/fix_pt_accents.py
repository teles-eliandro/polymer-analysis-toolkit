#!/usr/bin/env python3
"""Restaura os acentos que faltam nos valores portugueses do dicionario.

Por que um mapeamento explicito e nao uma substituicao automatica: em portugues
"e" pode ser a conjuncao (e) ou o verbo (e com acento), e "esta" pode ser o
demonstrativo (esta) ou o verbo (esta com acento). Nenhuma heuristica acerta
esses casos -- so a leitura. Entao cada par abaixo foi lido e decidido um a um,
e o script falha se algum nao casar exatamente uma vez.

Idempotente: rodar de novo reporta 0 alteracoes.
"""
from __future__ import annotations

import sys

PATH = "src/i18n/I18nContext.jsx"

# (forma atual, forma correta). Cada uma tem de ocorrer exatamente uma vez.
FIXES: list[tuple[str, str]] = [
    (
        "Modulo de elasticidade, a inclinacao da reta ajustada, em MPa.",
        "Módulo de elasticidade, a inclinação da reta ajustada, em MPa.",
    ),
    ("Deformacao do ponto i dentro da janela ajustada.", "Deformação do ponto i dentro da janela ajustada."),
    ("Tensao do ponto i dentro da janela ajustada, em MPa.", "Tensão do ponto i dentro da janela ajustada, em MPa."),
    (
        "Energia na ruptura por unidade de volume, a area sob a curva, em MJ/m3.",
        "Energia na ruptura por unidade de volume, a área sob a curva, em MJ/m3.",
    ),
    ("Tensao de engenharia, em MPa.", "Tensão de engenharia, em MPa."),
    ("Deformacao de engenharia, adimensional.", "Deformação de engenharia, adimensional."),
    (
        "Massa molar lida na curva de calibracao no volume de eluicao dado.",
        "Massa molar lida na curva de calibração no volume de eluição dado.",
    ),
    (
        "Fracao em massa na fatia da distribuicao centrada em M.",
        "Fração em massa na fatia da distribuição centrada em M.",
    ),
    ("Largura da distribuicao log-normal em ln M.", "Largura da distribuição log-normal em ln M."),
    ("Media de ln M da distribuicao.", "Média de ln M da distribuição."),
    (
        "Modulo de perda, a resposta viscosa (dissipadora de energia).",
        "Módulo de perda, a resposta viscosa (dissipadora de energia).",
    ),
    (
        "Modulo de armazenamento, a resposta elastica (acumuladora de energia).",
        "Módulo de armazenamento, a resposta elástica (acumuladora de energia).",
    ),
    ("Modulo de armazenamento no ponto de gel.", "Módulo de armazenamento no ponto de gel."),
    ("Modulo de perda no ponto de gel.", "Módulo de perda no ponto de gel."),
    ("Modulo de armazenamento, em Pa.", "Módulo de armazenamento, em Pa."),
    ("Modulo de perda, em Pa.", "Módulo de perda, em Pa."),
    (
        "Area das reflexoes cristalinas acima do fundo amorfo.",
        "Área das reflexões cristalinas acima do fundo amorfo.",
    ),
    ("Area total do padrao na mesma faixa angular.", "Área total do padrão na mesma faixa angular."),
    ("modulo de tracao (MPa)", "módulo de tração (MPa)"),
    (
        "tensao de engenharia (MPa), forca sobre a seccao original",
        "tensão de engenharia (MPa), força sobre a seção original",
    ),
    ("deformacao de engenharia (%)", "deformação de engenharia (%)"),
    (
        "O modulo so e comparavel entre amostras ajustadas na mesma faixa de "
        "deformacao. Um modulo ajustado de 0 a 5 % e sistematicamente menor que "
        "um ajustado de 0 a 0,5 %, porque a curva encurva ao escoar. A faixa "
        "usada e reportada junto com o resultado.",
        "O módulo só é comparável entre amostras ajustadas na mesma faixa de "
        "deformação. Um módulo ajustado de 0 a 5 % é sistematicamente menor que "
        "um ajustado de 0 a 0,5 %, porque a curva encurva ao escoar. A faixa "
        "usada é reportada junto com o resultado.",
    ),
    (
        "Minimos quadrados na janela de deformacao, detectada pela maior "
        "inclinacao local ou informada por voce. Uma janela que comece depois "
        "da regiao de acomodacao deve ser escolhida a olho; a deteccao "
        "automatica pode cair no ombro de escoamento numa amostra ductil.",
        "Mínimos quadrados na janela de deformação, detectada pela maior "
        "inclinação local ou informada por você. Uma janela que comece depois "
        "da região de acomodação deve ser escolhida a olho; a detecção "
        "automática pode cair no ombro de escoamento numa amostra dúctil.",
    ),
    ("Tensao e deformacao", "Tensão e deformação"),
    ("area da seccao antes do ensaio (mm2)", "área da seção antes do ensaio (mm2)"),
    ("comprimento util antes do ensaio (mm)", "comprimento útil antes do ensaio (mm)"),
    (
        "Sao valores de engenharia do inicio ao fim: a area original e usada e "
        "nunca atualizada durante o ensaio. A tensao real e maior numa amostra "
        "que estrica, entao a resistencia a tracao reportada aqui e conservadora.",
        "São valores de engenharia do início ao fim: a área original é usada e "
        "nunca atualizada durante o ensaio. A tensão real é maior numa amostra "
        "que estrica, então a resistência à tração reportada aqui é conservadora.",
    ),
    (
        "Area trapezoidal sob a curva fornecida. Se o ensaio foi interrompido "
        "antes da ruptura, o valor e um limite inferior e a ferramenta o reporta "
        "sem saber a diferenca.",
        "Área trapezoidal sob a curva fornecida. Se o ensaio foi interrompido "
        "antes da ruptura, o valor é um limite inferior e a ferramenta o reporta "
        "sem saber a diferença.",
    ),
    ("Modulos de armazenamento e de perda", "Módulos de armazenamento e de perda"),
    ("modulo de armazenamento (Pa), a resposta elastica", "módulo de armazenamento (Pa), a resposta elástica"),
    ("modulo de perda (Pa), a resposta viscosa", "módulo de perda (Pa), a resposta viscosa"),
    ("defasagem entre tensao e deformacao (rad)", "defasagem entre tensão e deformação (rad)"),
    (
        "Valido apenas dentro da regiao viscoelastica linear, onde os modulos "
        "nao dependem da amplitude de deformacao. Uma varredura fora dela "
        "reporta um modulo de armazenamento menor que parece mudanca de material "
        "e nao e.",
        "Válido apenas dentro da região viscoelástica linear, onde os módulos "
        "não dependem da amplitude de deformação. Uma varredura fora dela "
        "reporta um módulo de armazenamento menor que parece mudança de material "
        "e não é.",
    ),
    (
        "Acima de 1 a amostra dissipa mais do que armazena. Num fundido isso e "
        "normal; numa rede reticulada indica que o ensaio esta acima do ponto de "
        "gel ou que a rede nao esta totalmente formada.",
        "Acima de 1 a amostra dissipa mais do que armazena. Num fundido isso é "
        "normal; numa rede reticulada indica que o ensaio está acima do ponto de "
        "gel ou que a rede não está totalmente formada.",
    ),
    (
        "Reportado apenas quando os dois modulos permanecem dentro da tolerancia "
        "um do outro enquanto o modulo de armazenamento excede o de perda. A "
        "tolerancia importa: um teste de cruzamento simples dispara com ruido "
        "numa varredura ruidosa, entao os dois modulos precisam concordar em "
        "varios pontos consecutivos.",
        "Reportado apenas quando os dois módulos permanecem dentro da tolerância "
        "um do outro enquanto o módulo de armazenamento excede o de perda. A "
        "tolerância importa: um teste de cruzamento simples dispara com ruído "
        "numa varredura ruidosa, então os dois módulos precisam concordar em "
        "vários pontos consecutivos.",
    ),
    ("Frequencia de cruzamento", "Frequência de cruzamento"),
    (
        "A frequencia onde o fundido deixa de se comportar elasticamente. Ela "
        "desloca com a temperatura, entao um cruzamento citado sem a temperatura "
        "nao e reproduzivel.",
        "A frequência onde o fundido deixa de se comportar elasticamente. Ela "
        "desloca com a temperatura, então um cruzamento citado sem a temperatura "
        "não é reproduzível.",
    ),
    ("Medias numerica e ponderal", "Médias numérica e ponderal"),
    (
        "Mn e a media simples entre cadeias, Mw pondera cada cadeia pela sua "
        "massa. Mw e sempre maior ou igual a Mn; se um resultado violar isso, o "
        "erro esta nos dados ou na aritmetica, nao no polimero.",
        "Mn é a média simples entre cadeias, Mw pondera cada cadeia pela sua "
        "massa. Mw é sempre maior ou igual a Mn; se um resultado violar isso, o "
        "erro está nos dados ou na aritmética, não no polímero.",
    ),
    (
        "Uma dispersidade de 1,0 significa que todas as cadeias tem o mesmo "
        "comprimento, o que nenhuma polimerizacao real atinge: o minimo teorico "
        "para uma polimerizacao anionica viva e cerca de 1,02. Valores proximos "
        "de 2 indicam mecanismo de etapas ou dominado por transferencia de cadeia.",
        "Uma dispersidade de 1,0 significa que todas as cadeias têm o mesmo "
        "comprimento, o que nenhuma polimerização real atinge: o mínimo teórico "
        "para uma polimerização aniônica viva é cerca de 1,02. Valores próximos "
        "de 2 indicam mecanismo de etapas ou dominado por transferência de cadeia.",
    ),
    (
        "A media z e a usada em espalhamento de luz e em viscosimetria, entao "
        "compara-la com o Mw do mesmo traco verifica a forma da distribuicao, "
        "nao apenas a sua posicao.",
        "A média z é a usada em espalhamento de luz e em viscosimetria, então "
        "compará-la com o Mw do mesmo traço verifica a forma da distribuição, "
        "não apenas a sua posição.",
    ),
    ("constante especifica do polimero, solvente e temperatura", "constante específica do polímero, solvente e temperatura"),
    (
        "A curva de calibracao converte volume de eluicao em massa molar usando "
        "padroes de outro polimero, a menos que os padroes sejam do mesmo "
        "material da amostra. Por isso um resultado de SEC convencional e uma "
        "massa molar relativa, e por isso o padrao de calibracao precisa ser "
        "reportado.",
        "A curva de calibração converte volume de eluição em massa molar usando "
        "padrões de outro polímero, a menos que os padrões sejam do mesmo "
        "material da amostra. Por isso um resultado de SEC convencional é uma "
        "massa molar relativa, e por isso o padrão de calibração precisa ser "
        "reportado.",
    ),
    ("Distribuicao log-normal", "Distribuição log-normal"),
    (
        "Um modelo, nao uma medida. E mostrada para comparar a forma de uma "
        "distribuicao medida com uma idealizada, e presume que o traco nao tem "
        "alargamento de coluna, que alarga todo traco real.",
        "Um modelo, não uma medida. É mostrada para comparar a forma de uma "
        "distribuição medida com uma idealizada, e presume que o traço não tem "
        "alargamento de coluna, que alarga todo traço real.",
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
            # Idempotencia: a forma nova ja presente significa que ja foi feito.
            if text.count(new) == 1:
                continue
            problems.append(f"NAO ENCONTRADO (nem a forma nova): {old[:70]!r}")
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
