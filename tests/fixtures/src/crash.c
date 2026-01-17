/* crash.c - Exception testing (access violation) */

int main() {
    int *ptr = (int*)0;  /* NULL pointer */

    /* This will cause an access violation */
    *ptr = 42;  /* Line 7 - crash point */

    return 0;  /* Never reached */
}
