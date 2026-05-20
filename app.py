from flask import Flask, jsonify, render_template, request
import time
import os

app = Flask(__name__)

MAX_SAMPLES = 50

# ---------------- ESTADO GLOBAL ----------------
# Historial de muestras del ADC
history = {
    "time": [],
    "adc1": []
}

# Valor del threshold controlado desde la pagina web (voltios, 0.0 a 5.0)
threshold_actual = 2.5

# Ciclo de trabajo PWM controlado desde la pagina web (porcentaje, 0 a 100)
pwm_duty = 50

# Ultimo valor del pin logico (boton) recibido del ESP32
pin23_actual = 0

# ---------------- PAGINA PRINCIPAL ----------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- ESP32 POST DATA ----------------
# El ESP32 envia sus datos aqui cada 5 segundos.
# El servidor responde con el valor actual de PWM para que el ESP32 lo aplique.
@app.route("/data", methods=["POST"])
def recibir_data():

    global history, pin23_actual, pwm_duty

    data = request.get_json()

    if not data:
        return jsonify({
            "ok": False,
            "error": "No JSON recibido"
        }), 400

    try:

        adc1  = float(data.get("adc1", 0))
        pin23 = int(data.get("pin23", 0))

        history["time"].append(time.strftime("%H:%M:%S"))
        history["adc1"].append(round(adc1, 3))

        pin23_actual = pin23

        # Mantener maximo MAX_SAMPLES muestras
        for key in history:
            if len(history[key]) > MAX_SAMPLES:
                history[key].pop(0)

        print("POST recibido:", data)

        # Responder al ESP32 con el duty cycle actual en porcentaje
        return jsonify({
            "ok":      True,
            "samples": len(history["adc1"]),
            "pwm":     pwm_duty
        })

    except Exception as e:

        return jsonify({
            "ok":    False,
            "error": str(e)
        }), 400

# ---------------- REFRESH (Servidor -> Frontend) ----------------
# La pagina web consulta este endpoint cada segundo para actualizar la grafica.
@app.route("/refresh")
def refresh():
    return jsonify({
        "adc1":      history["adc1"],
        "time":      history["time"],
        "threshold": threshold_actual,
        "pin23":     pin23_actual,
        "pwm":       pwm_duty
    })

# ---------------- RECIBIR DUTY CYCLE DESDE LA WEB ----------------
# El frontend POST aqui cuando el usuario mueve el slider de PWM.
@app.route("/dutyCycle", methods=["POST"])
def set_duty_cycle():

    global pwm_duty

    data = request.get_json()

    if not data:
        return jsonify({"ok": False, "error": "No JSON"}), 400

    try:

        valor = float(data.get("pwm", 0))

        # Limitar entre 0 y 100
        pwm_duty = max(0.0, min(100.0, valor))

        print("PWM actualizado a:", pwm_duty, "%")

        return jsonify({
            "ok":  True,
            "pwm": pwm_duty
        })

    except Exception as e:

        return jsonify({"ok": False, "error": str(e)}), 400

# ---------------- RECIBIR THRESHOLD DESDE LA WEB ----------------
# El frontend POST aqui cuando el usuario mueve el slider de threshold.
@app.route("/threshold", methods=["POST"])
def set_threshold():

    global threshold_actual

    data = request.get_json()

    if not data:
        return jsonify({"ok": False, "error": "No JSON"}), 400

    try:

        valor = float(data.get("threshold", 2.5))

        # Limitar entre 0 y 5 voltios
        threshold_actual = max(0.0, min(5.0, valor))

        print("Threshold actualizado a:", threshold_actual, "V")

        return jsonify({
            "ok":       True,
            "threshold": threshold_actual
        })

    except Exception as e:

        return jsonify({"ok": False, "error": str(e)}), 400

# ---------------- HISTORY (compatibilidad) ----------------
@app.route("/history")
def history_route():
    return jsonify(history)

# ---------------- DEBUG ----------------
@app.route("/debug")
def debug():
    return jsonify({
        "samples":    len(history["adc1"]),
        "last_adc":   history["adc1"][-1] if history["adc1"] else None,
        "threshold":  threshold_actual,
        "pwm":        pwm_duty,
        "pin23":      pin23_actual,
        "history":    history
    })

# ---------------- STATUS ----------------
@app.route("/status")
def status():
    return jsonify({
        "ok":      True,
        "mode":    "HTTP POST bidireccional",
        "samples": len(history["adc1"]),
        "pwm":     pwm_duty,
        "threshold": threshold_actual
    })

# ---------------- MAIN ----------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5050))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
