"""
Leitura de arquivo de instrumento: colunas, unidades, metadados.

O arquivo de referência é um DSC real de LDPE, exportado por um NETZSCH DSC
204F1 Phoenix. Ele foi escolhido como fixture porque é o caso que o parser
ingênuo erra em quatro frentes ao mesmo tempo:

* quatro colunas, e a segunda é **tempo**, não o sinal;
* separador e decimal **declarados no cabeçalho** (``SEMICOLON``, ``POINT``);
* ``#EXO:-1``: o eixo está com exotérmico para cima, o inverso da convenção
  que a análise assume;
* ``#RANGE:-30°C/10,0(K/min)/200°C``: a taxa de aquecimento está no método,
  não nos dados -- e sem ela o ΔHm não tem unidade física.

O arquivo também é latin-1 e tem BOM, então ``np.loadtxt`` falha nele com
``UnicodeDecodeError``. É o comportamento correto do numpy; é a razão de
existir do decodificador.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.core.thermal import analyse_dsc
from app.core.trace_io import (
    TraceImportError,
    read_trace_file,
    resolve_trace,
)

FIXTURES = Path(__file__).parent / "fixtures"
NETZSCH = FIXTURES / "netzsch_dsc_ldpe.txt"


class TestReadingTheFile:
    def test_the_header_metadata_is_recovered(self):
        tf = read_trace_file(NETZSCH)
        assert tf.metadata["mtype"] == "DSC"
        assert tf.metadata["instrument"] == "NETZSCH DSC 204F1 Phoenix"
        assert tf.metadata["separator"] == "SEMICOLON"
        assert tf.metadata["sample"] == "1-90"

    def test_metadata_that_the_analysis_needs_is_resolved(self):
        """
        Taxa de aquecimento, massa e nome saem do cabecalho.

        A taxa e o caso importante: sem ela o modulo reporta dHm mas nao
        converte para J/g, porque a conversao depende dela.
        """
        tf = read_trace_file(NETZSCH)
        assert tf.heating_rate == 10.0, "taxa deveria vir de '#RANGE:...10,0(K/min)'"
        assert tf.sample_mass_mg == 4.98
        assert tf.sample_name == "1-90"

    def test_the_exothermic_convention_is_read(self):
        """
        ``#EXO:-1`` significa exotermico para baixo -- a convencao correta.

        O valor numerico e ambiguo entre fabricantes, entao o teste fixa
        apenas o que este arquivo declara. Um ``#EXO:1`` seria lido como
        'up' e dispararia a inversao.
        """
        tf = read_trace_file(NETZSCH)
        assert tf.exothermic_direction == "down"

    def test_every_column_gets_its_own_role(self):
        """
        As quatro colunas sao identificadas sem confusao.

        Este e o teste que falhava com a lista de tokens anterior: o token
        ``"s"`` (de segundos) fazia ``DSC/(mW/mg)`` e ``Sensit./(uV/mW)``
        casarem com *time*, porque ambos contem a letra s. O eixo y saia do
        arquivo errado e nada indicava o erro.
        """
        tf = read_trace_file(NETZSCH)
        roles = [c.role for c in tf.columns]
        assert roles == ["temperature", "time", "heat_flow", "sensitivity"], (
            f"papéis resolvidos como {roles}; esperado temperatura, tempo, "
            "fluxo de calor e sensibilidade"
        )

    def test_the_units_are_extracted_from_the_labels(self):
        tf = read_trace_file(NETZSCH)
        by_role = {c.role: c for c in tf.columns}
        assert by_role["temperature"].unit == "°c"
        assert by_role["heat_flow"].unit == "mw/mg"

    def test_latin1_and_bom_do_not_break_the_read(self):
        """
        O arquivo e latin-1 com BOM; o ``°`` e um byte unico.

        Uma decodificacao UTF-8 com ``errors='replace'`` transformaria o
        ``°C`` num caractere de substituicao e o rotulo de temperatura
        deixaria de casar.
        """
        with pytest.raises(UnicodeDecodeError):
            np.loadtxt(NETZSCH, delimiter=";", skiprows=33, usecols=(0, 2))
        tf = read_trace_file(NETZSCH)
        assert tf.column("temperature") is not None


class TestResolvingToATrace:
    def test_the_two_series_come_out_in_the_right_units(self):
        tf = read_trace_file(NETZSCH)
        rt = resolve_trace(tf, "temperature", "heat_flow", invert_for_endothermic_up=True)

        assert len(rt.x) == len(rt.y) == 186
        assert rt.x_unit == "C"
        assert rt.y_unit == "W/g"
        # 1 mW/mg e numericamente 1 W/g, entao a amplitude tem de ser a mesma
        # do arquivo, nao mil vezes maior nem menor.
        assert 1.5 < max(rt.y) < 1.8

    def test_the_signal_is_inverted_when_the_header_says_exothermic_up(self):
        """
        A inversao e a diferenca entre Tm e uma temperatura sem sentido.

        Medido neste arquivo: sem inverter, o modulo reporta
        Tg = 116.8 C num polimero cuja Tg esta muito abaixo da faixa medida;
        com a inversao -- que o ``#EXO`` exige -- o pico de fusao sai na
        posicao certa.
        """
        tf = read_trace_file(NETZSCH)
        inverted = resolve_trace(tf, "temperature", "heat_flow", invert_for_endothermic_up=True)

        # O pico tem de estar para cima depois da inversao, porque fusao e
        # endotermica na convencao da analise.
        assert max(inverted.y) > abs(min(inverted.y)) * 10

        r_inv = analyse_dsc(inverted.x, inverted.y, heating_rate=10.0)
        assert r_inv.Tm is not None
        assert 100.0 < r_inv.Tm < 115.0, (
            f"Tm em {r_inv.Tm:.1f} C; para LDPE o esperado e 105-115 C"
        )

    def test_a_missing_column_is_named_in_the_error(self):
        """A mensagem de erro tem de dizer o que faltou e o que existe."""
        tf = read_trace_file(NETZSCH)
        with pytest.raises(TraceImportError) as exc:
            resolve_trace(tf, "temperature", "stress")
        msg = str(exc.value)
        assert "tensão" in msg
        assert "Temp./°C" in msg, "a mensagem deve listar as colunas disponíveis"

    def test_the_raw_file_cannot_be_read_by_assuming_two_columns(self):
        """
        A prova de que o problema existe: o parser ingenuo le tempo como sinal.

        Tomando a coluna 1 (tempo) como se fosse o sinal, o resultado nao tem
        relacao com um DSC: e uma reta de 91 a 114 'W/g'.
        """
        tf = read_trace_file(NETZSCH)
        wrong = tf.column("time")
        right = tf.column("heat_flow")
        assert wrong is not None and right is not None
        wrong_range = max(wrong.values) - min(wrong.values)
        right_range = max(right.values) - min(right.values)
        assert wrong_range > 20, "a coluna de tempo varia dezenas de unidades"
        assert right_range < 2, "o sinal de DSC varia menos de 2 W/g"
