"""
gestos.py — Motor de classificação de gestos para visão computacional
Autor: Guivieira26
Descrição: Detecta gestos de mão via landmarks do MediaPipe usando uma
           bitmask de 5 bits (dedão, indicador, médio, anelar, mindinho) [32 gestos].
           Pinças são detectadas com prioridade por distância euclidiana.
           Gesto de rosto (nariz) é tratado separadamente.
"""

import math

# =============================================================================
# CONSTANTES DE LANDMARKS (MediaPipe Hand)
# =============================================================================

# Pontas dos dedos
PONTA_INDICADOR = 8
PONTA_MEDIO     = 12
PONTA_ANELAR    = 16
PONTA_MINDINHO  = 20
PONTA_DEDAO     = 4

# Articulações PIP (meio do dedo — referência para "dedo dobrado") 
# Evitar erro de confusão pinça/punho fechado
PIP_INDICADOR = 6
PIP_MEDIO     = 10
PIP_ANELAR    = 14
PIP_MINDINHO  = 18

# Articulação MCP do indicador — referência de largura da palma
MCP_INDICADOR = 9

# Ponta do nariz (Face Landmarker)
NARIZ_IDX = 1

# Limiar de distância para detecção de pinça (em coordenadas normalizadas 0–1)
LIMIAR_PINCA = 0.055

# =============================================================================
# MAPA COMPLETO: bitmask (dedão, indicador, médio, anelar, mindinho) → nome
# Todas as 32 combinações nomeadas. Combinações sem nome convencional recebem
# um identificador descritivo para uso no config.json.
# =============================================================================

MAPA_GESTOS = {
    # ── Mão totalmente fechada / aberta ──────────────────────────────────────
    (0, 0, 0, 0, 0): "MAO_FECHADA",
    (1, 1, 1, 1, 1): "MAO_ABERTA",

    # ── Um dedo ─────────────────────────────────────────────────────────────
    (1, 0, 0, 0, 0): "DEDAO",
    (0, 1, 0, 0, 0): "INDICADOR",
    (0, 0, 1, 0, 0): "MEDIO",
    (0, 0, 0, 1, 0): "ANELAR",
    (0, 0, 0, 0, 1): "MINDINHO",

    # ── Dois dedos ──────────────────────────────────────────────────────────
    (1, 1, 0, 0, 0): "DEDAO_INDICADOR",       # L invertido / pistola
    (1, 0, 1, 0, 0): "DEDAO_MEDIO",
    (1, 0, 0, 1, 0): "DEDAO_ANELAR",
    (1, 0, 0, 0, 1): "DEDAO_MINDINHO",
    (0, 1, 1, 0, 0): "INDICADOR_MEDIO",        # paz / tesoura
    (0, 1, 0, 1, 0): "INDICADOR_ANELAR",
    (0, 1, 0, 0, 1): "INDICADOR_MINDINHO",     # chifres do rock
    (0, 0, 1, 1, 0): "MEDIO_ANELAR",
    (0, 0, 1, 0, 1): "MEDIO_MINDINHO",
    (0, 0, 0, 1, 1): "ANELAR_MINDINHO",

    # ── Três dedos ──────────────────────────────────────────────────────────
    (1, 1, 1, 0, 0): "DEDAO_INDICADOR_MEDIO",
    (1, 1, 0, 1, 0): "DEDAO_INDICADOR_ANELAR",
    (1, 1, 0, 0, 1): "DEDAO_INDICADOR_MINDINHO",
    (1, 0, 1, 1, 0): "DEDAO_MEDIO_ANELAR",
    (1, 0, 1, 0, 1): "DEDAO_MEDIO_MINDINHO",
    (1, 0, 0, 1, 1): "DEDAO_ANELAR_MINDINHO",
    (0, 1, 1, 1, 0): "INDICADOR_MEDIO_ANELAR",
    (0, 1, 1, 0, 1): "INDICADOR_MEDIO_MINDINHO",
    (0, 1, 0, 1, 1): "INDICADOR_ANELAR_MINDINHO",
    (0, 0, 1, 1, 1): "MEDIO_ANELAR_MINDINHO",

    # ── Quatro dedos ────────────────────────────────────────────────────────
    (1, 1, 1, 1, 0): "QUATRO_SEM_MINDINHO",
    (1, 1, 1, 0, 1): "QUATRO_SEM_ANELAR",
    (1, 1, 0, 1, 1): "QUATRO_SEM_MEDIO",
    (1, 0, 1, 1, 1): "QUATRO_SEM_INDICADOR",
    (0, 1, 1, 1, 1): "QUATRO_SEM_DEDAO",       # quatro dedos / número 4
}

# Gestos de pinça (detecção por distância, ignoram bitmask)
# Chave: qual dedo está próximo do dedão
MAPA_PINCAS = {
    PONTA_INDICADOR: "PINCA_INDICADOR",   # pinça clássica
    PONTA_MEDIO:     "PINCA_MEDIO",
    PONTA_ANELAR:    "PINCA_ANELAR",
    PONTA_MINDINHO:  "PINCA_MINDINHO",
}

# Gesto especial de rosto
GESTO_ROSTO = "ROSTO"

# Gesto de calibração (dupla pinça simultânea)
GESTO_CALIBRACAO = "CALIBRACAO"

# Sentinel para nenhum gesto detectado
GESTO_DESCONHECIDO = "DESCONHECIDO"

# =============================================================================
# FUNÇÕES DE DETECÇÃO BASE
# =============================================================================

def _dist(lm_a, lm_b) -> float:
    """Distância euclidiana normalizada entre dois landmarks."""
    return math.hypot(lm_a.x - lm_b.x, lm_a.y - lm_b.y)


def is_dedo_estendido(lm, ponta_idx: int, pip_idx: int) -> bool:
    """
    Retorna True se o dedo está estendido.
    Critério: ponta do dedo tem Y menor (mais alto na tela) que a articulação PIP.
    Funciona para indicador, médio, anelar e mindinho.
    """
    return lm[ponta_idx].y < lm[pip_idx].y


def is_dedao_estendido(lm) -> bool:
    """
    Polegar usa deslocamento lateral (eixo X) em relação à base da palma.
    Referência: MCP do indicador (landmark 9) como âncora da palma.
    Threshold calibrado para ~10% da largura normalizada da mão.
    """
    return abs(lm[PONTA_DEDAO].x - lm[MCP_INDICADOR].x) > 0.1


def get_finger_mask(lm) -> tuple:
    """
    Retorna a bitmask de 5 bits como tupla:
    (dedão, indicador, médio, anelar, mindinho)
    Cada posição: 1 = estendido, 0 = dobrado.
    """
    return (
        1 if is_dedao_estendido(lm)                              else 0,
        1 if is_dedo_estendido(lm, PONTA_INDICADOR, PIP_INDICADOR) else 0,
        1 if is_dedo_estendido(lm, PONTA_MEDIO,     PIP_MEDIO)     else 0,
        1 if is_dedo_estendido(lm, PONTA_ANELAR,    PIP_ANELAR)    else 0,
        1 if is_dedo_estendido(lm, PONTA_MINDINHO,  PIP_MINDINHO)  else 0,
    )


def detectar_pinca(lm) -> str | None:
    """
    Verifica se algum dedo está em pinça com o dedão.
    Prioridade: indicador > médio > anelar > mindinho.
    Retorna o nome da pinça ou None se não houver.

    A pinça exige que o dedão esteja estendido (afastado da palma)
    E que a distância ponta-a-ponta seja menor que LIMIAR_PINCA.
    Isso evita falso-positivo com o punho fechado, onde o dedão fica
    recolhido e colado ao anelar — a distância pode ser pequena mas
    is_dedao_estendido() retornará False.
    """
    if not is_dedao_estendido(lm):
        return None

    for ponta_idx, nome in MAPA_PINCAS.items():
        if _dist(lm[PONTA_DEDAO], lm[ponta_idx]) < LIMIAR_PINCA:
            return nome

    return None


# =============================================================================
# CLASSIFICADOR PRINCIPAL
# =============================================================================

def classificar_gesto(lm) -> str:
    """
    Classifica o gesto de uma mão a partir dos landmarks do MediaPipe.

    Ordem de prioridade:
    1. Pinça  (distância + dedão estendido)
    2. Bitmask de 5 bits → lookup em MAPA_GESTOS
    3. DESCONHECIDO se a combinação não estiver mapeada

    Args:
        lm: lista de landmarks (hand_landmarks[i]) com atributos .x, .y, .z

    Returns:
        str: nome do gesto (chave para uso no config.json)
    """
    pinca = detectar_pinca(lm)
    if pinca:
        return pinca

    mask = get_finger_mask(lm)
    return MAPA_GESTOS.get(mask, GESTO_DESCONHECIDO)


# =============================================================================
# UTILIDADE: calibração de dupla pinça
# =============================================================================

def is_dupla_pinca(gesto_esq: str, gesto_dir: str) -> bool:
    """
    Retorna True se ambas as mãos estão fazendo PINCA_INDICADOR simultaneamente.
    Usado para recalibrar o centro do nariz no engine.py.
    """
    return gesto_esq == "PINCA_INDICADOR" and gesto_dir == "PINCA_INDICADOR"


# =============================================================================
# UTILIDADE: listar todos os gestos disponíveis (para a GUI)
# =============================================================================

def listar_gestos() -> list[str]:
    """
    Retorna lista ordenada de todos os nomes de gestos disponíveis,
    incluindo pinças, rosto e o sentinel DESCONHECIDO.
    Usado pela GUI para popular os dropdowns de seleção.
    """
    gestos = sorted(set(MAPA_GESTOS.values()))
    gestos += sorted(set(MAPA_PINCAS.values()))
    gestos += [GESTO_ROSTO]
    return gestos


# =============================================================================
# DEBUG / TESTE LOCAL - Exibição de todos os gestos mapeados
# =============================================================================

if __name__ == "__main__":
    print("=== Mapa completo de gestos (32 combinações) ===\n")
    print(f"{'Bitmask':<30} {'Nome do Gesto'}")
    print("-" * 55)

    for mask, nome in sorted(MAPA_GESTOS.items()):
        bits = f"(D={mask[0]} I={mask[1]} M={mask[2]} A={mask[3]} Mi={mask[4]})"
        print(f"{bits:<30} {nome}")

    print("\n=== Pinças (detecção por distância) ===\n")
    for ponta, nome in MAPA_PINCAS.items():
        print(f"  Landmark [{ponta}] próximo ao dedão [4] → {nome}")

    print(f"\n=== Gesto especial de rosto ===")
    print(f"  {GESTO_ROSTO}")

    print(f"\n=== Calibração ===")
    print(f"  Dupla PINCA_INDICADOR simultânea → recentraliza o nariz")

    print(f"\n=== Total de gestos únicos ===")
    print(f"  Bitmask:  {len(MAPA_GESTOS)}")
    print(f"  Pinças:   {len(MAPA_PINCAS)}")
    print(f"  Rosto:    1")
    print(f"  Total:    {len(MAPA_GESTOS) + len(MAPA_PINCAS) + 1}")

    print(f"\n=== Lista para GUI ===")
    for g in listar_gestos():
        print(f"  {g}")