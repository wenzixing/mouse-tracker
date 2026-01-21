import tkinter as tk
import time
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
import platform
import os
import csv
from datetime import datetime

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
        self.root.title("认知康复评估：鼠标运动学分析工具 (Pro)")
        
        # --- 2. 界面适配 (全屏/最大化) ---
        system_name = platform.system()
        if system_name == "Windows":
            self.root.state('zoomed') # Windows 最大化
        elif system_name == "Linux":
            self.root.attributes('-zoomed', True)
        # Mac 通常由用户手动最大化或使用 fullscreen，这里尝试设置初始尺寸为屏幕大小
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}")
        
        # 配色方案
        self.colors = {
            "bg": "#FAFAFA",
            "accent": "#2196F3",
            "text": "#333333",
            "canvas_bg": "#FFFFFF",
            "target": "#F44336",
            "active_btn": "#4CAF50"
        }
        self.root.configure(bg=self.colors["bg"])

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1) # Canvas 区域占据主要空间

        # 常量定义
        self.TARGET_RADIUS = 20 # 目标半径 (px)

        # 数据存储
        self.trajectory_data = [] 
        self.is_recording = False
        self.start_time = 0
        self.start_pos = (0, 0)
        
        # 多轮测试状态
        self.max_trials = 10
        self.current_trial = 0
        self.session_data = [] 
        
        # --- 顶部：标题与状态 ---
        self.header_frame = tk.Frame(root, bg=self.colors["bg"])
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        self.title_label = tk.Label(self.header_frame, text="Fitts's Law 认知评估任务", font=("Helvetica", 20, "bold"), bg=self.colors["bg"], fg=self.colors["text"])
        self.title_label.pack(side="top", pady=5)
        
        self.info_label = tk.Label(self.header_frame, text=f"准备就绪。本组测试共 {self.max_trials} 轮。", font=("Helvetica", 16), bg=self.colors["bg"], fg="#666")
        self.info_label.pack(side="top")
        
        # --- 中部：画布 (自适应) ---
        # 初始尺寸仅为占位，后续自适应
        self.canvas_width = 1000 
        self.canvas_height = 600
        self.canvas = tk.Canvas(root, bg=self.colors["canvas_bg"], relief="flat", highlightthickness=1, highlightbackground="#E0E0E0")
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        # 绑定 Resize 事件以更新画布尺寸记录
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        # --- 底部：控制栏 ---
        self.footer_frame = tk.Frame(root, bg=self.colors["bg"])
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        
        self.start_btn = tk.Button(self.footer_frame, text="开始测试 (Start)", command=self.start_test, font=("Helvetica", 14, "bold"), bg=self.colors["active_btn"], fg="white", relief="flat", padx=20, pady=10)
        self.start_btn.pack(side="bottom") # 居中放置

        # 绑定鼠标移动事件
        self.canvas.bind('<Motion>', self.record_movement)

    def on_canvas_resize(self, event):
        """画布大小改变时触发"""
        self.canvas_width = event.width
        self.canvas_height = event.height

    def start_test(self):
        """开始一个新的测试 Session"""
        self.canvas.delete("all")
        self.session_data = []
        self.current_trial = 0
        
        # 绘制起始按钮 (蓝色)
        r = 30 
        center_x, center_y = self.canvas_width // 2, self.canvas_height // 2
        self.start_pos = (center_x, center_y)
        
        self.start_circle = self.canvas.create_oval(center_x-r, center_y-r, center_x+r, center_y+r, fill=self.colors["accent"], outline="white", width=2, tags="start")
        self.canvas.create_text(center_x, center_y, text="Start", fill="white", font=("Helvetica", 12, "bold"), tags="start")
        
        self.canvas.tag_bind("start", "<Button-1>", self.first_click)
        
        self.info_label.config(text="请点击屏幕中央的蓝色起点开始...", fg=self.colors["accent"])

    def first_click(self, event):
        """点击起点，开始第一轮"""
        self.canvas.delete("start")
        # 记录起点作为上一轮的结束点/这一轮的起点
        self.last_click_pos = (event.x, event.y)
        self.spawn_target()

    def spawn_target(self):
        """生成目标点，开始记录某一轮"""
        self.current_trial += 1
        self.is_recording = True
        self.start_time = time.time()
        self.trajectory_data = [] # 重置当轮轨迹
        
        # 记录起始点数据 (复用上一轮的点击位置 或 起始位置)
        self.trajectory_data.append((self.last_click_pos[0], self.last_click_pos[1], self.start_time))
        
        # 随机生成目标位置
        margin = 100 # 增加边距，防止太靠边
        # 确保画布有足够空间
        safe_w = max(self.canvas_width - margin, margin + 1)
        safe_h = max(self.canvas_height - margin, margin + 1)
        
        target_x = random.randint(margin, safe_w)
        target_y = random.randint(margin, safe_h)
        self.target_pos = (target_x, target_y)
        
        # 绘制目标 (红色)
        r = self.TARGET_RADIUS
        self.target_circle = self.canvas.create_oval(target_x-r, target_y-r, target_x+r, target_y+r, fill=self.colors["target"], outline="white", width=2, tags="target")
        self.canvas.tag_bind("target", "<Button-1>", self.handle_target_click)
        
        self.info_label.config(text=f"进度: {self.current_trial}/{self.max_trials} - 请快速点击红色目标！", fg=self.colors["target"])

    def record_movement(self, event):
        """记录鼠标移动轨迹"""
        if self.is_recording:
            current_time = time.time()
            self.trajectory_data.append((event.x, event.y, current_time))

    def handle_target_click(self, event):
        """处理目标点击：记录数据，判断是否继续"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.canvas.delete("target")
        click_time = time.time()
        
        # 添加最后一点
        self.trajectory_data.append((event.x, event.y, click_time))
        
        # 分析本轮数据并存储
        trial_metrics = self.analyze_single_trial(self.trajectory_data, self.target_pos)
        self.session_data.append(trial_metrics)
        
        # 更新位置用于下一轮
        self.last_click_pos = (event.x, event.y)
        
        if self.current_trial < self.max_trials:
            # 立即开始下一轮
            self.spawn_target()
        else:
            # 结束 Session
            self.show_session_summary()

    def analyze_single_trial(self, trajectory, target_pos):
        """分析单次点击的数据"""
        if len(trajectory) < 2:
            return {
                "time": 0, "distance": 0, "speed": 0, "curvature": 1, 
                "ideal_distance": 0, "target_x": target_pos[0], "target_y": target_pos[1],
                "id": 0, "throughput": 0, # Fitts' Law
                "trajectory": []
            }

        # 计算距离和速度
        total_distance = 0
        velocities = []
        for i in range(1, len(trajectory)):
            x1, y1, t1 = trajectory[i-1]
            x2, y2, t2 = trajectory[i]
            dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            time_diff = t2 - t1
            total_distance += dist
            if time_diff > 0:
                velocities.append(dist / time_diff)

        # 理想直线
        start_x, start_y, _ = trajectory[0]
        end_x, end_y, _ = trajectory[-1]
        ideal_distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)

        # 指标
        time_elapsed = trajectory[-1][2] - trajectory[0][2]
        avg_speed = total_distance / time_elapsed if time_elapsed > 0 else 0
        curvature = total_distance / ideal_distance if ideal_distance > 0 else 1
        
        # --- Fitts' Law Metrics ---
        # ID = log2(D/W + 1)
        # W (Width) 通常指目标在运动方向上的宽度。这里简化为直径 (2 * Radius)
        width = 2 * self.TARGET_RADIUS
        index_of_difficulty = math.log2(ideal_distance / width + 1) if width > 0 else 0
        
        # Throughput = ID / Time (bits/s)
        throughput = index_of_difficulty / time_elapsed if time_elapsed > 0 else 0
        
        return {
            "time": time_elapsed,
            "distance": total_distance,
            "ideal_distance": ideal_distance,
            "speed": avg_speed,
            "curvature": curvature,
            "id": index_of_difficulty,
            "throughput": throughput,
            "target_x": target_pos[0],
            "target_y": target_pos[1],
            "trajectory": list(trajectory) # 保存轨迹副本
        }

    def show_session_summary(self):
        """显示 Session 汇总结果"""
        # 计算平均值
        total_trials = len(self.session_data)
        if total_trials == 0:
            return

        avg_time = sum(d["time"] for d in self.session_data) / total_trials
        avg_speed = sum(d["speed"] for d in self.session_data) / total_trials
        avg_curvature = sum(d["curvature"] for d in self.session_data) / total_trials
        avg_throughput = sum(d["throughput"] for d in self.session_data) / total_trials
        
        # 保存数据
        saved_path = self.save_to_csv()
        
        # 结果文本
        result_text = (
            f"--- 测试 Session 完成 ---\n"
            f"总轮次: {total_trials}\n\n"
            f"平均耗时 (Time): {avg_time:.3f} s\n"
            f"平均速度 (Speed): {avg_speed:.0f} px/s\n"
            f"平均吞吐量 (Throughput): {avg_throughput:.2f} bits/s\n"
            f"平均轨迹曲率: {avg_curvature:.2f} (理想=1.00)\n\n"
            f"数据已保存至:\n{saved_path}"
        )
        self.info_label.config(text="测试结束，正在生成分析报告...", fg="black")
        
        # 绘图
        self.plot_session_results(result_text)

    def save_to_csv(self):
        """将本次 Session 数据保存到 CSV"""
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp_str}.csv"
        filepath = os.path.join(data_dir, filename)
        
        headers = ["Trial_ID", "Time_Sec", "Distance_Px", "Ideal_Distance_Px", "Speed_PxSec", "Curvature", "Index_of_Difficulty_Bits", "Throughput_Bits_Sec", "Target_X", "Target_Y"]
        
        try:
            with open(filepath, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
                for i, trial in enumerate(self.session_data):
                    writer.writerow([
                        i + 1,
                        f"{trial['time']:.4f}",
                        f"{trial['distance']:.2f}",
                        f"{trial['ideal_distance']:.2f}",
                        f"{trial['speed']:.2f}",
                        f"{trial['curvature']:.4f}",
                        f"{trial['id']:.4f}",
                        f"{trial['throughput']:.4f}",
                        trial['target_x'],
                        trial['target_y']
                    ])
            return filepath
        except Exception as e:
            print(f"Save failed: {e}")
            return "保存失败"



    def plot_session_results(self, result_text):
        """绘制 Session 所有轨迹图"""
        top = tk.Toplevel(self.root)
        top.title("Session 汇总分析")
        top.geometry("900x700")

        # 上方显示文本结果
        lbl_result = tk.Label(top, text=result_text, font=("SimHei", 12), justify="left", bg="#e8f5e9", padx=10, pady=10)
        lbl_result.pack(fill="x", pady=5)

        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        h = self.canvas_height

        # 绘制每一轮的轨迹
        for i, trial in enumerate(self.session_data):
            traj = trial["trajectory"]
            x_vals = [p[0] for p in traj]
            y_vals = [h - p[1] for p in traj]
            
            # 使用较浅的颜色绘制旧轨迹，深色绘制最新轨迹
            alpha = 0.3 + 0.7 * (i / len(self.session_data))
            ax.plot(x_vals, y_vals, '-', color='#2196F3', alpha=alpha, linewidth=1)
            
            # 绘制理想路径 (虚线)
            sx, sy, _ = traj[0]
            ex, ey, _ = traj[-1]
            ax.plot([sx, ex], [h-sy, h-ey], '--', color='#F44336', alpha=0.3, linewidth=1)

        ax.set_title(f"全 Session 轨迹叠加 ({len(self.session_data)} Trials)", fontsize=14)
        ax.set_xlabel("X (px)")
        ax.set_ylabel("Y (px)")
        ax.grid(True, linestyle=':', alpha=0.6)
        
        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseTrackerApp(root)
    root.mainloop()