/* testdll_user.c - Executable that loads testdll.dll for multi-module debugging */

#include <windows.h>
#include <stdio.h>

/* Function pointer types for DLL functions */
typedef int (*DllFunction1Type)(int);
typedef int (*DllFunction2Type)(int, int);

int main() {
    HINSTANCE hDll;
    DllFunction1Type DllFunc1;
    DllFunction2Type DllFunc2;
    int result1, result2;

    /* Load the DLL */
    hDll = LoadLibrary("testdll.dll");  /* Line 17 - DLL load point */
    if (hDll == NULL) {
        return 1;  /* DLL not found */
    }

    /* Get function pointers */
    DllFunc1 = (DllFunction1Type)GetProcAddress(hDll, "DllFunction1");
    DllFunc2 = (DllFunction2Type)GetProcAddress(hDll, "DllFunction2");

    if (DllFunc1 == NULL || DllFunc2 == NULL) {
        FreeLibrary(hDll);
        return 2;  /* Functions not found */
    }

    /* Call DLL functions */
    result1 = DllFunc1(10);  /* Line 32 - calls into DLL */
    result2 = DllFunc2(5, 7);  /* Line 33 - calls into DLL */

    /* Free the DLL */
    FreeLibrary(hDll);

    return result1 + result2;
}
