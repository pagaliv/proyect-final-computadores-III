# Sistema IoT para control y monitorización de un terrario

Proyecto final de la asignatura **Instalación y Mantenimiento de Computadores** (Sistemas Empotrados II) — Grado en Ingeniería Informática.

Sistema IoT que automatiza el control ambiental de un terrario: temperatura, humedad, iluminación, ventilación y detección de fugas, con interfaz local y visualización en la nube mediante ThingSpeak.

---

## Arquitectura del sistema

```
┌─────────────────────┐        UART 9600        ┌──────────────────────┐        HTTPS        ┌──────────────┐
│    Arduino UNO      │ ◄──────────────────────► │  Raspberry Pi 3B+   │ ◄──────────────────► │  ThingSpeak  │
│                     │                          │                      │                      │    (nube)    │
│  · DHT11            │                          │  · LCD 16x2          │                      │              │
│  · HC-SR04          │                          │  · 2 botones         │                      │  · Gráficas  │
│  · 2 potenciómetros │                          │  · 2 LEDs            │                      │  · Control   │
│  · Ventilador PWM   │                          │  · Lógica de alarma  │                      │    remoto    │
│  · Tira LED PWM     │                          │  · Promediado 30s    │                      │              │
└─────────────────────┘                          └──────────────────────┘                      └──────────────┘
```

---

## Características principales

- **Adquisición de datos cada segundo** mediante interrupción de Timer1 hardware en Arduino
- **Control PWM** de ventilador e iluminación a través de transistores MOSFET IRL540n
- **Doble modo de control**: manual (potenciómetros) o remoto (ThingSpeak), con prioridad automática
- **Detección de fuga**: alarma automática si el HC-SR04 detecta un objeto a menos de 10 cm
- **Interfaz local**: pantalla LCD con temperatura, humedad y estado; botones de inicio y alarma
- **Publicación en ThingSpeak** cada 30 segundos con datos promediados

---

## Hardware necesario

| Componente | Cantidad |
|---|:---:|
| Arduino UNO R3 | 1 |
| Raspberry Pi 3B+ | 1 |
| Sensor DHT11 (temperatura y humedad) | 1 |
| Sensor ultrasonidos HC-SR04 | 1 |
| Transistor MOSFET IRL540n | 2 |
| Potenciómetro 10 kΩ | 2 |
| Ventilador 5 V | 1 |
| Tira LED | 1 |
| Pantalla LCD 16×2 con módulo I2C | 1 |
| Pulsadores | 2 |
| LEDs indicadores | 2 |
| Resistencias, cables y protoboard | — |
| Tarjeta microSD 16 GB | 1 |

Coste estimado total: **~100 €**

---

## Estructura del repositorio

```
.
├── codigo/
│   ├── arduino/
│   │   └── terrario.ino        # Firmware Arduino UNO
│   └── rpi/
│       └── cucu.py             # Programa Raspberry Pi (Python)
├── imagenes/
│   ├── esquema-electrico/      # Esquemas eléctricos (Fritzing y técnico)
│   ├── fotos-circuito/         # Fotografías del montaje
│   ├── thinkspeak/             # Capturas del canal ThingSpeak
│   ├── diagrama.svg            # Diagrama de flujo del sistema
│   └── diagrama.png
├── documentacion/
│   └── Práctica 4 - Proyecto Arduino RPi.pdf   # Enunciado original
├── memoria.tex                 # Memoria técnica completa (LaTeX)
└── README.md
```

---

## Instalación y puesta en marcha

### Arduino

1. Instalar las siguientes librerías desde el gestor de Arduino IDE:
   - `DHT sensor library` (Adafruit)
   - `PinChangeInterrupt`
2. Abrir `codigo/arduino/terrario.ino` y subirlo al Arduino UNO.

### Raspberry Pi

1. Instalar dependencias:
```bash
pip3 install RPi.GPIO pyserial
```
2. Asegurarse de que la librería `LCD` está disponible en el mismo directorio o en el `PYTHONPATH`.
3. Conectar el Arduino a la RPi por USB (`/dev/ttyUSB0`).
4. Ejecutar el programa:
```bash
python3 codigo/rpi/cucu.py
```

### ThingSpeak

1. Crear una cuenta en [thingspeak.com](https://thingspeak.com) y un canal nuevo.
2. Configurar 8 fields según la tabla de la memoria.
3. Actualizar en `cucu.py` las constantes `CHANNEL_ID`, `READ_API_KEY` y `WRITE_API_KEY` con los valores del canal creado.

---

## Compilar la memoria (LaTeX)

```bash
pdflatex memoria.tex
pdflatex memoria.tex   # segunda pasada para índice y referencias cruzadas
```

---

## Pinout GPIO Raspberry Pi (numeración BOARD)

| Pin | Función |
|:---:|---|
| 31 | Botón ALARMA (pull-down) |
| 33 | Botón ENCENDER (pull-down) |
| 35 | LED ESTADO |
| 37 | LED ALARMA |
| SDA (3) / SCL (5) | LCD I2C (dirección 0x27) |

---

## Protocolo serie Arduino ↔ Raspberry Pi

El Arduino envía una trama por línea cada vez que hay cambio o periódicamente:

```
V:<val> L:<val> T:<val> H:<val> D:<val>\n
```

| Campo | Descripción | Rango |
|---|---|---|
| `V` | Velocidad ventilador | 0–1023 (ADC) |
| `L` | Intensidad iluminación | 0–1023 (ADC) |
| `T` | Temperatura (°C) | float |
| `H` | Humedad (%) | float |
| `D` | Distancia (cm) | int |

La RPi envía comandos al Arduino:

| Comando | Efecto |
|---|---|
| `encender\n` | Activa el sistema |
| `apagar\n` | Desactiva el sistema y actuadores |
| `<int>\n` + `<int>\n` | Establece velocidad e intensidad (control remoto) |

---

## Autores

- **Pablo Galilea Valverde**
- **Pedro Zhuhan**

---

## Licencia

Este proyecto se comparte con fines académicos y educativos.
