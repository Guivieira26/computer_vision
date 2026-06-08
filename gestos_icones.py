"""
gestos_icones.py — Ícones SVG para cada gesto do sistema.
Cada ícone é uma string SVG 80x80px representando a mão em traços.
Dedos estendidos = linha reta saindo da palma.
Dedos dobrados = linha curta curvada sobre a palma.
Pinças = dedão e dedo-alvo com ponta verde se tocando.
Rosto = perfil de nariz com ponto verde na ponta.
"""

_PALMA     = "#4a4a5a"
_DEDO_ON   = "#e8e8f0"
_DEDO_OFF  = "#2a2a3a"
_PINCA     = "#00c875"
_STROKE    = "1.8"
_STROKE_TH = "1.2"


def _svg_wrap(conteudo: str, w: int = 80, h: int = 80) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">{conteudo}</svg>'
    )


def _palma_base() -> str:
    return (
        f'<rect x="22" y="44" width="36" height="26" rx="8" '
        f'fill="{_PALMA}" stroke="{_PALMA}" stroke-width="{_STROKE}"/>'
    )


def _dedo(x: int, y_base: int, comprimento: int, dobrado: bool) -> str:
    if not dobrado:
        return (
            f'<line x1="{x}" y1="{y_base}" x2="{x}" y2="{y_base - comprimento}" '
            f'stroke="{_DEDO_ON}" stroke-width="{_STROKE}" stroke-linecap="round"/>'
        )
    return (
        f'<path d="M{x},{y_base} Q{x+4},{y_base-8} {x+2},{y_base-4}" '
        f'stroke="{_DEDO_OFF}" stroke-width="{_STROKE_TH}" '
        f'fill="none" stroke-linecap="round"/>'
    )


def _dedao(estendido: bool) -> str:
    if estendido:
        return (
            f'<line x1="22" y1="52" x2="10" y2="44" '
            f'stroke="{_DEDO_ON}" stroke-width="{_STROKE}" stroke-linecap="round"/>'
        )
    return (
        f'<line x1="22" y1="54" x2="16" y2="50" '
        f'stroke="{_DEDO_OFF}" stroke-width="{_STROKE_TH}" stroke-linecap="round"/>'
    )


def _ponta_verde(x: int, y: int) -> str:
    return f'<circle cx="{x}" cy="{y}" r="3.5" fill="{_PINCA}"/>'


def _icone_mao(mask: tuple, pinca_idx: int | None = None) -> str:
    d, i, m, a, mi = mask
    comp = [22, 26, 24, 20]
    xs   = [32, 40, 48, 56]
    y_b  = 44

    svg  = _palma_base()
    svg += _dedao(bool(d))

    for x, c, ext in zip(xs, comp, [bool(i), bool(m), bool(a), bool(mi)]):
        svg += _dedo(x, y_b, c, not ext)

    if pinca_idx is not None:
        svg += _ponta_verde(12, 43)
        tip_xs = {8: 32, 12: 40, 16: 48, 20: 56}
        tip_ys = {8: 18, 12: 18, 16: 20, 20: 22}
        svg += _ponta_verde(tip_xs.get(pinca_idx, 32), tip_ys.get(pinca_idx, 18))

    return _svg_wrap(svg)


def _icone_rosto() -> str:
    svg = (
        f'<path d="M40,15 Q38,28 36,38 Q35,44 38,46" '
        f'stroke="{_DEDO_ON}" stroke-width="{_STROKE}" fill="none" stroke-linecap="round"/>'
        f'<path d="M38,46 Q34,50 32,48 Q30,46 33,44" '
        f'stroke="{_DEDO_ON}" stroke-width="{_STROKE}" fill="none" stroke-linecap="round"/>'
        f'<path d="M50,30 L58,30 M55,26 L59,30 L55,34" '
        f'stroke="{_PINCA}" stroke-width="{_STROKE_TH}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="33" cy="47" r="3.5" fill="{_PINCA}"/>'
        f'<text x="40" y="68" text-anchor="middle" font-size="9" fill="{_DEDO_ON}" font-family="sans-serif">nariz</text>'
    )
    return _svg_wrap(svg)


def _icone_calibracao() -> str:
    svg = (
        f'<rect x="4" y="44" width="22" height="18" rx="5" fill="{_PALMA}"/>'
        f'<line x1="10" y1="44" x2="9" y2="28" stroke="{_DEDO_ON}" stroke-width="1.5" stroke-linecap="round"/>'
        f'<circle cx="9" cy="27" r="2.5" fill="{_PINCA}"/>'
        f'<line x1="4" y1="50" x2="0" y2="43" stroke="{_DEDO_ON}" stroke-width="1.5" stroke-linecap="round"/>'
        f'<circle cx="0" cy="42" r="2.5" fill="{_PINCA}"/>'
        f'<rect x="54" y="44" width="22" height="18" rx="5" fill="{_PALMA}"/>'
        f'<line x1="60" y1="44" x2="59" y2="28" stroke="{_DEDO_ON}" stroke-width="1.5" stroke-linecap="round"/>'
        f'<circle cx="59" cy="27" r="2.5" fill="{_PINCA}"/>'
        f'<line x1="76" y1="50" x2="80" y2="43" stroke="{_DEDO_ON}" stroke-width="1.5" stroke-linecap="round"/>'
        f'<circle cx="80" cy="42" r="2.5" fill="{_PINCA}"/>'
        f'<path d="M32,38 Q40,32 48,38" stroke="{_PINCA}" stroke-width="1.5" fill="none"/>'
        f'<text x="40" y="68" text-anchor="middle" font-size="8" fill="{_DEDO_ON}" font-family="sans-serif">calibrar</text>'
    )
    return _svg_wrap(svg)


# =============================================================================
# MAPA PRINCIPAL
# =============================================================================

ICONES: dict[str, str] = {}

_BITMASKS = {
    "MAO_FECHADA":               (0, 0, 0, 0, 0),
    "MAO_ABERTA":                (1, 1, 1, 1, 1),
    "DEDAO":                     (1, 0, 0, 0, 0),
    "INDICADOR":                 (0, 1, 0, 0, 0),
    "MEDIO":                     (0, 0, 1, 0, 0),
    "ANELAR":                    (0, 0, 0, 1, 0),
    "MINDINHO":                  (0, 0, 0, 0, 1),
    "DEDAO_INDICADOR":           (1, 1, 0, 0, 0),
    "DEDAO_MEDIO":               (1, 0, 1, 0, 0),
    "DEDAO_ANELAR":              (1, 0, 0, 1, 0),
    "DEDAO_MINDINHO":            (1, 0, 0, 0, 1),
    "INDICADOR_MEDIO":           (0, 1, 1, 0, 0),
    "INDICADOR_ANELAR":          (0, 1, 0, 1, 0),
    "INDICADOR_MINDINHO":        (0, 1, 0, 0, 1),
    "MEDIO_ANELAR":              (0, 0, 1, 1, 0),
    "MEDIO_MINDINHO":            (0, 0, 1, 0, 1),
    "ANELAR_MINDINHO":           (0, 0, 0, 1, 1),
    "DEDAO_INDICADOR_MEDIO":     (1, 1, 1, 0, 0),
    "DEDAO_INDICADOR_ANELAR":    (1, 1, 0, 1, 0),
    "DEDAO_INDICADOR_MINDINHO":  (1, 1, 0, 0, 1),
    "DEDAO_MEDIO_ANELAR":        (1, 0, 1, 1, 0),
    "DEDAO_MEDIO_MINDINHO":      (1, 0, 1, 0, 1),
    "DEDAO_ANELAR_MINDINHO":     (1, 0, 0, 1, 1),
    "INDICADOR_MEDIO_ANELAR":    (0, 1, 1, 1, 0),
    "INDICADOR_MEDIO_MINDINHO":  (0, 1, 1, 0, 1),
    "INDICADOR_ANELAR_MINDINHO": (0, 1, 0, 1, 1),
    "MEDIO_ANELAR_MINDINHO":     (0, 0, 1, 1, 1),
    "QUATRO_SEM_MINDINHO":       (1, 1, 1, 1, 0),
    "QUATRO_SEM_ANELAR":         (1, 1, 1, 0, 1),
    "QUATRO_SEM_MEDIO":          (1, 1, 0, 1, 1),
    "QUATRO_SEM_INDICADOR":      (1, 0, 1, 1, 1),
    "QUATRO_SEM_DEDAO":          (0, 1, 1, 1, 1),
}

for nome, mask in _BITMASKS.items():
    ICONES[nome] = _icone_mao(mask)

_PINCAS_IDX = {
    "PINCA_INDICADOR": 8,
    "PINCA_MEDIO":     12,
    "PINCA_ANELAR":    16,
    "PINCA_MINDINHO":  20,
}

for nome, idx in _PINCAS_IDX.items():
    ICONES[nome] = _icone_mao((1, 0, 0, 0, 0), pinca_idx=idx)

ICONES["ROSTO"]      = _icone_rosto()
ICONES["CALIBRACAO"] = _icone_calibracao()

# =============================================================================
# CATEGORIAS para checkboxes da GUI
# =============================================================================

CATEGORIAS: dict[str, list[str]] = {
    "Nenhum dedo":  ["MAO_FECHADA"],
    "1 dedo":       ["DEDAO", "INDICADOR", "MEDIO", "ANELAR", "MINDINHO"],
    "2 dedos":      [
        "DEDAO_INDICADOR", "DEDAO_MEDIO", "DEDAO_ANELAR", "DEDAO_MINDINHO",
        "INDICADOR_MEDIO", "INDICADOR_ANELAR", "INDICADOR_MINDINHO",
        "MEDIO_ANELAR", "MEDIO_MINDINHO", "ANELAR_MINDINHO",
    ],
    "3 dedos":      [
        "DEDAO_INDICADOR_MEDIO", "DEDAO_INDICADOR_ANELAR", "DEDAO_INDICADOR_MINDINHO",
        "DEDAO_MEDIO_ANELAR", "DEDAO_MEDIO_MINDINHO", "DEDAO_ANELAR_MINDINHO",
        "INDICADOR_MEDIO_ANELAR", "INDICADOR_MEDIO_MINDINHO",
        "INDICADOR_ANELAR_MINDINHO", "MEDIO_ANELAR_MINDINHO",
    ],
    "4 dedos":      [
        "QUATRO_SEM_MINDINHO", "QUATRO_SEM_ANELAR", "QUATRO_SEM_MEDIO",
        "QUATRO_SEM_INDICADOR", "QUATRO_SEM_DEDAO",
    ],
    "Mão aberta":   ["MAO_ABERTA"],
    "Pinças":       list(_PINCAS_IDX.keys()),
    "Especiais":    ["ROSTO", "CALIBRACAO"],
}


def listar_todos() -> list[str]:
    ordem, vistos = [], set()
    for gestos in CATEGORIAS.values():
        for g in gestos:
            if g not in vistos:
                ordem.append(g)
                vistos.add(g)
    return ordem


if __name__ == "__main__":
    print(f"Total de ícones: {len(ICONES)}")
    for nome in listar_todos():
        print(f"  {nome}: {'OK' if nome in ICONES else 'FALTANDO'}")
