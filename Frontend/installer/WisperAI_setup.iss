; Inno Setup Script для WisperAI
; Скачать Inno Setup: https://jrsoftware.org/isinfo.php

#define MyAppName "Wisper AI"
#define MyAppVersion "1.0"
#define MyAppPublisher "Wisper"
#define MyAppURL "https://github.com/wisper"
#define MyAppExeName "WisperAI.exe"

[Setup]
; Уникальный идентификатор приложения (сгенерируйте свой на https://www.guidgenerator.com/)
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Убираем выбор папки в меню Пуск
DisableProgramGroupPage=yes
; Лицензия и информация (опционально)
; LicenseFile=..\LICENSE.txt
; InfoBeforeFile=..\README.txt
; Выходной файл установщика
OutputDir=..\dist
OutputBaseFilename=WisperAI_Setup
; Иконка установщика
SetupIconFile=..\assets\asteroid.ico
; Сжатие
Compression=lzma2/ultra64
SolidCompression=yes
; Стиль интерфейса
WizardStyle=modern
; Требования администратора для Program Files
PrivilegesRequired=admin
; Архитектура
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Копируем все файлы из dist\WisperAI
Source: "..\dist\WisperAI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Копируем .env.settings как шаблон (пользователь заполнит свои ключи)
Source: "..\..\env.settings"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Проверка наличия .env файла после установки
procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvFile: string;
  ExampleFile: string;
begin
  if CurStep = ssPostInstall then
  begin
    EnvFile := ExpandConstant('{app}\.env');
    ExampleFile := ExpandConstant('{app}\.env.example');
    
    // Если .env не существует, копируем из примера
    if not FileExists(EnvFile) and FileExists(ExampleFile) then
    begin
      FileCopy(ExampleFile, EnvFile, False);
    end;
  end;
end;
