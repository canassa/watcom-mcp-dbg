/* testdll_user.c - Executable that loads testdll.dll for multi-module debugging */

#include <windows.h>
#include <stdio.h>

/* Function pointer types for DLL functions */
typedef int (*DllFunction1Type)(int);
typedef int (*DllFunction2Type)(int, int);
typedef int (*DllFunction3Type)(int, int, int);

int main() {
    HINSTANCE hDll;
    DllFunction1Type DllFunc1;
    DllFunction2Type DllFunc2;
    DllFunction3Type DllFunc3;
    int result1, result2, result3;

    /* Load the DLL */
    hDll = LoadLibrary("testdll.dll");  /* Line 17 - DLL load point */
    if (hDll == NULL) {
        return 1;  /* DLL not found */
    }

    /* Get function pointers */
    DllFunc1 = (DllFunction1Type)GetProcAddress(hDll, "DllFunction1");
    DllFunc2 = (DllFunction2Type)GetProcAddress(hDll, "DllFunction2");
    DllFunc3 = (DllFunction3Type)GetProcAddress(hDll, "DllFunction3");

    if (DllFunc1 == NULL || DllFunc2 == NULL || DllFunc3 == NULL) {
        FreeLibrary(hDll);
        return 2;  /* Functions not found */
    }

    /* Call DLL functions */
    result1 = DllFunc1(10);  /* Line 35 - calls into DLL */
    result2 = DllFunc2(5, 7);  /* Line 36 - calls into DLL */
    result3 = DllFunc3(1, 2, 3);  /* Line 37 - calls into DLL with register args */

    /* Free the DLL */
    FreeLibrary(hDll);

    return result1 + result2 + result3;
}
