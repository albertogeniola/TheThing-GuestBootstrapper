#define PROG_NAME "Guest Agent Bootstrapper"
#define GUEST_CONTROLLER_DOWNLOAD_PATH "C:\GuestController"
#define START_COMMAND "InstallerAnalyzer1_Guest.exe"

[Setup]
AppName={#PROG_NAME}
AppVersion=0.1
DefaultDirName={pf}\{#PROG_NAME}
DefaultGroupName={#PROG_NAME}
UninstallDisplayIcon={app}\uninstall.exe
Compression=lzma2
SolidCompression=yes
OutputDir=..\dist
LicenseFile=license.rtf
SetupIconFile=icon.ico
OutputBaseFilename=agent_setup

[Files]
; Core python files to be installed/extracted into program files directory
Source: "..\..\ClientBootstrapper\src\bootstrapper.py"; DestDir: "{app}"; DestName: "bootstrapper.py";
Source: "..\..\ClientBootstrapper\requirements.txt"; DestDir: "{app}"; DestName: "requirements.txt";

; Python 2.7 dep.
Source: "dist\python-2.7.9.msi"; DestDir: "{tmp}"; Flags: deleteafterinstall

; .NET and C++ dependencies
Source: "dist\vc_2013_x86.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "dist\vc_2015_x86.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "dist\dotNetFx40_Full_x86_x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run] 
Filename: msiexec.exe; Parameters: "/i ""{tmp}\python-2.7.9.msi"" /passive /norestart ALLUSERS=1"; Check: MissingPython; Flags: runhidden shellexec waituntilterminated; StatusMsg: "Installing Python 2.7"
Filename: {tmp}\dotNetFx40_Full_x86_x64.exe; Parameters: "/passive /norestart /msioptions ""ALLUSERS=1"""; Check: MissingDotNET; Flags: runhidden shellexec waituntilterminated; StatusMsg: "Installing .NET Framework 4.0"
Filename: {tmp}\vc_2013_x86.exe; Parameters: "/install /passive /norestart"; Check: MissingVc2013; Flags: shellexec waituntilterminated; StatusMsg: "Installing Visual C++ 2013 redistributable package."
Filename: {tmp}\vc_2015_x86.exe; Parameters: "/install /passive /norestart"; Check: MissingVc2015; Flags: shellexec waituntilterminated; StatusMsg: "Installing Visual C++ 2015 redistributable package"
Filename: "schtasks.exe"; Parameters: "/F /RL HIGHEST /create /TN ""GuestAgent Bootstrapper"" /SC ONLOGON /TR ""{code:GetPythonPath}python.exe \""{app}\bootstrapper.py\"" \""{#GUEST_CONTROLLER_DOWNLOAD_PATH}\"" \""{#START_COMMAND}\"""""; Flags: shellexec waituntilterminated; StatusMsg: "Setting up autostart."
Filename: "{code:GetPythonPath}scripts\pip.exe"; Parameters: "install -r ""{app}\requirements.txt"""; Flags: shellexec waituntilterminated; StatusMsg: "Setting up autostart."

[Code]
// If python is installed, returns its path. Otherwise returns empty string.
function GetPythonPath(Param: String):String;
var 
path: String;
begin
    if RegQueryStringValue(HKLM32, 'SOFTWARE\Python\PythonCore\2.7\InstallPath', '', path) then
    begin
       Result := path;
    end
    else
    begin
       Result := '';
    end;
end;

// Check if python is available on this system
function MissingPython():Boolean;
begin
    if GetPythonPath('')='' then
    begin
       Result := True;
    end
    else
    begin
       Result := False;
    end;
end;

// Check if VC++2013 32bit is installed on the local system
function MissingVc2013():Boolean;
var 
uuid: String;
begin 
    if RegQueryStringValue(HKLM32, 'SOFTWARE\Classes\Installer\Dependencies\{f65db027-aff3-4070-886a-0d87064aabb1}', '', uuid) then
    begin
       if uuid = '{f65db027-aff3-4070-886a-0d87064aabb1}' then begin
          Result := False;
       end else begin
          Result := True;
       end
    end else begin
       Result := True;
    end;
end;

function MissingVc2015():Boolean;
var 
uuid: String;
begin 
    if RegQueryStringValue(HKLM32, 'SOFTWARE\Classes\Installer\Dependencies\{d992c12e-cab2-426f-bde3-fb8c53950b0d}', '', uuid) then
    begin
       if uuid = '{d992c12e-cab2-426f-bde3-fb8c53950b0d}' then begin
          Result := False;
       end else begin
          Result := True;
       end
    end else begin
       Result := True;
    end;
end;
 
// Check if .NET is installed on the local system
function MissingDotNET():Boolean;
var 
installed: Cardinal;
begin
    if RegQueryDWordValue(HKLM32, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full', 'Install', installed) then
    begin
       if installed = 1 then begin
          Result := False;
       end else begin
          Result := True;
       end
    end else begin
       Result := True;
    end;
end;
