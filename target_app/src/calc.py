def divide(a, b):
    # Intentional bug: No check for division by zero
    if b == 0:
        print('Logging: Division by zero')
        return float('inf')
    return a / b

def add(a, b):
    return a + b
