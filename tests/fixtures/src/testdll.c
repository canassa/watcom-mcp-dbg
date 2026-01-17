/* testdll.c - Simple DLL with exported functions for multi-module debugging */

#include <windows.h>

/* DLL exported function 1 */
__declspec(dllexport) int DllFunction1(int x) {
    int result = x * 2;  /* Line 7 - DLL breakpoint target */
    return result;
}

/* DLL exported function 2 */
__declspec(dllexport) int DllFunction2(int a, int b) {
    int sum = a + b;  /* Line 13 - another DLL breakpoint target */
    return sum * 3;
}

/* DLL entry point */
BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
    switch (fdwReason) {
        case DLL_PROCESS_ATTACH:
            /* DLL loaded */
            break;
        case DLL_PROCESS_DETACH:
            /* DLL unloaded */
            break;
        case DLL_THREAD_ATTACH:
        case DLL_THREAD_DETACH:
            break;
    }
    return TRUE;
}
