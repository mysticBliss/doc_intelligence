
import httpx
import time
import sys
import os

OLLAMA_URL = "http://ollama:11434/api/tags"

def is_ollama_ready():
    try:
        response = httpx.get(OLLAMA_URL, timeout=1)
        return response.status_code == 200
    except httpx.RequestError:
        return False

if __name__ == "__main__":
    while not is_ollama_ready():
        print("Ollama is unavailable - sleeping", file=sys.stderr)
        time.sleep(1)

    print("Ollama is up - executing command", file=sys.stderr)
    exec_args = sys.argv[1:]
    os.execvp(exec_args[0], exec_args)