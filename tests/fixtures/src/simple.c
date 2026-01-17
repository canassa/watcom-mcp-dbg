/* simple.c - Basic program with function calls for testing breakpoints */

int add(int a, int b) {
    int result = a + b;  /* Line 4 - breakpoint target */
    return result;
}

int main() {
    int x = 5;
    int y = 10;
    int sum = add(x, y);  /* Line 11 - function call breakpoint target */

    if (sum > 10) {
        sum = sum * 2;  /* Line 14 */
    }

    return sum;
}
