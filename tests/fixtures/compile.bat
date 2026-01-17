@echo off
REM Watcom compilation script for DGB test programs
REM Compiles all C programs with DWARF 2 debug info (-d2 -hw)

setlocal

REM Set Watcom path
set WATCOM=c:\watcom
set PATH=%WATCOM%\binnt;%WATCOM%\binw;%PATH%
set INCLUDE=%WATCOM%\h;%WATCOM%\h\nt

REM Output directory
set OUTDIR=bin32

REM Compilation flags:
REM -d2 = Full debugging info (DWARF 2)
REM -hw = Watcom debug format (appends ELF container)
REM -zc = Place literals in code segment
REM -bt=nt = Build target Windows NT
REM -bd = Build DLL (for testdll.c)
REM -l=nt = Link for Windows NT

echo Compiling test programs with Watcom DWARF 2 debug info...
echo.

REM Compile simple.exe
echo [1/7] Compiling simple.exe...
wcc386 -d2 -hw -zc -bt=nt src\simple.c -fo=%OUTDIR%\simple.obj
if errorlevel 1 goto error
wcl386 -d2 -hw -l=nt %OUTDIR%\simple.obj -fe=%OUTDIR%\simple.exe
if errorlevel 1 goto error
del %OUTDIR%\simple.obj

REM Compile loops.exe
echo [2/7] Compiling loops.exe...
wcc386 -d2 -hw -zc -bt=nt src\loops.c -fo=%OUTDIR%\loops.obj
if errorlevel 1 goto error
wcl386 -d2 -hw -l=nt %OUTDIR%\loops.obj -fe=%OUTDIR%\loops.exe
if errorlevel 1 goto error
del %OUTDIR%\loops.obj

REM Compile functions.exe
echo [3/7] Compiling functions.exe...
wcc386 -d2 -hw -zc -bt=nt src\functions.c -fo=%OUTDIR%\functions.obj
if errorlevel 1 goto error
wcl386 -d2 -hw -l=nt %OUTDIR%\functions.obj -fe=%OUTDIR%\functions.exe
if errorlevel 1 goto error
del %OUTDIR%\functions.obj

REM Compile multi_bp.exe
echo [4/7] Compiling multi_bp.exe...
wcc386 -d2 -hw -zc -bt=nt src\multi_bp.c -fo=%OUTDIR%\multi_bp.obj
if errorlevel 1 goto error
wcl386 -d2 -hw -l=nt %OUTDIR%\multi_bp.obj -fe=%OUTDIR%\multi_bp.exe
if errorlevel 1 goto error
del %OUTDIR%\multi_bp.obj

REM Compile crash.exe
echo [5/7] Compiling crash.exe...
wcc386 -d2 -hw -zc -bt=nt src\crash.c -fo=%OUTDIR%\crash.obj
if errorlevel 1 goto error
wcl386 -d2 -hw -l=nt %OUTDIR%\crash.obj -fe=%OUTDIR%\crash.exe
if errorlevel 1 goto error
del %OUTDIR%\crash.obj

REM Compile testdll.dll
echo [6/7] Compiling testdll.dll...
wcc386 -d2 -hw -zc -bt=nt -bd src\testdll.c -fo=%OUTDIR%\testdll.obj
if errorlevel 1 goto error
wcl386 -d2 -hw -l=nt -bd %OUTDIR%\testdll.obj -fe=%OUTDIR%\testdll.dll
if errorlevel 1 goto error
del %OUTDIR%\testdll.obj

REM Compile testdll_user.exe
echo [7/7] Compiling testdll_user.exe...
wcc386 -d2 -hw -zc -bt=nt src\testdll_user.c -fo=%OUTDIR%\testdll_user.obj
if errorlevel 1 goto error
wcl386 -d2 -hw -l=nt %OUTDIR%\testdll_user.obj -fe=%OUTDIR%\testdll_user.exe
if errorlevel 1 goto error
del %OUTDIR%\testdll_user.obj

echo.
echo ========================================
echo Compilation successful!
echo ========================================
echo All test programs compiled to %OUTDIR%\ with DWARF 2 debug info
echo.
dir /b %OUTDIR%\*.exe %OUTDIR%\*.dll
goto end

:error
echo.
echo ========================================
echo ERROR: Compilation failed!
echo ========================================
exit /b 1

:end
endlocal
