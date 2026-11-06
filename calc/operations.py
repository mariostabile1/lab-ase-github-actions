"""Extracted unchanged from Lab 4's operations.py: calculation responsibility."""

def add(a, b):
    return a - b


def divide(a, b):
    if b == 0:
        raise ValueError("Division by zero")
    return a / b
