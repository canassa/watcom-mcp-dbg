/*
 * Comprehensive test program for variable inspection.
 * Tests all basic types, arrays, pointers, structs, and edge cases.
 */

#include <stdio.h>
#include <string.h>

/* Global variables */
int global_int = 100;
char global_char = 'G';

/* Struct definition */
struct Point {
    int x;
    int y;
};

/* Function with basic types */
int test_basic_types() {
    char c = 'A';
    signed char sc = -5;
    unsigned char uc = 200;

    short s = -1000;
    unsigned short us = 50000;

    int i = -42;
    unsigned int ui = 3000000000u;

    long l = -100000L;
    unsigned long ul = 4000000000UL;

    float f = 3.14f;
    double d = 2.718281828;

    return i;  /* BREAKPOINT LINE: test_basic_types */
}

/* Function with pointers */
int test_pointers() {
    int value;
    int* ptr;
    int** ptr_ptr;
    char str[] = "Hello";
    char* str_ptr;
    void* void_ptr;

    value = 42;
    ptr = &value;
    ptr_ptr = &ptr;
    str_ptr = str;
    void_ptr = &value;

    return *ptr;  /* BREAKPOINT LINE: test_pointers */
}

/* Function with arrays */
int test_arrays() {
    int int_array[5] = {10, 20, 30, 40, 50};
    char char_array[10] = "Test";

    int matrix[3][3] = {
        {1, 2, 3},
        {4, 5, 6},
        {7, 8, 9}
    };

    return int_array[2];  /* BREAKPOINT LINE: test_arrays */
}

/* Function with struct */
int test_struct() {
    struct Point p;
    struct Point* p_ptr;

    p.x = 10;
    p.y = 20;
    p_ptr = &p;

    return p.x + p.y;  /* BREAKPOINT LINE: test_struct */
}

/* Function with parameters */
int add(int a, int b) {
    int result = a + b;
    return result;  /* BREAKPOINT LINE: add */
}

/* Function with many parameters */
int multi_param(int a, int b, int c, int d, int e) {
    int sum = a + b + c + d + e;
    return sum;  /* BREAKPOINT LINE: multi_param */
}

/* Function with mixed types */
int test_mixed(char ch, int num, float fval) {
    char local_char = ch + 1;
    int local_int = num * 2;
    float local_float = fval + 1.0f;

    return local_int;  /* BREAKPOINT LINE: test_mixed */
}

/* Function with zero values */
int test_zeros() {
    int zero_int = 0;
    char zero_char = '\0';
    float zero_float = 0.0f;
    int* null_ptr = 0;

    return zero_int;  /* BREAKPOINT LINE: test_zeros */
}

/* Function with negative values */
int test_negatives() {
    int neg_int = -42;
    signed char neg_char = -100;
    short neg_short = -30000;
    float neg_float = -3.14f;

    return neg_int;  /* BREAKPOINT LINE: test_negatives */
}

/* Function with max values */
int test_max_values() {
    unsigned char max_uchar = 255;
    unsigned short max_ushort = 65535;
    unsigned int max_uint = 0xFFFFFFFF;

    return max_uchar;  /* BREAKPOINT LINE: test_max_values */
}

/* Function with local variables only */
int test_locals_only() {
    int x = 10;
    int y = 20;
    int z = 30;
    int result = x + y + z;

    return result;  /* BREAKPOINT LINE: test_locals_only */
}

/* Function with parameters only */
int test_params_only(int p1, int p2, int p3) {
    return p1 + p2 + p3;  /* BREAKPOINT LINE: test_params_only */
}

/* Function with both locals and params */
int test_locals_and_params(int param1, int param2) {
    int local1 = param1 * 2;
    int local2 = param2 * 3;
    int sum = local1 + local2;

    return sum;  /* BREAKPOINT LINE: test_locals_and_params */
}

/* Function testing char as int parameter */
int test_char_param(char ch) {
    int as_int = (int)ch;
    char local_ch = ch + 1;

    return as_int;  /* BREAKPOINT LINE: test_char_param */
}

/* Main function */
int main() {
    int result;

    printf("Testing basic types...\n");
    result = test_basic_types();

    printf("Testing pointers...\n");
    result = test_pointers();

    printf("Testing arrays...\n");
    result = test_arrays();

    printf("Testing structs...\n");
    result = test_struct();

    printf("Testing parameters...\n");
    result = add(10, 20);

    printf("Testing multi-parameters...\n");
    result = multi_param(1, 2, 3, 4, 5);

    printf("Testing mixed types...\n");
    result = test_mixed('A', 100, 3.14f);

    printf("Testing zeros...\n");
    result = test_zeros();

    printf("Testing negatives...\n");
    result = test_negatives();

    printf("Testing max values...\n");
    result = test_max_values();

    printf("Testing locals only...\n");
    result = test_locals_only();

    printf("Testing params only...\n");
    result = test_params_only(5, 10, 15);

    printf("Testing locals and params...\n");
    result = test_locals_and_params(7, 11);

    printf("Testing char param...\n");
    result = test_char_param('Z');

    printf("All tests complete! Result: %d\n", result);

    return 0;
}
