#define DEBUG 1 // send trigger signals for oscilloscope inspection

/*
Analog Pins (from MK20DX256 datasheet)
  Most analog pins are 12 bit. 16 bit pins are ADCx_DPO, ADCx_DM0.
  From teensy schematic: https://www.pjrc.com/teensy/schematic.html
    ADC0_DP0 = A10 (pin 9)
    ADC0_DM0 = A11 (pin 10)
    ADC1_DP0 = A12 (pin 11) - need to change pin assignment from ADC0_DP3
    ADC1_DM0 = A13 (pin 12) - need to change pin assignment from ADC0_DM3
*/

#define BAUDRATE 115200 // doesn't really matter with teensy USB serial

// digital and analog pin definition
#define N_LASER_CHANNELS 2
#define N_ANALOG_CHANNELS 5
#define PD1 A6 // photodiode (closest to lasers)
#define PD2 A7 // photodiode
#define PD3 A8  // photodiode (furthest from lasers)
#define MPD1 A4 // 808nm MPD
#define MPD2 A5 // 850nm MPD
#define VREF1 A3 // 808nm voltage ref - not used
#define VREF2 A14 // 850nm voltage ref - not used
#define LD1 9 // 808nm laser diode
#define LD2 8 // 850nm laser diode
#define TRIGGER 5 // DIO pin to monitor with oscilloscope
//

#define ADC_AVERAGING 1 // default averaging - can be changed by PC

#define MAX_DATA 2 // for buffering data - target is to maximize single chunk data transfer in time <= ACQ_DELAY
#define N_PADS 1 // padding bytes "\n" on both ends of data points
#define BUFF_SIZE ((N_PADS*2)+4+(N_ANALOG_CHANNELS*2)+1)*N_LASER_CHANNELS*(MAX_DATA+2) // data buffer

// delay after laser is activated for maximum photodiode response
#define ACQ_DELAY 20 // microseconds - wait for photodiode response
// ~5us/data for 2 lasers, used to balance serial write with ACQ_DELAY
#define ADJUSTED_DELAY (ACQ_DELAY - (2.5*N_LASER_CHANNELS*MAX_DATA)) > 0 ? (ACQ_DELAY - (2.5*N_LASER_CHANNELS*MAX_DATA)):(0) 

#include <ADC.h> // extra features in this ADC library - https://github.com/pedvide/ADC

ADC *adc = new ADC(); // adc object

// device states
bool data_collection_start = false;
bool data_collecting = false;
bool data_collection_end = false;

int analog_channels[N_ANALOG_CHANNELS] = {PD1, PD2, PD3, MPD1, MPD2};
int i, j, k, dat;
int b_idx = 0;
int data_cnt = 0;
byte buff[BUFF_SIZE];

// timestamp
elapsedMicros sinceStart; // acquisition clock (takes ~10us to read), maximum read time before reset ~ 1.5 hours?
// used to convert a long (elapsed microseconds from acquisition start) to bytes for output
union serial_tstamp { 
  char myByte[4];
  long myLong;
};
serial_tstamp tstamp;

void setup() {
  Serial.begin(BAUDRATE);
  pinMode(LD1, OUTPUT);
  pinMode(LD2, OUTPUT);
  pinMode(TRIGGER,OUTPUT);
  pinMode(PD1, INPUT);
  pinMode(PD2, INPUT);
  pinMode(PD3, INPUT);
  pinMode(MPD1, INPUT);
  pinMode(MPD2, INPUT);
  pinMode(VREF1, INPUT);
  pinMode(VREF2, INPUT);
  pinMode(13, OUTPUT); // teensy LED
  
  // set ADC0
  adc->setReference(ADC_REF_EXTERNAL, ADC_0);
  adc->setAveraging(ADC_AVERAGING, ADC_0);
  adc->setResolution(12, ADC_0);
  adc->setConversionSpeed(ADC_HIGH_SPEED, ADC_0);
  adc->setSamplingSpeed(ADC_HIGH_SPEED, ADC_0);
}

// acquires timestamp and analog data, adds to buffer
void acquire_data(int laser_channel) {
  // add padding - N_PADS * 1 bytes
  for (i=0;i<N_PADS;i++) {
    buff[b_idx++] = char(10);
  }
  
  // add timestamp - 4 bytes
  tstamp.myLong = sinceStart;
  buff[b_idx++] = tstamp.myByte[0];
  buff[b_idx++] = tstamp.myByte[1];
  buff[b_idx++] = tstamp.myByte[2];
  buff[b_idx++] = tstamp.myByte[3];
  
  // add data - 5x2 = 10 bytes
  for (j=0;j<N_ANALOG_CHANNELS;j++) {
    dat = adc->analogRead(analog_channels[j], ADC_0);
    buff[b_idx++] = highByte(dat);
    buff[b_idx++] = lowByte(dat);
  }
  
  // add laser channel - 1 byte
  buff[b_idx++] = char(laser_channel);
  
  // add padding - N_PADS * 1 bytes
  for (i=0;i<N_PADS;i++) {
    buff[b_idx++] = char(10);
   }
  // total data added to buffer = N_PADS*2 + 15 bytes
 }
   
void loop() {
 while (Serial.available()) { // this loop takes about 4us to evaluate
   byte cmd = Serial.read();
   switch (cmd) {
      case 1:
        data_collection_start = true;
        break;
      case 2:
        data_collection_end = true;
        break;
      case 3:
        data_collecting = false;
        digitalWrite(LD1, LOW);
        digitalWrite(LD2, LOW);
        break;
      case 4:
        data_collecting = true;
        digitalWrite(LD2, LOW);
        digitalWrite(LD1,HIGH);
        delayMicroseconds(ACQ_DELAY);
        break;
    }
   if (cmd > 4) {
     adc->setAveraging(cmd-4);  // PC can change ADC averaging
   }
 }
 
 if (data_collection_start == true) {
   data_collection_start = false;
   data_collecting = true;
   sinceStart = 0; // reset acquisition timer to 0us
 }
 
 if (data_collecting == true) {
   #ifdef DEBUG
     digitalWrite(TRIGGER,LOW);
     digitalWrite(TRIGGER,HIGH);
   #endif
   acquire_data(0); // LD1 data - 40us
   digitalWrite(LD1, LOW);
   digitalWrite(LD2, HIGH);
   
   #ifdef DEBUG
     digitalWrite(TRIGGER, LOW);
   #endif
   delayMicroseconds(ACQ_DELAY);
   
   #ifdef DEBUG
     digitalWrite(TRIGGER, HIGH);
   #endif
   acquire_data(1); // LD2 data
   digitalWrite(LD2,LOW);
   digitalWrite(LD1,HIGH);
   
   #ifdef DEBUG
     digitalWrite(TRIGGER,LOW);
   #endif
   data_cnt++;
   if (data_cnt >= MAX_DATA) {
       Serial.write(buff,b_idx);
       b_idx = 0;
       data_cnt = 0;
       delayMicroseconds(ADJUSTED_DELAY); 
   }
   else {
     delayMicroseconds(ACQ_DELAY);
   }
   #ifdef DEBUG
     digitalWrite(TRIGGER,HIGH); 
   #endif
 }
 
 if (data_collection_end == true) {
   data_collecting = false;
   data_collection_end = false;
   digitalWrite(LD1, LOW);
   digitalWrite(LD2, LOW);
   Serial.flush();
 }
}

