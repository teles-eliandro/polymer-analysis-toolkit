"""
O endpoint de importação de arquivo de instrumento.

O que estes testes protegem é a diferença entre "leu o arquivo" e "leu o
arquivo certo". Um parser que pega a coluna errada não falha: devolve um
número, e o número parece plausível. Por isso o teste central não compara com
uma constante -- verifica que o *resultado tem a propriedade física esperada*
(Tm dentro da faixa do polímero), que é o que muda quando a coluna está errada.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"
NETZSCH = FIXTURES / "netzsch_dsc_ldpe.txt"

client = TestClient(app)


def _upload(path: Path, target: str = "dsc", extra: dict | None = None):
    data = {"target": target}
    if extra:
        data.update(extra)
    with path.open("rb") as fh:
        return client.post(
            "/api/v1/thermal/import",
            files={"file": (path.name, fh, "text/plain")},
            data=data,
        )


def _analyse(path: Path, target: str = "dsc", extra: dict | None = None):
    data = {"target": target}
    if extra:
        data.update(extra)
    with path.open("rb") as fh:
        return client.post(
            "/api/v1/thermal/analyse",
            files={"file": (path.name, fh, "text/plain")},
            data=data,
        )


class TestImportPreview:
    def test_the_file_is_read_and_its_metadata_surfaced(self):
        r = _upload(NETZSCH)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["sample_name"] == "1-90"
        assert body["sample_mass_mg"] == 4.98
        assert body["heating_rate_K_min"] == 10.0
        assert body["exothermic_direction"] == "down"

    def test_each_column_is_named_and_typed(self):
        body = _upload(NETZSCH).json()
        roles = [c["role"] for c in body["columns"]]
        assert roles == ["temperature", "time", "heat_flow", "sensitivity"]

    def test_the_time_column_is_not_used_as_the_signal(self):
        """
        A falha que o endpoint existe para prevenir.

        A coluna 1 é tempo e varia de 91 a 114; a coluna 2 é o sinal e varia
        dentro de 2 W/g. Se o resolvedor pegasse a coluna errada, a amplitude
        denunciaria: 23 unidades contra menos de 2.
        """
        body = _upload(NETZSCH).json()
        signal = body["signal"]
        assert signal is not None
        assert max(signal) - min(signal) < 2.0, (
            "o sinal resolvido tem amplitude de tempo, não de calorimetria"
        )

    def test_sparse_sampling_is_stated_in_the_notes(self):
        """
        186 pontos em 185 graus é 1,0 ponto por grau.

        A nota tem de aparecer porque é ela que explica por que a Tg não pode
        ser reportada -- sem ela, um campo Tg ausente parece um bug.
        """
        body = _upload(NETZSCH).json()
        assert body["points_per_degree"] is not None
        assert body["points_per_degree"] < 2.0
        assert any("ponto(s) por grau" in n for n in body["notes"]), (
            f"notes não mencionam a amostragem: {body['notes']}"
        )


class TestAnalyseInOneStep:
    def test_the_melting_temperature_lands_in_the_polymer_range(self):
        """
        LDPE funde entre 105 e 115 C. É este o teste que falha se o eixo y
        estiver errado, ou se o sinal não for invertido quando precisa.
        """
        r = _analyse(NETZSCH, extra={"ref_enthalpy_J_g": "293"})
        assert r.status_code == 200, r.text
        result = r.json()["result"]
        assert result["Tm"] is not None
        assert 100.0 < result["Tm"] < 115.0, (
            f"Tm em {result['Tm']:.1f} C; para LDPE o esperado é 105-115 C"
        )

    def test_a_transition_that_cannot_be_located_is_omitted_not_guessed(self):
        """
        Dizer que a amostragem é esparsa demais e ainda devolver um número
        seria contraditório. O campo Tg sai, e o motivo vai em ``refusals``.
        """
        body = _analyse(NETZSCH, extra={"ref_enthalpy_J_g": "293"}).json()
        assert body["result"]["Tg"] is None, (
            f"Tg = {body['result']['Tg']} reportada num arquivo cuja "
            "amostragem a torna impossível"
        )
        assert "Tg" not in body["result"].get("claims", {})
        assert any("Tg" in x or "transição vítrea" in x for x in body["refusals"])

    def test_the_heating_rate_from_the_header_enables_the_enthalpy(self):
        body = _analyse(NETZSCH, extra={"ref_enthalpy_J_g": "293"}).json()
        result = body["result"]
        assert body["heating_rate_K_min"] == 10.0
        # Sem a taxa, a integral não vira J/g. Com ela, vira.
        assert result["delta_Hm"] is not None
        assert result["delta_Hm"] > 50, (
            "ΔHm abaixo de 50 J/g sugere que a taxa de aquecimento não foi "
            "aplicada: o valor do arquivo está em mW/mg por grau"
        )
        # A cristalinidade exige a entalpia de referência, que foi fornecida.
        assert result["crystallinity_pct"] is not None
        assert 0 < result["crystallinity_pct"] < 100

    def test_a_missing_column_gives_a_message_that_names_it(self):
        """Pedir TGA deste arquivo tem de falhar com a razão, não em silêncio."""
        r = _analyse(NETZSCH, target="tga")
        assert r.status_code == 400
        assert "massa" in r.json()["detail"]

    def test_an_unknown_target_is_rejected(self):
        r = _analyse(NETZSCH, target="nao_existe")
        assert r.status_code == 400
        assert "nao_existe" in r.json()["detail"]

    def test_every_response_field_carries_its_provenance(self):
        """O resultado não vem sozinho: vem com o que o leitor decidiu."""
        body = _analyse(NETZSCH).json()
        assert body["columns"], "as colunas lidas têm de acompanhar o resultado"
        assert body["x_label"] == "Temp./°C"
        assert body["y_label"] == "DSC/(mW/mg)"
        assert body["sample_name"] == "1-90"
