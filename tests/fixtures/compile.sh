#!/bin/bash
# Compilation script for DGB test programs using Watcom

WATCOM=/c/watcom
WCC386=$WATCOM/binnt/wcc386.exe
WCL386=$WATCOM/binnt/wcl386.exe
OUTDIR=bin32

echo "Compiling test programs with Watcom DWARF 2 debug info..."
echo ""

# Compile loops.exe
echo "[1/6] Compiling loops.exe..."
$WCC386 -d2 -hw -zc -bt=nt src/loops.c -fo=$OUTDIR/loops.obj
$WCL386 -d2 -hw -l=nt $OUTDIR/loops.obj -fe=$OUTDIR/loops.exe
rm $OUTDIR/loops.obj

# Compile functions.exe
echo "[2/6] Compiling functions.exe..."
$WCC386 -d2 -hw -zc -bt=nt src/functions.c -fo=$OUTDIR/functions.obj
$WCL386 -d2 -hw -l=nt $OUTDIR/functions.obj -fe=$OUTDIR/functions.exe
rm $OUTDIR/functions.obj

# Compile multi_bp.exe
echo "[3/6] Compiling multi_bp.exe..."
$WCC386 -d2 -hw -zc -bt=nt src/multi_bp.c -fo=$OUTDIR/multi_bp.obj
$WCL386 -d2 -hw -l=nt $OUTDIR/multi_bp.obj -fe=$OUTDIR/multi_bp.exe
rm $OUTDIR/multi_bp.obj

# Compile crash.exe
echo "[4/6] Compiling crash.exe..."
$WCC386 -d2 -hw -zc -bt=nt src/crash.c -fo=$OUTDIR/crash.obj
$WCL386 -d2 -hw -l=nt $OUTDIR/crash.obj -fe=$OUTDIR/crash.exe
rm $OUTDIR/crash.obj

# Compile testdll.dll
echo "[5/6] Compiling testdll.dll..."
$WCC386 -d2 -hw -zc -bt=nt -bd -i=$WATCOM/h -i=$WATCOM/h/nt src/testdll.c -fo=$OUTDIR/testdll.obj
$WCL386 -d2 -hw -l=nt -bd $OUTDIR/testdll.obj -fe=$OUTDIR/testdll.dll
rm $OUTDIR/testdll.obj

# Compile testdll_user.exe
echo "[6/6] Compiling testdll_user.exe..."
$WCC386 -d2 -hw -zc -bt=nt -i=$WATCOM/h -i=$WATCOM/h/nt src/testdll_user.c -fo=$OUTDIR/testdll_user.obj
$WCL386 -d2 -hw -l=nt $OUTDIR/testdll_user.obj -fe=$OUTDIR/testdll_user.exe
rm $OUTDIR/testdll_user.obj

echo ""
echo "========================================"
echo "Compilation successful!"
echo "========================================"
echo "All test programs compiled to $OUTDIR/ with DWARF 2 debug info"
echo ""
ls -lh $OUTDIR/*.exe $OUTDIR/*.dll
