/* multi_bp.c - Multiple breakpoint testing */

int operation1(int x) {
    return x + 10;  /* Line 4 */
}

int operation2(int x) {
    return x * 2;  /* Line 8 */
}

int operation3(int x) {
    return x - 5;  /* Line 12 */
}

int main() {
    int value = 20;
    value = operation1(value);  /* Line 17 */
    value = operation2(value);  /* Line 18 */
    value = operation3(value);  /* Line 19 */

    /* Sequential operations for multiple breakpoints */
    value = value + 1;  /* Line 22 */
    value = value + 2;  /* Line 23 */
    value = value + 3;  /* Line 24 */

    return value;
}
