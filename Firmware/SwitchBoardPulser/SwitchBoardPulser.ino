int en = 6;
int sel = 7;
int onTime = 5;
bool is_grounded;
int t0;
int tf;
int latency;
void setup() {
Serial.begin(115200);
Serial.setTimeout(50);
pinMode(en, OUTPUT); 
pinMode(sel, OUTPUT);
// Set output to float on startup
digitalWrite(en, HIGH);
digitalWrite(sel, LOW);
delay(onTime);
digitalWrite(sel, LOW);
digitalWrite(en, LOW);
is_grounded = true;
}
void loop() {
 String command = Serial.readString();
 if (command != ""){
  command.trim(); //remove whitespace
  //Serial.println(command); // for debugging
 }
 if (command == "ground"){
    if(!is_grounded){
      digitalWrite(en, HIGH);
      digitalWrite(sel, LOW);
      delay(onTime);
      digitalWrite(sel, LOW);
      digitalWrite(en, LOW);
      is_grounded = true;
      }
  } else if (command == "float"){
    if (is_grounded){
      digitalWrite(en, HIGH);
      digitalWrite(sel, HIGH);
      delay(onTime);
      digitalWrite(sel, LOW);
      digitalWrite(en, LOW);
      is_grounded = false;
    }
  } else if (command == "is_grounded"){
    Serial.println(is_grounded);
  } else if(command == "startup"){
    Serial.println(is_grounded);
  }
  // Make sure switches are off at end
  digitalWrite(en, LOW);
  digitalWrite(sel, LOW);
}
