#!/usr/bin/env python3
"""
Baixa os dados de referência usados pela verificação contra a literatura.

Coloca tudo em `.reference-data/` na raiz do repositório, fora do controle de
versão (os arquivos têm alguns MB e licença própria, então não são
redistribuídos aqui). Depois de rodar isto, execute:

    cd backend && pytest tests/test_against_literature.py -v

Fontes
------
[1] Zenodo 10.5281/zenodo.17306416 (CC-BY-4.0)
    GPC/SEC de poli(ácido láctico) em THF e DMF.
    Centro de Física de Materiais (CSIC-UPV/EHU), San Sebastián, Espanha.
    Relatórios ASTRA 8.2.2 (Wyatt) com Mn, Mw, Mz, Mz+1 e incertezas.

[2] NIST IR 6091 (1998), DOI 10.6028/nist.ir.6091 (acesso aberto)
    "Recertification of the SRM 706a, a Polystyrene".
    Mw certificado = 2.85e5 g/mol, incerteza expandida 0.23e5 g/mol (k=2).
    O PDF é baixado e os valores extraídos dele, não digitados à mão.

Uso
---
    python scripts/fetch_reference_data.py
    python scripts/fetch_reference_data.py --skip-nist   # só o dataset de PLA
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = "PAT-verification/1.0 (research; contact via github.com/teles-eliandro)"
ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / ".reference-data"

ZENODO_RECORD = "17306416"
ZENODO_THF = (
    f"https://zenodo.org/api/records/{ZENODO_RECORD}/files/GPC_THF.zip/content"
)
NIST_IR = "https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir6091.pdf"

# DSC de policaprolactona comercial (CC-BY-4.0). Segundo aquecimento a
# 10 K/min, com o protocolo declarado no proprio arquivo. Usado para verificar
# Tg/Tm/cristalinidade contra valores publicados para PCL.
ZENODO_DSC_RECORD = "17293641"
ZENODO_DSC = (
    f"https://zenodo.org/api/records/{ZENODO_DSC_RECORD}/files/PCL_standard.txt/content"
)


def fetch(url: str, dest: Path, label: str) -> bool:
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  já existe: {dest.name} ({dest.stat().st_size} bytes)")
        return True
    print(f"  baixando {label} …")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
    except Exception as exc:
        print(f"  FALHOU: {exc}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"  salvo {dest.name} ({len(data)} bytes)")
    return True


# ---------------------------------------------------------------------------
# Extração dos valores reportados pelo ASTRA, a partir dos PDFs do dataset
# ---------------------------------------------------------------------------

SCI = re.compile(r"([\d.]+)\s*[×x]\s*10\s*([\d]?)")
FIELDS = ["Mn", "Mp", "Mv", "Mw", "Mz", "Mz+1", "M(avg)", "Mw/Mn", "Mz/Mn"]


def parse_sci(raw: str):
    """'1.941×104 (±1.645%)' -> (19410.0, 1.645)."""
    if not raw:
        return None, None
    raw = raw.strip()
    if raw.lower().startswith("n/a"):
        return None, None
    unc = None
    m = re.search(r"\(±([\d.]+)%\)", raw)
    if m:
        unc = float(m.group(1))
    m = SCI.search(raw)
    if not m:
        m2 = re.match(r"([\d.]+)", raw)
        if m2:
            return float(m2.group(1)), unc
        return None, unc
    mantissa = float(m.group(1))
    exp_digits = m.group(2) or ""
    if exp_digits:
        return mantissa * 10 ** int(exp_digits), unc
    # Expoente de um dígito perdido na extração: a mantissa do ASTRA fica em
    # [1, 10), então o expoente é a potência de 10 que põe o valor numa faixa
    # física de massa molar (1e3 a 1e8 g/mol).
    for cand in range(3, 9):
        val = mantissa * 10**cand
        if 1e3 <= val <= 1e8:
            return val, unc
    return None, unc


def extract_reports(reports_dir: Path, out_json: Path) -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        print("  pypdf ausente: pip install pypdf")
        return 0

    records = []
    for pdf in sorted(reports_dir.glob("*.pdf")):
        reader = PdfReader(str(pdf))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        rec = {"report": pdf.name, "fields": {}, "uncertainty_pct": {}}
        m = re.search(r"Sample:\s*(\S+)", text)
        rec["sample"] = m.group(1) if m else None
        m = re.search(r"dn/dc \(mL/g\)\s*([\d.]+)", text)
        rec["dn_dc_mL_g"] = float(m.group(1)) if m else None
        m = re.search(r"Concentration:\s*([\d.]+)\s*mg/mL", text)
        rec["concentration_mg_mL"] = float(m.group(1)) if m else None
        m = re.search(r"Light Scattering Model\s*(\w+)", text)
        rec["ls_model"] = m.group(1) if m else None
        m = re.search(r"Calculated Mass \(µg\)\s*([\d.]+)", text)
        rec["calculated_mass_ug"] = float(m.group(1)) if m else None
        for f in FIELDS:
            m = re.search(re.escape(f) + r"\s+([^\n]+)", text)
            if m:
                val, unc = parse_sci(m.group(1))
                if val is not None:
                    rec["fields"][f] = val
                if unc is not None:
                    rec["uncertainty_pct"][f] = unc
        records.append(rec)

    out_json.write_text(json.dumps(records, indent=2))
    print(f"  extraídos {len(records)} relatórios -> {out_json.name}")
    return len(records)


def extract_nist(pdf: Path, out_dir: Path) -> bool:
    """Baixa e lê o NIST IR 6091, guardando o texto para auditoria."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return False
    if not pdf.exists():
        return False
    text = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf)).pages)
    (out_dir / "nist_ir6091.txt").write_text(text, encoding="utf-8")

    found = {}
    m = re.search(r"determined to be\s*([\d.]+)\s*[x×]\s*10\s*5\s*g/mol", text)
    if m:
        found["Mw"] = float(m.group(1)) * 1e5
    m = re.search(r"([\d.]+)\s*[x×]\s*10\s*5\s*g/mol\s*±\s*([\d.]+)\s*[x×]\s*10\s*5", text)
    if m:
        found["Mw_certified"] = float(m.group(1)) * 1e5
        found["uncertainty_expanded"] = float(m.group(2)) * 1e5
    if found:
        (out_dir / "nist_706a_certified.json").write_text(json.dumps(found, indent=2))
        print(f"  valores certificados do NIST: {found}")
    else:
        print("  AVISO: não consegui localizar os valores certificados no PDF.")
        print("  O texto está salvo em nist_ir6091.txt para inspeção manual.")
    return bool(found)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-nist", action="store_true")
    ap.add_argument("--dsc", action="store_true", help="baixar também o DSC de PCL")
    args = ap.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)

    print("[1/4] Dataset de GPC/SEC de PLA (Zenodo, CC-BY-4.0)")
    zip_path = DEST / "GPC_THF.zip"
    if not fetch(ZENODO_THF, zip_path, "GPC_THF.zip"):
        print("  Não foi possível baixar o dataset; a verificação externa será pulada.")
    else:
        extract_dir = DEST / "thf"
        if not (extract_dir / "GPC_THF" / "tables").exists():
            print("  extraindo …")
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(extract_dir)

    print("[2/4] Extraindo os valores reportados pelo ASTRA")
    reports = DEST / "thf" / "GPC_THF" / "reports"
    if reports.exists():
        n = extract_reports(reports, DEST / "reported_values.json")
        if n == 0:
            print("  nenhum relatório extraído.")
    else:
        print("  diretório de relatórios ausente; pulando.")

    print("[3/4] Padrão certificado NIST SRM 706a")
    if args.skip_nist:
        print("  pulado por --skip-nist")
    else:
        nist_pdf = DEST / "nist_ir6091.pdf"
        if fetch(NIST_IR, nist_pdf, "NIST IR 6091"):
            extract_nist(nist_pdf, DEST)

    print("[4/4] DSC de policaprolactona comercial (Zenodo, CC-BY-4.0)")
    if not args.dsc:
        print("  pulado (use --dsc para baixar)")
    else:
        fetch(ZENODO_DSC, DEST / "PCL_standard.txt", "PCL_standard.txt")

    print()
    print(f"Pronto. Dados de referência em {DEST}")
    print("Rode: cd backend && pytest tests/test_against_literature.py "
          "tests/test_thermal_literature.py -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())
