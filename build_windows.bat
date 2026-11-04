@echo off
REM ============================================================
REM  Assistente Virtual — compilar o .exe para Windows
REM  Requer Python 3.12 instalado (py -3.12 --version)
REM  Resultado: dist\AssistenteVirtual.exe
REM ============================================================

echo.
echo === 1/3  Dependencias ===
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
py -3.12 -m pip install pyinstaller

echo.
echo === 2/3  Verificar ffmpeg ===
if not exist "ffmpeg\bin\ffmpeg.exe" (
    echo AVISO: ffmpeg\bin\ffmpeg.exe nao existe.
    echo        A musica continua a funcionar, mas a conversao/extraccao falha.
    echo        Descarrega em https://www.gyan.dev/ffmpeg/builds/ e copia
    echo        ffmpeg.exe + ffprobe.exe para ffmpeg\bin\
)

echo.
echo === 3/3  PyInstaller ===
py -3.12 -m PyInstaller assistente_virtual.spec --noconfirm --clean

if exist "dist\AssistenteVirtual.exe" (
    echo.
    echo OK!  dist\AssistenteVirtual.exe
    dir /b dist\AssistenteVirtual.exe
) else (
    echo.
    echo ERRO: o executavel nao foi gerado.
    exit /b 1
)
pause
