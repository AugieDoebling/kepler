#include <ArduinoJson.h>
StaticJsonDocument<1024> jsonCmdReceive;
StaticJsonDocument<1024> jsonInfoSend;
StaticJsonDocument<1024> jsonInfoHttp;

#include <SCServo.h>
#include <Preferences.h>
#include <nvs_flash.h>
#include <esp_system.h>
#include <LittleFS.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <WebServer.h>
#include <esp_now.h>
#include <nvs_flash.h>
#include <INA219_WE.h>
#include <SimpleKalmanFilter.h>
#include "ICM_20948.h"
#include "battery_ctrl.h"

// functions for oled.
#include "oled_ctrl.h"
#include "HexArth_config.h"
// functions for RoArm-M2 ctrl.
#include "HexArth_module.h"

// functions for pneumatic modules and lights ctrl. 
#include "switch_module.h"

// define json cmd.
#include "json_cmd.h"

// functions for editing the files in flash.
#include "files_ctrl.h"

#include "IMU_ctrl.h"

// advance functions for RoArm-M2 ctrl.
#include "HexArth_advance.h"

// functions for wifi ctrl.
#include "wifi_ctrl.h"

// functions for esp-now.
#include "esp_now_ctrl.h"

// functions for uart json ctrl.
#include "uart_ctrl.h"

// functions for http & web server.
#include "http_server.h"


void setup() {
 Serial.begin(115200);
  while(!Serial) {}
  Wire.begin(S_SDA, S_SCL, 400000);

  bool initialized = false;
  while (!initialized) {
    myICM.begin(Wire, AD0_VAL);
    Serial.print(F("Initialization of the sensor returned: "));
    Serial.println(myICM.statusString());
    if (myICM.status != ICM_20948_Stat_Ok) {
      Serial.println(F("Trying again..."));
      delay(500);
    }
    else {
      initialized = true;
    }
  }

  Serial.println(F("Device connected!"));

  bool success = true; // Use success to show if the DMP configuration was successful

  // Initialize the DMP. initializeDMP is a weak function. You can overwrite it if you want to e.g. to change the sample rate
  success &= (myICM.initializeDMP() == ICM_20948_Stat_Ok);

  // Enable the DMP orientation sensor
  success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_ORIENTATION) == ICM_20948_Stat_Ok);

  success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_RAW_GYROSCOPE) == ICM_20948_Stat_Ok);
  success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_RAW_ACCELEROMETER) == ICM_20948_Stat_Ok);
  // +
  success &= (myICM.enableDMPSensor(INV_ICM20948_SENSOR_MAGNETIC_FIELD_UNCALIBRATED) == ICM_20948_Stat_Ok);

  // Configuring DMP to output data at multiple ODRs:
  // DMP is capable of outputting multiple sensor data at different rates to FIFO.
  // Setting value can be calculated as follows:
  // Value = (DMP running rate / ODR ) - 1
  // E.g. For a 5Hz ODR rate when DMP is running at 55Hz, value = (55/5) - 1 = 10.

   //success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Quat9, 3) == ICM_20948_Stat_Ok); // Set to the maximum

  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Accel, 10) == ICM_20948_Stat_Ok); // Set to the maximum
  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Gyro, 10) == ICM_20948_Stat_Ok); // Set to the maximum

  // +
  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Cpass, 10) == ICM_20948_Stat_Ok);
  success &= (myICM.setDMPODRrate(DMP_ODR_Reg_Cpass_Calibr, 10) == ICM_20948_Stat_Ok);

  myICM.lowPower(false);

  // Enable the FIFO
  success &= (myICM.enableFIFO() == ICM_20948_Stat_Ok);

  // Enable the DMP
  success &= (myICM.enableDMP() == ICM_20948_Stat_Ok);

  // Reset DMP
  success &= (myICM.resetDMP() == ICM_20948_Stat_Ok);

  // Reset FIFO
  success &= (myICM.resetFIFO() == ICM_20948_Stat_Ok);

  // Check success
  if (success)
  {
    Serial.println(F("DMP enabled!"));
  }
  else
  {
    Serial.println(F("Enable DMP failed!"));
    Serial.println(F("Please check that you have uncommented line 29 (#define ICM_20948_USE_DMP) in ICM_20948_C.h..."));
  }

  
  
  ina219_init();
  inaDataUpdate();

  initOLED();
  screenLine_0 = "HexArth";
  screenLine_1 = "version: 0.84";
  screenLine_2 = "starting...";
  screenLine_3 = "";
  oled_update();
  
  delay(1200);
  // init the littleFS funcs in files_ctrl.h
  screenLine_2 = screenLine_3;
  screenLine_3 = "Initialize LittleFS";
  oled_update();
  if(InfoPrint == 1){Serial.println("Initialize LittleFS for Flash files ctrl.");}
  initFS();

  // init the funcs in switch_module.h
  screenLine_2 = screenLine_3;
  screenLine_3 = "Initialize 12V-switch ctrl";
  oled_update();
  if(InfoPrint == 1){Serial.println("Initialize the pins used for 12V-switch ctrl.");}
  led_pin_init();

  // servos power up
  screenLine_2 = screenLine_3;
  screenLine_3 = "Power up the servos";
  oled_update();
  if(InfoPrint == 1){Serial.println("Power up the servos.");}
  delay(500);
  
  // init servo ctrl functions.
  screenLine_2 = screenLine_3;
  screenLine_3 = "ServoCtrl init UART2TTL...";
  oled_update();
  if(InfoPrint == 1){Serial.println("ServoCtrl init UART2TTL...");}
  Claws_servoInit();

  // check the status of the servos.
  screenLine_2 = screenLine_3;
  screenLine_3 = "Bus servos status check...";
  oled_update();
  if(InfoPrint == 1){Serial.println("Bus servos status check...");}
  Claws_initCheck(false);

  if(InfoPrint == 1 && Claws_initCheckSucceed){
    Serial.println("All bus servos status checked.");
  }
  if(Claws_initCheckSucceed) {
    screenLine_2 = "Bus servos: succeed";
  } else {
    screenLine_2 = "Bus servos: failed";
  }
  screenLine_3 = ">>> Moving to init pos...";
  oled_update();
  Claws_resetPID();
  Claws_moveInit();
  Claws_getServoPosByXYZ(initInBase);
  screenLine_3 = "Reset joint torque to ST_TORQUE_MAX";
  oled_update();
  if(InfoPrint == 1){Serial.println("Reset joint torque to ST_TORQUE_MAX.");}

  screenLine_3 = "WiFi init";
  oled_update();
  if(InfoPrint == 1){Serial.println("WiFi init.");}
  initWifi();

  screenLine_3 = "http & web init";
  oled_update();
  if(InfoPrint == 1){Serial.println("http & web init.");}
  initHttpWebServer();

  screenLine_3 = "ESP-NOW init";
  oled_update();
  if(InfoPrint == 1){Serial.println("ESP-NOW init.");}
  initEspNow();

  screenLine_3 = "HexArth started";
  oled_update();
  if(InfoPrint == 1){Serial.println("HexArth started.");}

  getThisDevMacAddress();
  delay(3000);
  updateOledWifiInfo();
  
  imuCalibration();
  screenLine_2 = String("MAC:") + macToString(thisDevMac);
  oled_update();

  if(InfoPrint == 1){Serial.println("Application initialization settings.");}
  createMission("boot", "these cmds run automatically at boot.");
  missionPlay("boot", 1);
  
  //RoArmM2_handTorqueCtrl(300);
  gait.setMotionCommand(0.00,0.00,0.0);
}


void loop() {
    icm_20948_DMP_data_t data;
  myICM.readDMPdataFromFIFO(&data);

  if ((myICM.status == ICM_20948_Stat_Ok) || (myICM.status == ICM_20948_Stat_FIFOMoreDataAvail)) {
    if ((data.header & DMP_header_bitmap_Quat9) > 0) {
      // Scale to +/- 1
      q1 = ((double)data.Quat9.Data.Q1) / 1073741824.0; // Convert to double. Divide by 2^30
      q2 = ((double)data.Quat9.Data.Q2) / 1073741824.0; // Convert to double. Divide by 2^30
      q3 = ((double)data.Quat9.Data.Q3) / 1073741824.0; // Convert to double. Divide by 2^30
      q0 = sqrt(1.0 - ((q1 * q1) + (q2 * q2) + (q3 * q3)));

      q2sqr = q2 * q2;

      // roll (x-axis rotation)
      t0 = +2.0 * (q0 * q1 + q2 * q3);
      t1 = +1.0 - 2.0 * (q1 * q1 + q2sqr);
      icm_roll = atan2(t0, t1);

      // pitch (y-axis rotation)
      t2 = +2.0 * (q0 * q2 - q3 * q1);
      t2 = t2 > 1.0 ? 1.0 : t2;
      t2 = t2 < -1.0 ? -1.0 : t2;
      icm_pitch = asin(t2);

      // yaw (z-axis rotation)
      t3 = +2.0 * (q0 * q3 + q1 * q2);
      t4 = +1.0 - 2.0 * (q2sqr + q3 * q3);
      icm_yaw = atan2(t3, t4);

      // Serial.print(F("r:"));
      // Serial.print(icm_roll, 2);
      // Serial.print(F(" p:"));
      // Serial.print(icm_pitch, 2);
      // Serial.print(F(" y:"));
      // Serial.println(icm_yaw, 2);
    }

    if ((data.header & DMP_header_bitmap_Accel) > 0) {
      ax = data.Raw_Accel.Data.X;
      ay = data.Raw_Accel.Data.Y;
      az = data.Raw_Accel.Data.Z;
    }
    if ((data.header & DMP_header_bitmap_Gyro) > 0) {
      gx = data.Raw_Gyro.Data.X;
      gy = data.Raw_Gyro.Data.Y;
      gz = data.Raw_Gyro.Data.Z;
    }
    if ((data.header & DMP_header_bitmap_Compass) > 0) {
      mx = data.Compass.Data.X;
      my = data.Compass.Data.Y;
      mz = data.Compass.Data.Z;
    }
  }

  serialCtrl();
 // server.handleClient();
  Claws_getPosByServoFeedback();
  // for (int i=0;i<18;i++)
  // {
  //   Serial.print("ID");
  //   Serial.print(jointID[i]);
  //   Serial.print(":");
  //   Serial.println(servoFeedback[i].pos);
  // }
  // for(int i= 0; i < 6; i++)
  // {int j=0;
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("coxa:");
  //   Serial.println(legs[i].actualAngle.coxa);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("femur:");
  //   Serial.println(legs[i].actualAngle.femur);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("tibia:");
  //   Serial.println(legs[i].actualAngle.tibia);
  // }
  // for(int i= 0; i < 6; i++)
  // {int j=0;
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("x:");
  //   Serial.println(legs[i].endPos.actualInLeg.x);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("y:");
  //   Serial.println(legs[i].endPos.actualInLeg.y);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("z:");
  //   Serial.println(legs[i].endPos.actualInLeg.z);
  // }
  //   for(int i= 0; i < 6; i++)
  // {int j=0;
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("basex:");
  //   Serial.println(legs[i].endPos.actualInBase.x);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("basey:");
  //   Serial.println(legs[i].endPos.actualInBase.y);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("basez:");
  //   Serial.println(legs[i].endPos.actualInBase.z);
  // }
  //    for(int i= 0; i < 6; i++)
  // {int j=0;
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("basex:");
  //   Serial.println(BasegetXYZ[i].x);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("basey:");
  //   Serial.println(BasegetXYZ[i].y);
    // Serial.print("ID");
    // Serial.print(jointID[j]);j++;
    // Serial.print("basez:");
    // Serial.println(BasegetXYZ[i].z);
  // }
  unsigned long curr_time = millis();
  if(!Balanced_Mode)
  {
    if (curr_time - prev_time >= 50)
    {
     gait.update((curr_time - prev_time)* 0.001,BasegetXYZ,BasesetXYZ);
    }
  }
  else if(Balanced_Mode&&!Balanced_Init)
  {
    for(int i= 0; i < 6; i++)
    BasesetXYZ[i]=initInBase[i];
    Balanced_Init=true;
  }
  else if(Balanced_Mode&&Balanced_Init)
  {
    //if(!Balanced_frist)
  // {
  //     for(int i = 1; i < 18; i+=3)
  //    waitMove2Goal(i, ARM_SERVO_MIDDLE_POS-FEMUR_SERVO_MIDDLE_OFFSET, 150);
  //   for(int i = 2; i < 18; i+=3)
  // waitMove2Goal(i, ARM_SERVO_MIDDLE_POS-TIBIA_SERVO_MIDDLE_OFFSET, 150);
  // Balanced_frist=true;
  // }
    calcBalanceCorrection(icm_roll,icm_pitch,BasegetXYZ,BasesetXYZ);
    Claws_moveServoPosByXYZ();
  }
  
  prev_time = curr_time;
//   for(int i= 0; i < 6; i++)
//   {
//  BasegetXYZ[i].x= BasesetXYZ[i].x;
//  BasegetXYZ[i].y= BasesetXYZ[i].y;
//  BasegetXYZ[i].z= BasesetXYZ[i].z;
//   }
    // Serial.print("en_odom_x");
    // Serial.print(en_odom_x);
    // Serial.print("en_odom_y:");
    // Serial.println(en_odom_y);
    // Serial.print("en_odom_yaw:");
    // Serial.println(en_odom_yaw);
//   for(int i=0;i<6;i++)
//  BasesetXYZ[i]=BasegetXYZ[i];
// int j=0;
  //    for(int i= 0; i < 6; i++)
  // {
   
  //   Serial.print("BasesetX:");
  //   Serial.println(BasesetXYZ[i].x);
   
  //   Serial.print("BasesetY:");
  //   Serial.println(BasesetXYZ[i].y);

  //   Serial.print("BasesetZ:");
  //   Serial.println(BasesetXYZ[i].z);
  // }
 
  // for(int i= 0; i < 6; i++)
  // {int j=0;
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("targetInLegx:");
  //   Serial.println(legs[i].endPos.targetInLeg.x);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("targetInLegy:");
  //   Serial.println(legs[i].endPos.targetInLeg.y);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("targetInLegz:");
  //   Serial.println(legs[i].endPos.targetInLeg.z);
  // }
  // for(int i= 0; i < 6; i++)
  // {int j=0;
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("targetAngle coxa:");
  //   Serial.println(legs[i].targetAngle.coxa);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("targetAngle femur:");
  //   Serial.println(legs[i].targetAngle.femur);
  //   Serial.print("ID");
  //   Serial.print(jointID[j]);j++;
  //   Serial.print("targetAngle tibia:");
  //   Serial.println(legs[i].targetAngle.tibia);
  // }
  //delay(500);
  // for(int i= 0; i < 18; i++)
  // {
  //   Serial.println(Servo_pos[i]);
  // }
  // esp-now flow ctrl as a flow-leader.
  oledInfoUpdate();
  switch(espNowMode) {
  case 1: espNowGroupDevsFlowCtrl();break;
  case 2: espNowSingleDevFlowCtrl();break;
  }

  if (InfoPrint == 2) {
    Claws_infoFeedback();
  }

  if(runNewJsonCmd) {
    jsonCmdReceiveHandler();
    jsonCmdReceive.clear();
    runNewJsonCmd = false;
  }
  heartBeatCtrl();
  
}