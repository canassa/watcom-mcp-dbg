/* functions.c - Multiple function calls for testing call hierarchy */

int level3(int x) {
    return x * 2;  /* Line 4 - deepest function */
}

int level2(int x) {
    int result = level3(x + 1);  /* Line 8 */
    return result + 5;
}

int level1(int x) {
    int temp = level2(x);  /* Line 13 */
    return temp * 3;
}

int compute(int a, int b) {
    int val1 = level1(a);  /* Line 18 */
    int val2 = level1(b);  /* Line 19 */
    return val1 + val2;
}

int main() {
    int result = compute(5, 10);  /* Line 24 */

    if (result > 100) {
        result = result - 10;
    }

    return result;
}
