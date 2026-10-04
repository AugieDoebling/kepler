
#include <math.h>
#define ANG2DEG 0.017453292

// Instantiate a servo control object.
SMS_STS st;

// place holder.
void serialCtrl();
void Claws_moveInit_web();
Vec3 transform_to_leg_frame_mm(Vec3 p_root_mm, int leg_index);
void cartesian_to_polar(double x, double y, double* r, double* theta);
void simpleLinkageIkRad(int leg, double LA, double LB, double aIn, double bIn);
void Claws_getServoPosByXYZ(Vec3 v[6]);
void Claws_JointCtrlRad();
void Claws_moveInit() ;
// Used to store the feedback information from the servo.
struct ServoFeedback {
  bool status;
  int pos;
  int speed;
  int load;
  float voltage;
  float current;
  float temper;
  byte mode;
};
struct Mat3 
{
    double m[3][3];
};
//绕yaw pitch roll旋转矩阵
Mat3 eulerZYX(double yaw, double pitch, double roll){
    double cy = cos(yaw), sy = sin(yaw);
    double cp = cos(pitch), sp = sin(pitch);
    double cr = cos(roll), sr = sin(roll);
    Mat3 R;
    R.m[0][0] = cy*cp;      R.m[0][1] = cy*sp*sr - sy*cr; R.m[0][2] = cy*sp*cr + sy*sr;
    R.m[1][0] = sy*cp;      R.m[1][1] = sy*sp*sr + cy*cr; R.m[1][2] = sy*sp*cr - cy*sr;
    R.m[2][0] = -sp;        R.m[2][1] = cp*sr;            R.m[2][2] = cp*cr;
    return R;
}
// 生成绕X轴旋转矩阵
Mat3 rotX(double angle) {
    Mat3 R;
    double c = cos(angle), s = sin(angle);
    R.m[0][0] = 1; R.m[0][1] = 0;  R.m[0][2] = 0;
    R.m[1][0] = 0; R.m[1][1] = c;  R.m[1][2] = -s;
    R.m[2][0] = 0; R.m[2][1] = s;  R.m[2][2] = c;
    return R;
}

// 生成绕Y轴旋转矩阵
Mat3 rotY(double angle) {
    Mat3 R;
    double c = cos(angle), s = sin(angle);
    R.m[0][0] = c;  R.m[0][1] = 0; R.m[0][2] = s;
    R.m[1][0] = 0;  R.m[1][1] = 1; R.m[1][2] = 0;
    R.m[2][0] = -s; R.m[2][1] = 0; R.m[2][2] = c;
    return R;
}

// 矩阵相乘
Mat3 mulMat(const Mat3& A, const Mat3& B) {
    Mat3 R{};
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            R.m[i][j] = A.m[i][0] * B.m[0][j] +
                        A.m[i][1] * B.m[1][j] +
                        A.m[i][2] * B.m[2][j];
        }
    }
    return R;
}
Mat3 transpose (Mat3  M)
{Mat3 T;
    for (int r = 0; r < 3; ++r)
      for (int c = 0; c < 3; ++c)
        T.m[r][c] = M.m[c][r];
    return T;

}
Vec3 mulVec( Mat3 M,  Vec3 v)
{return {
      M.m[0][0]*v.x + M.m[0][1]*v.y + M.m[0][2]*v.z,
      M.m[1][0]*v.x + M.m[1][1]*v.y + M.m[1][2]*v.z,
      M.m[2][0]*v.x + M.m[2][1]*v.y + M.m[2][2]*v.z
    };
} 
ServoFeedback servoFeedback[18];

s16 Servo_pos [18];


struct Vec2 { double x = 0, y = 0; };
struct LegTarget {
  double x, y, z;
  bool lifting;
};

class TripodGait {
public:
  TripodGait(const Vec3 basePos[6]) {
    for (int i = 0; i < 6; ++i) legBasePos[i] = basePos[i];
  }

  void setMotionCommand(double x,double y, double yaw) {//设置速度
    velocity.x = x;
    velocity.y = y;
    yawRate = yaw;
    if((x!=0)||(y!=0)||(yaw!=0))
    {
      isPaused = false;
    }
  }
  void setMotionAmp(double rollAmp,double pitchAmp, double yawAmp, double Freq ) {//设置摆动频率和幅度
    BaseAmp.rollAmp = rollAmp;
    BaseAmp.pitchAmp = pitchAmp;
    BaseAmp.yawAmp = yawAmp;
    swayFreq=Freq;
       if((rollAmp!=0)||(pitchAmp!=0)||(yawAmp!=0))
    {
      isPaused = false;
    }
   
  }
  void pause() {
    isPaused = true;
  }

  void resume() {
    isPaused = false;
  }

  void stopAndSync(const Vec3 foot[6]) {//重新初始化周期乱了或者周期结束
    for (int i = 0; i < 6; ++i)
    {
      legBasePos[i] = foot[i];
      prevPhase[i]=0;
      first[i]=0;
      currentFootPos[i]=foot[i];
      legHomePos[i]=foot[i];
    } 
    timeInCycle = 0;
    isPaused = true;
    nextCorrectionT = n * gaitCycleDuration;
    velocity.x = 0.0;
    velocity.y = 0.0;
    yawRate = 0.0;
    odom_dx=0.0;
    odom_dy=0.0;
    odom_yaw=0.0;
    odom_last_dx=0.0;
    odom_last_dy=0.0;
    odom_last_yaw=0.0;
    BaseAmp.rollAmp = 0.0;
    BaseAmp.pitchAmp = 0.0;
    BaseAmp.yawAmp = 0.0;
    gaitInitialized = false;
    basePosInitialized = false; 
    directionChanged = false;
    defaultZ=-83.18;
  }

void update(double dt, Vec3 leg[6], Vec3 targets[6]) {
  if (isPaused) {
    for (int i = 0; i < 6; ++i) {
      //currentFootPos[i].z=defaultZ;
      //targets[i] = currentFootPos[i];

    }
    return;
  }
  bool hasMotion = !(velocity.x == 0 && velocity.y == 0 && yawRate == 0);
  bool wantSway  = (BaseAmp.rollAmp != 0.0 || BaseAmp.pitchAmp != 0.0 || BaseAmp.yawAmp != 0.0);
  if (!hasMotion && !wantSway) {
    for (int i = 0; i < 6; ++i) {
      targets[i] = initInBase[i];
      currentFootPos[i] = initInBase[i];
      targets[i].z=defaultZ;
      currentFootPos[i].z=defaultZ;
      // Serial.println("targets[i].z:");
      // Serial.println(targets[i].z);
      legHomePos[i]=initInBase[i];
      legBasePos[i] = initInBase[i];
      legHomePos[i].z=defaultZ;
      legBasePos[i].z=defaultZ;
      prevPhase[i]=0;
      first[i]=0;
    }
    timeInCycle = 0;
    isPaused = true;
    nextCorrectionT = n * gaitCycleDuration;
    velocity.x = 0.0;
    velocity.y = 0.0;
    yawRate = 0.0;
    odom_dx=0.0;
    odom_dy=0.0;
    odom_yaw=0.0;
    odom_last_dx=0.0;
    odom_last_dy=0.0;
    odom_last_yaw=0.0;
    BaseAmp.rollAmp = 0.0;
    BaseAmp.pitchAmp = 0.0;
    BaseAmp.yawAmp = 0.0;
    gaitInitialized = false;
    basePosInitialized = false; 
    directionChanged = false;
    Serial.print("basez:");
    Claws_getServoPosByXYZ(targets);
    Claws_JointCtrlRad();
    return;
  }
  
//45rpm=45/60 rev/s=0.75 * 2π =4.7124 rad/s
  const double servoOmegaMax = 4.7124;;  
  const double safety = 0.7; // 安全系数
  const double dthetaMax = servoOmegaMax * dt * safety;//一个周期最大的旋转角度

  // 先求一个全局缩放因子
  double s_global = 1.0;
  for (int legIndex = 0; legIndex < 6; ++legIndex) {
    // 先根据 currentFootPos 计算目标关节角
    double base_r, coxaCurr, femurCurr, tibiaCurr;
    Vec3 localCurr = transform_to_leg_frame_mm(currentFootPos[legIndex], legIndex);
    cartesian_to_polar(localCurr.x, localCurr.y, &base_r, &coxaCurr);
    simpleLinkageIkRad(legIndex, l2, l3, base_r - l1, localCurr.z);
    femurCurr=legs[legIndex].targetAngle.femur;
    tibiaCurr=legs[legIndex].targetAngle.tibia;
    // 再根据 "不缩放" 的当前脚端算出目标关节角
    double base_r_t, coxaTgt, femurTgt, tibiaTgt;
    Vec3 localTgt = transform_to_leg_frame_mm(leg[legIndex], legIndex); // 或者临时算的轨迹点
    cartesian_to_polar(localTgt.x, localTgt.y, &base_r_t, &coxaTgt);
    simpleLinkageIkRad(legIndex, l2, l3, base_r_t - l1, localTgt.z);
    femurTgt=legs[legIndex].targetAngle.femur;
    tibiaTgt=legs[legIndex].targetAngle.tibia;
    // 对三个关节分别计算速率系数
    double diffC = fabs(coxaTgt - coxaCurr);//角度差
    double diffF = fabs(femurTgt - femurCurr);
    double diffT = fabs(tibiaTgt - tibiaCurr);

    double s_leg = 1.0;
    if (diffC > dthetaMax) s_leg = std::min(s_leg, dthetaMax / diffC);
    if (diffF > dthetaMax) s_leg = std::min(s_leg, dthetaMax / diffF);
    if (diffT > dthetaMax) s_leg = std::min(s_leg, dthetaMax / diffT);//角度差很大比舵机满速还大小于1缩放 dt减慢相位推进

    if (s_leg < s_global) s_global = s_leg;
  }


   // ------------------ 初始化逻辑（修正点） ------------------
  // 两个独立标志：
  static bool basePosInitialized = false; // legBasePos 是否已根据真实运动初始化（可能要等到速度非零时）

  // 先做相位的初始化（仅设置 timeInCycle 的偏移）
  if (!gaitInitialized) {
    // 起步时让相位居中，避免脚突然跳动
    timeInCycle = gaitCycleDuration * 0.25; // 0.25 周期相当于轨迹中点处开始（支撑段中点）
    gaitInitialized = true;
  }
  // 在 basePos 未被真实初始化前，每次都检查当前是否有有效的运动信号（平移或旋转）
  // if (!basePosInitialized) {
  //   Vec3 initStep = { velocity.x * gaitCycleDuration * 1000.0,
  //                     velocity.y * gaitCycleDuration * 1000.0, 0.0 };
  //   double initStepLen = std::sqrt(initStep.x * initStep.x + initStep.y * initStep.y);
  //   double initYaw = -yawRate * gaitCycleDuration * 0.5; // 半周期旋转角

  //   const double STEP_LEN_THRESHOLD = 1.0; // mm 阈值，可按实际调小/调大
  //   const double YAW_THRESHOLD = 1e-6;

  //   if (initStepLen >= STEP_LEN_THRESHOLD) {
  //     // 有明显平移：以平移为准，后退半步，不再额外绕机身旋转半周期（避免重复“往后半圈”）
  //     for (int i = 0; i < 6; ++i) {
  //       Vec3 p = leg[i];
  //       p.x -= 0.5 * initStep.x;
  //       p.y -= 0.5 * initStep.y;
  //       legBasePos[i] = p;
  //     }
  //     basePosInitialized = true;
  //   } else if (fabs(yawRate) > YAW_THRESHOLD) {
  //     // 纯旋转（或平移很小）：用绕机身旋转半周期的方法初始化
  //     double c = cos(initYaw);
  //     double s = sin(initYaw);
  //     for (int i = 0; i < 6; ++i) {
  //       Vec3 p = leg[i];
  //       double x_new = c * p.x - s * p.y;
  //       double y_new = s * p.x + c * p.y;
  //       p.x = x_new;
  //       p.y = y_new;
  //       legBasePos[i] = p;
  //     }
  //     basePosInitialized = true;
  //   } else {
  //     // 没有明显运动：暂把 legBasePos 设为当前脚位置（中点），但不标记为“已初始化”
  //     // 这样当将来速度出现时会重新进入上面的 init 分支
  //     for (int i = 0; i < 6; ++i) {
  //       legBasePos[i] = leg[i];
  //     }
  //     // basePosInitialized stays false
  //   }
  // }
// 缩放 dt（相当于减慢相位推进）
    // if ((velocity.x*Prevvelocity.x < 0.0)||(velocity.y*Prevvelocity.y < 0.0)) 
    // {
    // phaseDir *= 1.0;
    // }
  double dt_scaled = dt * s_global;
  
  timeInCycle += dt_scaled;
  if (timeInCycle < 0.0) timeInCycle += gaitCycleDuration;

 odom_dx=velocity.x * dt_scaled;
 odom_dy=velocity.y * dt_scaled; 
 odom_yaw=yawRate * dt_scaled;

 en_odom_x+=odom_last_dx;
 en_odom_y+=odom_last_dy;
 en_odom_yaw+=odom_last_yaw;

 odom_last_dx=odom_dx;
 odom_last_dy=odom_dy;
 odom_last_yaw=odom_yaw;

  double phase = fmod(timeInCycle, gaitCycleDuration);
  bool isPhaseA = phase < gaitCycleDuration * 0.5;
  double half = gaitCycleDuration * 0.5;


const double correctionFactor = 0.015; // 越小越慢越平滑
const float tol = 0.01f;
for (int i = 0; i < 6; ++i) {
  bool lifting = (isPhaseA == isInGroupA(i));
       double supportCenter = isInGroupA(i)
        ? 0.25   // A 组支撑中心
        : 0.75;  // B 组支撑中心
        double phaseNorm = phase / gaitCycleDuration;
            bool crossed = false;
            if (phaseNorm >= prevPhase[i]) {
                // 正常前进：检测从前一帧到当前帧是否跨过中点
                if (prevPhase[i] < supportCenter && phaseNorm >= supportCenter)
                    crossed = true;
            } else {
                // 周期回绕：phase 从大跳到小
                if (prevPhase[i] < supportCenter || phaseNorm >= supportCenter)
                    crossed = true;
            }

        // 跨帧检测支撑→抬腿切换
        if (!lifting &&crossed) {
            legBasePos[i] = leg[i];
            if (first[i] == 0) {
                legHomePos[i] = legBasePos[i];
                first[i] = 1;
            }
        }
        prevPhase[i] = phaseNorm;
  if (timeInCycle >= nextCorrectionT) {
    // 只在到达门限的这一帧做修正怕步态起点累积偏移（可只对支撑腿做）
    for (int i = 0; i < 6; ++i) {
        bool lifting = (isPhaseA == isInGroupA(i));
        if (lifting) continue; // 只修支撑腿，避免影响摆动

        Vec3 error;
        error.x = legHomePos[i].x - legBasePos[i].x;
        error.y = legHomePos[i].y - legBasePos[i].y;
        error.z = legHomePos[i].z - legBasePos[i].z;

        legBasePos[i].x += error.x * correctionFactor;
        legBasePos[i].y += error.y * correctionFactor;
        legBasePos[i].z += error.z * correctionFactor;
      
    }
    nextCorrectionT += n * gaitCycleDuration; 
    }


    }

  // 步态矢量计算
  Vec2 stepPrev = {Prevvelocity.x * gaitCycleDuration * 1000.0,Prevvelocity.y * gaitCycleDuration * 1000.0};
  Vec2 step = { velocity.x * gaitCycleDuration * 1000.0, velocity.y * gaitCycleDuration * 1000.0 };
 
  double totalYaw = yawRate * gaitCycleDuration;
  for (int i = 0; i < 6; ++i) {
    bool lifting = (isPhaseA == isInGroupA(i));
    double offset = lifting ? 0.0 : half;
    double local = std::fmod(phase + offset, gaitCycleDuration) / half;
    if (local >= 1.0) local -= 1.0;

    double motionLocal = lifting ? local : 1.0 - local;
    double s = motionLocal * motionLocal * (3 - 2 * motionLocal); // s型曲线

  //    if (phaseDir==-1) {
  //  s=1-s;
  //    }
    
    // 当前腿的参考起点
    double baseX = legBasePos[i].x;
    
    double baseY = legBasePos[i].y;

    // 平移轨迹（对称地以起点为中心走一个步长）
    double dx =  - step.x / 2.0+step.x * s;
    double dy = - step.y / 2.0+ step.y * s;
    double yawNow = -totalYaw/2 + totalYaw * s;
  
    // 旋转补偿（以机身为圆心转动）
    double rx = -baseY * std::sin(yawNow) + baseX * (std::cos(yawNow) - 1);
    double ry =  baseX * std::sin(yawNow) + baseY * (std::cos(yawNow) - 1);
    prvs=s;
    if((abs(velocity.x)>0&&abs(yawRate)>0&&i==1)||(abs(velocity.x)>0&&abs(yawRate)>0&&i==4)||(abs(velocity.y)>0&&abs(yawRate)>0&&i==1)||(abs(velocity.y)>0&&abs(yawRate)>0&&i==4))
    {
      dx*=0.4;
      rx*=0.4;
      dy*=0.4;
      ry*=0.4;
    }
    double finalX = baseX + dx + rx;
    double finalY = baseY + dy + ry;
    x_Current[i]=dx + rx;
    y_Current[i]=dy + ry;
    double finalZ  = defaultZ;
    if (lifting) {
      finalZ +=  liftZ(motionLocal, liftHeight);//liftZ(motionLocal, liftHeight);//finalZ  += liftHeight*s;
    }

    double rollAngle  = BaseAmp.rollAmp  * sin(2 * M_PI * swayFreq * timeInCycle);
    double pitchAngle = BaseAmp.pitchAmp  * sin(2 * M_PI * swayFreq * timeInCycle);
    double yawAngle   = BaseAmp.yawAmp    * sin(2 * M_PI * swayFreq * timeInCycle);

    Mat3 swayRot = transpose(eulerZYX(yawAngle, pitchAngle, rollAngle));
    
    // double swayX = swayRot.m[0][0]*finalX + swayRot.m[0][1]*finalY + swayRot.m[0][2]*finalZ;
    // double swayY = swayRot.m[1][0]*finalX + swayRot.m[1][1]*finalY + swayRot.m[1][2]*finalZ;
    // double swayZ = swayRot.m[2][0]*finalX + swayRot.m[2][1]*finalY + swayRot.m[2][2]*finalZ;
    if (!hasMotion && wantSway) {
      Vec3 home ;
      if (first[i] == 0) {
        home = legHomePos[i];   // 刚上电，还没走过步态，用 home 点
      } else {
        home = legBasePos[i];   // 已经走过，停下时用最后的基准点
      }
      home.z=-83.18;//保证姿态角摇摆时机身高度处于初始
      Vec3 p_body = mulVec(swayRot, home);
      finalX = p_body.x;
      finalY = p_body.y;
      finalZ = p_body.z;
    }
    // 步长限制
    double ddx = finalX - leg[i].x;
    double ddy = finalY - leg[i].y;
    double strideLen = std::sqrt(ddx * ddx + ddy * ddy);
    if (strideLen > maxStepLength) {
      double ratio = maxStepLength / strideLen;
      finalX = leg[i].x + ddx * ratio;
      finalY = leg[i].y + ddy * ratio;
    }
 
    targets[i] = { finalX, finalY, finalZ  };
    Vec3 newTarget  =transform_to_leg_frame_mm(targets[i],i);
    cartesian_to_polar(newTarget.x, newTarget.y, &base_r, &legs[i].targetAngle.coxa);
    simpleLinkageIkRad(i,l2, l3, base_r-l1, newTarget.z);
      if (isnan(legs[i].targetAngle.coxa) || isnan(legs[i].targetAngle.femur) || isnan(legs[i].targetAngle.tibia)) {
      // NaN 出现，保留上一次有效位置
      targets[i] = currentFootPos[i];
    }
    //currentFootPos[i] = targets[i];
  }
  // for (int i = 0; i < 6; ++i) {
  //   if (!(isPhaseA == isInGroupA(i))) continue; // 只处理支撑腿

  //   for (int j = 0; j < 6; ++j) {
  //       if (i == j) continue;
  //       double dx = targets[i].x - targets[j].x;
  //       double dy = targets[i].y - targets[j].y;
  //       double dist = sqrt(dx*dx + dy*dy);
  //       if (dist < minDist) {
  //           // 按比例缩小当前腿步幅
  //           double scale = dist / minDist;
  //           targets[i].x = legBasePos[i].x + x_Current[i] * scale;
  //           targets[i].y = legBasePos[i].y + y_Current[i]* scale;
  //       }
      
  //   }
  // }
    for (int i = 0; i < 6; ++i)
    {
      currentFootPos[i] = targets[i];
    }
  Claws_getServoPosByXYZ(targets);
  Claws_JointCtrlRad();
  Prevvelocity.x=velocity.x;
  Prevvelocity.y=velocity.y;
}

  // 参数接口
  void setmaxStepLength (double mm)   { maxStepLength  = mm; }
  void setLiftHeight(double mm)   { liftHeight = mm; }
  void setCycle(double sec)       { gaitCycleDuration = sec; }
  void setDefaultZ(double mm)     { defaultZ = mm; }

  private:
  static bool isInGroupA(int idx) {
    return idx == 0 || idx == 2 || idx == 4;
  }

  double maxStepLength  = 400.0;
  double minDist=100;
  double liftHeight = 15.0;//相对于默认着地高度（defaultZ）
  double gaitCycleDuration = 1;
  double defaultZ = -83.18;

  bool gaitInitialized = false;
  bool basePosInitialized = false;
  
  double timeInCycle = 0.0;
  double prevPhase[6] ={0.0};
  bool isPaused = false;

  double x_Current[6]={0};
  double y_Current[6]={0};
  double odom_dx=0.0,odom_dy=0.0,odom_yaw=0.0,odom_last_dx=0.0,odom_last_dy=0.0,odom_last_yaw=0.0;

  int first[6]={0};
  Amp BaseAmp ={0.0,0.0,0.0};//摆动幅度
  double swayFreq = 1.0; //摆动频率
  Vec3 legBasePos[6];
  Vec3 legHomePos[6]={
    {134.83, -97.38, -83.18},
  {0.14, -172.49, -83.18},
  {-134.68, -97.63, -83.18},
  {134.68, 97.63, -83.18},
  {-0.14, 172.49, -83.18},
  {-134.83, 97.38, -83.18}
  };
  const int n=2;
  bool directionChanged = false;
  double nextCorrectionT = n * gaitCycleDuration;
  Vec3 currentFootPos[6]={
  {134.83, -97.38, -83.18},
  {0.14, -172.49, -83.18},
  {-134.68, -97.63, -83.18},
  {134.68, 97.63, -83.18},
  {-0.14, 172.49, -83.18},
  {-134.83, 97.38, -83.18}
};//暂停保存位置;//暂停保存位置
double phaseDir = 1.0; 
double prvs=0.0;
Vec2 velocity = {0, 0};
Vec2 Prevvelocity = {0, 0};
double yawRate = 0.0f;
double liftZ(double step, double liftHeight) {
    return liftHeight * 4.0 * step * (1.0 - step);
  }

};
TripodGait gait(initInBase);
// ==================== 死区滤波器 ====================
// 当角度变化小于 deadband（弧度）时，忽略变化
double deadbandFilter(double input, double prevOutput, double deadband) {
    if (fabs(input - prevOutput) < deadband)
        return prevOutput;
    else
        return input;
}

void calcBalanceCorrection(double imuRoll, double imuPitch,Vec3 v1[6],Vec3 v2[6]) {
    static double filteredRoll = 0.0;
    static double filteredPitch = 0.0;
    // 死区阈值（弧度）：例如 0.0087 rad ≈ 0.5°
    const double deadband = 0.0087;

    filteredRoll  = deadbandFilter(imuRoll,  filteredRoll,  deadband);
    filteredPitch = deadbandFilter(imuPitch, filteredPitch, deadband);

    double roll_rad  = filteredRoll;
    double pitch_rad = filteredPitch;
    Mat3 Rx = rotX(roll_rad);
    Mat3 Ry = rotY(pitch_rad);
    // 先绕X（roll），再绕Y（pitch）
    Mat3 R = mulMat(Ry, Rx);
    for(int i= 0; i < 6; i++)
    v2[i]  = mulVec(R, BalancedinitInBase[i]);
}
void setDefaultz(double z)
{  if (z>-60.83)
  z=-60.83;
  else if(z<-140.83)
  z=-140.83;
  for(int i=0;i<6;i++)
    BalancedinitInBase[i].z=z;
  gait.setDefaultZ(z);
  Claws_moveInit_web();
}
//-0.04~0.04 m/s  -0.2~0.2rad/s
void setGoalSpeed(double x, double y,double yaw) {
  if (x<-0.07)
  x=-0.07;
  else if(x>0.07)
  x=0.07;
  if (y<-0.07)
  y=-0.07;
  else if(y>0.07)
  y=0.07;
  if (yaw<-0.6)
  yaw=-0.6;
  else if(yaw>0.6)
  yaw=0.6;

  gait.setMotionCommand(x,y,yaw);
}
void setGoalAmp(double rollAmp,double pitchAmp, double yawAmp, double Freq) {
  if (yawAmp>0.0)
  {
    rollAmp=constrain(rollAmp,0.0,0.3);
    pitchAmp=constrain(pitchAmp,0.0,0.3);
    yawAmp=constrain(yawAmp,0.0,0.3);
    Freq=constrain(Freq,0.0,0.2);
  }
  else if(yawAmp==0.0)
  {
    rollAmp=constrain(rollAmp,0.0,0.3);
    pitchAmp=constrain(pitchAmp,0.0,0.3);
    yawAmp=constrain(yawAmp,0.0,0.3);
    Freq=constrain(Freq,0.0,0.4);
  }
  gait.setMotionAmp(rollAmp,pitchAmp,yawAmp,Freq);
}
void setGoalStop()
{
  gait.setMotionCommand(0,0,0);
  gait.setMotionAmp(0,0,0,0);
 // Claws_moveInit();
}
void heartBeatCtrl() {

  currentTimeMillis = millis();
  if (currentTimeMillis - lastCmdRecvTime > HEART_BEAT_DELAY) {
    if (!heartbeatStopFlag) {
      heartbeatStopFlag = true;
      setGoalSpeed(0.00, 0.00,0.00);
      setGoalAmp(0.00, 0.00,0.00,1.0);
    }
    
  }
}



// 每条腿的安装参数（位置单位：mm）
typedef struct {
    Vec3 position_in_root_mm; // 安装位置，单位mm
    double rotation_deg_z;        // 绕Z轴旋转角度（单位：度）
} LegMount_mm;


// 六条腿的安装参数相对于根坐标系下的偏移（单位：mm + 度）右手定则 右手握拳，大拇指指向 旋转轴正方向（比如 Z 轴正方向）其余四指弯曲的方向就是 正方向的旋转
const LegMount_mm leg_mounts_mm[6] = {
    //x朝右y朝前
    // {{ 50.36, 53.0, 0.0 }, 90.0},  // Leg 0: 右前
    // {{78.11, 0.00, 0.0 }, 0.0},  // Leg 1: 右中
    // {{50.36, -53.0, 0.0 }, -90.0}, // Leg 2: 右后
    // {{ -50.36,  53.0, 0.0 },  90.0},  // Leg 3: 左前
    // {{  -78.11,  0.0, 0.0 },  180.0},  // Leg 4: 左中
    // {{-50.36,  -53.0, 0.0 }, -90.0},  // Leg 5: 左后
    {{ 53.0, -50.36, 0.0 }, 0.0},  // Leg 0: 右前
    {{0.00, -78.11, 0.0 }, -90.0},  // Leg 1: 右中
    {{-53.0, -50.36, 0.0 }, 180.0}, // Leg 2: 右后
    {{ 53.0,  50.36, 0.0 },  0.0},  // Leg 3: 左前
    {{  0.0,  78.11, 0.0 },  90.0},  // Leg 4: 左中
    {{-53.0,  50.36, 0.0 }, 180.0},  // Leg 5: 左后
};

double ang2deg(double inputAng) {
  return (inputAng / 180) * M_PI;
}
//坐标偏移坐标减法
Vec3 vec_sub_mm(Vec3 a, Vec3 b) {
    Vec3 res = {a.x - b.x, a.y - b.y, a.z - b.z};
    return res;
}

// 坐标加法
Vec3 vec_add_mm(Vec3 a, Vec3 b) {
    Vec3 res = {a.x + b.x, a.y + b.y, a.z + b.z};
    return res;
}

// 绕Z轴正向旋转（单位：度）
Vec3 rotateZ_mm(Vec3 v, double theta_deg) {
    double theta_rad = ang2deg(theta_deg);  // 正向旋转
    double c = cos(theta_rad);
    double s = sin(theta_rad);
    Vec3 res = {
        c * v.x - s * v.y,
        s * v.x + c * v.y,
        v.z
    };
    return res;
}

// 绕Z轴逆旋转（单位：度）
Vec3 rotateZ_inv_mm(Vec3 v, double theta_deg) {
    double theta_rad = ang2deg(-theta_deg);  // 逆旋转
    double c = cos(theta_rad);
    double s = sin(theta_rad);
    Vec3 res = {
        c * v.x - s * v.y,
        s * v.x + c * v.y,
        v.z
    };
    return res;
}

// 将根坐标系下点转换为指定腿部坐标系下（单位：mm）
Vec3 transform_to_leg_frame_mm(Vec3 p_root_mm, int leg_index) {
    if (leg_index < 0 || leg_index >= 6) {
        Vec3 error = {0, 0, 0};
        return error;
    }

    LegMount_mm mount = leg_mounts_mm[leg_index];

    // 步骤1：平移补偿
    Vec3 p_relative_mm = vec_sub_mm(p_root_mm, mount.position_in_root_mm);

    // 步骤2：逆旋转
    Vec3 p_leg_mm = rotateZ_inv_mm(p_relative_mm, mount.rotation_deg_z);

    return p_leg_mm;
}

// 将腿部坐标系下点转换为根坐标系下（单位：mm）
Vec3 transform_to_root_frame_mm(Vec3 p_leg_mm, int leg_index) {
    if (leg_index < 0 || leg_index >= 6) {
        Vec3 error = {0, 0, 0};
        return error;
    }

    LegMount_mm mount = leg_mounts_mm[leg_index];

    // 步骤1：正向旋转
    Vec3 p_rotated_mm = rotateZ_mm(p_leg_mm, mount.rotation_deg_z);

    // 步骤2：平移回根坐标系
    Vec3 p_root_mm = vec_add_mm(p_rotated_mm, mount.position_in_root_mm);

    return p_root_mm;
}

// [0] BASE_SERVO_ID
// [1] SHOULDER_DRIVING_SERVO_ID
// [2] SHOULDER_DRIVEN_SERVO_ID
// [3] ELBOW_SERVO_ID
// [4] GRIPPER_SERVO_ID

int calculateStepsByRad(double rad, int jointName) {
  int steps = 0;
  switch(jointName){
  case 1:
    steps = (int)(-(rad - M_PI) * ARM_SERVO_POS_RANGE / (2 * M_PI));
    break;
  case 2:
    steps = (int)(-(rad - M_PI) * ARM_SERVO_POS_RANGE / (2 * M_PI));
    break;
  case 3:
    steps = (int)((3 * M_PI / 2 - rad) * ARM_SERVO_POS_RANGE / (2 * M_PI));
    break;
  }
  return steps;
}

void Claws_JointCtrlRad()
{int j=0;
  for(int i = 0; i < 18; i+=3)
  {
    Servo_pos[i]=calculateStepsByRad(legs[j++].targetAngle.coxa,1);
    if((jointID[i]/10==2 || jointID[i]/10==5) && jointID[i]%10==1)//id为21 和51
    {
      Servo_pos[i] = constrain(Servo_pos[i], 2047, 2779);//0-0.
    }
    else if((jointID[i]/10==3 || jointID[i]/10==6) && jointID[i]%10==1)
    {
      Servo_pos[i] = constrain(Servo_pos[i], 1526, 2572);
    }
    else if((jointID[i]/10==4 || jointID[i]/10==7) && jointID[i]%10==1)
    {
      Servo_pos[i] = constrain(Servo_pos[i], 1324, 2047);
    }
  }
  j=0;
  for(int i = 1; i < 18; i+=3)
  {
    Servo_pos[i]=calculateStepsByRad(legs[j++].targetAngle.femur,2);
    Servo_pos[i] = constrain(Servo_pos[i],1023, 2047);
  }
  j=0;
  for(int i = 2; i < 18; i+=3)
  {
    Servo_pos[i]=calculateStepsByRad(legs[j++].targetAngle.tibia,3);
    Servo_pos[i] = constrain(Servo_pos[i],1023, 3070);
  }
  st.SyncWritePosEx(jointID, 18, Servo_pos, moveSpd, moveAcc);
}

// input the angle in radians, and it returns the number of servo steps.
double calculatePosByRad(double radInput) {
  return round((radInput / (2 * M_PI)) * ARM_SERVO_POS_RANGE);
}

// input the number of servo steps and the joint name
// return the joint angle in radians.
double calculateRadByFeedback(int inputSteps, int jointName) {
  double getRad;
  switch(jointName){
  case 1:
  case 2:
    getRad = -(inputSteps * 2 * M_PI / ARM_SERVO_POS_RANGE) + M_PI;
    break;
  
    // getRad = -(inputSteps * 2 * M_PI / ARM_SERVO_POS_RANGE) + M_PI;
    // break;
  case 3:
    getRad =  (M_PI*3 / 2)-(inputSteps * 2 * M_PI / ARM_SERVO_POS_RANGE) ;
    break;
  }
  return getRad;
}


// input the ID of the servo,
// and get the information saved in servoFeedback[5].
// returnType: false - return everything.
//              true - return only when failed.
bool getFeedback(int servoID, bool returnType) {
  if(st.FeedBack(jointID[servoID])!=-1) {
    servoFeedback[servoID].status = true;
  	servoFeedback[servoID].pos = st.ReadPos(jointID[servoID]);
    servoFeedback[servoID].speed = st.ReadSpeed(jointID[servoID]);
    servoFeedback[servoID].load = st.ReadLoad(jointID[servoID]);
    servoFeedback[servoID].voltage = st.ReadVoltage(jointID[servoID]);
    servoFeedback[servoID].current = st.ReadCurrent(jointID[servoID]);
    servoFeedback[servoID].temper = st.ReadTemper(jointID[servoID]);
    servoFeedback[servoID].mode = st.ReadMode(jointID[servoID]);
    if(!returnType){
      if(InfoPrint == 1){
        Serial.print("Servo ID:");Serial.print(jointID[servoID]);
                    Serial.print(" status: checked. pos:");
                    Serial.println(servoFeedback[servoID].pos);
                    }
    }
    else{
      return true;
    }
    return true;
  } else{
    servoFeedback[servoID].status = false;
    if(InfoPrint == 1){
      Serial.print("Servo ID:");Serial.print(jointID[servoID]);
                  Serial.println(" status: failed.");
                  }
  	return false;
  }
}


// input the old servo ID and the new ID you want it to change to.
bool changeID(byte oldID, byte newID) {
  if(!getFeedback(oldID, true)) {
    if(InfoPrint == 1) {Serial.print("change: ");Serial.print(oldID);Serial.println("failed");}
    return false;
  }
  else {
    st.unLockEprom(oldID);
    st.writeByte(oldID, SMS_STS_ID, newID);
    st.LockEprom(newID);

    if(InfoPrint == 1) {Serial.print("change: ");Serial.print(oldID);Serial.println("succeed");}
    return true;
  }
}


// ctrl the torque lock of a servo.
// input the servo ID and command: 1-on : produce torque.
//                                 0-off: release torque.
void servoTorqueCtrl(byte servoID, u8 enableCMD){
  st.EnableTorque(servoID, enableCMD);
}


// set the current position as the middle position of the servo.
// input the ID of the servo that you wannna set middle position. 
void setMiddlePos(byte InputID){
  st.CalibrationOfs(InputID);
}


// to release all servos' torque for 10s.
void emergencyStopProcessing() {
  st.EnableTorque(254, 0);
  delay(10000);
  st.EnableTorque(254, 1);
}


// position check.
// it will wait for the servo to move to the goal position.
void waitMove2Goal(byte InputID, s16 goalPosition, s16 offSet){
  while(servoFeedback[InputID].pos < goalPosition - offSet || 
        servoFeedback[InputID].pos > goalPosition + offSet){
    if (!servoFeedback[InputID].status) {
      servoTorqueCtrl(254, 0);
      break;
    }
    getFeedback(InputID, true);
    delay(10);
  }
}


// initialize bus servo libraris and uart2ttl.
void Claws_servoInit(){
  Serial1.begin(1000000, SERIAL_8N1, S_RXD, S_TXD);
  st.pSerial = &Serial1;
  while(!Serial1) {}
  if(InfoPrint == 1){Serial.println("ServoCtrl init succeed.");}
}


// check the status of every servo,
// if all status are ok, set the Clws_initCheckSucceed as 1.
// 0: used to init check, print everything.
// 1: used to check while working, print when failed.
void Claws_initCheck(bool returnType) {
  Claws_initCheckSucceed = false;
  for(int i = 0; i < 9; i++)
  Claws_initCheckSucceed = getFeedback(i, true) &&
                             getFeedback(17-i, true) ;
  if(!returnType){
    if(InfoPrint == 1 || Claws_initCheckSucceed){Serial.println("All bus servos status checked.");}
    else if(InfoPrint == 1 || !Claws_initCheckSucceed){Serial.println("Bus servos status check: failed.");}
  }
  else if(returnType && Claws_initCheckSucceed){}
  else if(returnType && !Claws_initCheckSucceed){
    if(InfoPrint == 1){Serial.println("Check failed.");}
  }
}


// set all servos PID as the Claws settings.
bool setServosPID(byte InputID, byte InputP) {
  if(!getFeedback(InputID, true)){return false;}
  st.unLockEprom(InputID);
  st.writeByte(InputID, ST_PID_P_ADDR, InputP); 
  st.LockEprom(InputID);
  return true;
}


// move every joint to its init position.
// it moves only when RoArmM2_initCheckSucceed is 1.
void Claws_moveInit() {
  if(!Claws_initCheckSucceed){
    if(InfoPrint == 1){Serial.println("Init failed, skip moveInit.");}
    return;
  }
  else if(InfoPrint == 1){Serial.println("Stop moving to initPos.");}

  // move BASE_SERVO to middle position.
  if(InfoPrint == 1){Serial.println("Moving COXA_JOINT to initPos.");}
  for(int i = 0; i < 18; i+=3)
  {
    if (i==3 ||  i==12 )
    {
      st.WritePosEx(jointID[i], ARM_SERVO_MIDDLE_POS, ARM_SERVO_INIT_SPEED, ARM_SERVO_INIT_ACC);
    }
    else if (i==0 ||  i==15 )
    {
      st.WritePosEx(jointID[i], ARM_SERVO_MIDDLE_POS+COXA_SERVO_MIDDLE_OFFSET, ARM_SERVO_INIT_SPEED, ARM_SERVO_INIT_ACC);
    }
    else if (i==6 ||  i==9 )
    {
      st.WritePosEx(jointID[i], ARM_SERVO_MIDDLE_POS-COXA_SERVO_MIDDLE_OFFSET, ARM_SERVO_INIT_SPEED, ARM_SERVO_INIT_ACC);
    }
    delay(10);
  }
  
  // move SHOULDER_DRIVING_SERVO to middle position.
  if(InfoPrint == 1){Serial.println("Moving FEMUR_JOINT to initPos.");}
  for(int i = 1; i < 18; i+=3)
  {
    st.WritePosEx(jointID[i], ARM_SERVO_MIDDLE_POS-FEMUR_SERVO_MIDDLE_OFFSET, ARM_SERVO_INIT_SPEED, ARM_SERVO_INIT_ACC);
    delay(10);
  }
  

  if(InfoPrint == 1){Serial.println("...");}
  for(int i = 1; i < 18; i+=3)
  {
     waitMove2Goal(i, ARM_SERVO_MIDDLE_POS-FEMUR_SERVO_MIDDLE_OFFSET, 120);
  }
  delay(1200);


  // move ELBOW_SERVO to middle position.
  if(InfoPrint == 1){Serial.println("Moving TIBIA_SERVO to middle position.");}
   for(int i = 2; i < 18; i+=3)
  {
    st.WritePosEx(jointID[i], ARM_SERVO_MIDDLE_POS-TIBIA_SERVO_MIDDLE_OFFSET, ARM_SERVO_INIT_SPEED, ARM_SERVO_INIT_ACC);
     delay(10);
}
  
  for(int i = 2; i < 18; i+=3)
  waitMove2Goal(i, ARM_SERVO_MIDDLE_POS-TIBIA_SERVO_MIDDLE_OFFSET, 120);
  Serial.println("Moving TIBIA_SERVO to middle position.");
  gait.stopAndSync(initInBase);
  delay(1000);
}


// // // single joint ctrl for simple uses, base on radInput // // //

// use this function to compute the servo position to ctrl base joint.
// returnType 0: only returns the base joint servo position and save it to goalPos[0],
//               servo will NOT move.
//            1: returns the base joint servo position and save it to goalPos[0],
//               servo moves.
// input the angle in radius(double), the speedInput(u16) is servo steps/second,
// // the accInput(u8) is the acceleration of the servo movement.

 
//   return goalPos[0];
// }

// use this function to ctrl the max torque of base joint.
void Claws_coxaTorqueCtrl(int inputTorque) {
  for(int i = 0; i < 18; i+=3)
  {
    st.unLockEprom(jointID[i]);
    st.writeWord(jointID[i], SMS_STS_TORQUE_LIMIT_L, constrain(inputTorque, ST_TORQUE_MIN, ST_TORQUE_MAX));
    st.LockEprom(jointID[i]);
  }
  
}


// use this function to ctrl the max torque of shoulder joint.
void Claws_femurTorqueCtrl(int inputTorque) {
  for(int i = 1; i < 18; i+=3)
  {
    st.unLockEprom(jointID[i]);
    st.writeWord(jointID[i], SMS_STS_TORQUE_LIMIT_L, constrain(inputTorque, ST_TORQUE_MIN, ST_TORQUE_MAX));
    st.LockEprom(jointID[i]);
  }
}


// use this function to ctrl the max torque of elbow joint.
void Claws_tibiaTorqueCtrl(int inputTorque) {
    for(int i = 2; i < 18; i+=3)
  {
    st.unLockEprom(jointID[i]);
    st.writeWord(jointID[i], SMS_STS_TORQUE_LIMIT_L, constrain(inputTorque, ST_TORQUE_MIN, ST_TORQUE_MAX));
    st.LockEprom(jointID[i]);
  }
}




// dynamic external force adaptation.
// mode: 0 - stop: reset every limit torque to 1000.
//       1 - start: set the joint limit torque. 
// b, s, e, h = bassJoint, shoulderJoint, elbowJoint, handJoint
// example:
// starts. input the limit torque of every joint.
// {"T":112,"mode":1,"b":50,"s":50,"e":50,"h":50}
// stop
// {"T":112,"mode":0,"b":1000,"s":1000,"e":1000,"h":1000}
void Claws_dynamicAdaptation(byte inputM, int inputC, int inputF, int inputT) {
  if (inputM == 0) {
    Claws_coxaTorqueCtrl(ST_TORQUE_MAX);
    Claws_femurTorqueCtrl(ST_TORQUE_MAX);
    Claws_tibiaTorqueCtrl(ST_TORQUE_MAX);
  } else if (inputM == 1) {
    Claws_coxaTorqueCtrl(inputC);
    Claws_femurTorqueCtrl(inputF);
    Claws_tibiaTorqueCtrl(inputT);
  }
}

double clamp(double x, double minVal, double maxVal) {
  return fmax(minVal, fmin(x, maxVal));
}

// Simple Linkage IK:
// input the position of the end and return angle.
//   O----O
//  /
// O
// ---------------------------------------------------
// |       /beta           /delta                    |
//        O----LB---------X------                    |
// |     /       omega.   |       \LB                |
//      LA        .                < ----------------|
// |alpha     .          bIn         \LB -EP  <delta |
//    /psi.                           \LB -EP        |
// | /.   lambda          |                          |
// O- - - - - aIn - - - - X -                        |
// ---------------------------------------------------
// alpha, beta > 0 ; delta <= 0 ; aIn, bIn > 0
void simpleLinkageIkRad(int leg, double LA, double LB, double aIn, double bIn) {
  double psi, alpha, omega, beta, L2C, LC, lambda, delta;

  if (fabs(bIn) < 1e-6) {
    psi = acos((LA * LA + aIn * aIn - LB * LB) / (2 * LA * aIn)) + t2rad;
    alpha = M_PI / 2.0 - psi;
    omega = acos((aIn * aIn + LB * LB - LA * LA) / (2 * aIn * LB));
    beta = psi + omega - t3rad;
  } else {
    L2C = aIn * aIn + bIn * bIn;
    LC = sqrt(L2C);
    lambda = atan2(bIn, aIn);
    psi = acos((LA * LA + L2C - LB * LB) / (2 * LA * LC)) + t2rad;
    alpha = M_PI / 2.0 - lambda - psi;
    omega = acos((LB * LB + L2C - LA * LA) / (2 * LC * LB));
    beta = psi + omega - t3rad;
  }

  legs[leg].targetAngle.femur = alpha;
  legs[leg].targetAngle.tibia    = beta;
  nanIK = isnan(alpha) || isnan(beta);
}


// AI prompt:
// *** this function is written with AI. ***
// '''
// 我需要一个C语言函数，在一个平面直角坐标系中，输入一个坐标点(x,y)，返回值有两个：
// 1. 这个坐标点距离坐标系原点的距离。
// 2. 这个点与坐标系原点所连线段与x轴正方向的夹角，夹角范围在(-PI, PI)之间。
// '''

// AI prompt:
// I need a C language function. In a 2D Cartesian coordinate system, 
// input a coordinate point (x, y). The function should return two values:

// The distance from this coordinate point to the origin of the coordinate system.
// The angle, in radians, between the line connecting this point and the origin 
// of the coordinate system and the positive direction of the x-axis. 
// The angle should be in the range (-π, π).
void cartesian_to_polar(double x, double y, double* r, double* theta) {
    *r = sqrt(x * x + y * y);
    *theta = atan2(y, x);
}


// AI prompt:
// *** this function is written with AI. ***
// 我现在需要一个功能与上面函数相反的函数：
// 输入机械臂三个关节的轴的角度（弧度制），返回当前机械臂末端点的坐标点。

// 你在回答的过程中可以告诉我你还有什么其它需要的信息。
// '''
// use this two functions to compute the position of coordinate point
// by inputing the jointRad.
// 这个函数用于将极坐标转换为直角坐标
void polarToCartesian(double r, double theta, double &x, double &y) {
  x = r * cos(theta);
  y = r * sin(theta);
}


// this function is used to compute the position of the end point.
// input the angle of every joint in radius.
// compute the positon and save it to lastXYZ by default.
void Claws_computePosbyJointRad(int leg ) {
    // the end of the arm.
    double r_ee, x_ee, y_ee, z_ee;

    // compute the end position of the first linkage(the linkage between baseJoint and shoulderJoint).
    double aOut, bOut, cOut, dOut, eOut, fOut;

    polarToCartesian(l2, ((M_PI / 2) - (legs[leg].actualAngle.femur+ t2rad)), aOut, bOut);
    polarToCartesian(l3, ((M_PI / 2) - (legs[leg].actualAngle.tibia + legs[leg].actualAngle.femur+ t3rad)), cOut, dOut);

    r_ee = aOut + cOut+l1;
    legs[leg].endPos.actualInLeg.z = bOut + dOut;
    
    polarToCartesian(r_ee, legs[leg].actualAngle.coxa, eOut, fOut);
    legs[leg].endPos.actualInLeg.x = eOut;
    legs[leg].endPos.actualInLeg.y = fOut;
}


// EEmode funcs change here.
// get position by servo feedback.
void Claws_getPosByServoFeedback() {
  int j=0;
  for(int i = 0; i < 18; i++)
  {
    getFeedback(i, true);
  }
  for(int i= 0; i < 18; )
  {
    legs[j].actualAngle.coxa = calculateRadByFeedback(servoFeedback[i].pos, 1);i++;
    legs[j].actualAngle.femur = calculateRadByFeedback(servoFeedback[i].pos, 2);i++;
    legs[j].actualAngle.tibia = calculateRadByFeedback(servoFeedback[i].pos, 3);i++;
    j++;
  }
  for(int i= 0; i < 6; i++)
  { 
    Claws_computePosbyJointRad(i);
    legs[i].endPos.actualInBase=transform_to_root_frame_mm(legs[i].endPos.actualInLeg,i);
    BasegetXYZ[i]=legs[i].endPos.actualInBase;
  }
}


// feedback info in json.
void Claws_infoFeedback() {
	static unsigned long last_feedback_time;
	if (millis() - last_feedback_time < feedbackFlowExtraDelay) {
		return;
	}
	
	last_feedback_time = millis();
  
	jsonInfoHttp.clear();
	jsonInfoHttp["T"] = FEEDBACK_CLAWS_INFO;

	// jsonInfoHttp["r"] = icm_roll;
	// jsonInfoHttp["p"] = icm_pitch;
	// jsonInfoHttp["y"] = icm_yaw;



  jsonInfoHttp["x"] = legs[1].endPos.targetInBase.x;
	jsonInfoHttp["y"] = legs[1].endPos.targetInBase.y;
	jsonInfoHttp["z"] = legs[1].endPos.targetInBase.z;

  jsonInfoHttp["coxa"] = legs[1].targetAngle.coxa;
	jsonInfoHttp["femur"] = legs[1].targetAngle.femur;
	jsonInfoHttp["tibia"] = legs[1].targetAngle.tibia;

  jsonInfoHttp["coxa"] = legs[1].targetAngle.coxa;
	jsonInfoHttp["femur"] = legs[1].targetAngle.femur;
	jsonInfoHttp["tibia"] = legs[1].targetAngle.tibia;

	jsonInfoHttp["q0"] = q0;
	jsonInfoHttp["q1"] = q1;
	jsonInfoHttp["q2"] = q2;
	jsonInfoHttp["q3"] = q3;

	jsonInfoHttp["ax"] = ax;
	jsonInfoHttp["ay"] = ay;
	jsonInfoHttp["az"] = az;

	jsonInfoHttp["gx"] = gx;
	jsonInfoHttp["gy"] = gy;
	jsonInfoHttp["gz"] = gz;

	jsonInfoHttp["mx"] = mx;
	jsonInfoHttp["my"] = my;
	jsonInfoHttp["mz"] = mz;


  int v_int = (int)(loadVoltage_V * 100);
	jsonInfoHttp["v"] = v_int;

	String getInfoJsonString;
	serializeJson(jsonInfoHttp, getInfoJsonString);
	Serial.println(getInfoJsonString);
}
// ---===< Muti-assembly IK config here >===---
// change this func and goalPosMove()
// Coordinate Ctrl: input the coordinate point of the goal position to compute
// the goalPos of every joints.
void Claws_baseCoordinateCtrl(int leg){
    cartesian_to_polar(legs[leg].endPos.targetInLeg.x, legs[leg].endPos.targetInLeg.y, &base_r, &legs[leg].targetAngle.coxa);
    simpleLinkageIkRad(leg,l2, l3, base_r-l1, legs[leg].endPos.targetInLeg.z);
}

void Claws_allPosAbsBesselCtrl(int leg,double x,double y,double z)
{
  legs[leg].endPos.targetInBase.x=x;
  legs[leg].endPos.targetInBase.y=y;
  legs[leg].endPos.targetInBase.z=z;
  legs[leg].endPos.targetInLeg=transform_to_leg_frame_mm(legs[leg].endPos.targetInBase,leg);
  Claws_baseCoordinateCtrl(leg);
  Claws_JointCtrlRad();
}
void Claws_singleJointAbsCtrl(int leg,double coxa,double femur,double tibia)
{
legs[leg].targetAngle.coxa=coxa;
legs[leg].targetAngle.femur=femur;
legs[leg].targetAngle.tibia=tibia;
Claws_JointCtrlRad();
}

void Claws_singleJointAngleCtrl(int leg,double coxa,double femur,double tibia)
{
legs[leg].targetAngle.coxa=ang2deg(coxa);
legs[leg].targetAngle.femur=ang2deg(femur);
legs[leg].targetAngle.tibia=ang2deg(tibia);
Claws_JointCtrlRad();
}

void Claws_moveServoPosByXYZ()
{
  for(int i = 0; i < 6; i++)
  {
    legs[i].endPos.targetInBase=BasesetXYZ[i];
    legs[i].endPos.targetInLeg=transform_to_leg_frame_mm(legs[i].endPos.targetInBase,i);
    Claws_baseCoordinateCtrl(i);
  }
  Claws_JointCtrlRad();
}

void Claws_getServoPosByXYZ(Vec3 v[6])
{
  for(int i = 0; i < 6; i++)
  {
    legs[i].endPos.targetInBase=v[i];
    legs[i].endPos.targetInLeg=transform_to_leg_frame_mm(legs[i].endPos.targetInBase,i);
    Claws_baseCoordinateCtrl(i);
  }
  //Claws_JointCtrlRad();
}
void Claws_moveInit_web()
{
  for(int i = 0; i < 6; i++)
  {
    legs[i].endPos.targetInBase=BalancedinitInBase[i];
    legs[i].endPos.targetInLeg=transform_to_leg_frame_mm(legs[i].endPos.targetInBase,i);
    Claws_baseCoordinateCtrl(i);
  }
  Claws_JointCtrlRad();
}
// delay cmd.
void RoArmM2_delayMillis(int inputTime) {
  delay(inputTime);
}


// set the P&I/PID of a joint.
void Claws_setJointPID(byte jointInput, float inputP, float inputI) {
  switch (jointInput) {
  case COXA_JOINT:
        for(int i=0;i<6;i+=3)
          {
            st.writeByte(jointID[i], ST_PID_P_ADDR, inputP);
            st.writeByte(jointID[i], ST_PID_I_ADDR, inputI);
          }
        break;
  case FEMUR_JOINT:
        for(int i=1;i<6;i+=3)
          {
            st.writeByte(jointID[i], ST_PID_P_ADDR, inputP);
            st.writeByte(jointID[i], ST_PID_I_ADDR, inputI);
          }
        break;
  case TIBIA_JOINT:
       for(int i=2;i<6;i+=3)
          {
            st.writeByte(jointID[i], ST_PID_P_ADDR, inputP);
            st.writeByte(jointID[i], ST_PID_I_ADDR, inputI);
          }
        break;
  }
}


// reset the P&I/PID of RoArm-M2.
void Claws_resetPID() {
  Claws_setJointPID(COXA_JOINT, 16, 0);
  Claws_setJointPID(FEMUR_JOINT, 16, 0);
  Claws_setJointPID(TIBIA_JOINT, 16, 0);
}




