from langchain.tools import tool

@tool
def add_numbers(a: int, b: int) -> int:
    "Add two numbers and return results."
    return int(a) + int(b)

@tool
def subtract_numbers(a: int, b: int) -> int:
    "Subtract two numbers and return results."
    return int(a) - int(b)

@tool
def multiply_numbers(a: int, b: int) -> int:
    "Multiply two numbers and return results."
    return int(a) * int(b)

tools = [add_numbers, subtract_numbers, multiply_numbers]