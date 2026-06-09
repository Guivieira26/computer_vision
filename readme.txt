Projeto: CV Engine - Rastreamento de rosto e mãos com mapeamento de gestos

Descrição
Este projeto usa MediaPipe, OpenCV e vgamepad para transformar movimentos do
rosto e gestos das mãos em entrada de controle virtual. A versão atual não é
mais estática: ela possui uma GUI para configurar o mapa de gestos, salvar o
`config.json` e iniciar o motor de execução.

Como instalar e executar no Windows

Opção 1:
  Usar o instalador CVEngine_Setup_v2.2.0.exe que irá realizar a instalação dos drivers dependências
  e o executável do projeto. Caso tente iniciar o engine e ele não funcione tente instalar o driver manualemnte em drivers/ViGEmBus_1.22.0_x64_x86_arm64.exe

Opção 2:
  1. Abra um terminal PowerShell na pasta do projeto. /src
  2. Instale as dependências:

  ```bash
  python -m pip install -r requirements.txt
  ```

  3. Execute a interface principal:

  ```bash
  python gui.py
  ```

4. Na GUI, faça o mapeamento desejado, salve e clique em `Iniciar Engine`.
5. Abra o jogo e use a câmera normalmente.


O fluxo principal agora é:
1. Abrir a interface em `gui.py`.
2. Mapear os gestos desejados nos botões/ações da manete virtual.
3. Salvar a configuração ou iniciar o motor diretamente pela GUI.
4. Abrir o jogo e usar a câmera como entrada.

Principais recursos
- GUI para configuração visual do controle.
- Mapeamento de gestos para ESQ/DIR da manete.
- Gestos baseados em 5 dedos, totalizando 2^5 combinações por mão.
- Suporte adicional às pinças do dedão com indicador, médio, anelar e mindinho.
- Controle do rosto pelo nariz para o eixo analógico direito.
- Calibração do centro com dupla `PINCA_INDICADOR` simultânea.
- `config.json` personalizável, com validação de conflito de mapeamento.

![Example Image](example.png)

Como o mapeamento funciona
O arquivo `config.json` define apenas a associação entre gesto e ação do controle.
O formato esperado é:

```json
{
  "ESQ_NOME_DO_GESTO": "ACAO_DO_CONTROLE",
  "DIR_NOME_DO_GESTO": "ACAO_DO_CONTROLE"
}
```

Exemplo prático:
- `ESQ_ANALOG_ESQ_CIMA`: gesto da mão esquerda que move o analógico esquerdo para cima.
- `DIR_BTN_A`: gesto da mão direita que aciona o botão A.
- `DIR_GATILHO_RT`: gesto da mão direita que pressiona o gatilho direito.

Os gestos disponíveis são gerados por `gestos.py`. Entre eles estão:
- Gestos de 5 dedos: `MAO_FECHADA`, `MAO_ABERTA`, `INDICADOR`, `MEDIO`, `ANELAR`, `MINDINHO`, etc.
- Pinças: `PINCA_INDICADOR`, `PINCA_MEDIO`, `PINCA_ANELAR`, `PINCA_MINDINHO`.
- Gesto especial de rosto: `ROSTO`.

O `config.json` atual já vem com um mapa pré-configurado, mas o usuário tem
liberdade para montar o mapa que quiser pela GUI. O editor mostra a mão esquerda
e a mão direita separadamente, permitindo configurar o mesmo gesto em lados
diferentes quando fizer sentido.

Estrutura do projeto
- `gui.py`: interface gráfica de configuração. Permite mapear gestos, salvar o
  `config.json` e iniciar o motor.
- `engine.py`: motor principal. Lê a configuração, executa o rastreamento e
  envia as ações para a manete virtual.
- `gestos.py`: classificador dos gestos. Contém o mapa dos dedos, pinças e a
  lógica de interpretação dos landmarks da mão.
- `gestos_icones.py`: ícones SVG e categorias usados pela GUI para exibir os
  gestos de forma visual.
- `config.json`: configuração do usuário. Guarda os mapeamentos ESQ/DIR e
  opções como a inversão do eixo X do rosto.
- `models/`: modelos do MediaPipe usados pelo rosto e pelas mãos.

Configuração padrão
O projeto já vem com um `config.json` pré-configurado com uma proposta de uso
prática, baseada no meu gosto pessoal. A ideia é oferecer um ponto de partida
funcional para testes, mas sem limitar o usuário.

Comportamento principal configurado por padrão:
- Dupla `PINCA_INDICADOR` para recentralizar o eixo da câmera / nariz.
- Gestos de mão esquerda e direita podem ser atribuídos separadamente.
- A GUI evita salvar configurações inconsistentes e ajuda a manter o mapa legível.

Requisitos
- Python 3
- OpenCV (`opencv-python`)
- MediaPipe
- vgamepad
- PySide6

Observações
- Os modelos do MediaPipe são baixados automaticamente para `models/` na
  primeira execução, se ainda não existirem.
- O preview da câmera é espelhado, então a lógica de ESQ/DIR foi tratada para
  refletir o lado que o usuário vê na tela.
- Se houver conflito de mapeamento, a GUI bloqueia o salvamento e mostra um
  aviso.
- Para encerrar o motor, pressione `Esc` na janela do OpenCV.

Estado do projeto
Esta versão está próxima da versão final. O próximo passo é testar com usuários
para identificar falhas, bugs de uso e pequenos ajustes de comportamento antes
de estabilizar a entrega.

Licença e uso
Uso experimental e educacional. Teste em ambiente controlado antes de usar em
situações críticas.

