[Setup]
AppId=AudioLoopbackTester
AppName=Audio Loopback Tester
AppVersion=0.1.0
DefaultDirName={autopf}\AudioLoopbackTester
DefaultGroupName=Audio Loopback Tester
OutputDir=..\dist\installers
OutputBaseFilename=AudioLoopbackTester-windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\AudioLoopbackTester.exe

[Files]
Source: "..\dist\AudioLoopbackTester\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Audio Loopback Tester"; Filename: "{app}\AudioLoopbackTester.exe"

[Run]
Filename: "{app}\AudioLoopbackTester.exe"; Description: "Launch Audio Loopback Tester"; Flags: nowait postinstall skipifsilent