/* loops.c - Loop constructs for testing breakpoints in iterations */

int main() {
    int i;
    int sum = 0;

    /* Test breakpoint in for loop */
    for (i = 0; i < 5; i++) {
        sum = sum + i;  /* Line 9 - loop breakpoint target */
    }

    /* Test breakpoint in while loop */
    i = 0;
    while (i < 3) {
        sum = sum + 1;  /* Line 15 - while loop breakpoint */
        i++;
    }

    /* Test breakpoint in do-while loop */
    i = 0;
    do {
        sum = sum + 2;  /* Line 22 - do-while breakpoint */
        i++;
    } while (i < 2);

    return sum;
}
