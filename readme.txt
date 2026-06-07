Projeto: Rastreador de rosto e mãos (Rastreador)

Descrição:
Este projeto demonstra detecção e rastreamento de pontos faciais e marcações
das mãos usando MediaPipe e OpenCV, e envia controles simulados via vgamepad
para testar interação com aplicações que aceitem entrada de gamepad virtual.

Proposta do projeto:
- Explorar controle por gestos e movimentos do rosto para prototipagem rápida.
- Servir como base de testes para integrações entre visão computacional e
  controladores virtuais.

Tecnologias utilizadas:
- Python 3 (recomendado: 3.10–3.11; foi testado localmente em 3.14)
- OpenCV (opencv-python)
- MediaPipe
- vgamepad

Como executar (Windows):
1) Abra um terminal PowerShell na pasta do projeto.
2) Ative a virtualenv do projeto:
   .\.venv\Scripts\Activate.ps1
   (Se o PowerShell bloquear a execução, rode: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
3) Instale as dependências (se ainda não instaladas):
   python -m pip install -r requirements.txt
4) Execute o script principal:
   python rastreador.py

Observações importantes:
- Os modelos binários usados pelo MediaPipe são baixados automaticamente
  para a pasta `models/` na primeira execução.
- Esta versão NÃO possui mapeamento dinâmico de funções; os botões e ações
  são pré-definidos no código apenas para fins de teste e demonstração.
  Se pretende um mapeamento personalizável, será necessário implementar
  uma camada de configuração ou interface para associar gestos a ações.
  (Estou trabalhando nesses tópicos)
- Para encerrar, pressione `Esc` na janela do OpenCV.

Licença e uso:
- Uso experimental e educacional. Não há garantias de funcionamento em todos
  os sistemas; teste em ambiente controlado primeiro.

