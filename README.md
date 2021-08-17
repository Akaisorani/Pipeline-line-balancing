# Line balancing

## Problem
在服装加工工厂的流水线上，衣服的制作流程会被拆分成30～80个不同的工序，交由18～21个员工协作完成。预平衡问题指的是如何将工序分配给流水线上的员工，让每个员工分配到其熟练的工序，并使每个员工的工作时间较为接近，以达到流水线高效、通畅的目标。

## Steps
1. 根据流水线打卡记录表计算员工技能熟练度
2. 根据技能熟练度和工序表建模预平衡问题
3. 使用混合01整数规划求解

<img src="https://z3.ax1x.com/2021/08/17/fhNrnA.png" width="70%">

## 整数规划
### 约束
1. 一个人可以做最多一段连续的工序
2. 一个组中的工序最多分配给一个人
3. 一个人操作的机器不超过2个
4. 一个人不能分配不会的工序
5. 一个人不能操作不会的机器
6. 每个工序被分配一次且仅一次

### 方程
其中变量![formula](https://render.githubusercontent.com/render/math?math=x_{klr})表示第k个员工是否分配到序号区间[l, r]的工序，m为员工数量，n为工序数量，![formula](https://render.githubusercontent.com/render/math?math=t_{k})表示第k个员工的工序总工时，![formula](https://render.githubusercontent.com/render/math?math=g_{ki})为根据工序表和员工能力表计算出的第k个员工做第i个工序的工时，![formula](https://render.githubusercontent.com/render/math?math=\overline{t})表示员工平均工时。总优化目标为最小化平均工时和工时平均差的加权平均指标。

<img src="https://z3.ax1x.com/2021/08/17/fhwdUI.png" width="50%">

