import RPi.GPIO as GPIO
import time
import serial
import urllib.request
import urllib.parse
import json
from LCD import LCD
import threading
from collections import deque

# ========== CONFIGURACION ==========
# ThingSpeak (cambia por tus propios datos)
CHANNEL_ID = "3363628"
READ_API_KEY = "N7QU3O0EG5NPU5X1"      # para leer comandos
WRITE_API_KEY = "FPWPE0IL0JNWG3Z5"    # tu clave de escritura

# Pines GPIO (BOARD)
LED_ESTADO = 35      # LED de sistema activo
LED_ALARMA = 37      # LED de alarma
BOTON_ENCENDER = 33  # Inicio/parada del sistema
BOTON_PANICO = 31    # Alarma manual

# LCD
LCD_I2C_ADDR = 0x27
lcd = LCD(2, LCD_I2C_ADDR, True)

# Serie (Arduino)
SERIAL_PORT = '/dev/ttyUSB0'
BAUDRATE = 9600

# Variables globales
active = False
alarm = False
temp_avg = 0.0
hum_avg = 0.0
dist_avg = 0.0
ventilador_cmd = 0      # 0-100
iluminacion_cmd = 0     # 0-100

# Colas para promediar datos cada 30s (guardamos hasta 30 muestras, una por segundo)
data_buffer = deque(maxlen=300)

# Control de tiempo para ThingSpeak
last_thingspeak_send = 0
last_thingspeak_read = 0
THINGSPEAK_INTERVAL = 30

# ========== INICIALIZACION GPIO ==========
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LED_ESTADO, GPIO.OUT)
GPIO.setup(LED_ALARMA, GPIO.OUT)
GPIO.setup(BOTON_ENCENDER, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # pull-down
GPIO.setup(BOTON_PANICO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# ========== FUNCIONES AUXILIARES ==========
def update_leds():
    """Actualiza LEDs segun estado del sistema y alarma"""
    GPIO.output(LED_ESTADO, active)
    GPIO.output(LED_ALARMA, alarm)

def send_command_to_arduino(cmd):
    """Envia un comando al Arduino por serie"""
    ser.write((cmd + "\n").encode())

def read_serial_data():
    """Lee una linea del Arduino y actualiza los buffers"""
    global temp_avg, hum_avg, dist_avg, alarm  # <-- CORREGIDO: anadido alarm
    if ser.in_waiting:
        try:
            # Usar errors='replace' para no petar con bytes invalidos
            line = ser.readline().decode('utf-8', errors='replace').strip()
           
            # Ignorar lineas vacias o que no empiecen con "T:"
            if not line:
                return
               
            # Ejemplo de formato: "T:24.5 H:60.2 D:12.0"
            parts = line.split()
            temp = None
            hum = None
            dist = None
            vel = None
            lum = None
            for part in parts:
                if part.startswith("T:"):
                    temp = float(part[2:])
                elif part.startswith("H:"):
                    hum = float(part[2:])
                elif part.startswith("D:"):
                    dist = float(part[2:])
                elif part.startswith("V:"):
                    vel = float(part[2:])
                elif part.startswith("L:"):
                    lum = float(part[2:])
                   
            if temp is not None and hum is not None and dist is not None:
                data_buffer.append((vel,lum,temp, hum, dist))
                # Actualizar valores instantaneos para la LCD
                temp_avg, hum_avg, dist_avg = temp, hum, dist
               
                # Si la distancia es < 10 cm, activar alarma automatica
                if dist>0 and dist < 10 and not alarm:
                    alarm = True
                    update_leds()
                    send_command_to_arduino("apagar")
                    lcd.clear()
                    lcd.message("ALARMA! Fuga", 1)
                    lcd.message("Dist < 10 cm", 2)
                   
        except ValueError:
            pass  # Ignorar lineas mal formateadas
        except Exception as e:
            print("Error leyendo serie:", e)

def send_to_thingspeak():
    """Envia los datos promediados a ThingSpeak"""
    if not data_buffer:
        return
    # Calcular promedios
    vels = [d[0] for d in data_buffer]
    lums = [d[1] for d in data_buffer]
    temps = [d[2] for d in data_buffer]
    hums = [d[3] for d in data_buffer]
    dists = [d[4] for d in data_buffer]
    avg_vel = sum(vels) / len(temps)
    avg_lum = sum(lums) / len(hums)
    avg_temp = sum(temps) / len(temps)
    avg_hum = sum(hums) / len(hums)
    avg_dist = sum(dists) / len(dists)

    url = f"https://api.thingspeak.com/update?api_key={WRITE_API_KEY}"
    url += f"&field1={avg_temp}&field2={avg_hum}&field3={avg_dist}"
    url += f"&field4={1 if alarm else 0}"
    url += f"&field5={ventilador_cmd}&field6={iluminacion_cmd}"
    url += f"&field7={avg_vel}&field8={avg_lum}"
    try:
        urllib.request.urlopen(url, timeout=5)
        print("Datos enviados a ThingSpeak")
    except urllib.error.URLError as e:
        print("Error write:", e.reason)
    except Exception as e:
        print("Error enviando a ThingSpeak:", e)

def read_commands_from_thingspeak():
    """Lee los comandos del usuario desde los fields 5 y 6 de ThingSpeak"""
    global ventilador_cmd, iluminacion_cmd
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json?api_key={READ_API_KEY}"
    try:
        response = urllib.request.urlopen(url, timeout=5)
        data = json.loads(response.read().decode())
        # field5 = velocidad ventilador (0-100)
        # field6 = intensidad iluminacion (0-100)
        if 'field5' in data and data['field5'] is not None:
            new_vent = int(float(data['field5']))
            if new_vent != ventilador_cmd:
                ventilador_cmd = new_vent
                if active:
                    send_command_to_arduino(f"VENTILADOR:{ventilador_cmd}")
        if 'field6' in data and data['field6'] is not None:
            new_ilu = int(float(data['field6']))
            if new_ilu != iluminacion_cmd:
                iluminacion_cmd = new_ilu
                if active:
                    send_command_to_arduino(f"ILUMINACION:{iluminacion_cmd}")
        print("Comandos ThingSpeak leidos")
    except urllib.error.URLError as e:
        print("Error read:", e.reason)
    except Exception as e:
        print("Error leyendo ThingSpeak:", e)

def update_lcd():
    """Actualiza la pantalla LCD con los valores actuales"""
    lcd.clear()
    if alarm:
        lcd.message("ALARMA ACTIVA", 1)
        lcd.message("Sistema detenido", 2)
    elif active:
        # Usar 'C' en vez de caracter especial de grado
        lcd.message(f"T:{temp_avg:.1f}C H:{hum_avg:.1f}%", 1)
        lcd.message(f"V:{ventilador_cmd}% I:{iluminacion_cmd}%", 2)
    else:
        lcd.message("Sistema OFF", 1)
        lcd.message("Pulse Inicio", 2)

def thingspeak_thread():
    """Hilo para enviar/recibir datos de ThingSpeak cada 30s"""
    global last_thingspeak_send, last_thingspeak_read
    while True:
        now = time.time()
        # Enviar datos promediados
        if now - last_thingspeak_send >= THINGSPEAK_INTERVAL:
            send_to_thingspeak()
            last_thingspeak_send = now
        # Leer comandos (cada 30s tambien, pero puede ser menos frecuente)
        if now - last_thingspeak_read >= THINGSPEAK_INTERVAL:
            read_commands_from_thingspeak()
            last_thingspeak_read = now
        time.sleep(1)  # no saturar

def button_thread():
    """Hilo para gestionar pulsadores con anti-rebote"""
    global active, alarm
    last_encender = False
    last_panico = False
    while True:
        # Boton Encender (pulso ascendente)
        encender = GPIO.input(BOTON_ENCENDER)
        if encender and not last_encender:
            # Flanco de subida: alterna active
            active = not active
            if active:
                # Al arrancar, enviar comandos actuales al Arduino
                send_command_to_arduino("encender")
            else:
                send_command_to_arduino("apagar")
            update_leds()
            update_lcd()
        last_encender=encender
        # Boton Panico (pulso ascendente): activa/desactiva alarma
        panico = GPIO.input(BOTON_PANICO)
        if panico and not last_panico:
            alarm = not alarm
            if alarm:
                active = False
                send_command_to_arduino("apagar")
            else:
                # Si se desactiva alarma, no reactiva el sistema automaticamente
                pass
            update_leds()
            update_lcd()
        last_panico=panico

# ========== PROGRAMA PRINCIPAL ==========
if __name__ == "__main__":
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    time.sleep(2)  # esperar a que el Arduino reinicie

    # === LIMPIAR BUFFER INICIAL DEL ARDUINO ===
    ser.reset_input_buffer()
    while ser.in_waiting:
        ser.readline()
    # ==========================================

    # Iniciar hilos
    t1 = threading.Thread(target=thingspeak_thread, daemon=True)
    t2 = threading.Thread(target=button_thread, daemon=True)
    t1.start()
    t2.start()

    # Bucle principal: leer datos del Arduino y actualizar LCD
    try:
        while True:
            read_serial_data()
            update_lcd()
               
    except KeyboardInterrupt:
        print("Programa detenido")
    finally:
        ser.close()
        GPIO.cleanup()
        lcd.clear()
