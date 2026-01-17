#!/bin/bash
# Compilation script for DGB test programs using Watcom

WATCOM=/c/watcom
WCC386=$WATCOM/binnt/wcc386.exe
WLINK=$WATCOM/binnt/wlink.exe
OUTDIR=bin32

echo "Compiling test programs with Watcom DWARF 2 debug info..."
echo ""

# Compile simple.exe
echo "[1/7] Compiling simple.exe..."
$WCC386 -d2 -hd -zc -bt=nt src/simple.c -fo=$OUTDIR/simple.obj
$WLINK debug all option quiet system nt file $OUTDIR/simple.obj name $OUTDIR/simple.exe
rm $OUTDIR/simple.obj

# Compile loops.exe
echo "[2/7] Compiling loops.exe..."
$WCC386 -d2 -hd -zc -bt=nt src/loops.c -fo=$OUTDIR/loops.obj
$WLINK debug all option quiet system nt file $OUTDIR/loops.obj name $OUTDIR/loops.exe
rm $OUTDIR/loops.obj

# Compile functions.exe
echo "[3/7] Compiling functions.exe..."
$WCC386 -d2 -hd -zc -bt=nt src/functions.c -fo=$OUTDIR/functions.obj
$WLINK debug all option quiet system nt file $OUTDIR/functions.obj name $OUTDIR/functions.exe
rm $OUTDIR/functions.obj

# Compile multi_bp.exe
echo "[4/7] Compiling multi_bp.exe..."
$WCC386 -d2 -hd -zc -bt=nt src/multi_bp.c -fo=$OUTDIR/multi_bp.obj
$WLINK debug all option quiet system nt file $OUTDIR/multi_bp.obj name $OUTDIR/multi_bp.exe
rm $OUTDIR/multi_bp.obj

# Compile crash.exe
echo "[5/7] Compiling crash.exe..."
$WCC386 -d2 -hd -zc -bt=nt src/crash.c -fo=$OUTDIR/crash.obj
$WLINK debug all option quiet system nt file $OUTDIR/crash.obj name $OUTDIR/crash.exe
rm $OUTDIR/crash.obj

# Compile testdll.dll
echo "[6/7] Compiling testdll.dll..."
$WCC386 -d2 -hd -zc -bt=nt -bd -i=$WATCOM/h -i=$WATCOM/h/nt src/testdll.c -fo=$OUTDIR/testdll.obj
$WLINK debug all option quiet system nt_dll file $OUTDIR/testdll.obj name $OUTDIR/testdll.dll
rm $OUTDIR/testdll.obj

# Compile testdll_user.exe
echo "[7/7] Compiling testdll_user.exe..."
$WCC386 -d2 -hd -zc -bt=nt -i=$WATCOM/h -i=$WATCOM/h/nt src/testdll_user.c -fo=$OUTDIR/testdll_user.obj
$WLINK debug all option quiet system nt file $OUTDIR/testdll_user.obj name $OUTDIR/testdll_user.exe
rm $OUTDIR/testdll_user.obj

echo ""
echo "========================================"
echo "Compilation successful!"
echo "========================================"
echo "All test programs compiled to $OUTDIR/ with DWARF 2 debug info"
echo ""
ls -lh $OUTDIR/*.exe $OUTDIR/*.dll
