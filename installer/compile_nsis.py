"""
Compile NSIS installer from a clean ASCII temp path.
Workaround for NSIS encoding issues with Chinese characters in project path.

Usage: python installer/compile_nsis.py [--version 1.0.0]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(SCRIPT_DIR, 'build')
NSI_TEMPLATE = os.path.join(SCRIPT_DIR, 'installer.nsi')

# NSIS installer path
MAKENSIS_PATHS = [
    r'C:\Program Files (x86)\NSIS\makensis.exe',
    r'C:\Program Files\NSIS\makensis.exe',
]

NSI_CONTENT = r'''Unicode true

; ============================================================
; PathMind NSIS Installer Script
; ============================================================

!include "MUI2.nsh"
!include "x64.nsh"

!define APP_NAME "${{APP_NAME}}"
!define APP_VERSION "{version}"
!define APP_PUBLISHER "PathMind"
!define APP_EXE_NAME "pythonw.exe"
!define APP_DATA_DIR "$APPDATA\${{APP_NAME}}"
!define OLD_APP_NAME "${{OLD_APP_NAME}}"
!define UNINSTALL_REG "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{APP_NAME}}"

Name "${{APP_NAME}}"
OutFile "{output_file}"
InstallDir "$PROGRAMFILES64\${{APP_NAME}}"
InstallDirRegKey HKLM "${{UNINSTALL_REG}}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

; UI config
!define MUI_ABORTWARNING
!define MUI_ICON "{build_dir}\icon.ico"
!define MUI_UNICON "{build_dir}\icon.ico"

; Finish page: use custom function to launch app
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchApp"
!define MUI_FINISHPAGE_RUN_TEXT "${{APP_NAME}}"

; Install pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstall pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "SimpChinese"

; ============================================================
; Functions
; ============================================================
Function LaunchApp
    Exec '"$INSTDIR\python\pythonw.exe" "$INSTDIR\launcher.pyw"'
FunctionEnd

; ============================================================
; Install Section
; ============================================================
Section "MainApp" SecMain
    SetOutPath "$INSTDIR"

    ; === Migrate old version data ===
    IfFileExists "$APPDATA\${{OLD_APP_NAME}}\*.*" 0 skip_migrate
        IfFileExists "${{APP_DATA_DIR}}\*.*" skip_migrate
        Rename "$APPDATA\${{OLD_APP_NAME}}" "${{APP_DATA_DIR}}"
    skip_migrate:
    ; Clean old shortcuts and registry
    Delete "$DESKTOP\${{OLD_APP_NAME}}.lnk"
    RMDir /r "$SMPROGRAMS\${{OLD_APP_NAME}}"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{OLD_APP_NAME}}"

    ; Copy all files
    File /r "{build_dir}\python"
    File /r "{build_dir}\app"
    File "{build_dir}\run.py"
    File "{build_dir}\config.yaml.example"
    File "{build_dir}\launcher.pyw"
    File "{build_dir}\stop_server.bat"
    File "{build_dir}\debug_launch.bat"
    File "{build_dir}\icon.ico"

    ; Create user data directory
    CreateDirectory "${{APP_DATA_DIR}}"
    CreateDirectory "${{APP_DATA_DIR}}\data"

    ; Copy config on first install
    IfFileExists "${{APP_DATA_DIR}}\config.yaml" skip_config
        CopyFiles /SILENT "$INSTDIR\config.yaml.example" "${{APP_DATA_DIR}}\config.yaml"
    skip_config:

    ; Desktop shortcut
    CreateShortCut "$DESKTOP\${{APP_NAME}}.lnk" \
        "$INSTDIR\python\${{APP_EXE_NAME}}" \
        '"$INSTDIR\launcher.pyw"' \
        "$INSTDIR\icon.ico" 0

    ; Start Menu
    CreateDirectory "$SMPROGRAMS\${{APP_NAME}}"
    CreateShortCut "$SMPROGRAMS\${{APP_NAME}}\${{APP_NAME}}.lnk" \
        "$INSTDIR\python\${{APP_EXE_NAME}}" \
        '"$INSTDIR\launcher.pyw"' \
        "$INSTDIR\icon.ico" 0
    CreateShortCut "$SMPROGRAMS\${{APP_NAME}}\Uninstall.lnk" \
        "$INSTDIR\uninstall.exe" "" \
        "$INSTDIR\icon.ico" 0

    ; Registry (Add/Remove Programs)
    WriteRegStr HKLM "${{UNINSTALL_REG}}" "DisplayName" "${{APP_NAME}}"
    WriteRegStr HKLM "${{UNINSTALL_REG}}" "DisplayVersion" "${{APP_VERSION}}"
    WriteRegStr HKLM "${{UNINSTALL_REG}}" "Publisher" "${{APP_PUBLISHER}}"
    WriteRegStr HKLM "${{UNINSTALL_REG}}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${{UNINSTALL_REG}}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "${{UNINSTALL_REG}}" "DisplayIcon" "$INSTDIR\icon.ico"
    WriteRegDWORD HKLM "${{UNINSTALL_REG}}" "NoModify" 1
    WriteRegDWORD HKLM "${{UNINSTALL_REG}}" "NoRepair" 1

    ; Uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; ============================================================
; Uninstall Section
; ============================================================
Section "Uninstall"
    ; Stop running service
    nsExec::ExecToLog '"$INSTDIR\stop_server.bat"'

    ; Delete program files
    RMDir /r "$INSTDIR\python"
    RMDir /r "$INSTDIR\app"
    Delete "$INSTDIR\run.py"
    Delete "$INSTDIR\config.yaml.example"
    Delete "$INSTDIR\launcher.pyw"
    Delete "$INSTDIR\stop_server.bat"
    Delete "$INSTDIR\debug_launch.bat"
    Delete "$INSTDIR\icon.ico"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"

    ; Delete shortcuts
    Delete "$DESKTOP\${{APP_NAME}}.lnk"
    Delete "$SMPROGRAMS\${{APP_NAME}}\${{APP_NAME}}.lnk"
    Delete "$SMPROGRAMS\${{APP_NAME}}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${{APP_NAME}}"

    ; Delete registry
    DeleteRegKey HKLM "${{UNINSTALL_REG}}"

    ; Ask to delete user data
    MessageBox MB_YESNO|MB_ICONQUESTION \
        "Delete user data (database, screenshots, config)?$\n$\nData location: ${{APP_DATA_DIR}}" \
        IDNO skip_data
        RMDir /r "${{APP_DATA_DIR}}"
    skip_data:
SectionEnd
'''


def find_makensis():
    """Find makensis.exe"""
    exe = shutil.which('makensis')
    if exe:
        return exe
    for p in MAKENSIS_PATHS:
        if os.path.exists(p):
            return p
    return None


def main():
    parser = argparse.ArgumentParser(description='Compile NSIS installer')
    parser.add_argument('--version', default='1.0.0', help='Version (default: 1.0.0)')
    args = parser.parse_args()

    makensis = find_makensis()
    if not makensis:
        print('[ERROR] makensis.exe not found. Install NSIS 3.x first.')
        sys.exit(1)

    if not os.path.isdir(BUILD_DIR):
        print(f'[ERROR] Build directory not found: {BUILD_DIR}')
        print('Run build_installer.py --skip-nsis first.')
        sys.exit(1)

    print(f'[NSIS] makensis: {makensis}')
    print(f'[NSIS] build dir: {BUILD_DIR}')
    print(f'[NSIS] version: {args.version}')

    # Create temp directory with ASCII-only path
    temp_base = os.path.join(tempfile.gettempdir(), 'pathmind_nsis')
    if os.path.exists(temp_base):
        print(f'[NSIS] Cleaning old temp dir: {temp_base}')
        shutil.rmtree(temp_base, ignore_errors=True)

    temp_build = os.path.join(temp_base, 'build')
    print(f'[NSIS] Copying build files to temp: {temp_base}')
    shutil.copytree(BUILD_DIR, temp_build)

    # Output file path (in temp dir for compilation, move later)
    output_filename = f'PathMind_Setup_v{args.version}.exe'
    temp_output = os.path.join(temp_base, output_filename)

    # Generate NSI file with UTF-8 BOM in temp dir
    app_name = '\u8def\u5f84\u667a\u6167\u5e93'  # 路径智慧库
    build_dir_nsis = temp_build.replace('\\', '/')
    output_nsis = temp_output.replace('\\', '/')

    nsi_content = NSI_CONTENT.format(
        version=args.version,
        build_dir=build_dir_nsis,
        output_file=output_nsis,
    )
    # Replace ${{...}} with ${...} (our escape for Python .format())
    nsi_content = nsi_content.replace('${{', '${').replace('}}', '}')
    # Insert actual APP_NAME
    nsi_content = nsi_content.replace('${APP_NAME}', app_name, 1)  # Only the !define line
    # Actually, we need to be smarter - only the !define value should have the Chinese name,
    # all other ${APP_NAME} references will be expanded by NSIS itself.
    # Let's rewrite: in the !define line, APP_NAME should be the literal Chinese string
    # The rest uses ${APP_NAME} which NSIS resolves.

    # Reset - build NSI content properly
    nsi_content = NSI_CONTENT.format(
        version=args.version,
        build_dir=build_dir_nsis,
        output_file=output_nsis,
    )
    nsi_content = nsi_content.replace('${{', '${').replace('}}', '}')

    # Now fix the APP_NAME define line specifically
    # The template has: !define APP_NAME "${APP_NAME}" which after our replace becomes
    # !define APP_NAME "${APP_NAME}". We need the define to have the actual Chinese string.
    # Let's use a different placeholder approach.

    # Actually, let me reconsider the template. The issue is that ${APP_NAME} in the template
    # is both a Python format placeholder AND an NSIS variable. Let me use a unique placeholder.
    nsi_content = nsi_content.replace(
        '!define APP_NAME "${APP_NAME}"',
        f'!define APP_NAME "{app_name}"'
    )
    old_app_name = '\u4ea7\u54c1\u4f7f\u7528\u8def\u5f84\u77e5\u8bc6\u5e93'  # 产品使用路径知识库
    nsi_content = nsi_content.replace(
        '!define OLD_APP_NAME "${OLD_APP_NAME}"',
        f'!define OLD_APP_NAME "{old_app_name}"'
    )

    nsi_path = os.path.join(temp_base, 'installer.nsi')
    # Write with UTF-8 BOM - NSIS 3.x detects this as UTF-8
    with open(nsi_path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
        f.write(nsi_content.encode('utf-8'))

    print(f'[NSIS] Generated NSI: {nsi_path}')
    print(f'[NSIS] Compiling...')

    # Run makensis
    result = subprocess.run(
        [makensis, nsi_path],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )

    print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
    if result.stderr:
        print('[STDERR]', result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)

    if result.returncode != 0:
        print(f'[ERROR] makensis failed with code {result.returncode}')
        print(f'[INFO] NSI file kept at: {nsi_path}')
        sys.exit(1)

    # Move output to installer directory
    final_output = os.path.join(SCRIPT_DIR, output_filename)
    if os.path.exists(temp_output):
        shutil.move(temp_output, final_output)
        size_mb = os.path.getsize(final_output) / (1024 * 1024)
        print(f'[NSIS] SUCCESS! Installer: {final_output}')
        print(f'[NSIS] Size: {size_mb:.1f} MB')
    else:
        print(f'[ERROR] Output file not found: {temp_output}')
        sys.exit(1)

    # Cleanup temp
    shutil.rmtree(temp_base, ignore_errors=True)
    print('[NSIS] Temp files cleaned up.')


if __name__ == '__main__':
    main()
