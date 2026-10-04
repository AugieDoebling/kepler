// the uart used to control servos.
// GPIO 18 - S_RXD, GPIO 19 - S_TXD, as default.
#define RoArmM2_Servo_RXD 18
#define RoArmM2_Servo_TXD 19


unsigned long lastCmdRecvTime = millis();
bool heartbeatStopFlag = false;
int HEART_BEAT_DELAY = 3000;
// 2: flow feedback.
// 1: [default]print debug info in serial.
// 0: don't print debug info in serial.
byte InfoPrint = 1;
int feedbackFlowExtraDelay = 50;
// devices info:
// espNowMode: 0 - none
//             1 - flow-leader(group): sending cmds
//             2 - flow-leader(single): sending cmds to a single follower
//             3 - [default]follower: recv cmds
byte espNowMode = 3;
String thisMacStr;
#define FEEDBACK_CLAWS_INFO  1001
// set the broadcast ctrl mode.
// broadcast mac address: FF:FF:FF:FF:FF:FF.
// true  - [default]it can be controled by broadcast mac address.
// false - it won't be controled by broadcast mac address.
bool ctrlByBroadcast = true;

// you can define some whitelist mac addresses here.
uint8_t mac_whitelist_broadcast[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// the mac that esp-now cmd received from
uint8_t mac_received_from[6];

// Multifunction End-Effector Switching System.
// 0 - end servo as grab.
// 1 - end servo as a joint moving in vertical plane.
byte EEMode = 0;

// esp-now run json block cmd
// false: can not run esp-now block cmd
// true:  it can process esp-now block cmd but there'll be a delay
bool espNowRunBlockCmd = true;

// run new json cmd
bool runNewJsonCmd = false;

bool Balanced_Mode=false;
bool Balanced_Init=false;
bool Balanced_frist=false;
u8 jointID[18] = {21,22,23,31,32,33,41,42,43,71,72,73,61,62,63,51,52,53};

#define COXA_JOINT 1
#define FEMUR_JOINT 2
#define TIBIA_JOINT 3

#define leg0_coxa_joint 0
#define leg0_femur_joint 1
#define leg0_tibia_joint 2
#define leg1_coxa_joint 3
#define leg1_femur_joint 4
#define leg1_tibia_joint 5
#define leg2_coxa_joint 6
#define leg2_femur_joint 7
#define leg2_tibia_joint 8

#define leg3_coxa_joint 9
#define leg3_femur_joint 10
#define leg3_tibia_joint 11
#define leg4_coxa_joint 12
#define leg4_femur_joint 13
#define leg4_tibia_joint 14
#define leg5_coxa_joint 15
#define leg5_femur_joint 16
#define leg5_tibia_joint 17


// define servoID
//   |---[14]---|
//   ||  |  |  ||
//   ||        ||
//   ||  |  |  ||
//   ||        ||
//   ||  |  |  ||
//   || -[15]- ||
//   ||        ||
//   ||[13][12]||
//     |  __  |
//       [11]


#define ARM_SERVO_MIDDLE_POS  2047
#define COXA_SERVO_MIDDLE_OFFSET  341
#define FEMUR_SERVO_MIDDLE_OFFSET  341
#define TIBIA_SERVO_MIDDLE_OFFSET  682
#define ARM_SERVO_MIDDLE_ANGLE 180
#define ARM_SERVO_POS_RANGE   4096
#define ARM_SERVO_ANGLE_RANGE  360
#define ARM_SERVO_INIT_SPEED   600
#define ARM_SERVO_INIT_ACC      20

#define ARM_L1_LENGTH_MM    32.966
#define ARM_L2_LENGTH_MM_A  43.00
#define ARM_L2_LENGTH_MM_B	50.00 
#define ARM_L3_LENGTH_MM_A_0	95.353
#define ARM_L3_LENGTH_MM_B_0	3.257

// 	  TYPE:0
//    -------L3A-----------O==L2B===
//    |                    ^       ||
//   L3B                   |       ||
//    |              ELBOW_JOINT   ||
//                                L2A
//                                 ||
//                                 ||
//                                 ||
//               SHOULDER_JOINT -> OO
//                                [||]
//                                 L1
//                                [||]
//                   BASE_JOINT -> X
double l1  = ARM_L1_LENGTH_MM;
double l2A = ARM_L2_LENGTH_MM_A;
double l2B = ARM_L2_LENGTH_MM_B;
double l2  = sqrt(l2A * l2A + l2B * l2B);
double t2rad = atan2(l2B, l2A);
double l3A = ARM_L3_LENGTH_MM_A_0;
double l3B = ARM_L3_LENGTH_MM_B_0;
double l3  = sqrt(l3A * l3A + l3B * l3B);
double t3rad = atan2(l3B, l3A);



#define MAX_SERVO_ID 32 // MAX:253

// the uart used to control servos.
// GPIO 18 - S_RXD, GPIO 19 - S_TXD, as default.
#define S_RXD 18
#define S_TXD 19

struct LegIKResult {
    double coxa;   // 髋关节水平旋转角（绕垂直轴）
    double femur;  // 大腿抬起角（绕侧向轴）
    double tibia;  // 小腿伸展角（绕侧向轴）
};
LegIKResult ESPAngle[6];
// 单条腿的关节反馈角度（三个关节）
// 从舵机或编码器读取的当前实际角度
struct LegJointFeedback {
    double coxa;   // 髋关节反馈角度
    double femur;  // 大腿反馈角度
    double tibia;  // 小腿反馈角度
};

// 通用三维向量结构体，表示空间中一个点或向量
// 用于描述末端位置在不同坐标系下的表示
struct Vec3 {
    double x;
    double y;
    double z;
};

struct Amp {
    double rollAmp;
    double pitchAmp;
    double yawAmp;
};
// 单条腿的末端位置（足端）
// 包括目标位置与反馈位置，分别在根坐标系与腿局部坐标系中表示
struct LegEndPosition {
    Vec3 targetInBase;   // 期望末端位置（目标），在根坐标系下
    Vec3 targetInLeg;    // 期望末端位置（目标），在腿坐标系下

    Vec3 actualInBase;   // 实际末端位置（反馈），根据正解由反馈角度计算，根坐标系下
    Vec3 actualInLeg;    // 实际末端位置（反馈），腿坐标系下
};

// 单条腿的整体状态信息
// 包括期望角度、反馈角度，以及末端位置（目标与实际）
struct LegState {
    LegIKResult      targetAngle;   // 逆解结果：目标关节角度
    LegJointFeedback actualAngle;   // 舵机反馈：当前实际角度
    LegEndPosition   endPos;        // 末端位置（根/腿坐标系 + 目标/实际）
};
LegState legs[6];

Vec3 BasegetXYZ[6]={
  {134.83, -97.38, -83.18},
  {0.14, -172.49, -83.18},
  {-134.68, -97.63, -83.18},
  {134.68, 97.63, -83.18},
  {-0.14, 172.49, -83.18},
  {-134.83, 97.38, -83.18}
  // {175.94,-121.01,-83.86},
  // {0.22 , -219.99 , -83.86},
  // {-175.72,-121.38,-83.86},
  // {175.72,121.38,-83.86},
  // {-0.22 , 219.90 , -83.86},
  // {-175.94,121.01,-83.86}
};
Vec3 BasesetXYZ[6]{
  //   {156.24,-109.69,-80.83},
  // {0.18,-197.19,-80.83},
  // {-156.06,-110.00,-80.83},
  // {156.06,110.00,-80.83},
  // {-0.18,197.19,-80.83},
  // {-156.24,109.69,-80.83}
  {134.83, -97.38, -83.18},
  {0.14, -172.49, -83.18},
  {-134.68, -97.63, -83.18},
  {134.68, 97.63, -83.18},
  {-0.14, 172.49, -83.18},
  {-134.83, 97.38, -83.18}
  // {175.94,-121.01,-83.86},
  // {0.22 , -219.99 , -83.86},
  // {-175.72,-121.38,-83.86},
  // {175.72,121.38,-83.86},
  // {-0.22 , 219.90 , -83.86},
  // {-175.94,121.01,-83.86}
};;
//初始腿部坐标系末端位置
const Vec3 initInLeg[6]=
{
//43.00 
//95.353
  // {103.24,-59.33,-80.83},
  // {119.08 , 0.18,-80.83},
  // {103.06,59.64,-80.83},
  // {103.06,59.64,-80.83},
  // {119.08 , 0.18,-80.83},
  // {103.24,-59.33,-80.83}
  {81.83,-47.02,-83.18},
  {94.38 , 0.14,-83.18},
  {81.68,47.27,-83.18},
  {81.68,47.27,-83.18},
  {94.38 , 0.14,-83.18},
  {81.83,-47.02,-83.18}

  //73.00 
//125.353
  // {122.94,-70.65,-83.86},
  // {141.79 , 0.22 , -83.86},
  // {122.72,71.02,-83.86},
  // {122.72,71.02,-83.86},
  // {141.79 , 0.22 , -83.86},
  // {122.94,-70.65,-83.86}
};
// {
//   {122.12,-121.74,-72.17},
//   {172.44 , 0 , -72.17},
//   {121.93,121.93,-72.17},
//   {121.93,121.93,-72.17},
//   {172.44 , 0 , -72.17},
//   {122.12,-121.74,-72.17}
// };
Vec3 initInBase[6]=
{
  {134.83, -97.38, -83.18},
  {0.14, -172.49, -83.18},
  {-134.68, -97.63, -83.18},
  {134.68, 97.63, -83.18},
  {-0.14, 172.49, -83.18},
  {-134.83, 97.38, -83.18}
    //73.00 
//125.353
  // {175.94,-121.01,-83.86},
  // {0.22 , -219.99 , -83.86},
  // {-175.72,-121.38,-83.86},
  // {175.72,121.38,-83.86},
  // {-0.22 , 219.90 , -83.86},
  // {-175.94,121.01,-83.86}
};
Vec3 BalancedinitInBase[6]=
{
  {134.83, -97.38, -83.18},
  {0.14, -172.49, -83.18},
  {-134.68, -97.63, -83.18},
  {134.68, 97.63, -83.18},
  {-0.14, 172.49, -83.18},
  {-134.83, 97.38, -83.18}
    //73.00 
//125.353
  // {175.94,-121.01,-83.86},
  // {0.22 , -219.99 , -83.86},
  // {-175.72,-121.38,-83.86},
  // {175.72,121.38,-83.86},
  // {-0.22 , 219.90 , -83.86},
  // {-175.94,121.01,-83.86}
};
// {
//   {174.65,175.77,-72.17},
//   {252.76 , 0 , -72.17},
//   {174.26,-175.77,-72.17},
//   {-172.66,176.05,-72.17},
//   {-252.81 , 0 , -72.17},
//   {-172.09,-176.61,-72.17}
// };
double BASE_JOINT_ANG  = 0;
double SHOULDER_JOINT_ANG = 0;
double ELBOW_JOINT_ANG = 90.0;
double EOAT_JOINT_ANG  = 180.0;

// true: torqueLock ON, servo produces torque.
// false: torqueLock OFF, servo release torque.
bool RoArmM2_torqueLock = true;
bool RoArmM2_emergencyStopFlag = false;
bool newCmdReceived = false;

bool nanIK;


// bool RoArmM2_initCheckSucceed   = true;
bool Claws_initCheckSucceed = false;
// // // args for syncWritePos.
u16 moveSpd[18] = {0, 0, 0, 0, 0,0,0,0,0,0,0,0,0,0,0,0,0,0};
u8  moveAcc[18] = {ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
            ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
            ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
            ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC,
			      ARM_SERVO_INIT_ACC};

double base_r;

double en_odom_x=0.0, en_odom_y=0.0,en_odom_yaw=0.0;
// --- --- --- Pneumatic Components && Lights --- --- ---
#define IO4_PIN 4
#define IO5_PIN 5
const uint16_t FREQ = 200;
const uint16_t ANALOG_WRITE_BITS = 8;

#define PWMA 25         // Motor A PWM control  
#define AIN2 17         // Motor A input 2     
#define AIN1 21         // Motor A input 1     
#define BIN1 22         // Motor B input 1       
#define BIN2 23         // Motor B input 2       
#define PWMB 26         // Motor B PWM control  

#define AENCA 35        // Encoder A input      
#define AENCB 34

#define BENCB 16        // Encoder B input     
#define BENCA 27

// --- --- --- ugv imu --- --- ---
double icm_pitch = 0;
double icm_roll = 0;
double icm_yaw = 0;

double qc0 = 1.0;
double qc1 = 0.0;
double qc2 = 0.0;
double qc3 = 0.0;

double q0, q1, q2, q3, q2sqr, t0, t1, t2, t3, t4;
// Define a storage struct for the biases. Include a non-zero header and a simple checksum
struct biasStore
{
  int32_t biasGyroX = 0;
  int32_t biasGyroY = 0;
  int32_t biasGyroZ = 0;
  int32_t biasAccelX = 0;
  int32_t biasAccelY = 0;
  int32_t biasAccelZ = 0;
  int32_t biasCPassX = 0;
  int32_t biasCPassY = 0;
  int32_t biasCPassZ = 0;
};
biasStore store;
double ax, ay, az;
double mx, my, mz;
double gx, gy, gz;
// --- --- --- Bus Servo Settings --- --- ---


#define ST_PID_P_ADDR 21
#define ST_PID_D_ADDR 22
#define ST_PID_I_ADDR 23

#define ST_PID_ROARM_P   16
#define ST_PID_DEFAULT_P 32

#define ST_TORQUE_MAX 1000
#define ST_TORQUE_MIN 50


// --- --- --- i2c Settings --- --- ---

#define S_SCL   33
#define S_SDA   32

unsigned long prev_time = 0;

String jsonFeedbackWeb = "";