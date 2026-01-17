@echo off
REM Watcom compilation script for DGB test programs
REM Compiles all C programs with DWARF 2 debug info (-d2 -hd)

setlocal

REM Set Watcom path
set WATCOM=c:\watcom
set PATH=%WATCOM%\binnt;%WATCOM%\binw;%PATH%
set INCLUDE=%WATCOM%\h;%WATCOM%\h\nt

REM Output directory
set OUTDIR=bin32

REM Compilation flags:
REM -d2 = Full debugging info (DWARF 2)
REM -hd = DWARF debug format (appends ELF container with DWARF sections)
REM -zc = Place literals in code segment
REM -bt=nt = Build target Windows NT
REM -bd = Build DLL (for testdll.c)
REM wlink debug all = Include full debug info in executable

echo Compiling test programs with Watcom DWARF 2 debug info...
echo.

REM Compile variables.exe
echo [1/8] Compiling variables.exe...
wcc386 -d2 -hd -zc -bt=nt src\variables.c -fo=%OUTDIR%\variables.obj
if errorlevel 1 goto error
wlink debug all option quiet system nt file %OUTDIR%\variables.obj name %OUTDIR%\variables.exe
if errorlevel 1 goto error
del %OUTDIR%\variables.obj

REM Compile simple.exe
echo [2/8] Compiling simple.exe...
wcc386 -d2 -hd -zc -bt=nt src\simple.c -fo=%OUTDIR%\simple.obj
if errorlevel 1 goto error
wlink debug all option quiet system nt file %OUTDIR%\simple.obj name %OUTDIR%\simple.exe
if errorlevel 1 goto error
del %OUTDIR%\simple.obj

REM Compile loops.exe
echo [3/8] Compiling loops.exe...
wcc386 -d2 -hd -zc -bt=nt src\loops.c -fo=%OUTDIR%\loops.obj
if errorlevel 1 goto error
wlink debug all option quiet system nt file %OUTDIR%\loops.obj name %OUTDIR%\loops.exe
if errorlevel 1 goto error
del %OUTDIR%\loops.obj

REM Compile functions.exe
echo [4/8] Compiling functions.exe...
wcc386 -d2 -hd -zc -bt=nt src\functions.c -fo=%OUTDIR%\functions.obj
if errorlevel 1 goto error
wlink debug all option quiet system nt file %OUTDIR%\functions.obj name %OUTDIR%\functions.exe
if errorlevel 1 goto error
del %OUTDIR%\functions.obj

REM Compile multi_bp.exe
echo [5/8] Compiling multi_bp.exe...
wcc386 -d2 -hd -zc -bt=nt src\multi_bp.c -fo=%OUTDIR%\multi_bp.obj
if errorlevel 1 goto error
wlink debug all option quiet system nt file %OUTDIR%\multi_bp.obj name %OUTDIR%\multi_bp.exe
if errorlevel 1 goto error
del %OUTDIR%\multi_bp.obj

REM Compile crash.exe
echo [6/8] Compiling crash.exe...
wcc386 -d2 -hd -zc -bt=nt src\crash.c -fo=%OUTDIR%\crash.obj
if errorlevel 1 goto error
wlink debug all option quiet system nt file %OUTDIR%\crash.obj name %OUTDIR%\crash.exe
if errorlevel 1 goto error
del %OUTDIR%\crash.obj

REM Compile testdll.dll
echo [7/8] Compiling testdll.dll...
wcc386 -d2 -hd -zc -bt=nt -bd src\testdll.c -fo=%OUTDIR%\testdll.obj
if errorlevel 1 goto error
wlink @src\testdll.lnk file %OUTDIR%\testdll.obj name %OUTDIR%\testdll.dll
if errorlevel 1 goto error
del %OUTDIR%\testdll.obj

REM Compile testdll_user.exe
echo [8/8] Compiling testdll_user.exe...
wcc386 -d2 -hd -zc -bt=nt src\testdll_user.c -fo=%OUTDIR%\testdll_user.obj
if errorlevel 1 goto error
wlink debug all option quiet system nt file %OUTDIR%\testdll_user.obj name %OUTDIR%\testdll_user.exe
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
