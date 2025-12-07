import os
import subprocess

def run_dangerous_actions(user_input):
    # Intentional Vulnerability 1: Command Injection
    # OpenGrep/Semgrep should flag 'shell=True' with variable input
    subprocess.call("echo " + user_input, shell=True)

    # Intentional Vulnerability 2: Eval Injection
    # OpenGrep/Semgrep should flag use of 'eval'
    eval(user_input)

    # Intentional Vulnerability 3: Hardcoded Password (sometimes caught)
    password = "correcthorsebatterystaple"
    if user_input == password:
        print("Access granted")

if __name__ == "__main__":
    run_dangerous_actions("test")
