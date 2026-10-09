# Conjunto de dados de teste — um arquivo por módulo

Sete arquivos CSV, um para cada módulo do PAT, para você testar a ferramenta
carregando-os diretamente na interface.

## Origem de cada arquivo

| Arquivo | Módulo | Origem | Real? |
|---|---|---|---|
| `molar_mass_gpc_pla.csv` | Massa molar | Zenodo 17306416 — GPC/SEC de PLLA em THF | **sim** |
| `dsc_plla_second_heating.csv` | Térmico (DSC) | Zenodo 17288962 — PLLA, 2º aquecimento | **sim** |
| `tga_eva_nitrogen.csv` | Térmico (TGA) | figshare 24595695 — TGA-FTIR de EVA | **sim** |
| `ftir_pet_transmittance.csv` | Estrutura (FTIR) | figshare 24593022 — PET as-received | **sim** |
| `xrd_plla_waxs.csv` | Estrutura (XRD) | Zenodo 20466241 — WAXS de filme PLLA | **sim** |
| `mechanical_tensile_SYNTHETIC.csv` | Mecânica | **modelo bilinear — não é dado real** | não |
| `rheology_frequency_sweep_SYNTHETIC.csv` | Reologia | **Maxwell de 2 modos — não é dado real** | não |

Cada arquivo traz, em linhas `#` no topo, a fonte, as unidades e os valores
publicados para você conferir o resultado. O carregador ignora as linhas `#`.

## Por que dois são sintéticos

Os datasets publicados que este projeto usa (figshare 24462004, 24593022,
24595695; Zenodo 17306416, 17288962, 20466241) cobrem DSC, TGA, FTIR, XRD e
GPC/SEC. **Nenhum deles é de tração mecânica ou de reologia.** Inventar um CSV
numérico e apresentá-lo como "dado real" seria pior do que dizer que não tenho:
os dois arquivos estão marcados no nome (`_SYNTHETIC`) e no cabeçalho, com os
parâmetros do modelo que os gerou, para que a origem seja rastreável.

Se você tiver acesso a uma máquina de tração ou a um reômetro, esses dois são
os que mais ganham com dado verdadeiro.

## O que esperar de cada um

### Massa molar — funciona, com ressalva

O arquivo dá a massa molar de cada *slice* do cromatograma, mas **não a fração
de cada slice** — o relatório ASTRA publicado não a traz na tabela exportada.
Ao carregar, use `normalise = true`: o módulo trata os slices como igualmente
ponderados. O resultado (Mn ≈ 14 400, Mw ≈ 17 800, Đ ≈ 1,23) **não vai bater**
com o valor do instrumento (Mn = 14 060, Mw = 15 440, Đ = 1,099) justamente
porque depende das frações. Isso é útil como exercício: mostra o quanto as
médias ponderais são sensíveis à ponderação escolhida.

### DSC — o módulo erra a Tg, e isso está documentado

O traço é bom e real: PLLA_50K, 2º aquecimento, 10 K/min. O que o módulo
reporta:

| Grandeza | Módulo | Literatura | Veredito |
|---|---|---|---|
| Tm | 173,2 °C | 170–180 °C | ✅ correto |
| ΔHm | 59,5 J/g | 93 J/g ref. 100 % cristalino | ✅ plausível (64 % crist.) |
| Tg | **94,7 °C** | ~60–65 °C | ❌ **errado** |

(Este resultado foi obtido passando `ref_enthalpy_J_g = 93` — a entalpia de
fusão do PLLA 100 % cristalino — para o módulo obter a cristalinidade. Sem
esse valor, o módulo reporta ΔHm mas se recusa a calcular a cristalinidade,
que é o comportamento documentado.)

A Tg real está no traço: entre 55 e 85 °C há o degrau de capacidade térmica
(o sinal sobe de 0,44 para 0,49 W/g), e o maior gradiente dessa região cai em
**56,3 °C**. O módulo em vez disso devolve 94,7 °C, que é o pico de
**cristalização fria** — o mergulho exotérmico em 90 °C. Ou seja: ele confundiu
uma transição com outra.

Este é exatamente o limite que o paper descreve na §3.6 e no item 4 da §4:
distinguir *qual* transição é qual não é confiável, e por isso a ferramenta
marca toda temperatura de transição como `suggested` em vez de `read`. Vê-lo
acontecer neste arquivo é o teste mais informativo do conjunto — e o motivo de
a ferramenta se recusar a chamar isso de medição.

### TGA — funciona e bate com o dataset

EVA em nitrogênio. O módulo devolve Td5% = 362,6 °C e resíduo = 6,3 %, que são
os valores do próprio dataset para esta amostra (≈363 °C, ≈6 %). A curva tem
duas etapas de perda (desacetilação e quebra de cadeia), que o módulo separa.

### FTIR — o arquivo é %T de propósito

O instrumento exporta **transmitância**, e o módulo do PAT espera
**absorbância**. Ao carregar este arquivo como está, o módulo vai **recusar**,
com a mensagem *"This looks like transmittance, not absorbance"*. Isso não é um
defeito do arquivo — é o guard de entrada funcionando, que é justamente o que a
§3.3 do paper descreve. Para ver o módulo analisar, converta antes:

```python
A = -log10(T / 100)
```

Convertido, ele encontra 18 picos e atribui 13, com o C=O do PET em 1713 cm⁻¹ e
o anel aromático em 1505/1410 cm⁻¹ — todos corretos para PET.

### XRD — funciona, mas o primeiro pico é artefato

Padrão WAXS de filme de PLLA, já em 2θ. O módulo lista 25 picos; o **primeiro**
(2θ ≈ 5,1°, d ≈ 17,4 Å) é o pico do **feixe direto** do instrumento, não uma
reflexão do polímero. Os picos de PLLA que importam ficam em 16,7° e 19,1°
(d = 5,3 e 4,6 Å). O módulo não distingue o artefato do resto — vale saber ao
ler a lista.

### Mecânica — dado sintético, validado como tal

Curva bilinear: E = 1200 MPa, σ_y = 28 MPa, ruptura em 350 % / 22 MPa. O módulo
recupera E = 1200,0 MPa e σ_max = 28,00 MPa, isto é, exatamente os parâmetros
do modelo. Serve para confirmar que a regressão do módulo está correta; não
serve como referência de material.

### Reologia — dado sintético, validado como tal

Maxwell de dois modos: (τ = 10 ms, G = 1,2 MPa) e (τ = 1 s, G = 30 kPa). O
módulo devolve cruzamento em 95 rad/s e G₀ ≈ 1,2 MPa — os valores do modelo,
o que novamente valida a aritmética sem valer como dado de material.

## Como reproduzir

```bash
# a partir da raiz do repositório
backend/.venv/bin/python scripts/make_test_datasets.py      # gera os 7 CSVs
backend/.venv/bin/python scripts/verify_test_datasets.py    # prova que os 7 carregam
```

Os quatro primeiros dependem dos datasets brutos já baixados em
`.reference-data/` e em `/tmp/dsc116`, `/tmp/tga_ega`, `/tmp/ftir`,
`/home/hermes/pat-test-data`. O script pula, com aviso, o que não encontrar.
