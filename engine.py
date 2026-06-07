"""
engine.py — Motor de visão computacional
Autor: Guivieira26

Responsabilidades:
- Captura de câmera e inferência MediaPipe (rosto + mãos)
- Classificação de gestos via gestos.py
- Leitura do config.json (mapeamento gesto → ação do controle)
- Execução das ações no controle virtual vgamepad (Xbox 360)
- HUD OpenCV com trackbars de sensibilidade e zona morta

O analógico direito é SEMPRE reservado ao rosto (nariz).
O analógico esquerdo é mapeável via config.json.
A calibração do centro do nariz ocorre por dupla PINCA_INDICADOR simultânea.

config.json NÃO define os gestos — apenas vincula nome_do_gesto → ação_do_controle.
Os gestos são definidos inteiramente em gestos.py.
Se config.json não existir, o engine inicia em modo monitor (sem ações mapeadas).
"""

import cv2
import mediapipe as mp
import time
import math
import json
import vgamepad as vg

from pathlib import Path
from urllib.request import urlretrieve

from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import face_landmarker as mp_face_landmarker
from mediapipe.tasks.python.vision import hand_landmarker as mp_hand_landmarker
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
from mediapipe.tasks.python.vision import drawing_styles as mp_drawing_styles
from mediapipe.tasks.python.vision import drawing_utils as mp_drawing

from gestos import classificar_gesto, is_dupla_pinca, GESTO_ROSTO

# =============================================================================
# CAMINHOS
# =============================================================================

BASE_DIR        = Path(__file__).parent
MODELS_DIR      = BASE_DIR / "models"
CONFIG_PATH     = BASE_DIR / "config.json"

FACE_MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
FACE_MODEL_PATH = MODELS_DIR / "face_landmarker.task"
HAND_MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
HAND_MODEL_PATH = MODELS_DIR / "hand_landmarker.task"

# =============================================================================
# AÇÕES DISPONÍVEIS DO CONTROLE
# Estas são as strings que o config.json usa como valores.
# Cada uma mapeia para uma função de execução em EXECUTOR_MAP (abaixo).
# =============================================================================

ACOES_CONTROLE = [
    # Botões face
    "BTN_A", "BTN_B", "BTN_X", "BTN_Y",
    # Bumpers
    "BTN_LB", "BTN_RB",
    # Start / Select
    "BTN_START", "BTN_SELECT",
    # L3 / R3
    "BTN_L3", "BTN_R3",
    # Gatilhos (valor máximo)
    "GATILHO_LT", "GATILHO_RT",
    # D-Pad
    "DPAD_CIMA", "DPAD_BAIXO", "DPAD_ESQ", "DPAD_DIR",
    # Analógico esquerdo
    "ANALOG_ESQ_CIMA", "ANALOG_ESQ_BAIXO", "ANALOG_ESQ_ESQ", "ANALOG_ESQ_DIR",
    # Reservado — não usar no config.json
    # "ANALOG_DIR_*" → sempre controlado pelo rosto
]

# =============================================================================
# DOWNLOAD DE MODELOS
# =============================================================================

def baixar_modelos() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if not FACE_MODEL_PATH.exists():
        print("[engine] Baixando modelo de rosto...")
        urlretrieve(FACE_MODEL_URL, FACE_MODEL_PATH)
    if not HAND_MODEL_PATH.exists():
        print("[engine] Baixando modelo de mãos...")
        urlretrieve(HAND_MODEL_URL, HAND_MODEL_PATH)

# =============================================================================
# CONFIG.JSON
# Estrutura esperada:
# {
#   "ESQ_MAO_ABERTA":  "ANALOG_ESQ_CIMA",
#   "ESQ_MAO_FECHADA": "ANALOG_ESQ_BAIXO",
#   "DIR_PINCA_INDICADOR": "GATILHO_RT",
#   "DIR_MAO_ABERTA":  "BTN_A",
#   ...
# }
# Chaves: prefixo ESQ_ ou DIR_ + nome do gesto de gestos.py
# Valores: uma das strings em ACOES_CONTROLE
# =============================================================================

def carregar_config() -> dict:
    """
    Lê o config.json e retorna o mapeamento {gesto_prefixado: ação}.
    Se não existir, retorna dicionário vazio (modo monitor).
    """
    if not CONFIG_PATH.exists():
        print("[engine] config.json não encontrado — iniciando em modo monitor (sem ações mapeadas).")
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    mapeamentos = {k: v for k, v in cfg.items() if not k.startswith("_")}
    print(f"[engine] config.json carregado — {len(mapeamentos)} mapeamentos.")
    return cfg


def ler_flag_inverter_x(config: dict) -> bool:
    """
    Lê a flag 'inverter_x_rosto' do config.json.
    True  → movimento para direita move a câmera para a esquerda (e vice-versa).
    False → comportamento padrão.
    Ausente no config → False.
    """
    return bool(config.get("inverter_x_rosto", False))

# =============================================================================
# EXECUTOR DE AÇÕES
# Recebe o controle virtual e o nome da ação, executa o comando vgamepad.
# Separado em press e release para que botões possam ser mantidos pressionados
# enquanto o gesto estiver ativo e soltos ao sair.
# =============================================================================

_BUTTON_MAP = {
    "BTN_A":      vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "BTN_B":      vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "BTN_X":      vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "BTN_Y":      vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "BTN_LB":     vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "BTN_RB":     vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "BTN_START":  vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "BTN_SELECT": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "BTN_L3":     vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "BTN_R3":     vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "DPAD_CIMA":  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "DPAD_BAIXO": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "DPAD_ESQ":   vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "DPAD_DIR":   vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
}

_TRIGGER_ACOES  = {"GATILHO_LT", "GATILHO_RT"}
_ANALOG_ESQ     = {"ANALOG_ESQ_CIMA", "ANALOG_ESQ_BAIXO", "ANALOG_ESQ_ESQ", "ANALOG_ESQ_DIR"}


def executar_acoes_ativas(controle, acoes_ativas: set, acoes_anteriores: set) -> None:
    """
    Compara o conjunto de ações do frame atual com o anterior.
    - Ações novas  → press / ativar
    - Ações saindo → release / zerar
    Garante que botões não sejam re-pressionados desnecessariamente a cada frame.
    """
    entrando = acoes_ativas - acoes_anteriores
    saindo   = acoes_anteriores - acoes_ativas

    for acao in entrando:
        _press(controle, acao)

    for acao in saindo:
        _release(controle, acao)


def _press(controle, acao: str) -> None:
    if acao in _BUTTON_MAP:
        controle.press_button(button=_BUTTON_MAP[acao])
    elif acao == "GATILHO_LT":
        controle.left_trigger_float(value_float=1.0)
    elif acao == "GATILHO_RT":
        controle.right_trigger_float(value_float=1.0)
    elif acao == "ANALOG_ESQ_CIMA":
        controle.left_joystick_float(x_value_float=0.0, y_value_float=1.0)
    elif acao == "ANALOG_ESQ_BAIXO":
        controle.left_joystick_float(x_value_float=0.0, y_value_float=-1.0)
    elif acao == "ANALOG_ESQ_ESQ":
        controle.left_joystick_float(x_value_float=-1.0, y_value_float=0.0)
    elif acao == "ANALOG_ESQ_DIR":
        controle.left_joystick_float(x_value_float=1.0, y_value_float=0.0)


def _release(controle, acao: str) -> None:
    if acao in _BUTTON_MAP:
        controle.release_button(button=_BUTTON_MAP[acao])
    elif acao == "GATILHO_LT":
        controle.left_trigger_float(value_float=0.0)
    elif acao == "GATILHO_RT":
        controle.right_trigger_float(value_float=0.0)
    elif acao in _ANALOG_ESQ:
        # Zera o analógico esquerdo apenas se nenhuma outra direção está ativa
        controle.left_joystick_float(x_value_float=0.0, y_value_float=0.0)

# =============================================================================
# CÁLCULO DO ANALÓGICO DIREITO (rosto)
# =============================================================================

def calcular_analogico_rosto(
    nariz_pos: tuple,
    centro: tuple,
    largura: int,
    altura: int,
    sensibilidade: float,
    zona_morta: int,
    inverter_x: bool = False,
) -> tuple[float, float]:
    """
    Converte a posição do nariz em valores de analógico (-1.0 a 1.0).
    Retorna (analog_x, analog_y).

    O sinal base de X já é invertido por causa do espelhamento da câmera.
    Se inverter_x=True, aplica uma segunda inversão — útil para jogos que
    não têm opção de inverter o eixo X da câmera internamente.
    """
    delta_x = nariz_pos[0] - centro[0]
    delta_y = nariz_pos[1] - centro[1]

    analog_x = 0.0
    analog_y = 0.0

    sinal_x = 1 if inverter_x else -1  # -1 = padrão (espelhado), 1 = invertido

    if abs(delta_x) > zona_morta:
        analog_x = sinal_x * (delta_x / (largura / 2)) * sensibilidade
    if abs(delta_y) > zona_morta:
        analog_y = (-delta_y / (altura / 2)) * sensibilidade

    analog_x = max(-1.0, min(1.0, analog_x))
    analog_y = max(-1.0, min(1.0, analog_y))
    return analog_x, analog_y

# =============================================================================
# HUD — desenho de informações na janela OpenCV
# =============================================================================

JANELA = "CV Engine"

def _noop(val): pass  # callback vazio para trackbars


def criar_janela() -> None:
    cv2.namedWindow(JANELA)
    cv2.createTrackbar("Sensib. (x10)", JANELA, 30, 80, _noop)
    cv2.createTrackbar("Zona Morta",    JANELA, 20, 100, _noop)


def ler_hud() -> tuple[float, int]:
    sens = max(0.1, cv2.getTrackbarPos("Sensib. (x10)", JANELA) / 10.0)
    zona = cv2.getTrackbarPos("Zona Morta", JANELA)
    return sens, zona


def desenhar_hud(
    frame,
    largura: int,
    nariz_pos: tuple | None,
    centro: tuple,
    zona_morta: int,
    gesto_esq: str,
    gesto_dir: str,
    acoes_ativas: set,
    calibrando: bool,
) -> None:
    x_centro_esp = int(largura - centro[0])
    y_centro     = int(centro[1])

    cv2.rectangle(
        frame,
        (x_centro_esp - zona_morta, y_centro - zona_morta),
        (x_centro_esp + zona_morta, y_centro + zona_morta),
        (255, 0, 0), 2,
    )

    if nariz_pos:
        x_esp = largura - nariz_pos[0]
        cv2.circle(frame, (x_esp, nariz_pos[1]), 8, (0, 255, 0), -1)
        cv2.putText(frame, f"Nariz: X:{x_esp} Y:{nariz_pos[1]}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    if calibrando:
        cv2.putText(frame, "CALIBRANDO CENTRO...",
                    (x_centro_esp - 110, y_centro - 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.putText(frame, f"ESQ: {gesto_esq}", (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    cv2.putText(frame, f"DIR: {gesto_dir}", (10, 95),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    if acoes_ativas:
        acoes_str = "  ".join(sorted(acoes_ativas))
        cv2.putText(frame, f"[{acoes_str}]", (10, 125),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)


def desenhar_hud_inverter(frame, largura: int, inverter_x: bool) -> None:
    """Exibe indicador de inversão no canto superior direito do frame."""
    label = "X: INVERTIDO" if inverter_x else "X: normal"
    cor   = (0, 100, 255) if inverter_x else (160, 160, 160)
    cv2.putText(frame, label, (largura - 160, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, cor, 2)

# =============================================================================
# LOOP PRINCIPAL
# =============================================================================

def main() -> None:
    baixar_modelos()
    config    = carregar_config()
    inverter_x = ler_flag_inverter_x(config)

    controle = vg.VX360Gamepad()

    cap     = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Centro inicial do nariz = meio da tela
    centro = [largura / 2, altura / 2]

    face_options = mp_face_landmarker.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(FACE_MODEL_PATH)),
        running_mode=VisionTaskRunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.6,
        min_face_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    hand_options = mp_hand_landmarker.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(HAND_MODEL_PATH)),
        running_mode=VisionTaskRunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    criar_janela()
    acoes_anteriores: set = set()

    with (
        mp_face_landmarker.FaceLandmarker.create_from_options(face_options) as face_mesh,
        mp_hand_landmarker.HandLandmarker.create_from_options(hand_options) as hand_tracker,
    ):
        while cap.isOpened():
            sucesso, frame = cap.read()
            if not sucesso:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            timestamp = int(time.time() * 1000)

            res_rosto = face_mesh.detect_for_video(mp_image, timestamp)
            res_maos  = hand_tracker.detect_for_video(mp_image, timestamp)

            sensibilidade, zona_morta = ler_hud()

            # ------------------------------------------------------------------
            # ROSTO — posição do nariz
            # ------------------------------------------------------------------
            nariz_pos = None
            if res_rosto.face_landmarks:
                for face_lm in res_rosto.face_landmarks:
                    ponta = face_lm[1]
                    nariz_pos = (int(ponta.x * largura), int(ponta.y * altura))
                    mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_lm,
                        connections=mp_face_landmarker.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style(),
                    )

            # ------------------------------------------------------------------
            # MÃOS — classificação de gestos
            # ------------------------------------------------------------------
            gesto_esq = "NENHUM"
            gesto_dir = "NENHUM"

            if res_maos.hand_landmarks:
                for lm_list, handedness in zip(res_maos.hand_landmarks, res_maos.handedness):
                    lado_camera = handedness[0].category_name
                    gesto = classificar_gesto(lm_list)

                    # MediaPipe: "Right" na câmera = mão esquerda real (espelhado)
                    if lado_camera == "Right":
                        gesto_esq = gesto
                    else:
                        gesto_dir = gesto

                    mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=lm_list,
                        connections=mp_hand_landmarker.HandLandmarksConnections.HAND_CONNECTIONS,
                        connection_drawing_spec=mp_drawing_styles.get_default_hand_connections_style(),
                    )

            # ------------------------------------------------------------------
            # CALIBRAÇÃO — dupla pinça simultânea recentra o nariz
            # ------------------------------------------------------------------
            calibrando = False
            if is_dupla_pinca(gesto_esq, gesto_dir) and nariz_pos:
                calibrando = True
                centro[0]  = nariz_pos[0]
                centro[1]  = nariz_pos[1]
                gesto_esq  = "NENHUM"   # bloqueia mapeamento no frame de calibração
                gesto_dir  = "NENHUM"

            # ------------------------------------------------------------------
            # ANALÓGICO DIREITO — sempre o rosto
            # ------------------------------------------------------------------
            if nariz_pos:
                ax, ay = calcular_analogico_rosto(
                    nariz_pos, centro, largura, altura,
                    sensibilidade, zona_morta, inverter_x,
                )
                controle.right_joystick_float(x_value_float=ax, y_value_float=ay)
            else:
                controle.right_joystick_float(x_value_float=0.0, y_value_float=0.0)

            # ------------------------------------------------------------------
            # MAPEAMENTO CONFIG.JSON — gesto → ação do controle
            # Chave no config: "ESQ_<GESTO>" ou "DIR_<GESTO>"
            # ------------------------------------------------------------------
            acoes_ativas: set = set()

            chave_esq = f"ESQ_{gesto_esq}"
            chave_dir = f"DIR_{gesto_dir}"

            if chave_esq in config:
                acoes_ativas.add(config[chave_esq])
            if chave_dir in config:
                acoes_ativas.add(config[chave_dir])

            executar_acoes_ativas(controle, acoes_ativas, acoes_anteriores)
            acoes_anteriores = acoes_ativas.copy()
            controle.update()

            # ------------------------------------------------------------------
            # HUD E EXIBIÇÃO
            # ------------------------------------------------------------------
            frame_flip = cv2.flip(frame, 1)
            desenhar_hud(
                frame_flip, largura, nariz_pos, centro,
                zona_morta, gesto_esq, gesto_dir, acoes_ativas, calibrando,
            )
            desenhar_hud_inverter(frame_flip, largura, inverter_x)

            cv2.imshow(JANELA, frame_flip)
            if cv2.waitKey(5) & 0xFF == 27:  # ESC para sair
                break

    cap.release()
    cv2.destroyAllWindows()
    del controle
    print("[engine] Encerrado.")


if __name__ == "__main__":
    main()