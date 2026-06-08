[Setup]
AppName=Controle Por Gestos - Visão Computacional
AppVersion=2.0
DefaultDirName={autopf}\ControleGestos
DefaultGroupName=Controle de Gestos
OutputDir=Instalador_Final
OutputBaseFilename=Setup_Rastreador
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
; 1. CORREÇÃO: Copia o conteúdo da pasta inteira (note o \* no final do caminho da pasta)
Source: "G:\projects\CV\computer_vision\dist\Controle_por_Gestos_visao_computacional\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Adiciona o instalador do ViGEmBus
Source: "G:\projects\CV\computer_vision\ViGEmBus_1.22.0_x64_x86_arm64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
; (Opcional, mas recomendado) Cria um atalho na Área de Trabalho do usuário
Name: "{autodesktop}\Controle de Gestos"; Filename: "{app}\Controle_por_Gestos_visao_computacional.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na Area de Trabalho"; GroupDescription: "Atalhos adicionais:"

[Run]
; 2. CORREÇÃO: Executa o ViGEmBus direto da pasta temporária do usuário final
Filename: "{tmp}\ViGEmBus_1.22.0_x64_x86_arm64.exe"; Parameters: "/quiet /norestart"; StatusMsg: "Instalando driver do gamepad virtual (ViGEmBus)..."

; 3. CORREÇÃO: Inicia a sua aplicação ao concluir e arruma a flag cortada
Filename: "{app}\Controle_por_Gestos_visao_computacional.exe"; Description: "Iniciar Rastreador Minecraft"; Flags: nowait postinstall skipifsilent