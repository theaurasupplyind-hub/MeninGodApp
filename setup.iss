; setup.iss
; Installer de MVP 1.0 para Windows — generado con Inno Setup 6.x
;
; Uso:
;   1. Correr PyInstaller primero:  pyinstaller build.spec
;   2. Confirmar que existe:        dist\MVP_1.0\MVP_1.0.exe
;   3. Compilar este script con Inno Setup Compiler (ISCC.exe o GUI)
;
; Estructura esperada antes de compilar:
;   dist\MVP_1.0\      ← salida de PyInstaller (toda la carpeta)
;   assets\icon.ico     ← ícono de la aplicación
;   assets\banner.bmp   ← imagen superior del wizard (497x58 px, 24-bit BMP)  [opcional]
;   assets\wizard.bmp   ← imagen lateral del wizard (164x314 px, 24-bit BMP)  [opcional]
;   LICENSE.txt         ← texto de licencia mostrado en el instalador           [opcional]

; ---------------------------------------------------------------------------
#define MyAppName        "MVP 1.0"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "TheAuraSupply(JESU)"
#define MyAppURL         "https://tusitio.com"
#define MyAppExeName     "MVP_1.0.exe"
#define MyAppId          "{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"
; ↑ Reemplazá el GUID con uno nuevo generado en:
;   Tools → Generate GUID  (Inno Setup Compiler)
;   o en PowerShell:  [guid]::NewGuid()

; ---------------------------------------------------------------------------
[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Directorio de instalación por defecto
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Nombre del instalador generado (en la raíz del proyecto)
OutputBaseFilename=MVP_1.0_Setup_{#MyAppVersion}
OutputDir=installer_output

; Compresión
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Requerir privilegios de administrador para instalar en Program Files
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Plataforma mínima: Windows 10
MinVersion=10.0

; Arquitectura: x64
ArchitecturesInstallIn64BitMode=x64compatible

; Mostrar asistente moderno
WizardStyle=modern

; Imágenes del wizard (descomentá si tenés los archivos)
; WizardImageFile=assets\wizard.bmp
; WizardSmallImageFile=assets\banner.bmp

; Ícono del instalador (sin ícono personalizado)
; SetupIconFile=assets\icon.ico

; Desinstalar desde Panel de Control
Uninstallable=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
CreateUninstallRegKey=yes

; No cerrar otras apps automáticamente
CloseApplications=no

; Información del archivo EXE de salida
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Instalador de {#MyAppName}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; ---------------------------------------------------------------------------
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

; ---------------------------------------------------------------------------
[Tasks]
Name: "desktopicon";    Description: "Crear acceso directo en el &Escritorio"; GroupDescription: "Íconos adicionales:"; Flags: checkedonce
Name: "startmenuicon";  Description: "Crear acceso directo en el &Menú de inicio"; GroupDescription: "Íconos adicionales:"

; ---------------------------------------------------------------------------
[Files]
Source: "dist\MVP_1.0\*";  DestDir: "{app}";  Flags: ignoreversion recursesubdirs createallsubdirs

; ---------------------------------------------------------------------------
[Dirs]
Name: "{app}\assets\generated"
Name: "{app}\db"

; ---------------------------------------------------------------------------
[Icons]
Name: "{group}\{#MyAppName}";             Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: startmenuicon
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}";        Tasks: startmenuicon
Name: "{autodesktop}\{#MyAppName}";       Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; ---------------------------------------------------------------------------
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName} ahora"; Flags: nowait postinstall skipifsilent

; ---------------------------------------------------------------------------
[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: skipifdoesntexist runhidden

; ---------------------------------------------------------------------------
[UninstallDelete]
Type: filesandordirs; Name: "{app}\assets\generated"
Type: filesandordirs; Name: "{app}\mvp10_debug.log"

; ---------------------------------------------------------------------------
[Messages]
WelcomeLabel1=Bienvenido al asistente de instalación de [name]
WelcomeLabel2=Este asistente instalará [name/ver] en tu equipo.%n%nSe recomienda cerrar todas las aplicaciones antes de continuar.
FinishedHeadingLabel=Instalación completada
FinishedLabel={#MyAppName} fue instalado correctamente en tu equipo.

; ---------------------------------------------------------------------------
; Para compilar desde línea de comandos:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
