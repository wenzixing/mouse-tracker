# Fitts' Law（费茨定律）

## 简介

Fitts' Law（费茨定律）是人机交互领域最重要的定律之一，由美国心理学家 Paul Fitts 于 1954 年提出。该定律描述了人类快速移动到目标区域所需时间与目标距离和目标大小之间的关系。

## 数学公式

### 基本公式

$$MT = a + b \cdot \log_2\left(\frac{2D}{W}\right)$$

其中：
- **MT (Movement Time)**: 移动时间，完成动作所需的时间
- **D (Distance)**: 从起点到目标中心的距离
- **W (Width)**: 目标的宽度（在移动方向上）
- **a**: 截距常数，与设备启动/停止时间相关
- **b**: 斜率常数，与设备的固有速度相关

### 难度指数 (Index of Difficulty, ID)

$$ID = \log_2\left(\frac{2D}{W}\right)$$

难度指数以"比特"为单位，表示移动任务的信息复杂度。

### 吞吐量 (Throughput, TP)

$$TP = \frac{ID}{MT}$$

吞吐量以"比特/秒"为单位，衡量人机交互的效率。

## 核心含义

1. **距离越远，时间越长**: 目标距离 D 增加，移动时间 MT 增加
2. **目标越小，时间越长**: 目标宽度 W 减小，移动时间 MT 增加
3. **对数关系**: 时间与难度呈对数关系，而非线性关系

## 在认知康复中的应用

### 评估指标

| 指标 | 含义 | 临床意义 |
|------|------|----------|
| 移动时间 (MT) | 完成点击所需时间 | 反映运动速度和协调能力 |
| 难度指数 (ID) | 任务的信息复杂度 | 用于标准化不同任务的难度 |
| 吞吐量 (TP) | 信息处理效率 | 综合评估运动控制能力 |
| 有效目标宽度 (We) | 实际点击精确度 | 反映运动精确性 |

### 康复训练应用

1. **基线评估**: 通过标准化测试获取患者的基线 Fitts' Law 参数
2. **进度追踪**: 监测 a、b 参数的变化来量化康复进度
3. **难度调整**: 根据 ID 自适应调整训练难度
4. **效果评估**: 使用吞吐量 (TP) 作为综合评估指标

## 实验范式

### 经典范式

```
    ┌─────┐                           ┌─────┐
    │     │ ◄──────── D ────────────► │     │
    │  ■  │                           │  □  │
    │     │                           │     │
    └─────┘                           └─────┘
      W                                  W

    起始目标                           目标区域
```

被试需要在两个目标之间来回点击，通过改变 D 和 W 来测量不同难度下的表现。

### 本程序的实现

本 Mouse Tracker 程序采用改进的单向指向范式：
- 起始点固定在屏幕中央
- 目标随机出现在不同位置
- 记录每次移动的轨迹和时间
- 自动计算 Fitts' Law 相关指标

## 参考文献

1. Fitts, P. M. (1954). The information capacity of the human motor system in controlling the amplitude of movement. *Journal of Experimental Psychology*, 47(6), 381-391.

2. MacKenzie, I. S. (1992). Fitts' law as a research and design tool in human-computer interaction. *Human-Computer Interaction*, 7(1), 91-139.

3. Soukoreff, R. W., & MacKenzie, I. S. (2004). Towards a standard for pointing device evaluation, perspectives on 27 years of Fitts' law research in HCI. *International Journal of Human-Computer Studies*, 61(6), 751-789.

---

*本文档为 Mouse Tracker 认知训练程序的理论背景说明*
