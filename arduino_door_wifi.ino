#include <Servo.h>
#include <SoftwareSerial.h>

Servo microServo;
const int servoPin = 9; // 서보 모터 핀
const int espRx = 2;   // ESP-01S RX (아두이노 TX)
const int espTx = 3;   // ESP-01S TX (아두이노 RX)

SoftwareSerial espSerial(espRx, espTx);

const char* ssid = "project_net";
const char* password = "1q2w3e4r";
const char* host = "192.168.178.37";
const int port = 5003;

void setup() {
  Serial.begin(9600);
  espSerial.begin(9600);
  microServo.attach(servoPin);
  microServo.write(80); // 초기 각도 설정
  delay(500);

  connectWiFi();
  connectServer();
}

void loop() {
  if (espSerial.available()) {
    String response = espSerial.readStringUntil('\n');
    response.trim();
    Serial.println("서버 응답: " + response);

    if (response == "open") {
      openDoor();
      sendData("open_done");
    } else if (response == "close") {
      closeDoor();
      sendData("close_done");
    }
  }
}

void connectWiFi() {
  sendCommand("AT+CWJAP=\"" + String(ssid) + "\",\"" + String(password) + "\"", 10000);
}

void connectServer() {
  sendCommand("AT+CIPSTART=\"TCP\",\"" + String(host) + "\", " + String(port), 10000);
  sendData("Arduino Connected");
}

void sendCommand(String command, int delayTime) {
  espSerial.println(command);
  delay(delayTime);
}

void sendData(String data) {
  sendCommand("AT+CIPSEND=" + String(data.length() + 2), 1000);
  espSerial.println(data);
}

void openDoor() {
  Serial.println("문 열기 시작");
  for (int angle = 80; angle <= 170; angle++) {
    microServo.write(angle);
    delay(20);
  }
  Serial.println("문 열기 완료");
}

void closeDoor() {
  Serial.println("문 닫기 시작");
  for (int angle = 170; angle >= 80; angle--) {
    microServo.write(angle);
    delay(20);
  }
  Serial.println("문 닫기 완료");
}