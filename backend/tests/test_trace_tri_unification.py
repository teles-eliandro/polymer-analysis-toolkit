"""
Testes da unificação: um .tri bruto atravessa o mesmo caminho do arquivo de texto.

O PAT tinha duas portas de entrada -- ``read_trace_file`` para texto e
``read_tri`` para o contêiner binário da TA Instruments -- e só a primeira
resolvia papéis de coluna, convertia unidades e validava coerência. O
adaptador faz o .tri terminar no mesmo ``TraceFile``, de modo que a análise
receba as séries nas unidades canônicas sem saber de que formato vieram.

Estes testes fixam o contrato do adaptador contra um arquivo real (PS do
figshare 24462004, recortado): se a leitura do cabeçalho binário, o mapa de
nomes de canal ou a conversão de unidade regredirem, falha aqui em vez de
produzir uma curva silenciosamente errada.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.trace_io import TraceFile, read_trace_file, resolve_trace

FIXTURES = Path(__file__).parent / "fixtures"
#: Recorte de um .tri real (PS, figshare 24462004): cabeçalho + os 14 canais.
TRI_FIXTURE = FIXTURES / "tri_ps1_ar_head.bin"
TRI_EXPECT = FIXTURES / "tri_ps1_ar_expect.json"


def _have_fixture() -> bool:
    return TRI_FIXTURE.exists() and TRI_EXPECT.exists()


pytestmark = pytest.mark.skipif(not _have_fixture(), reason="tri fixture not present")


@pytest.fixture(scope="module")
def expect() -> dict:
    return json.loads(TRI_EXPECT.read_text())


@pytest.fixture(scope="module")
def tf() -> TraceFile:
    return read_trace_file(TRI_FIXTURE)


# ---------------------------------------------------------------------------
# Detecção de formato
# ---------------------------------------------------------------------------


def test_binary_is_detected_by_content_not_extension(tf: TraceFile):
    """Um .tri sem extensão .tri ainda é lido como .tri.

    O fixture é um .bin: se o despacho dependesse só do sufixo, este arquivo
    cairia no parser de texto, que decodifica latin-1 e encontra lixo -- e o
    erro só apareceria longe da causa.
    """
    assert tf.columns
    assert any(c.role == "heat_flow" for c in tf.columns)


def test_dispatch_matches_explicit_tri_suffix(tmp_path: Path):
    """Sufixo e conteúdo levam ao mesmo resultado."""
    renamed = tmp_path / "sample.tri"
    renamed.write_bytes(TRI_FIXTURE.read_bytes())
    by_suffix = read_trace_file(renamed)
    by_content = read_trace_file(TRI_FIXTURE)
    assert len(by_suffix.columns) == len(by_content.columns)
    assert by_suffix.sample_name == by_content.sample_name
    assert by_suffix.heating_rate == by_content.heating_rate


def test_plain_png_is_not_mistaken_for_a_container(tmp_path: Path):
    """Um PNG puro não é tratado como .tri, apesar de o container embutir um PNG.

    A distinção importa: um PNG exportado do gráfico não tem canais, e mandá-lo
    ao leitor binário produziria "nenhum canal recuperado" -- uma mensagem que
    culpa o arquivo errado. O parser de texto é quem deve reclamar, dizendo que
    não achou linha de dados.
    """
    png = tmp_path / "plot.bin"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    with pytest.raises(Exception) as exc:
        read_trace_file(png)
    assert "nenhum canal" not in str(exc.value)


def test_binary_content_is_refused_not_parsed(tmp_path: Path):
    """Conteúdo binário é recusado em vez de virar colunas inventadas.

    ``latin-1`` decodifica qualquer byte, então sem a guarda um binário
    atravessava o parser de texto e devolvia um TraceFile com colunas lixo --
    silenciosamente, que é o pior desfecho. O erro nomeia a causa provável.
    """
    blob = tmp_path / "capture.bin"
    blob.write_bytes(bytes(range(256)) * 64)
    with pytest.raises(Exception) as exc:
        read_trace_file(blob)
    assert "binário" in str(exc.value)


# ---------------------------------------------------------------------------
# Metadados
# ---------------------------------------------------------------------------


def test_metadata_survives_the_adapter(tf: TraceFile, expect: dict):
    """Nome, massa e taxa chegam ao TraceFile com as chaves do caminho comum."""
    assert tf.sample_name == expect["sample_name"]
    assert tf.sample_mass_mg == pytest.approx(expect["mass_mg"])


def test_heating_rate_is_read_from_the_procedure(tf: TraceFile, expect: dict):
    """A taxa sai da procedure, apesar do grau corrompido em latin-1.

    A procedure chega como ``Â°C/min`` (dois bytes no lugar de um). Sem
    consertar isso na leitura, o regex de taxa não casa e a análise roda sem
    taxa de aquecimento -- o que silenciosamente desliga delta_Hm.
    """
    assert tf.heating_rate == pytest.approx(expect["heating_rate_K_min"])


# ---------------------------------------------------------------------------
# Papéis e unidades
# ---------------------------------------------------------------------------


def test_canonical_roles_are_the_first_of_each_kind(tf: TraceFile):
    """Temperature e heat flow canônicos vêm do primeiro canal de cada tipo.

    O arquivo traz 6 canais de temperatura e 3 de fluxo. Sem a regra do
    primeiro, ``resolve_trace`` escolheria por ordem de arquivo e poderia
    eleger ``Flange Temperature`` (index 7) ou ``Heat Flow B`` (index 12).
    O índice prova qual canal foi eleito, já que o cabeçalho é reescrito para
    a forma canônica com unidade.
    """
    temp = tf.column("temperature")
    hf = tf.column("heat_flow")
    assert temp is not None and hf is not None
    # Tzero Temperature é o index 1; Heat Flow (canônico) é o 13.
    assert temp.index == 1
    assert hf.index == 13


def test_auxiliary_channels_are_listed_without_a_role(tf: TraceFile):
    """Canais redundantes aparecem na prévia mas não competem pela análise."""
    no_role = [c for c in tf.columns if c.role is None]
    names = " ".join(c.raw_header for c in no_role)
    assert "Temperature A" in names
    assert "Heat Flow B" in names
    # Um canal sem papel nunca deve ser escolhido.
    temp = tf.column("temperature")
    assert temp is not None
    assert temp.raw_header == "Temp. [°C]"


def test_units_are_converted_to_the_canonical_ones(tf: TraceFile, expect: dict):
    """mW/mg -> W/g e °C -> C, os nomes canônicos que a análise espera."""
    temp = tf.column("temperature")
    hf = tf.column("heat_flow")
    assert temp is not None and hf is not None
    assert temp.factor == pytest.approx(1.0)
    assert hf.factor == pytest.approx(1.0)
    assert temp.unit == "°c"
    assert hf.unit == "mw/mg"


def test_resolved_trace_carries_canonical_units(tf: TraceFile):
    """O trace resolvido fala as unidades que a análise documenta."""
    r = resolve_trace(tf, "temperature", "heat_flow", invert_for_endothermic_up=True)
    assert r.x_unit == "C"
    assert r.y_unit == "W/g"
    assert len(r.x) == len(r.y)
    assert not r.refusals


def test_resolved_axis_is_the_instrument_ramp(tf: TraceFile):
    """O eixo x varre o programa do método, em ordem crescente.

    O método é ``Equilibrate -90 C ; Ramp 10 C/min to 270 C``. Um eixo que
    começasse perto de 0 ou terminasse muito antes de 270 indicaria que o
    canal de temperatura errado foi escolhido.
    """
    r = resolve_trace(tf, "temperature", "heat_flow", invert_for_endothermic_up=True)
    assert min(r.x) < -50.0
    assert max(r.x) > 250.0
    assert r.x == sorted(r.x)
