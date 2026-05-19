#include <PinChangeInterrupt.h>
#include <PinChangeInterruptBoards.h>
#include <PinChangeInterruptPins.h>
#include <PinChangeInterruptSettings.h>

#include "DHT.h";

#define DHTTYPE DHT11

unsigned long t_init,t_end;
int interupt_pin=0;
int echo=8;
int trigger=9;
int pin_temperatura_y_humedad=10;
int pin_ventilador=11;
int pin_led=12;
int pin_in_temp=A0;
int pin_in_venti=A1;
int velocidad=0;
int intensidad=0;
int old_velocidad=0;
int old_intensidad=0;
float  temperatura=0;
float  humedad=0;
int ultrasonido=0;
bool active=false;
bool ThingSpeak=false;

/*
 * LAB Name: Arduino Timer Compare Match Interrupt
 * Author: Khaled Magdy
 * For More Info Visit: www.DeepBlueMbedded.com
*/
DHT dht(pin_temperatura_y_humedad, DHTTYPE);

ISR(TIMER1_COMPA_vect)// Timer every second
{
  OCR1A += 62500; // Advance The COMPA Register
  // Handle The Timer Interrupt
  //...
  INT2_vect();
}

void INT2_vect(){
humedad=dht.readHumidity();
temperatura=dht.readTemperature();
if (isnan(temperatura)){ temperatura = -1;}
if (isnan(humedad)) {humedad     = -1;}

  digitalWrite(trigger, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigger, LOW);
  long duracion = pulseIn(echo, HIGH);

  if (duracion == 0) return -1;
  return (int)(duracion / 59);

}

// the setup function runs once when you press reset or power the board
void setup() {
  // initialize digital pin LED_BUILTIN as an output.

  TCCR1A = 0;           // Init Timer1A
  TCCR1B = 0;           // Init Timer1B
  TCCR1B |= B00000100;  // Prescaler = 256
  OCR1A = 62500;        // Timer Compare1A Register
  TIMSK1 |= B00000010;  // Enable Timer COMPA Interrupt

  Serial.begin(9600);

  dht.begin();
  pinMode(interupt_pin, INPUT);
  attachPCINT(digitalPinToPCINT(interupt_pin), INT2_vect, RISING);

  pinMode(echo, INPUT);
  pinMode(trigger, OUTPUT);
  pinMode(pin_temperatura_y_humedad, INPUT);

  pinMode(pin_ventilador, OUTPUT);
  pinMode(pin_led, OUTPUT);

  pinMode(pin_in_temp, INPUT);
  pinMode(pin_in_venti, INPUT);

  digitalWrite(trigger, LOW);
}

// the loop function runs over and over again forever
void loop() {
  if(active){
    if(!ThingSpeak){
          if(old_velocidad!=analogRead(pin_in_temp) || old_intensidad!=analogRead(pin_in_venti)){ // si cambian potenciometros por hw
            ThingSpeak=false;
            velocidad=analogRead(pin_in_temp) ;
            intensidad=analogRead(pin_in_venti);
            Serial.write(" V:");
            Serial.write(String(velocidad).c_str());
            Serial.write(" L:");
            Serial.write(String(intensidad).c_str());
            Serial.write(" T:");
            Serial.write(String(temperatura).c_str());
            Serial.write(" H:");
            Serial.write(String(humedad).c_str());
            Serial.write(" D:");
            Serial.write(String(ultrasonido).c_str());
            Serial.write('\n');
          }

          String input="";
          if (Serial.available()) {
            String input_v=Serial.readStringUntil('\n');
            input_v.trim();
            if(input_v=="apagar"){// Tratar Apagar y alarma como misma cosa. No hay una diferencia real en lo que hacen.
              active=false;
            } else{
              input_v=Serial.readStringUntil('\n');
            }
            String input_i=Serial.readStringUntil('\n');
            ThingSpeak=true;
            velocidad=input_v.toInt();
            intensidad=input_i.toInt();
            old_velocidad=velocidad;
            old_intensidad=intensidad;
          }
      }
      else{
        velocidad=analogRead(pin_in_temp);
        intensidad=analogRead(pin_in_venti);
            Serial.write("V:");
            Serial.write(String(velocidad).c_str());
            Serial.write("L:");
            Serial.write(String(intensidad).c_str());
            Serial.write("T:");
            Serial.write(String(temperatura).c_str());
            Serial.write("H:");
            Serial.write(String(humedad).c_str());
            Serial.write("D:");
            Serial.write(String(ultrasonido).c_str());
            Serial.write('\n');
      }
    }
    else{
          if(Serial.available()){//Hay datos de pi
            String input_v=Serial.readStringUntil('\n');
            if(input_v=="encender"){
              active=true;
            }
          }
    }
    analogWrite(pin_ventilador,velocidad);
    analogWrite(pin_led,intensidad);

}
