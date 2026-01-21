import tkinter as tk
import time
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
import platform

# --- 1. 解决中文显示乱码问题 ---
system_name = platform.system()
if system_name == "Windows":
    # Windows系统通常使用 SimHei (黑体) 或 Microsoft YaHei (微软雅黑)
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
elif system_name == "Darwin":
    # Mac系统通常使用 Arial Unicode MS 或 Heiti TC
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC']
else:
    # Linux 或其他系统尝试通用中文字体
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Droid Sans Fallback']

plt.rcParams['axes.unicode_minus'] = False # 解决负号显示为方块的问题

class MouseTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("认知康复评估：鼠标运动学分析工具 (大屏版)")
        
        # --- 2. 调整页面尺寸 (更大) ---
        # 设置窗口大小为 1400x900 (适配常见的笔记本和台式机屏幕)
        self.root.geometry("1400x900")
        
        # 数据存储
        self.trajectory_data = [] 
        self.is_recording = False
        self.start_time = 0
        self.start_pos = (0, 0)
        
        # 界面布局 - 顶部标题与说明
        self.header_frame = tk.Frame(root)
        self.header_frame.pack(pady=10)
        
        self.title_label = tk.Label(self.header_frame, text="任务：Fitts's Law 目标点击测试", font=("Arial", 18, "bold"))
        self.title_label.pack()
        
        self.info_label = tk.Label(self.header_frame, text="点击 '开始测试'，然后尽快、准确地点击出现的红色圆球。", font=("Arial", 14), fg="#333")
        self.info_label.pack(pady=5)
        
        # --- 3. 调整画布 Canvas 尺寸 ---
        # 扩大活动区域，方便大幅度鼠标移动
        self.canvas_width = 1200
        self.canvas_height = 650
        self.canvas = tk.Canvas(root, bg="#f0f0f0", width=self.canvas_width, height=self.canvas_height, relief="sunken", borderwidth=2)
        self.canvas.pack(pady=10)
        
        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(self.btn_frame, text="开始测试", command=self.start_test, font=("Arial", 14), bg="#4CAF50", fg="white", width=15, height=2)
        self.start_btn.pack()

        # 绑定鼠标移动事件
        self.canvas.bind('<Motion>', self.record_movement)

    def start_test(self):
        """开始一个新的测试任务"""
        self.canvas.delete("all")
        self.trajectory_data = []
        
        # 设定起始点（画布中心）
        center_x, center_y = self.canvas_width // 2, self.canvas_height // 2
        self.start_pos = (center_x, center_y)
        
        # 绘制起始按钮 (蓝色)
        r = 25 # 半径
        self.start_circle = self.canvas.create_oval(center_x-r, center_y-r, center_x+r, center_y+r, fill="#2196F3", outline="white", width=2, tags="start")
        self.canvas.create_text(center_x, center_y, text="起点", fill="white", font=("Arial", 12), tags="start")
        
        self.canvas.tag_bind("start", "<Button-1>", self.spawn_target)
        
        self.info_label.config(text="请点击蓝色的起始点...", fg="#2196F3")

    def spawn_target(self, event):
        """点击起始点后，生成目标点，开始记录"""
        self.canvas.delete("start")
        self.is_recording = True
        self.start_time = time.time()
        
        # 记录起始点数据
        self.trajectory_data.append((event.x, event.y, self.start_time))
        
        # 随机生成目标位置 (在画布范围内，预留边距)
        margin = 50
        target_x = random.randint(margin, self.canvas_width - margin)
        target_y = random.randint(margin, self.canvas_height - margin)
        self.target_pos = (target_x, target_y)
        
        # 绘制目标 (红色)
        r = 20 # 目标半径略小，增加难度
        self.target_circle = self.canvas.create_oval(target_x-r, target_y-r, target_x+r, target_y+r, fill="#F44336", outline="white", width=2, tags="target")
        self.canvas.tag_bind("target", "<Button-1>", self.end_test)
        
        self.info_label.config(text="请快速点击红球！", fg="#F44336")

    def record_movement(self, event):
        """记录鼠标移动轨迹"""
        if self.is_recording:
            current_time = time.time()
            self.trajectory_data.append((event.x, event.y, current_time))

    def end_test(self, event):
        """结束测试并进行分析"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.canvas.delete("target")
        
        # 添加最后一点
        self.trajectory_data.append((event.x, event.y, time.time()))
        
        # 执行分析
        self.analyze_data()

    def analyze_data(self):
        """核心算法：计算运动学指标"""
        if len(self.trajectory_data) < 2:
            return

        # 计算距离和速度
        total_distance = 0
        velocities = []
        
        for i in range(1, len(self.trajectory_data)):
            x1, y1, t1 = self.trajectory_data[i-1]
            x2, y2, t2 = self.trajectory_data[i]
            
            dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            time_diff = t2 - t1
            
            total_distance += dist
            
            if time_diff > 0:
                velocities.append(dist / time_diff)

        # 计算理想直线距离
        start_x, start_y, _ = self.trajectory_data[0]
        end_x, end_y, _ = self.trajectory_data[-1]
        ideal_distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)

        # 核心指标
        curvature_index = total_distance / ideal_distance if ideal_distance > 0 else 0
        total_time = self.trajectory_data[-1][2] - self.trajectory_data[0][2]
        avg_speed = total_distance / total_time if total_time > 0 else 0
        pauses = sum(1 for v in velocities if v < 20) 

        # 结果文本
        result_text = (
            f"--- 分析完成 ---\n"
            f"1. 轨迹曲率 (Curvature): {curvature_index:.2f} (理想为1.0)\n"
            f"2. 总耗时 (Time): {total_time:.2f} 秒\n"
            f"3. 停顿/迟疑次数: {pauses}\n"
            f"4. 平均速度: {avg_speed:.0f} px/s"
        )
        self.info_label.config(text="测试结束，正在生成分析图表...", fg="black")
        
        # 绘图
        self.plot_trajectory(start_x, start_y, end_x, end_y, result_text)

    def plot_trajectory(self, sx, sy, ex, ey, result_text):
        """绘制轨迹图"""
        # 注意：Canvas坐标原点在左上角，Matplotlib默认在左下角，这里需要转换Y轴以便直观对应
        # 或者直接按数值绘制，标注清楚即可。这里为了对应视觉习惯，我们Y轴反转。
        h = self.canvas_height
        x_vals = [p[0] for p in self.trajectory_data]
        y_vals = [h - p[1] for p in self.trajectory_data] 
        
        # 创建一个较大的弹窗
        top = tk.Toplevel(self.root)
        top.title("轨迹可视化分析报告")
        top.geometry("900x700")

        # 上方显示文本结果
        lbl_result = tk.Label(top, text=result_text, font=("SimHei", 12), justify="left", bg="#e8f5e9", padx=10, pady=10)
        lbl_result.pack(fill="x", pady=5)

        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        
        # 绘制
        ax.plot(x_vals, y_vals, color='#2196F3', linestyle='-', linewidth=2, label='实际轨迹 (Patient Path)')
        ax.plot(x_vals, y_vals, 'b.', markersize=2, alpha=0.5) # 采样点
        
        # 理想路径
        ax.plot([sx, ex], [h-sy, h-ey], color='#F44336', linestyle='--', linewidth=2, label='理想路径 (Ideal Path)')
        
        # 标注
        ax.set_title("鼠标运动学轨迹分析", fontsize=14)
        ax.set_xlabel("X 轴位移 (像素)")
        ax.set_ylabel("Y 轴位移 (像素)")
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.6)
        
        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseTrackerApp(root)
    root.mainloop()