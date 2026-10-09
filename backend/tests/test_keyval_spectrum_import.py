"""
Espectros cujos eixos são declarados no cabeçalho, não nas colunas.

O caso que originou estes testes é o ``FTIR_spectra_LDPE-SBC-818_0_2.txt`` de
um JASCO FT/IR-4600: o arquivo é íntegro, os eixos estão declarados
(``XUNITS 1/CM``, ``YUNITS ABSORBANCE``), e mesmo assim o leitor recusava --
porque procurava ``#CHAVE:valor`` e tomava a linha ``TITLE<TAB>ldpe sbc 818 0``
por cabeçalho de colunas. O resultado era uma "coluna" chamada TITLE, nenhum
eixo com papel, e a mensagem "não encontrei a coluna de número de onda".

Os testes usam o arquivo real (78380 bytes, 3736 pontos) e o CSV real do
PerkinElmer Spectrum, para que a leitura seja verificada contra o que o
instrumento escreve, não contra uma imitação.

Validação científica embutida: os picos detectados no espectro de LDPE são
comparados com as bandas conhecidas do polietileno (2915 e 2848 cm-1 de
estiramento CH2, 1470 de deformação, 717 de rocking). Um parser que casasse o
eixo errado devolveria picos em posições físicas implausíveis, então esta
verificação pega o erro que o teste de estrutura sozinho não pegaria.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.structure import analyse_ftir
from app.core.trace_io import TraceImportError, read_trace_file, resolve_trace

FIXTURES = Path(__file__).parent / "fixtures"


class TestJascoFtir:
    """O arquivo JASCO real que o leitor recusava."""

    path = FIXTURES / "jasco_ftir_ldpe.txt"

    def test_header_is_read_as_metadata(self) -> None:
        tf = read_trace_file(self.path)
        # O cabeçalho CHAVE<TAB>valor tem 17 chaves úteis neste arquivo.
        assert len(tf.metadata) >= 15
        assert tf.metadata["origin"] == "JASCO"
        assert tf.metadata["xunits"] == "1/CM"
        assert tf.metadata["yunits"] == "ABSORBANCE"
        assert tf.metadata["npoints"] == "3736"

    def test_sample_name_from_title(self) -> None:
        # TITLE é onde o JASCO escreve a amostra. Sem isto, a resolução de
        # polímero do PAT não tem o que resolver.
        assert read_trace_file(self.path).sample_name == "ldpe sbc 818 0"

    def test_axes_carry_role_and_unit(self) -> None:
        tf = read_trace_file(self.path)
        assert len(tf.columns) == 2
        x, y = tf.columns
        assert x.role == "wavenumber"
        assert x.unit == "cm-1"
        assert x.factor == 1.0
        assert y.role == "absorbance"
        assert y.unit == "au"
        assert y.factor == 1.0
        # NPOINTS declara 3736 e é o que o arquivo realmente tem.
        assert len(x.values) == 3736
        assert len(y.values) == 3736

    def test_comma_decimals_are_parsed(self) -> None:
        # Os dados usam vírgula decimal ("399,1927"), e TAB como separador de
        # campo. Ler a vírgula como separador produziria duas colunas de
        # números falsos.
        tf = read_trace_file(self.path)
        assert tf.columns[0].values[0] == pytest.approx(399.1927, abs=1e-4)
        assert tf.columns[1].values[0] == pytest.approx(0.0104689, abs=1e-7)

    def test_resolves_to_wavenumber_and_absorbance(self) -> None:
        r = resolve_trace(read_trace_file(self.path), "wavenumber", "absorbance")
        assert len(r.x) == 3736
        assert r.x_unit == "cm-1"
        assert r.y_unit == "au"
        # O eixo x vem crescente depois da resolução (o arquivo traz 399 ->
        # 4000, então não precisa inverter).
        assert r.x[0] == pytest.approx(399.19, abs=0.01)
        assert r.x[-1] == pytest.approx(4000.60, abs=0.01)

    def test_detected_bands_are_polyethylene(self) -> None:
        """
        As bandas do LDPE, verificadas contra a literatura.

        CH2 estiramento assimétrico ~2915, simétrico ~2848, deformação
        (scissoring) ~1470, rocking ~717 cm-1. Se o leitor tivesse casado o
        eixo errado, ou lido tempo em lugar de número de onda, estes picos não
        apareceriam nestas posições.
        """
        r = resolve_trace(read_trace_file(self.path), "wavenumber", "absorbance")
        res = analyse_ftir(r.x, r.y)
        peaks = set(round(p) for p in res.detected_peaks)
        for expected in (2915, 2848, 1470, 717):
            nearest = min(peaks, key=lambda p: abs(p - expected))
            assert abs(nearest - expected) <= 6, (
                f"esperava uma banda perto de {expected} cm-1; "
                f"a mais próxima foi {nearest} cm-1 (bandas: {sorted(peaks)})"
            )


class TestPerkinElmerCsv:
    """O CSV do PerkinElmer Spectrum, que traz as unidades no cabeçalho."""

    path = FIXTURES / "perkinelmer_ftir_pe.csv"

    def test_sample_name_from_preamble(self) -> None:
        # A primeira linha é "Created as New Dataset,PE pellet 124kDa Alfa
        # Aesar". O segundo campo é a amostra; lê-la como dado deslocaria tudo.
        assert read_trace_file(self.path).sample_name == "PE pellet 124kDa Alfa Aesar"

    def test_percent_transmittance_is_converted_to_absorbance(self) -> None:
        tf = read_trace_file(self.path)
        y = tf.columns[1]
        assert y.role == "absorbance"
        assert y.raw_header.startswith("Absorbance")
        # E o aviso precisa dizer que a conversão foi feita.
        assert any("%T" in w for w in tf.warnings)

    def test_axis_is_reversed_to_increasing(self) -> None:
        # O arquivo traz 4000 -> 400 cm-1; a análise precisa de ordem
        # crescente e o resolvedor inverte.
        r = resolve_trace(read_trace_file(self.path), "wavenumber", "absorbance")
        assert r.x[0] < r.x[-1]
        assert any("decrescente" in n for n in r.notes)

    def test_bands_are_polyethylene(self) -> None:
        r = resolve_trace(read_trace_file(self.path), "wavenumber", "absorbance")
        res = analyse_ftir(r.x, r.y)
        peaks = set(round(p) for p in res.detected_peaks)
        nearest = min(peaks, key=lambda p: abs(p - 2915))
        assert abs(nearest - 2915) <= 8, f"CH2 stretch esperado perto de 2915, veio {nearest}"


class TestTransmittanceBaselineAbove100:
    """
    %T acima de 100 é deriva de linha de base, e o PLA-1 do conjunto real cai
    exatamente nisso (baseline entre 88 e 100,22 %T).
    """

    path = FIXTURES / "perkinelmer_ftir_pla.csv"

    def test_reads_without_negative_absorbance(self) -> None:
        # A = 2 - log10(100,22) = -0,00095 é negativo, e a análise de FTIR
        # recusa absorbância negativa. Sem o limite em 100 %, este arquivo não
        # era analisável.
        r = resolve_trace(read_trace_file(self.path), "wavenumber", "absorbance")
        assert min(r.y) >= 0.0

    def test_reports_the_clamp(self) -> None:
        tf = read_trace_file(self.path)
        assert any("acima de 100" in w for w in tf.warnings)

    def test_la_1600_band_present(self) -> None:
        # O PLA tem carbonila de éster ~1750 cm-1; é a banda que distingue PLA
        # de poliolefina.
        r = resolve_trace(read_trace_file(self.path), "wavenumber", "absorbance")
        res = analyse_ftir(r.x, r.y)
        peaks = set(round(p) for p in res.detected_peaks)
        nearest = min(peaks, key=lambda p: abs(p - 1748))
        assert abs(nearest - 1748) <= 12, f"carbonila esperada ~1748, veio {nearest}"


class TestNoRegressionOnOtherReaders:
    """As portas anteriores continuam funcionando."""

    def test_netzsch_still_reads(self) -> None:
        tf = read_trace_file(FIXTURES / "netzsch_dsc_ldpe.txt")
        r = resolve_trace(tf, "temperature", "heat_flow", invert_for_endothermic_up=True)
        assert len(r.x) == 186
        assert r.sample_mass_mg == pytest.approx(4.98)
        assert r.heating_rate == pytest.approx(10.0)

    def test_plain_two_column_csv_is_untouched(self, tmp_path: Path) -> None:
        # Um CSV comum, com nomes de grandeza nas colunas, não deve ser
        # capturado pelo caminho novo.
        p = tmp_path / "plain.csv"
        p.write_text(
            "wavenumber,absorbance\n"
            "4000,0.01\n3999,0.02\n3998,0.03\n3997,0.04\n",
            encoding="utf-8",
        )
        r = resolve_trace(read_trace_file(p), "wavenumber", "absorbance")
        assert len(r.x) == 4

    def test_refuses_a_spectrum_with_unmappable_units(self, tmp_path: Path) -> None:
        # Um cabeçalho que declara unidades que não sei mapear deve ser
        # recusado com o motivo, não lido como se fosse outra coisa.
        p = tmp_path / "weird.txt"
        p.write_text(
            "TITLE\tx\nXUNITS\tFURLOGS\nYUNITS\tBARNES\nXYDATA\n1\t2\n2\t3\n3\t4\n",
            encoding="utf-8",
        )
        with pytest.raises(TraceImportError) as exc:
            read_trace_file(p)
        assert "FURLOGS" in str(exc.value)
