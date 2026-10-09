"""
A API: o banco de entalpias e o preenchimento automático pelo nome da amostra.

O que se verifica aqui é o que o usuário vê: que o campo de entalpia de
referência possa ser preenchido sem digitar o número, e que a citação venha
junto -- um valor sem a fonte não é verificável, e um ΔHf100 do polímero
errado dá uma cristalinidade plausível e errada.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


class TestCrystallinityReferencesEndpoint:
    def test_lists_the_database(self, client: TestClient) -> None:
        r = client.get("/api/v1/thermal/crystallinity-references")
        assert r.status_code == 200
        body = r.json()
        assert len(body["references"]) >= 15
        # A nota explica a fórmula e a especificidade por polímero.
        assert "ΔHf100" in body["note"]

    def test_every_entry_carries_its_citation(self, client: TestClient) -> None:
        body = client.get("/api/v1/thermal/crystallinity-references").json()
        for entry in body["references"]:
            if entry["value_J_g"] is not None:
                assert entry["source"], f"{entry['key']} sem citação"
                assert entry["confidence"] in {"verified", "compilation", "divergent"}

    def test_pe_and_pla_are_present_with_their_values(self, client: TestClient) -> None:
        body = client.get("/api/v1/thermal/crystallinity-references").json()
        by_key = {e["key"]: e for e in body["references"]}
        assert by_key["PE"]["value_J_g"] == pytest.approx(293.0)
        assert by_key["PLA"]["value_J_g"] == pytest.approx(93.0)
        assert by_key["PP"]["value_J_g"] == pytest.approx(207.0)


class TestAutoFillFromSampleName:
    """A entalpia resolvida do nome no arquivo, com a citação no resultado."""

    @staticmethod
    def _dsc_file_with_sample(tmp_path: Path, sample: str) -> Path:
        """O DSC real da NETZSCH, com o nome da amostra trocado."""
        src = (FIXTURES / "netzsch_dsc_ldpe.txt").read_text(encoding="latin-1")
        out = re.sub(r"(#SAMPLE:)(.*)", rf"\g<1>{sample}", src, count=1)
        p = tmp_path / f"DSC_{sample}.txt"
        p.write_text(out, encoding="latin-1")
        return p

    def test_fills_from_an_identifiable_name(self, client: TestClient, tmp_path: Path) -> None:
        p = self._dsc_file_with_sample(tmp_path, "LDPE-SBC-818")
        with p.open("rb") as f:
            r = client.post(
                "/api/v1/thermal/analyse",
                files={"file": (p.name, f, "text/plain")},
                data={"target": "dsc"},
            )
        assert r.status_code == 200
        body = r.json()
        res = body["result"]
        # A cristalinidade foi calculada sem o usuário informar a entalpia.
        assert res["crystallinity_pct"] is not None
        assert 0.0 < res["crystallinity_pct"] < 100.0
        # E a nota diz de onde veio o valor, com a citação.
        joined = " ".join(body["notes"])
        assert "banco interno" in joined
        assert "293" in joined
        assert "doi:" in joined.lower()

    def test_explicit_value_overrides_the_database(self, client: TestClient, tmp_path: Path) -> None:
        # Quem informa o valor decide; o banco é conveniência, não autoridade.
        p = self._dsc_file_with_sample(tmp_path, "LDPE-SBC-818")
        with p.open("rb") as f:
            r = client.post(
                "/api/v1/thermal/analyse",
                files={"file": (p.name, f, "text/plain")},
                data={"target": "dsc", "ref_enthalpy_J_g": "500"},
            )
        body = r.json()
        # 500 J/g de referência deve dar cerca de metade do que 293 dá.
        assert body["result"]["crystallinity_pct"] is not None
        assert body["result"]["crystallinity_pct"] < 30.0
        assert "banco interno" not in " ".join(body["notes"])

    def test_unknown_name_reports_the_refusal(self, client: TestClient, tmp_path: Path) -> None:
        # Nome que não identifica polímero: não se adivinha. O motivo aponta
        # para o endpoint que lista as opções.
        p = self._dsc_file_with_sample(tmp_path, "amostra-42")
        with p.open("rb") as f:
            r = client.post(
                "/api/v1/thermal/analyse",
                files={"file": (p.name, f, "text/plain")},
                data={"target": "dsc"},
            )
        body = r.json()
        assert body["result"]["crystallinity_pct"] is None
        joined = " ".join(body["refusals"])
        assert "crystallinity-references" in joined

    def test_amorphous_polymer_is_refused_with_a_reason(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        # PS atático: a resposta certa não é um número nem um silêncio, é
        # "não se aplica".
        p = self._dsc_file_with_sample(tmp_path, "PS-1")
        with p.open("rb") as f:
            r = client.post(
                "/api/v1/thermal/analyse",
                files={"file": (p.name, f, "text/plain")},
                data={"target": "dsc"},
            )
        body = r.json()
        assert body["result"]["crystallinity_pct"] is None
        assert "amorfo" in " ".join(body["refusals"])


class TestFtirTarget:
    """O alvo 'ftir' leva o arquivo do instrumento até a análise, numa chamada."""

    def test_jasco_file_through_the_api(self, client: TestClient) -> None:
        p = FIXTURES / "jasco_ftir_ldpe.txt"
        with p.open("rb") as f:
            r = client.post(
                "/api/v1/thermal/analyse",
                files={"file": (p.name, f, "text/plain")},
                data={"target": "ftir"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["sample_name"] == "ldpe sbc 818 0"
        res = body["result"]
        assert len(res["detected_peaks"]) >= 4
        peaks = [round(p) for p in res["detected_peaks"]]
        # Bandas do polietileno.
        assert any(abs(pk - 2915) <= 6 for pk in peaks)
        assert any(abs(pk - 717) <= 6 for pk in peaks)

    def test_perkinelmer_transmittance_file_through_the_api(self, client: TestClient) -> None:
        p = FIXTURES / "perkinelmer_ftir_pla.csv"
        with p.open("rb") as f:
            r = client.post(
                "/api/v1/thermal/analyse",
                files={"file": (p.name, f, "text/csv")},
                data={"target": "ftir"},
            )
        assert r.status_code == 200
        body = r.json()
        # A conversão de %T precisa aparecer nos avisos que o usuário lê.
        assert any("%T" in n for n in body["notes"])
        peaks = [round(p) for p in body["result"]["detected_peaks"]]
        assert any(abs(pk - 1748) <= 12 for pk in peaks)

    def test_import_preview_shows_the_declared_units(self, client: TestClient) -> None:
        p = FIXTURES / "jasco_ftir_ldpe.txt"
        with p.open("rb") as f:
            r = client.post(
                "/api/v1/thermal/import",
                files={"file": (p.name, f, "text/plain")},
                data={"target": "ftir"},
            )
        assert r.status_code == 200
        body = r.json()
        # A prévia mostra o que o arquivo declarou, não só o que foi resolvido.
        assert body["metadata"]["xunits"] == "1/CM"
        assert body["metadata"]["yunits"] == "ABSORBANCE"
        assert [c["role"] for c in body["columns"]] == ["wavenumber", "absorbance"]
