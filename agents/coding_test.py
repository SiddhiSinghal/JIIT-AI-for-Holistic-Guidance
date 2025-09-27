# agents/coding_test.py
import random, subprocess, os, shlex

QUESTIONS = [
    "Reverse a string.",
    "Check if a number is prime.",
    "Print the first n Fibonacci numbers.",
    "Find factorial of a number."
]

EXPECTED = {
    "Reverse a string.": "gnirts",
    "Check if a number is prime.": "Prime",
    "Find factorial of a number.": "120",
    "Print the first n Fibonacci numbers.": "0 1 1 2 3"
}

def get_random_question():
    return random.choice(QUESTIONS)

def evaluate_code(code_text: str, question: str, custom_input: str = ""):
    """
    Writes code_text to user_code.cpp, tries to compile and run (requires g++).
    Returns (output, marks)
    """
    fname = "user_code.cpp"
    out_exe = "./user_code.out"
    try:
        with open(fname, "w") as f:
            f.write(code_text)
        compile_cmd = ["g++", fname, "-o", "user_code.out"]
        cp = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=20)
        if cp.returncode != 0:
            return (cp.stderr, 0)
        run = subprocess.run([out_exe], input=custom_input, capture_output=True, text=True, timeout=5)
        output = run.stdout.strip()
        marks = 100 if output == EXPECTED.get(question, "") else 50
        return (output, marks)
    except Exception as e:
        return (str(e), 0)
