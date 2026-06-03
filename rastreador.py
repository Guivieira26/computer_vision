import cv2
import mediapipe as mp
import time
from pathlib import Path
from urllib.request import urlretrieve

from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import drawing_styles as mp_drawing_styles
from mediapipe.tasks.python.vision import drawing_utils as mp_drawing
from mediapipe.tasks.python.vision import face_landmarker as mp_face_landmarker
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
)
MODEL_PATH = Path(__file__).with_name("models") / "face_landmarker.task"

def ensure_model() -> str:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        print("Baixando o modelo do Face Landmarker pela primeira vez...")
        urlretrieve(MODEL_URL, MODEL_PATH)
    return str(MODEL_PATH)

# Capturando a webcam (mantivemos o DSHOW para o Windows não chiar)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Configurando o modelo de Face Landmarker
options = mp_face_landmarker.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=ensure_model()),
    running_mode=VisionTaskRunningMode.VIDEO,
    num_faces=1,
    min_face_detection_confidence=0.6,
    min_face_presence_confidence=0.6,
    min_tracking_confidence=0.6,
)

with mp_face_landmarker.FaceLandmarker.create_from_options(options) as face_mesh:

    while cap.isOpened():
        sucesso, frame = cap.read()
        if not sucesso:
            print("Ignorando frame vazio da câmera.")
            continue

        # O OpenCV lê a imagem em BGR, mas o MediaPipe precisa de RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # Fazendo a detecção
        resultados = face_mesh.detect_for_video(mp_image, int(time.time() * 1000))

        # Se encontrou um rosto, vamos desenhar!
        if resultados.face_landmarks:
            for face_landmarks in resultados.face_landmarks:
                
                # --- 1. O SEGREDO PARA O JOGO (O Nariz) ---
                # Acessamos o índice 1 direto da lista
                ponta_nariz = face_landmarks[1]
                
                altura, largura, _ = frame.shape
                coord_x = int(ponta_nariz.x * largura)
                coord_y = int(ponta_nariz.y * altura)

                # Desenhando o nosso "joystick" (círculo verde destacado no nariz)
                cv2.circle(frame, (coord_x, coord_y), 8, (0, 255, 0), -1)
                cv2.putText(frame, f"Nariz: X:{coord_x} Y:{coord_y}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # --- 2. DESENHO DA MALHA (Apenas visual) ---
                # Passando a lista nativa diretamente para a função da API nova!
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_face_landmarker.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style())

        # Mostra o resultado na tela espelhado (flip) para ficar mais natural
        cv2.imshow('Rastreamento de Camera', cv2.flip(frame, 1))

        # Pressione 'ESC' para sair
        if cv2.waitKey(5) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()