#include "HexArth_web_page.h"

// // Create AsyncWebServer object on port 80
// WebServer server(80);

// void handleRoot(){
//   server.send(200, "text/html", index_html); //Send web page
// }


// void webCtrlServer(){
//   server.on("/", handleRoot);


//   server.on("/js", [](){
//     String jsonCmdWebString = server.arg(0);
//     deserializeJson(jsonCmdReceive, jsonCmdWebString);
//     jsonCmdReceiveHandler();
//     serializeJson(jsonInfoHttp, jsonFeedbackWeb);
//     server.send(200, "text/plane", jsonFeedbackWeb);
//     jsonFeedbackWeb = "";
//     jsonInfoHttp.clear();
//     jsonCmdReceive.clear();
//   });

//   // Start server
//   server.begin();
//   Serial.println("Server Starts.");
// }

// void initHttpWebServer(){
//   webCtrlServer();
// }
#include <ESPAsyncWebServer.h>

// Create AsyncWebServer object on port 80
AsyncWebServer server(80);

void handleRoot(AsyncWebServerRequest *request) {
  request->send(200, "text/html", index_html); //Send web page
}

void webCtrlServer() {
  // 根目录
  server.on("/", HTTP_GET, handleRoot);

  // /js 接口
  server.on("/js", HTTP_GET, [](AsyncWebServerRequest *request) {
    if (request->hasParam("json")) {
      String jsonCmdWebString = request->getParam("json")->value();

      // 反序列化 JSON
      DeserializationError error = deserializeJson(jsonCmdReceive, jsonCmdWebString);
      if (!error) {
        jsonCmdReceiveHandler();
      }
    }

    // 序列化 JSON 并返回
    serializeJson(jsonInfoHttp, jsonFeedbackWeb);
    request->send(200, "application/json", jsonFeedbackWeb);

    // 清理
    jsonFeedbackWeb = "";
    jsonInfoHttp.clear();
    jsonCmdReceive.clear();
  });

  // 启动服务
  server.begin();
  Serial.println("AsyncWebServer Starts.");
}

void initHttpWebServer() {
  webCtrlServer();
}