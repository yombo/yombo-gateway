#!/usr/bin/env python3
"""
Shows the performance differences between creating lists and tuples, as well as accessing them.

Results:
Creations:
Tuple: 0.08209210599306971
List: 0.5055116860894486

Access:
Tuple: 0.1949025789508596
List: 0.1922776399878785

Explanation:
Tuples are typically faster to create, but tend to be slower to access. However, lists are typically faster to access.

"""
import timeit

print("Creations:")
print(f"Tuple: {timeit.timeit('x=(1,2,3,4,5,6,7,8)', number=10000000)}")
print(f"List: {timeit.timeit('x=[1,2,3,4,5,6,7,8]', number=10000000)}")

print("\nAccess:")
print(f"Tuple: {timeit.timeit('y=x[3]', 'x=(1,2,3,4,5,6,7,8)', number=10000000)}")
print(f"List: {timeit.timeit('y=x[3]', 'x=[1,2,3,4,5,6,7,8]', number=10000000)}")
