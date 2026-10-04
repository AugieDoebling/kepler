void jsonCmdReceiveHandler(){
	int cmdType = jsonCmdReceive["T"].as<int>();
	switch(cmdType){
	// emergency stop.
	case CMD_EMERGENCY_STOP:
												RoArmM2_emergencyStopFlag = true;
												emergencyStopProcessing();
												break;
	case CMD_RESET_EMERGENCY: 
												RoArmM2_emergencyStopFlag = false;
												break;
  case CMD_SPEED_CTRL:	
												heartbeatStopFlag = false;
												lastCmdRecvTime = millis();
												setGoalSpeed(
												jsonCmdReceive["X"],
												jsonCmdReceive["Y"],
                        jsonCmdReceive["Yaw"]);
												break;
  case CMD_DEFAULTZ:	
                        setDefaultz(
                        jsonCmdReceive["cmd"]);
                        break;
   case CMD_AMP_CTRL:	
                        heartbeatStopFlag = false;
												lastCmdRecvTime = millis();
												setGoalAmp(
												jsonCmdReceive["r"],
												jsonCmdReceive["p"],
                        jsonCmdReceive["y"],
                        jsonCmdReceive["f"]);
												break;
  case CMD_BALANCED_ENABLE:	
												if(jsonCmdReceive["cmd"]==0)
                        {
                          Balanced_Mode=false;
                          Balanced_Init=false;
                          Balanced_frist=false;
                        }else
                        {
                          Balanced_Mode=true;
                          Balanced_Init=false;
                          Balanced_frist=false;
                        }
												break;                     
  case CMD_Goal_STOP:
                      setGoalStop();
                       break;                     
  case CMD_MOVE_INIT: 
                      Claws_moveInit_web();
                      break;
  case CMD_CLAWS_FEEDBACK:
												Claws_infoFeedback();
                        break;

	// mission & steps edit & file edit.
	case CMD_SCAN_FILES:  scanFlashContents();
												break;
	case CMD_CREATE_FILE: createFile(
												jsonCmdReceive["name"],
												jsonCmdReceive["content"]
												);break;
	case CMD_READ_FILE:		readFile(
												jsonCmdReceive["name"]
												);break;
	case CMD_DELETE_FILE: deleteFile(
												jsonCmdReceive["name"]
												);break;
	case CMD_APPEND_LINE:	appendLine(
												jsonCmdReceive["name"],
												jsonCmdReceive["content"]
												);break;
	case CMD_INSERT_LINE: insertLine(
												jsonCmdReceive["name"],
												jsonCmdReceive["lineNum"],
												jsonCmdReceive["content"]
												);break;
	case CMD_REPLACE_LINE:
												replaceLine(
												jsonCmdReceive["name"],
												jsonCmdReceive["lineNum"],
												jsonCmdReceive["content"]
												);break;
	case CMD_READ_LINE:   readSingleLine(
												jsonCmdReceive["name"],
												jsonCmdReceive["lineNum"]
												);break;
	case CMD_DELETE_LINE: deleteSingleLine(
												jsonCmdReceive["name"],
												jsonCmdReceive["lineNum"]
												);break;


	case CMD_TORQUE_CTRL: servoTorqueCtrl(254,
												jsonCmdReceive["cmd"]);
												break;
  case CMD_OLED_CTRL:		oledCtrl(
												jsonCmdReceive["lineNum"],
												jsonCmdReceive["Text"]);break;
  case CMD_OLED_DEFAULT:setOledDefault();break;
	case CMD_CREATE_MISSION:
												createMission(
												jsonCmdReceive["name"],
												jsonCmdReceive["intro"]
												);break;
	case CMD_MISSION_CONTENT:
												missionContent(
												jsonCmdReceive["name"]
												);break;
	case CMD_APPEND_STEP_JSON: 
												appendStepJson(
												jsonCmdReceive["name"],
												jsonCmdReceive["step"]
												);break;

	case CMD_APPEND_DELAY:
												appendDelayCmd(
												jsonCmdReceive["name"],
												jsonCmdReceive["delay"]
												);break;
	case CMD_INSERT_STEP_JSON:
												insertStepJson(
												jsonCmdReceive["name"],
												jsonCmdReceive["stepNum"],
												jsonCmdReceive["step"]
												);break;

	case CMD_INSERT_DELAY:
												insertDelayCmd(
												jsonCmdReceive["name"],
												jsonCmdReceive["stepNum"],
												jsonCmdReceive["spd"]
												);break;
	case CMD_REPLACE_STEP_JSON:
												replaceStepJson(
												jsonCmdReceive["name"],
												jsonCmdReceive["stepNum"],
												jsonCmdReceive["step"]
												);break;
	case CMD_REPLACE_DELAY:
												replaceDelayCmd(
												jsonCmdReceive["name"],
												jsonCmdReceive["stepNum"],
												jsonCmdReceive["delay"]
												);break;
	case CMD_DELETE_STEP: deleteStep(
												jsonCmdReceive["name"],
												jsonCmdReceive["stepNum"]
												);break;

	case CMD_MOVE_TO_STEP:
												moveToStep(
												jsonCmdReceive["name"],
												jsonCmdReceive["stepNum"]
												);break;
	case CMD_MISSION_PLAY:
												missionPlay(
												jsonCmdReceive["name"],
												jsonCmdReceive["times"]
												);break;

	case CMD_GET_IMU_DATA:
												getIMUData();break;
	case CMD_CALI_IMU_STEP:
												imuCalibration();break;
	case CMD_GET_IMU_OFFSET:
												getIMUOffset();
												break;
	case CMD_SET_IMU_OFFSET:
												setIMUOffset(
												jsonCmdReceive["gx"],
												jsonCmdReceive["gy"],
												jsonCmdReceive["gz"],
                        jsonCmdReceive["ax"],
												jsonCmdReceive["ay"],
												jsonCmdReceive["az"],
                        jsonCmdReceive["cx"],
												jsonCmdReceive["cy"],
												jsonCmdReceive["cz"]);break;

	// esp-now settings.
  case CMD_BROADCAST_FOLLOWER:
  											changeBroadcastMode(
  											jsonCmdReceive["mode"],
  											jsonCmdReceive["mac"]
  											);break;
  case CMD_ESP_NOW_CONFIG:
  											changeEspNowMode(
  											jsonCmdReceive["mode"]
  											);break;
  case CMD_GET_MAC_ADDRESS: 
  											getThisDevMacAddress();
  											break;
  case CMD_ESP_NOW_ADD_FOLLOWER:
  											registerNewFollowerToPeer(
  											jsonCmdReceive["mac"]);break;
  case CMD_ESP_NOW_REMOVE_FOLLOWER:
  											deleteFollower(
  											jsonCmdReceive["mac"]);break;
  case CMD_ESP_NOW_GROUP_CTRL:
  											espNowGroupSend(
  											jsonCmdReceive["dev"],
  											jsonCmdReceive["x1"],
  											jsonCmdReceive["y1"],
  											jsonCmdReceive["z1"],
  											jsonCmdReceive["x2"],
  											jsonCmdReceive["y2"],
  											jsonCmdReceive["z2"],
                        jsonCmdReceive["x3"],
  											jsonCmdReceive["y3"],
  											jsonCmdReceive["z3"],
  											jsonCmdReceive["x4"],
  											jsonCmdReceive["y4"],
  											jsonCmdReceive["z4"],
                        jsonCmdReceive["x5"],
  											jsonCmdReceive["y5"],
  											jsonCmdReceive["z5"],
  											jsonCmdReceive["x6"],
  											jsonCmdReceive["y6"],
  											jsonCmdReceive["z6"],
  											jsonCmdReceive["cmd"],
  											jsonCmdReceive["megs"]
  											);break;
  case CMD_ESP_NOW_SINGLE:
  											espNowSingleDevSend(
  											jsonCmdReceive["mac"],
  											jsonCmdReceive["dev"],
  											jsonCmdReceive["x1"],
  											jsonCmdReceive["y1"],
  											jsonCmdReceive["z1"],
  											jsonCmdReceive["x2"],
  											jsonCmdReceive["y2"],
  											jsonCmdReceive["z2"],
                        jsonCmdReceive["x3"],
  											jsonCmdReceive["y3"],
  											jsonCmdReceive["z3"],
  											jsonCmdReceive["x4"],
  											jsonCmdReceive["y4"],
  											jsonCmdReceive["z4"],
                        jsonCmdReceive["x5"],
  											jsonCmdReceive["y5"],
  											jsonCmdReceive["z5"],
  											jsonCmdReceive["x6"],
  											jsonCmdReceive["y6"],
  											jsonCmdReceive["z6"],
  											jsonCmdReceive["cmd"],
  											jsonCmdReceive["megs"]
  											);break;



	// wifi settings.
	case CMD_WIFI_ON_BOOT: 
												configWifiModeOnBoot(
												jsonCmdReceive["cmd"]
												);break;
	case CMD_SET_AP: 			wifiModeAP(
									 			jsonCmdReceive["ssid"],
									 			jsonCmdReceive["password"]
									 			);break;
	case CMD_SET_STA: 		wifiModeSTA(
												jsonCmdReceive["ssid"],
												jsonCmdReceive["password"]
												);break;
	case CMD_WIFI_APSTA: 	wifiModeAPSTA(
										 	 	jsonCmdReceive["ap_ssid"],
											 	jsonCmdReceive["ap_password"],
											 	jsonCmdReceive["sta_ssid"],
											 	jsonCmdReceive["sta_password"]
											 	);break;
	case CMD_WIFI_INFO: 	wifiStatusFeedback();break;
	case CMD_WIFI_CONFIG_CREATE_BY_STATUS: 
												createWifiConfigFileByStatus();break;
	case CMD_WIFI_CONFIG_CREATE_BY_INPUT: 
												createWifiConfigFileByInput(
												jsonCmdReceive["mode"],
												jsonCmdReceive["ap_ssid"],
												jsonCmdReceive["ap_password"],
												jsonCmdReceive["sta_ssid"],
												jsonCmdReceive["sta_password"]
												);break;
	case CMD_WIFI_STOP: 	wifiStop();break;



	// servo settings.
	case CMD_SET_SERVO_ID:
												changeID(
												jsonCmdReceive["raw"],
												jsonCmdReceive["new"]
												);break;
	case CMD_SET_MIDDLE:  setMiddlePos(
												jsonCmdReceive["id"]
												);break;
	case CMD_SET_SERVO_PID: 
												setServosPID(
												jsonCmdReceive["id"],
												jsonCmdReceive["p"]
												);break;
  case CMD_LED_CTRL:		led_pwm_ctrl(
												jsonCmdReceive["IO4"],
												jsonCmdReceive["IO5"]);break;

	// esp-32 dev ctrl.
	case CMD_REBOOT: 			esp_restart();break;
	case CMD_FREE_FLASH_SPACE:
												freeFlashSpace();break;
	case CMD_BOOT_MISSION_INFO:
												missionContent("boot");break;
	case CMD_RESET_BOOT_MISSION:
												deleteFile("boot.mission");break;
												createFile("boot", "these cmds run automatically at boot.");
	case CMD_NVS_CLEAR:		nvs_flash_erase();
												delay(1000);
												nvs_flash_init();
												break;
	case CMD_INFO_PRINT:	configInfoPrint(
												jsonCmdReceive["cmd"]
												);break;
  case CMD_XYZT_CLAWS_CTRL: 
												Claws_allPosAbsBesselCtrl(
												jsonCmdReceive["leg"],
												jsonCmdReceive["x"],
												jsonCmdReceive["y"],
												jsonCmdReceive["z"]
												);break;
  case CMD_RAD_CLAWS_CTRL: 
												Claws_singleJointAbsCtrl(
												jsonCmdReceive["leg"],
												jsonCmdReceive["coxa"],
												jsonCmdReceive["femur"],
												jsonCmdReceive["tibia"]
												);break;
  case CMD_ANGLE_CLAWS_CTRL: 
												Claws_singleJointAngleCtrl(
												jsonCmdReceive["leg"],
												jsonCmdReceive["coxa"],
												jsonCmdReceive["femur"],
												jsonCmdReceive["tibia"]
												);break;                                            
	}
}


void serialCtrl() {
  static String receivedData;

  while (Serial.available() > 0) {
    char receivedChar = Serial.read();
    receivedData += receivedChar;

    // Detect the end of the JSON string based on a specific termination character
    if (receivedChar == '\n') {
      // Now we have received the complete JSON string
      DeserializationError err = deserializeJson(jsonCmdReceive, receivedData);
      if (err == DeserializationError::Ok) {
  			if (InfoPrint == 1) {
  				Serial.println(receivedData);
  			}
        jsonCmdReceiveHandler();
      } else {
        // Handle JSON parsing error here
      }
      // Reset the receivedData for the next JSON string
      receivedData = "";
    }
  }
}