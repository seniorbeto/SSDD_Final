from flask import Flask, render_template, request, redirect, url_for
import subprocess
import threading
import os

app = Flask(__name__)

output_log = []

path = os.path.dirname(os.path.abspath(__file__))

# Lanzamos el cliente como proceso interactivo
client_process = subprocess.Popen(
    ["python3", os.path.join(path, "../client.py"), "-s", "localhost", "-p", "4444"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    bufsize=1
)

def read_output():
    for line in client_process.stdout:
        output_log.append(line)

# Hilo para leer stdout del cliente
threading.Thread(target=read_output, daemon=True).start()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        command = request.form["command"]
        if client_process.poll() is None:
            client_process.stdin.write(command + "\n")
            client_process.stdin.flush()
        return redirect(url_for("index"))

    return render_template("index.html", output=output_log[-40:])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

