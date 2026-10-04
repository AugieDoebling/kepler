const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>CLAWS_WEB</title>
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <!-- <script src="http://code.jquery.com/jquery-1.9.1.min.js"></script> -->
    <style type="text/css">
    html {
        display: inline-block;
        text-align: center;
        font-family: sans-serif;
    }
    body {
        background-image: -webkit-linear-gradient(#3F424F, #1E212E);
        font-family: "roboto",helt "sans-serif";
        font-weight: lighter;
        background-position: center 0;
        background-attachment: fixed;
        color: rgba(255, 255, 255, 0.6);
        font-size: 14px;
    }
    .cc-btn {
        border: 0;
        cursor: pointer;
        color: #fff;
        background: rgba(164,169,186,0);
        font-size: 1em;
        width: 100px;
        height: 100px;
         -webkit-touch-callout: none;
        -webkit-user-select: none;
        -khtml-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none; 
    }
    .cc-middle{
        width: 100px;
        height: 100px;
        border-radius: 50%;
        background-color: rgba(94,98,112,0.8);
    }
    .cc-btn:hover svg, .cc-middle:hover {
        opacity: 0.5;
    }
    .cc-btn:active svg, .cc-middle:hover{
        opacity: 0.5;
    }
    .controlor-c > div{
        width: 300px;
        height: 300px; 
        background-color: rgba(94,98,112,0.2);
        border-radius: 40px;
        box-shadow: 10px 10px 10px rgba(0,0,0,0.05);
        margin: auto;
    }
    .controlor-c > div > div{
        display: flex;
    }
    main {
        width: 960px;
        margin: auto;
    }
    section{margin: 40px 0;}
    .for-move {
        display: flex;
        align-items: center;
    }
    .for-move-a, .for-move-b{
        flex: 1;
        margin: 0 20px;
    }
    .h2-tt {
        font-size: 2em;
        font-weight: normal;
        color: rgba(255, 255, 255, 0.8);
        text-transform: uppercase;
    }
    .info-device-box .info-box{display: flex;}
    .info-device-box .info-box{padding: 20px 0;}
    .num-box-big > div, .num-box-sma > div{flex: 1;}
    .num-box-big > div:first-child{border-right: 1px solid rgba(216,216,216,0.1);}
    .num-box-mid {
        flex-wrap: wrap;
        justify-content: space-between;
    }
    .num-box-mid div{
        width:33.3333%;
        margin: 20px 0;
    }
    .info-device-box .info-box > div > span {
        display: block;
    }
    .info-box {
        background-image: linear-gradient(to right, rgba(94, 98, 112, 0.3), rgba(75, 80, 95, 0.3)) ;
        margin: 20px auto;
        border: 1px solid rgba(216, 216, 216, 0.1);
        box-shadow: 10px 10px 10px rgba(0,0,0,0.05);
        border-radius: 4px;
        color: rgba(255,255,255,0.5);
    }
    .big-num{font-size: 3em;}
    .mid-num{font-size: 2em;}
    .sma-num{font-size: 1.2em;}
    .num-color{
        background-image: linear-gradient(rgba(255,255,255,1),rgba(255,255,255,0.5));
        background-clip: text;
        color:transparent;
        -webkit-background-clip: text;
        -moz-background-clip: text;
        -ms-background-clip: text;
        font-weight: 900;
        line-height: 1em;
        margin: 0.5em 0;
    }
    .num-color-red{
        background-image: linear-gradient(rgba(181,104,108,1),rgba(181,104,108,0.5));
        background-clip: text;
        color:transparent;
        -webkit-background-clip: text;
        -moz-background-clip: text;
        -ms-background-clip: text;
        font-weight: 900;
        line-height: 1em;
        margin: 0.5em 0;
    }
    .controlor > div {margin: 80px 0;}
    .json-cmd-info{
        display: flex;
        flex-wrap: wrap;
    }
    .json-cmd-info > div {
        width: 33.33333%;
        padding: 10px 0;
    }
    .json-cmd-info p{
        line-height: 30px;
        margin: 0;
    }
    .json-cmd-info p span {
        display: block;
        color: rgba(255,255,255,0.8);
    }
    .small-btn{
        color: rgba(255,255,255,0.8);
        background-color: #5E6270;
        border: none;
        height: 48px;
        border-radius: 4px;
    }
    .small-btn-active{
        background-color: rgba(38,152,234,0.1);
        color: #2698EA;
        border: 1px solid #2698EA;
        height: 48px;
        border-radius: 4px;
    }
    .feedb-p input{
        width: 100%;
        height: 46px;
        background-color: rgba(0,0,0,0);
        padding: 0 10px;
        border: 1px solid rgba(194,196,201,0.15);
        border-radius: 4px;
        color: rgba(255, 255, 255, 0.8);
        font-size: 1.2em;
        margin-right: 10px;
    }
    .control-speed > div {
        width: 290px;
        margin: auto;
    }
    .control-speed > div > div{display: flex;}
    .control-speed label {flex: 1;}
    .small-btn, .small-btn-active{
        width: 90px;
    }
    .feedb-p{ display: flex;}
    .fb-input-info{
        margin: 0 20px;
    }
    .fb-info {margin: 20px;}
    .fb-info > span{line-height: 2.4em;}
    .btn-send:hover, .small-btn:hover{background-color: #2698EA;}
    .btn-send:active, .small-btn:active{background-color: #1b87d4;}
    .w-btn{
        color: #2698EA;
        background: transparent;
        padding: 10px;
        border: none;
    }
    .w-btn:hover{color: #2698EA;}
    .w-btn:active{color: #1b87d4;}
    @media screen and (min-width: 768px) and (max-width: 1200px){
        body{font-size: 16px;}
        main {
            width: 100%;
        }
        .for-move {
            display: block;
        }
        /* .controlor-c > div{width: 600px;height: 600px;}
        .cc-btn{width: 200px;height: 200px;} */
        .json-cmd-info{display: block;}
        .json-cmd-info p span{display: inline;}
        .json-cmd-info > div{
            display: flex;
            width: auto;
            padding: 20px;
            flex-wrap: wrap;
            justify-content: space-between;
        }
        .control-speed > div{width: 600px;}
        section{margin: 20px 0;}
    }
    @media screen and (min-width: 360px) and (max-width: 767px){
        main {
            width: 100%;
        }
        .for-move {
            display: block;
        }
        .json-cmd-info{display: block;}
        .json-cmd-info p span{display: inline;}
        .json-cmd-info > div{
            display: flex;
            width: auto;
            padding: 20px;
            flex-wrap: wrap;
            justify-content: space-between;
        }
        section{margin: 10px 0;}
        .info-box{margin: 10px auto;}
        .info-device-box .info-box{padding: 10px;}
        .num-box-mid div{margin: 10px 0;}
        .controlor-c > div{
            width: 270px;
            height: 270px;
        }
        .cc-btn{
            width: 90px;
            height: 90px;;
        }
        .big-num{font-size: 2em;}
        .controlor > div{margin: 40px 0;}
    }
    </style>
</head>
<script>
    // 方向与参数映射表
    const motionMap = {
        upLeft:   { x: 0.06,  y: 0.06,yaw:0.00 },
        up:       { x: 0.08,  y: 0.00,yaw:0.00 },
        upRight:  { x: 0.06,  y: -0.06,yaw:0.00 },
        left:     { x: 0.0,  y: 0.08,yaw:0.00 },
        stop:     { x: 0.00,  y: 0.00,yaw:0.00  },
        right:    { x: 0.00,  y: -0.08,yaw:0.00 },
        downLeft: { x: -0.06,  y: 0.06,yaw:0.00 },
        down:     { x: -0.08,  y: 0.00,yaw:0.00 },
        downRight:{ x: -0.06,  y: -0.06,yaw:0.00 },
        rotate_left:{ x: 0.0,  y: 0.0,yaw:0.6 },
        rotate_right:{ x: 0.0,  y: 0.0,yaw:-0.6 }
    };

    // 通用按钮控制函数
    function handleMotion(key) {
        const { x, y, yaw } = motionMap[key];
        movtionButton(x, y,yaw);
    }
</script>
<body>
    <main>
        <section>
            <div>
                <h2 class="h2-tt" id="deviceInfo">Control Panel</h2>
            </div>
            <div class="for-move">
                <div class="for-move-a">
                    <div class="info-device-box">
                        <div class="info-box num-box-big">
                            <div >
                                <span class="big-num num-color" id="V">-1.01</span>
                                <span id="Vn">VOLTAGE</span>
                            </div>
                            <div>
                                <span class="big-num num-color" id="RSSI">-1.01</span>
                                <span id="RSSIn">RSSI</span>
                            </div>
                        </div>
                    </div>
                    <div class="info-device-box">
                        <div class="info-box num-box-mid">
                            <!-- <div>
                                <span class="num-color mid-num" id="r">-1.01</span>
                                <span id="rn">ROLL</span>
                            </div>
                            <div>
                                <span class="num-color mid-num" id="p">-1.01</span>
                                <span id="pn">PITCH</span>
                            </div>
                            <div>
                                <span class="num-color mid-num" id="y">-1.01</span>
                                <span id="yn">YAW</span>
                            </div>
                            <div>
                                <span class="num-color mid-num" id="mX">-1.01</span>
                                <span id="mXn">PAN</span>
                            </div>
                            <div>
                                <span class="num-color mid-num" id="mY">-1.01</span>
                                <span id="mYn">TILT</span>
                            </div>
                            <div>
                                <span class="num-color mid-num" id="mZ">-1.01</span>
                                <span id="mZn">SPD_R</span>
                            </div> -->
                        </div>
                    </div>
                    <div class="info-device-box">
                        <div class="info-box num-box-sma">
                            <div>
                                <span class="num-color sma-num" id="IP">192.168.10.67</span>
                                <span id="IPn">IP</span>
                            </div>
                            <div>
                                <span class="num-color sma-num" id="MAC">44:17:93:EE:F8:F8</span>
                                <span id="MACn">MAC</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="for-move-b controlor">
                    <div class="controlor-c">
                        <div>
                            <div>
                                <label><button class="cc-btn" onmousedown="handleMotion('upLeft');" ontouchstart="handleMotion('upLeft');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');"><svg fill="none" version="1.1" width="23" height="23" viewBox="0 0 23 23"><g style="mix-blend-mode:passthrough"><path d="M0,2L0,18.1716C0,19.9534,2.15428,20.8457,3.41421,19.5858L19.5858,3.41421C20.8457,2.15428,19.9534,0,18.1716,0L2,0C0.895431,0,0,0.895431,0,2Z" fill="#D8D8D8" fill-opacity="0.20000000298023224"/></g></svg></button></label>
                                <label><button class="cc-btn" onmousedown="handleMotion('up');" ontouchstart="handleMotion('up');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');"><svg fill="none" version="1.1" width="26.87807685863504" height="15.435028109846826" viewBox="0 0 26.87807685863504 15.435028109846826"><g style="mix-blend-mode:passthrough" transform="matrix(0.9999999403953552,0,0,0.9999999403953552,0,0)"><path d="M12.0248,0.585787L0.589796,12.0208C-0.670133,13.2807,0.222199,15.435,2.00401,15.435L24.8741,15.435C26.6559,15.435,27.5482,13.2807,26.2883,12.0208L14.8533,0.585787C14.0722,-0.195262,12.8059,-0.195262,12.0248,0.585787Z" fill="#D8D8D8" fill-opacity="0.800000011920929"/></g></svg></button></label>
                                <label><button class="cc-btn" onmousedown="handleMotion('upRight');" ontouchstart="handleMotion('upRight');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');"><svg fill="none" version="1.1" width="23" height="23" viewBox="0 0 23 23"><g style="mix-blend-mode:passthrough" transform="matrix(0,1,-1,0,23,-23)"><path d="M23,2L23,18.1716C23,19.9534,25.15428,20.8457,26.41421,19.5858L42.5858,3.41421C43.8457,2.15428,42.9534,0,41.1716,0L25,0C23.895431,0,23,0.895431,23,2Z" fill="#D8D8D8" fill-opacity="0.20000000298023224"/></g></svg></button></label>
                            </div>
                            <div>
                                <label><button class="cc-btn" onmousedown="handleMotion('left');" ontouchstart="handleMotion('left');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');"><svg fill="none" version="1.1" width="15.435028109846769" height="26.87807685863504" viewBox="0 0 15.435028109846769 26.87807685863504"><g style="mix-blend-mode:passthrough" transform="matrix(0.9999999403953552,0,0,0.9999999403953552,0,0)"><path d="M0.585787,14.8533L12.0208,26.2883C13.2807,27.5482,15.435,26.6559,15.435,24.8741L15.435,2.00401C15.435,0.222199,13.2807,-0.670133,12.0208,0.589795L0.585787,12.0248C-0.195262,12.8059,-0.195262,14.0722,0.585787,14.8533Z" fill="#D8D8D8" fill-opacity="0.800000011920929"/></g></svg></button></label>
                                <label><button class="cc-btn" onmousedown="handleMotion('stop');" ontouchstart="handleMotion('stop');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');">STOP</button></label>
                                <label><button class="cc-btn" onmousedown="handleMotion('right');" ontouchstart="handleMotion('right');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');"><svg fill="none" version="1.1" width="15.435030017195288" height="26.87807685863504" viewBox="0 0 15.435030017195288 26.87807685863504"><g style="mix-blend-mode:passthrough" transform="matrix(0.9999999403953552,0,0,0.9999999403953552,0,0)"><path d="M14.8492,12.0248L3.41422,0.589796C2.15429,-0.670133,-9.53674e-7,0.222199,9.53674e-7,2.00401L9.53674e-7,24.8741C-9.53674e-7,26.6559,2.15429,27.5482,3.41421,26.2883L14.8492,14.8533C15.6303,14.0722,15.6303,12.8059,14.8492,12.0248Z" fill="#D8D8D8" fill-opacity="0.800000011920929"/></g></svg></button></label>
                            </div>
                            <div>
                                <label><button class="cc-btn" onmousedown="handleMotion('downLeft');" ontouchstart="handleMotion('downLeft');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');"><svg fill="none" version="1.1" width="23" height="23" viewBox="0 0 23 23"><g style="mix-blend-mode:passthrough" transform="matrix(0,-1,1,0,-23,23)"><path d="M0,25L0,41.1716C0,42.9534,2.15428,43.8457,3.41421,42.5858L19.5858,26.41421C20.8457,25.15428,19.9534,23,18.1716,23L2,23C0.895431,23,0,23.895431,0,25Z" fill="#D8D8D8" fill-opacity="0.20000000298023224"/></g></svg></button></label>
                                <label><button class="cc-btn" onmousedown="handleMotion('down');" ontouchstart="handleMotion('down');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');"><svg fill="none" version="1.1" width="26.87807685863504" height="15.435030017195231" viewBox="0 0 26.87807685863504 15.435030017195231"><g style="mix-blend-mode:passthrough" transform="matrix(0.9999999403953552,0,0,0.9999999403953552,0,0)"><path d="M14.8533,14.8492L26.2883,3.41422C27.5482,2.15429,26.6559,-9.53674e-7,24.8741,9.53674e-7L2.00401,9.53674e-7C0.222199,-9.53674e-7,-0.670133,2.15429,0.589795,3.41421L12.0248,14.8492C12.8059,15.6303,14.0722,15.6303,14.8533,14.8492Z" fill="#D8D8D8" fill-opacity="0.800000011920929"/></g></svg></button></label>
                                <label><button class="cc-btn" onmousedown="handleMotion('downRight');" ontouchstart="handleMotion('downRight');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');"><svg fill="none" version="1.1" width="23" height="23" viewBox="0 0 23 23"><g style="mix-blend-mode:passthrough" transform="matrix(-1,0,0,-1,46,46)"><path d="M23,25L23,41.1716C23,42.9534,25.15428,43.8457,26.41421,42.5858L42.5858,26.41421C43.8457,25.15428,42.9534,23,41.1716,23L25,23C23.895431,23,23,23.895431,23,25Z" fill="#D8D8D8" fill-opacity="0.20000000298023224"/></g></svg></button></label>
                            </div>
                        </div>
                    </div>
                    <div class="control-speed">
                        <br>
                        <div>
                            <div id="device-gimbal-btn_B">
                                <label><button name="speedbtn" class="small-btn" onmousedown="handleMotion('rotate_left');" ontouchstart="handleMotion('rotate_left');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');">LEFT</button></label>
                                <label><button name="speedbtn" class="small-btn" onclick="clawsinit();">INIT</button></label>
                                <label><button name="speedbtn" class="small-btn" onmousedown="handleMotion('rotate_right');" ontouchstart="handleMotion('rotate_right');" onmouseup="handleMotion('stop');" ontouchend="handleMotion('stop');">RIGHT</button></label>
                            </div>
                        </div>
                        <br>
                        <br>
                        <div>
                            <div id="device-gimbal-btn_D">
                                <label><button name="speedbtn" class="small-btn" onclick="Steadystart(1);">STEADY START</button></label>
                                <label><button name="speedbtn" class="small-btn" onclick="Steadystart(0);">STEADY END</button></label>
                            </div>
                        </div>
                        <br>
                        <br>
                        <div>
                            <div id="device-speed-btn">
                                <label><button name="speedbtn" class="small-btn" onclick="changeSpeed(0.5);">SLOW</button></label>
                                <label><button name="speedbtn" class="small-btn" onclick="changeSpeed(0.8);">MIDDLE</button></label>
                                <label><button name="speedbtn" class="small-btn" onclick="changeSpeed(1.0);">FAST</button></label>
                            </div>
                        </div>
                        <br>
                        <div>
                            <div id="device-led-btn">
                                <label><button name="speedbtn" class="small-btn" onclick="ledCtrl(1);">IO4</button></label>
                                <label><button name="speedbtn" class="small-btn" onclick="ledCtrl(2);">IO5</button></label>
                                <label><button name="speedbtn" class="small-btn" onclick="ledCtrl(0);">OFF</button></label>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
        <section>
            <div class="fb-info">
                <h2 class="h2-tt" id="deviceInfo">Feedback infomation</h2>
                <span id="fbInfo" word-wrap="break-all">Json feedback infomation shows here.</span>
            </div>
            <div class="fb-input-info">
                <div class="feedb-p">
                    <input type="text" id="jsonData" placeholder="Input json cmd here.">
                    <label><button class="small-btn btn-send" onclick="jsonSend();">SEND</button></label>
                </div>
                <div class="info-box json-cmd-info">
                    <div>
                        <p>CMD_Goal_STOP: <span id="cmd0" class="cmd-value">{"T":2}</span> </p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd0');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_SPEED_CTRL: <span id="cmd1" class="cmd-value">{"T":1,"X":0.02,"Y":0.02,"Yaw":0.0}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd1');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_AMP_CTRL: <span id="cmd13" class="cmd-value">{"T":3,"r":0.1,"p":0.0,"y":0.0,"f":1}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd13');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_XYZT_CLAWS_CTRL: <span id="cmd701" class="cmd-value">{"T":701,"leg":0,"x":-0.18,"y":-109.69,"z":-80.83}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd701');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_RAD_CLAWS_CTRL: <span id="cmd702" class="cmd-value">{"T":702,"leg":0,"coxa":0,"femur":0,"tibia":1.57}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd702');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_ANGLE_CLAWS_CTRL: <span id="cmd703" class="cmd-value">{"T":703,"leg":0,"coxa":0,"femur":0,"tibia":90}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd703');">INPUT</button>
                    </div>
                </div>
                <div class="info-box json-cmd-info">
                    <div>
                        <p>OLED_SET: <span id="cmd3" class="cmd-value">{"T":13,"lineNum":0,"Text":"putYourTextHere"}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd3');">INPUT</button>
                    </div>
                    <div>
                        <p>OLED_DEFAULT: <span id="cmd-3" class="cmd-value">{"T":-3}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd-3');">INPUT</button>
                    </div>
                </div>
                <div class="info-box json-cmd-info">
                    <div>
                        <p>CMD_GET_IMU_DATA: <span id="cmd126" class="cmd-value">{"T":126}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd126');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_CALI_IMU_STEP: <span id="cmd127" class="cmd-value">{"T":127,"step":0}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd127');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_GET_IMU_OFFSET: <span id="cmd128" class="cmd-value">{"T":128}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd128');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_SET_IMU_OFFSET: <span id="cmd129" class="cmd-value">{"T":129,"x":-12,"y":0,"z":0}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd129');">INPUT</button>
                    </div>
                </div>
                <div class="info-box json-cmd-info">
                    <div>
                        <p>CMD_BASE_FEEDBACK: <span id="cmd130" class="cmd-value">{"T":130}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd130');">INPUT</button>
                    </div>
                </div>
                <div class="info-box json-cmd-info">
                    <div>
                        <p>CMD_LED_CTRL: <span id="cmd132" class="cmd-value">{"T":132,"IO4":255,"IO5":255}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd132');">INPUT</button>
                    </div>
                </div>
                <div class="info-box json-cmd-info">
                    <div>
                        <p>CMD_MISSION_CONTENT: <span id="cmd221" class="cmd-value">{"T":221,"name":"mission_a"}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd221');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_APPEND_STEP_JSON: <span id="cmd222" class="cmd-value">{"T":222,"name":"mission_a","step":"{\"T\":137,\"s\":1,\"y\":0}"}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd222');">INPUT</button>
                    </div>
                </div>
                <div class="info-box json-cmd-info">
                    <div>
                        <p>CMD_WIFI_ON_BOOT: <span id="cmd401" class="cmd-value">{"T":401,"cmd":3}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd401');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_SET_AP: <span id="cmd402" class="cmd-value">{"T":402,"ssid":"RoArm-M2","password":"12345678"}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd402');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_SET_STA: <span id="cmd403" class="cmd-value">{"T":403,"ssid":"na","password":"ps"}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd403');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_WIFI_APSTA: <span id="cmd404" class="cmd-value">{"T":404,"ap_ssid":"RoArm-M2","ap_password":"12345678","sta_ssid":"na","sta_password":"ps"}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd404');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_WIFI_INFO: <span id="cmd405" class="cmd-value">{"T":405}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd405');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_WIFI_CONFIG_CREATE_BY_STATUS: <span id="cmd406" class="cmd-value">{"T":406}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd406');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_WIFI_CONFIG_CREATE_BY_INPUT: <span id="cmd406" class="cmd-value">{"T":407,"mode":3,"ap_ssid":"RoArm-M2","ap_password":"12345678","sta_ssid":"na","sta_password":"ps"}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd406');">INPUT</button>
                    </div>
                </div>
                <div class="info-box json-cmd-info">
                    <div>
                        <p>CMD_SET_SERVO_ID: <span id="cmd501" class="cmd-value">{"T":501,"raw":1,"new":21}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd501');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_SET_MIDDLE: <span id="cmd502" class="cmd-value">{"T":502,"id":21}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd502');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_SET_SERVO_PID: <span id="cmd503" class="cmd-value">{"T":503,"id":21,"p":16}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd503');">INPUT</button>
                    </div>
                </div>
                <div class="info-box json-cmd-info">
                    <div>
                        <p>CMD_REBOOT: <span id="cmd600" class="cmd-value">{"T":600}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd600');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_FREE_FLASH_SPACE: <span id="cmd601" class="cmd-value">{"T":601}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd601');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_BOOT_MISSION_INFO: <span id="cmd602" class="cmd-value">{"T":602}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd602');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_RESET_BOOT_MISSION: <span id="cmd603" class="cmd-value">{"T":603}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd603');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_NVS_CLEAR: <span id="cmd604" class="cmd-value">{"T":604}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd604');">INPUT</button>
                    </div>
                    <div>
                        <p>CMD_INFO_PRINT: <span id="cmd605" class="cmd-value">{"T":605,"cmd":1}</span></p>
                        <button class="w-btn" onclick="cmdFill('jsonData', 'cmd605');">INPUT</button>
                    </div>
                </div>
            </div>
        </section>
    </main>
<script>
    var cmdA;
    var cmdB;
    var cmdC;

    var forwardButton;   // 1
    var backwardButton;  // 2
    var fbNewer;

    var leftButton;      // 1
    var rightButton;     // 2
    var lrNewer;

    var last_forwardButton;   // 1
    var last_backwardButton;  // 2
    var last_fbNewer;

    var last_leftButton;      // 1
    var last_rightButton;     // 2
    var last_lrNewer;

    var speed_rate  = 1; // 1:fast 0.6:middle 0.3:slow
    var left_speed  = 0;
    var right_speed = 0;
    var send_heartbeat = 0;

    var io4_status = 0;
    var io5_status = 0;

    var gimbal_T = 135;
    var gimbal_X = 0;
    var gimbal_Y = 0;
    var read_X = 0;
    var read_Y = 0;

    var steady_status = 0;
    var steady_bias   = 0;

    getDevInfo();
    ledCtrl(0);
    setInterval(function() {
        getDevInfo();
    }, 2510);

    setInterval(function() {
        heartBeat();
    }, 1500);

    setInterval(function() {
        infoUpdate();
    }, 2000);


    function cmdFill(rawInfo, fillInfo) {
        document.getElementById(rawInfo).value = document.getElementById(fillInfo).innerHTML;
    }
    function jsonSend() {
        send_heartbeat = 0;
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function() {
            if (this.readyState == 4 && this.status == 200) {
              document.getElementById("fbInfo").innerHTML =
              this.responseText;
            }
        };
        xhttp.open("GET", "js?json="+document.getElementById('jsonData').value, true);
        xhttp.send();
    }
    function infoUpdate() {
        var jsonCmd = {
            "T": 130
        }
        var jsonString = JSON.stringify(jsonCmd);
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function() {
            if (this.readyState == 4 && this.status == 200) {
                var jsonResponse = JSON.parse(this.responseText);
                document.getElementById("V").innerHTML = jsonResponse.v.toFixed(2)/100;
                if (jsonResponse.v<11.06) {
                    document.getElementById("V").classList.remove("num-color");
                    document.getElementById("V").classList.add("num-color-red");
                }else{
                    document.getElementById("V").classList.remove("num-color-red");
                    document.getElementById("V").classList.add("num-color");
                }

                // document.getElementById("r").innerHTML = jsonResponse.r.toFixed(2);
                // document.getElementById("p").innerHTML = jsonResponse.p.toFixed(2);
                // document.getElementById("y").innerHTML = jsonResponse.y.toFixed(2);
                // document.getElementById("mZ").innerHTML = speed_rate;

                // if (jsonResponse.hasOwnProperty('pan')) {
                //     document.getElementById("mX").innerHTML = jsonResponse.pan.toFixed(2);
                //     document.getElementById("mY").innerHTML = jsonResponse.tilt.toFixed(2);

                //     read_X = jsonResponse.pan;
                //     read_Y = jsonResponse.tilt;
                // } else{
                //     document.getElementById("mX").innerHTML = "null";
                //     document.getElementById("mY").innerHTML = "null";

                //     read_X = 0;
                //     read_Y = 0;
                // }
            }
        };
        xhttp.open("GET", "js?json=" + jsonString, true);
        xhttp.send();
    }
    function getDevInfo() {
        var jsonCmd = {
            "T": 405
        }
        var jsonString = JSON.stringify(jsonCmd);
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function() {
            if (this.readyState == 4 && this.status == 200) {
                var jsonResponse = JSON.parse(this.responseText);

                document.getElementById("IP").innerHTML = jsonResponse.ip;
                document.getElementById("MAC").innerHTML = jsonResponse.mac;
                document.getElementById("RSSI").innerHTML = jsonResponse.rssi;
            }
        };
        xhttp.open("GET", "js?json=" + jsonString, true);
        xhttp.send();
    }
    function changeSpeed(inputSpd) {
        speed_rate = inputSpd;
    }
    function heartBeat() {
        if (send_heartbeat == 1) {
            var jsonCmd = {
               "T":1,
                "X":left_speed*speed_rate,
                "Y":right_speed*speed_rate,
              "Yaw":yaw_speed,
            }
            var jsonString = JSON.stringify(jsonCmd);
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "js?json=" + jsonString, true);
            xhr.send();
        }
    }
    function movtionButton(spdL, spdR,yaw){
        left_speed  = spdL;
        right_speed = spdR;
        yaw_speed=yaw;
        send_heartbeat = 1;
        const EPS = 1e-6;
        if (Math.abs(spdL) < EPS && Math.abs(spdR) < EPS && Math.abs(yaw) < EPS)
        {
          var jsonCmd = {
            "T":2,
        }
        }
        else {
        var jsonCmd = {
            "T":1,
            "X":spdL*speed_rate,
            "Y":spdR*speed_rate,
            "Yaw":yaw_speed*speed_rate,
        }
        }
        var jsonString = JSON.stringify(jsonCmd);
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "js?json=" + jsonString, true);
        xhr.send();
    }
    function ledCtrl(inputCmd){
        if (inputCmd == 0) {
            io4_status = 0;
            io5_status = 0;
        }
        else if (inputCmd == 1) {
            if (io4_status == 0) {
                io4_status = 255;
            }
            else {
                io4_status = 0;
            }
        }
        else if (inputCmd == 2) {
            if (io5_status == 0) {
                io5_status = 255;
            }
            else {
                io5_status = 0;
            }
        }
        var jsonCmd = {
            "T":132,
            "IO4":io4_status,
            "IO5":io5_status
        }
        var jsonString = JSON.stringify(jsonCmd);
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "js?json=" + jsonString, true);
        xhr.send();
    }
    function clawsinit(){
        var jsonCmd = {
            "T":100,
        }
        var jsonString = JSON.stringify(jsonCmd);
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "js?json=" + jsonString, true);
        xhr.send();
    }
    function Steadystart(inputS){
        var jsonCmd = {
            "T":4,
            "cmd":inputS
        }
        var jsonString = JSON.stringify(jsonCmd);
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "js?json=" + jsonString, true);
        xhr.send();
    }
    function gimbalSteady(inputS,inputY){
        steady_status = inputS;
        steady_bias = inputY;
        var jsonCmd = {
            "T":137,
            "s":steady_status,
            "y":steady_bias
        }
        var jsonString = JSON.stringify(jsonCmd);
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "js?json=" + jsonString, true);
        xhr.send();
    }
    function gimbalCtrl(inputCmd){
        if (inputCmd == 0) {
            gimbal_T = 135;
        }else if (inputCmd == 1) {
            gimbal_T = 134;
            gimbal_X = read_X;
            gimbal_Y = 90;
            if (steady_status == 1) {
                steady_bias = steady_bias + 5;
                if (steady_bias > 90) {
                    steady_bias = 90;
                }
            }
        }else if (inputCmd == 2) {
            gimbal_T = 134;
            gimbal_X = read_X;
            gimbal_Y = -45;
            if (steady_status == 1) {
                steady_bias = steady_bias - 5;
                if (steady_bias < -45) {
                    steady_bias = 45;
                }
            }
        }else if (inputCmd == 3) {
            gimbal_T = 134;
            gimbal_X = -180;
            gimbal_Y = read_Y;
        }else if (inputCmd == 4) {
            gimbal_T = 134;
            gimbal_X = 180;
            gimbal_Y = read_Y;
        }else if (inputCmd == 5) {
            gimbal_T = 134;
            gimbal_X = 0;
            gimbal_Y = 0;
            if (steady_status == 1) {
                steady_bias = 0;
            }
        }

        if (steady_status == 0) {
            var jsonCmd = {
                "T":gimbal_T,
                "X":gimbal_X,
                "Y":gimbal_Y,
                "SX":600,
                "SY":600
            }
            var jsonString = JSON.stringify(jsonCmd);
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "js?json=" + jsonString, true);
            xhr.send();
        }else if (steady_status == 1) {
            gimbalSteady(1,steady_bias);
        }
    }

    function cmdProcess(){
        if (forwardButton == 0 && backwardButton == 0 && leftButton == 0 && rightButton == 0) {
            handleMotion('stop');
        }
        else if (forwardButton == 1 && backwardButton == 0 && leftButton == 0 && rightButton == 0){
            handleMotion('up');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 1 && leftButton == 0 && rightButton == 0){
            handleMotion('up');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 2 && leftButton == 0 && rightButton == 0){
            handleMotion('down');
        }else if (forwardButton == 0 && backwardButton == 1 && leftButton == 0 && rightButton == 0){
            handleMotion('down');
        }
        else if (forwardButton == 0 && backwardButton == 0 && leftButton == 1 && rightButton == 0){
            handleMotion('left');
        }else if (forwardButton == 0 && backwardButton == 0 && leftButton == 1 && rightButton == 1 && lrNewer == 1){
            handleMotion('left');
        }else if (forwardButton == 0 && backwardButton == 0 && leftButton == 0 && rightButton == 1){
            handleMotion('right');
        }else if (forwardButton == 0 && backwardButton == 0 && leftButton == 1 && rightButton == 1 && lrNewer == 2){
            handleMotion('right');
        }
        else if (forwardButton == 1 && backwardButton == 0 && leftButton == 1 && rightButton == 0){
            handleMotion('upLeft');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 1 && leftButton == 1 && rightButton == 0){
            handleMotion('upLeft');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 1 && leftButton == 1 && rightButton == 1 && lrNewer == 1){
            handleMotion('upLeft');
        }else if (forwardButton == 1 && backwardButton == 0 && leftButton == 1 && rightButton == 1 && lrNewer == 1){
            handleMotion('upLeft');
        }
        else if (forwardButton == 1 && backwardButton == 0 && leftButton == 0 && rightButton == 1){
            handleMotion('upRight');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 1 && leftButton == 0 && rightButton == 1){
            handleMotion('upRight');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 1 && leftButton == 1 && rightButton == 1 && lrNewer == 2){
            handleMotion('upRight');
        }else if (forwardButton == 1 && backwardButton == 0 && leftButton == 1 && rightButton == 1 && lrNewer == 2){
            handleMotion('upRight');
        }
        else if (forwardButton == 0 && backwardButton == 1 && leftButton == 1 && rightButton == 0){
            handleMotion('downLeft');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 2 && leftButton == 1 && rightButton == 0){
            handleMotion('downLeft');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 2 && leftButton == 1 && rightButton == 1 && lrNewer == 1){
            handleMotion('downLeft');
        }else if (forwardButton == 0 && backwardButton == 1 && leftButton == 1 && rightButton == 1 && lrNewer == 1){
            handleMotion('downLeft');
        }
        else if (forwardButton == 0 && backwardButton == 1 && leftButton == 0 && rightButton == 1){
            handleMotion('downRight');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 2 && leftButton == 0 && rightButton == 1){
            handleMotion('downRight');
        }else if (forwardButton == 1 && backwardButton == 1 && fbNewer == 2 && leftButton == 1 && rightButton == 1 && lrNewer == 2){
            handleMotion('downRight');
        }else if (forwardButton == 0 && backwardButton == 1 && leftButton == 1 && rightButton == 1 && lrNewer == 2){
            handleMotion('downRight');
        }
    }

    document.onkeydown = function (event) {
        var e = event || window.event || arguments.callee.caller.arguments[0];
        if (e && e.keyCode == 65) {
            // alert ("A down");
            leftButton = 1;
            lrNewer = 1;
        }else if (e && e.keyCode == 87) {
            // alert ("W down");
            forwardButton = 1;
            fbNewer = 1;
        }else if (e && e.keyCode == 83) {
            // alert ("S down");
            backwardButton = 1;
            fbNewer = 2;
        }else if (e && e.keyCode == 68) {
            // alert ("D down");
            rightButton = 1;
            lrNewer = 2;
        }
        else if (e && e.keyCode == 13) {
            // alert ("Enter down");
            jsonSend();
        }
        else if (e && e.keyCode == 37) {
            // alert ("left down");
            leftButton = 1;
            lrNewer = 1;
        }else if (e && e.keyCode == 38) {
            // alert ("up down");
            forwardButton = 1;
            fbNewer = 1;
        }else if (e && e.keyCode == 40) {
            // alert ("down down");
            backwardButton = 1;
            fbNewer = 2;
        }else if (e && e.keyCode == 39) {
            // alert ("right down");
            rightButton = 1;
            lrNewer = 2;
        }

        if(forwardButton != last_forwardButton || backwardButton != last_backwardButton || fbNewer != last_fbNewer || leftButton != last_leftButton || last_rightButton != rightButton || lrNewer != last_fbNewer) {
            cmdProcess();
            last_forwardButton = forwardButton;
            last_backwardButton = backwardButton;
            last_fbNewer = fbNewer;

            last_leftButton = leftButton;
            last_rightButton = rightButton;
            last_lrNewer = lrNewer;
        }
    }

    document.onkeyup = function (event) {
        var e = event || window.event || arguments.callee.caller.arguments[0];
        if (e && e.keyCode == 65) {
            // alert ("A up");
            leftButton = 0;
        }else if (e && e.keyCode == 87) {
            // alert ("W up");
            forwardButton = 0;
        }else if (e && e.keyCode == 83) {
            // alert ("S up");
            backwardButton = 0;
        }else if (e && e.keyCode == 68) {
            // alert ("D up");
            rightButton = 0;
        }
        else if (e && e.keyCode == 37) {
            // alert ("left up");
            leftButton = 0;
        }else if (e && e.keyCode == 38) {
            // alert ("up up");
            forwardButton = 0;
        }else if (e && e.keyCode == 40) {
            // alert ("down up");
            backwardButton = 0;
        }else if (e && e.keyCode == 39) {
            // alert ("right up");
            rightButton = 0;
        }

        cmdProcess();

        last_forwardButton = forwardButton;
        last_backwardButton = backwardButton;
        last_fbNewer = fbNewer;

        last_leftButton = leftButton;
        last_rightButton = rightButton;
        last_lrNewer = lrNewer;
    }
</script>
</body>
</html>
)rawliteral";