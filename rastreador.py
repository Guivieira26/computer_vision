import cv2
import mediapipe as mp
import time
import math
import vgamepad as vg # Virtual gamepad
from pathlib import Path
from urllib.request import urlretrieve

controle = vg.VX360Gamepad() # Inicializa o gamepad virtual como um controle Xbox 360 virtual

# Importações do rosto
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import face_landmarker as mp_face_landmarker
# Novas importações da mão
from mediapipe.tasks.python.vision import hand_landmarker as mp_hand_landmarker
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

from mediapipe.tasks.python.vision import drawing_styles as mp_drawing_styles
from mediapipe.tasks.python.vision import drawing_utils as mp_drawing

# --- 1. GERENCIAMENTO DOS MODELOS ---
MODELS_DIR = Path(__file__).with_name("models")

FACE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
FACE_MODEL_PATH = MODELS_DIR / "face_landmarker.task"

HAND_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
HAND_MODEL_PATH = MODELS_DIR / "hand_landmarker.task"

# --- CONFIGURAÇÕES DO JOYSTICK ---
ZONE_MORTA_FACE = 20 # Pixels de tolerância no centro - Evitar movimentos involuntários
# Sensibilidade: quanto maior, mais devagar a camera gira
SENSIBILIDADE_FACE = 1

def baixar_modelos():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if not FACE_MODEL_PATH.exists():
        print("Baixando modelo do Rosto...")
        urlretrieve(FACE_MODEL_URL, FACE_MODEL_PATH)
    if not HAND_MODEL_PATH.exists():
        print("Baixando modelo das Mãos...")
        urlretrieve(HAND_MODEL_URL, HAND_MODEL_PATH)

baixar_modelos()

# --- 2. LÓGICA DE DETECÇÃO DE GESTOS ---
def is_mao_aberta(hand_landmarks):
    # O eixo Y cresce para baixo na tela.
    # Se a ponta do dedo médio (12) está acima (Y menor) que a base dele (9), a mão está aberta.
    ponta_medio_y = hand_landmarks[12].y
    base_medio_y = hand_landmarks[9].y
    return ponta_medio_y < base_medio_y
def is_pinca(hand_landmarks):
    dedao = hand_landmarks[4]
    indicador = hand_landmarks[8]
    dx = dedao.x - indicador.x
    dy = dedao.y - indicador.y
    distancia = math.hypot(dx, dy)
    return distancia < 0.05  # Ajuste o valor conforme necessário

# --- 3. CONFIGURAÇÃO E LOOP PRINCIPAL ---
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# ---------------------------------------------------------
# VARIÁVEIS GLOBAIS DE CALIBRAÇÃO (Iniciam no meio da tela)
# ---------------------------------------------------------
centro_ativo_x = largura / 2
centro_ativo_y = altura / 2

# Opções do Rosto
face_options = mp_face_landmarker.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=str(FACE_MODEL_PATH)),
    running_mode=VisionTaskRunningMode.VIDEO,
    num_faces=1,
    min_face_detection_confidence=0.6,
    min_face_presence_confidence=0.6,
    min_tracking_confidence=0.6,
)

# Opções da Mão
hand_options = mp_hand_landmarker.HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=str(HAND_MODEL_PATH)),
    running_mode=VisionTaskRunningMode.VIDEO,
    num_hands=2, # Precisamos detectar as duas mãos
    min_hand_detection_confidence=0.6,
    min_hand_presence_confidence=0.6,
    min_tracking_confidence=0.6,
)



# Inicializando as duas IAs simultaneamente
with mp_face_landmarker.FaceLandmarker.create_from_options(face_options) as face_mesh, \
     mp_hand_landmarker.HandLandmarker.create_from_options(hand_options) as hand_tracker:

    # Função vazia necessária para o trackbar do OpenCV funcionar
    def atualiza_hud(val):
        pass

    # Forçamos a criação da janela com um nome fixo antes do loop
    cv2.namedWindow('Rastreamento Completo')

    # Criamos as barras de rolagem (HUD)
    # Argumentos: Nome da barra, Janela, Valor Inicial, Valor Máximo, Callback
    cv2.createTrackbar('Sensibilidade (x10)', 'Rastreamento Completo', 30, 80, atualiza_hud) 
    cv2.createTrackbar('Zona Morta', 'Rastreamento Completo', 20, 100, atualiza_hud)

    while cap.isOpened():
        sucesso, frame = cap.read()
        if not sucesso:
            continue

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        timestamp = int(time.time() * 1000)

        # Processando rosto e mãos no mesmo frame
        resultados_rosto = face_mesh.detect_for_video(mp_image, timestamp)
        resultados_maos = hand_tracker.detect_for_video(mp_image, timestamp)

        # Variáveis para guardar o estado antes de espelhar
        nariz_original = None
        estado_mao_esquerda = "Parado"
        estado_mao_direita = "Sem Acao"

        # Incluir pinças para salto e simultaneas para centralizar nariz
        pinca_esq_ativa = False
        pinca_dir_ativa = False
        
        # --- RASTREAMENTO DO ROSTO ---
        if resultados_rosto.face_landmarks:
            for face_landmarks in resultados_rosto.face_landmarks:
                ponta_nariz = face_landmarks[1]
                nariz_original = (int(ponta_nariz.x * largura), int(ponta_nariz.y * altura))
                
                mp_drawing.draw_landmarks(
                    image=frame, landmark_list=face_landmarks,
                    connections=mp_face_landmarker.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION,
                    landmark_drawing_spec=None, # <--- CORREÇÃO DOS PONTOS VERMELHOS AQUI
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style())

        # --- RASTREAMENTO DAS MÃOS ---
        if resultados_maos.hand_landmarks:
            for hand_landmarks, handedness in zip(resultados_maos.hand_landmarks, resultados_maos.handedness):
                
                lado_camera = handedness[0].category_name
                mao_aberta = is_mao_aberta(hand_landmarks)
                pinca = is_pinca(hand_landmarks)

                if lado_camera == "Right": # Sua Mão Direita Real
                    if pinca:
                        pinca_dir_ativa = True
                        estado_mao_direita = "Salto"
                    if mao_aberta:
                        estado_mao_direita = "Botao Esquerdo"
                    else:
                        estado_mao_direita = "Botao Direito"

                elif lado_camera == "Left": # Sua Mão Esquerda Real
                    if pinca:
                        pinca_esq_ativa = True
                        estado_mao_esquerda = "Salto"
                    elif mao_aberta:
                        estado_mao_esquerda = "Tras (S)"
                    else:
                        estado_mao_esquerda = "Frente (W)"

                # Desenhando o esqueleto da mão
                mp_drawing.draw_landmarks(
                    image=frame, landmark_list=hand_landmarks,
                    connections=mp_hand_landmarker.HandLandmarksConnections.HAND_CONNECTIONS,
                    connection_drawing_spec=mp_drawing_styles.get_default_hand_connections_style())

        #Calibração camera
        calibrando = False
        if pinca_esq_ativa and pinca_dir_ativa:
            calibrando = True
            if nariz_original:
                # Atualiza as variáveis globais com a posição atual do nariz
                centro_ativo_x = nariz_original[0]
                centro_ativo_y = nariz_original[1]
            
            # Neutraliza os comandos para o boneco não pular/clicar sozinho ao calibrar
            estado_mao_esquerda = "Parado"
            estado_mao_direita = "Sem Acao"

        # --- PREPARANDO A TELA FINAL ---
        frame_flipped = cv2.flip(frame, 1)

        # Desenhando o nariz
        if nariz_original:
            x_espelhado = largura - nariz_original[0]
            
            # --- LEITURA DO HUD EM TEMPO REAL ---
            hud_sensibilidade = cv2.getTrackbarPos('Sensibilidade (x10)', 'Rastreamento Completo') / 10.0
            hud_zona_morta = cv2.getTrackbarPos('Zona Morta', 'Rastreamento Completo')
            
            if hud_sensibilidade <= 0.1:
                hud_sensibilidade = 0.1

            cv2.circle(frame_flipped, (x_espelhado, nariz_original[1]), 8, (0, 255, 0), -1)
            cv2.putText(frame_flipped, f"Nariz: X:{x_espelhado} Y:{nariz_original[1]}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            x_centro_espelhado = int(largura - centro_ativo_x)
            y_centro = int(centro_ativo_y)
            
            # Quadrado Azul agora usa o tamanho dinâmico do HUD
            cv2.rectangle(frame_flipped, 
                          (x_centro_espelhado - hud_zona_morta, y_centro - hud_zona_morta),
                          (x_centro_espelhado + hud_zona_morta, y_centro + hud_zona_morta),
                          (255, 0, 0), 2)
            
            if calibrando:
                cv2.putText(frame_flipped, "CALIBRANDO CENTRO...", (x_centro_espelhado - 110, y_centro - 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # --- CÁLCULO DO ANALÓGICO COM HUD ---
            delta_x = nariz_original[0] - centro_ativo_x
            delta_y = nariz_original[1] - centro_ativo_y

            divisor_x = largura / 2
            divisor_y = altura / 2

            analog_x = 0.0
            analog_y = 0.0

            # Multiplicamos pela sensibilidade do HUD para alcançar 1.0 mais rápido
            if abs(delta_x) > hud_zona_morta:
                analog_x = -1*((delta_x / divisor_x) * hud_sensibilidade) # O sinal negativo é para inverter o movimento, já que o espelhamento inverte a direção
                
            if abs(delta_y) > hud_zona_morta:
                analog_y = (-delta_y / divisor_y) * hud_sensibilidade

            analog_x = max(-1.0, min(1.0, analog_x))
            analog_y = max(-1.0, min(1.0, analog_y))

            controle.right_joystick_float(x_value_float=analog_x, y_value_float=analog_y)
        
        # --- MAPEAMENTO DOS BOTÕES DAS MÃOS ---
        if estado_mao_direita == "Botao Esquerdo":
            # Gatilho Direito (RT - geralmente quebrar bloco/atacar) pressionado até o fundo
            controle.right_trigger_float(value_float=1.0)
        elif(estado_mao_direita == "Sem Acao"):
            controle.right_trigger_float(value_float=0.0)
            
        if estado_mao_direita == "Botao Direito":
            # Gatilho Esquerdo (LT - geralmente colocar bloco/mirar) pressionado até o fundo
            controle.left_trigger_float(value_float=1.0)
        else:
            controle.left_trigger_float(value_float=0.0)
        # if estado_mao_direita == "Salto":
        #     controle.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        # else:            
        #     controle.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)    
        if estado_mao_esquerda == "Salto":
            controle.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        else:            
            controle.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
            
        if estado_mao_esquerda == "Frente (W)":
            # Analógico esquerdo totalmente para CIMA
            controle.left_joystick_float(x_value_float=0.0, y_value_float=1.0)
            
        elif estado_mao_esquerda == "Tras (S)":
            # Analógico esquerdo totalmente para BAIXO
            controle.left_joystick_float(x_value_float=0.0, y_value_float=-1.0)
            
        else:
            # Se estiver "Parado" (ou fazendo o "Salto"), zera o analógico para o boneco parar de andar
            controle.left_joystick_float(x_value_float=0.0, y_value_float=0.0)
        
        controle.update()

        # Exibindo os comandos
        cv2.putText(frame_flipped, f"Movimento: {estado_mao_esquerda}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame_flipped, f"Acoes: {estado_mao_direita}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow('Rastreamento Completo', frame_flipped)

        if cv2.waitKey(5) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()

del controle # Certifique-se de liberar o controle virtual ao final do programa