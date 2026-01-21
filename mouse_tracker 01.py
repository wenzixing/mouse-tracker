# -*- coding: utf-8 -*-
"""
Mouse tracker / Fitts task tool (optimized)

主要改进点：
- 使用 time.perf_counter() 进行高分辨率时间戳
- 采样节流（min_sample_interval，可在 UI 中设置）
- 同时保存 CSV（汇总）与 JSON（原始轨迹 + 元数据）
- 支持随机与受控(preset)试次设计
- 额外运动学指标：peak_velocity, reaction_time
- 更友好的 UI：设置试次数、采样率、保存目录、实验模式
"""
import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import time
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
import platform
import os
import csv
import json
from datetime import datetime

# --- 字体/中文显示适配 ---
system_name = platform.system()
if system_name == "Windows":
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
elif system_name == "Darwin":
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC']
else:
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Droid Sans Fallback']
plt.rcParams['axes.unicode_minus'] = False

class MouseTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("认知康复评估：鼠标运动学分析工具 (Pro)")

        # 尝试最大化/适配
        try:
            if system_name == "Windows":
                self.root.state('zoomed')
            elif system_name == "Linux":
                self.root.attributes('-zoomed', True)
        except Exception:
            pass

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}")

        # 颜色方案
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
        self.root.rowconfigure(1, weight=1)

        # 常量与默认配置
        self.DEFAULT_TARGET_RADIUS = 20  # 默认半径（px）
        self.TARGET_RADIUS = self.DEFAULT_TARGET_RADIUS
        self.max_trials = 10
        self.current_trial = 0

        # 采样节流（秒）
        self.min_sample_interval = 0.01  # 默认 10 ms (100 Hz)
        self.last_sample_time = 0.0

        # 数据
        self.trajectory_data = []
        self.session_data = []
        self.is_recording = False
        self.start_time = 0.0
        self.last_click_pos = (0, 0)

        # 试次计划（当使用 preset 模式时会被填充）
        self.trial_plan = []  # 列表 of dicts: {"distance":..., "width":..., "target_pos":(x,y), "radius":...}
        self.experiment_mode = tk.StringVar(value="random")  # "random" or "preset"
        self.save_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(self.save_dir, exist_ok=True)

        # 顶部：标题
        self.header_frame = tk.Frame(root, bg=self.colors["bg"])
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        self.title_label = tk.Label(self.header_frame, text="Fitts's Law 认知评估任务 (优化版)", font=("Helvetica", 20, "bold"), bg=self.colors["bg"], fg=self.colors["text"])
        self.title_label.pack(side="top", pady=5)
        self.info_label = tk.Label(self.header_frame, text=f"准备就绪。", font=("Helvetica", 14), bg=self.colors["bg"], fg="#666")
        self.info_label.pack(side="top")

        # 中部：canvas
        self.canvas_width = 1000
        self.canvas_height = 600
        self.canvas = tk.Canvas(root, bg=self.colors["canvas_bg"], relief="flat", highlightthickness=1, highlightbackground="#E0E0E0")
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<Motion>", self.record_movement)

        # 底部：控制区
        self.footer_frame = tk.Frame(root, bg=self.colors["bg"])
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=12)

        # 左侧：实验参数
        param_frame = tk.Frame(self.footer_frame, bg=self.colors["bg"])
        param_frame.pack(side="left", padx=10)

        tk.Label(param_frame, text="模式:", bg=self.colors["bg"]).grid(row=0, column=0, sticky="w")
        mode_menu = tk.OptionMenu(param_frame, self.experiment_mode, "random", "preset")
        mode_menu.config(width=10)
        mode_menu.grid(row=0, column=1, padx=6)

        tk.Label(param_frame, text="试次数:", bg=self.colors["bg"]).grid(row=0, column=2, sticky="w")
        self.trial_entry = tk.Entry(param_frame, width=6)
        self.trial_entry.insert(0, str(self.max_trials))
        self.trial_entry.grid(row=0, column=3, padx=6)

        tk.Label(param_frame, text="采样间隔(s):", bg=self.colors["bg"]).grid(row=0, column=4, sticky="w")
        self.sample_entry = tk.Entry(param_frame, width=6)
        self.sample_entry.insert(0, f"{self.min_sample_interval:.3f}")
        self.sample_entry.grid(row=0, column=5, padx=6)

        # 保存目录选择
        save_frame = tk.Frame(self.footer_frame, bg=self.colors["bg"])
        save_frame.pack(side="left", padx=10)
        tk.Button(save_frame, text="选择保存目录", command=self.choose_save_dir, relief="groove").pack(side="left", padx=4)
        self.save_label = tk.Label(save_frame, text=os.path.abspath(self.save_dir), bg=self.colors["bg"], fg="#444", anchor="w")
        self.save_label.pack(side="left", padx=6)

        # 右侧：行动按钮
        action_frame = tk.Frame(self.footer_frame, bg=self.colors["bg"])
        action_frame.pack(side="right", padx=10)
        self.start_btn = tk.Button(action_frame, text="开始测试 (Start)", command=self.start_test, font=("Helvetica", 12, "bold"), bg=self.colors["active_btn"], fg="white", relief="flat", padx=12, pady=6)
        self.start_btn.pack(side="left", padx=6)
        self.cancel_btn = tk.Button(action_frame, text="停止 (Stop)", command=self.stop_session, font=("Helvetica", 12), bg="#F57C00", fg="white", relief="flat", padx=8, pady=6)
        self.cancel_btn.pack(side="left", padx=6)

        # 记录初始起点
        self.start_pos = (self.canvas_width // 2, self.canvas_height // 2)

        # 预定义 preset 设定（距离/宽度 示例）
        # 你可以扩展此处以符合实际实验设计：在设计模式下会用这些 (distance, width) 组合生成试次
        self.preset_distances = [120, 200, 320]  # px
        self.preset_widths = [20, 40]  # px (宽度, 注意绘制以半径 = width/2)
        # preset 组合将被重复/随机化到所需试次数

    def choose_save_dir(self):
        d = filedialog.askdirectory(initialdir=self.save_dir, title="选择保存目录")
        if d:
            self.save_dir = d
            self.save_label.config(text=os.path.abspath(self.save_dir))

    def on_canvas_resize(self, event):
        self.canvas_width = event.width
        self.canvas_height = event.height

    def parse_params(self):
        """读取 UI 中的参数（试次数、采样间隔）并验证"""
        try:
            trials = int(self.trial_entry.get())
            if trials <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("参数错误", "请提供合法的试次数（正整数）。默认 10。")
            trials = 10
        try:
            samp = float(self.sample_entry.get())
            if samp <= 0:
                raise ValueError
        except Exception:
            messagebox.showwarning("参数错误", "请提供合法的采样间隔（秒）。默认 0.01。")
            samp = 0.01
        self.max_trials = trials
        self.min_sample_interval = samp

    def start_test(self):
        """初始化并开始 Session"""
        # 读取参数
        self.parse_params()

        # 清屏并初始化状态
        self.canvas.delete("all")
        self.session_data = []
        self.current_trial = 0
        self.trial_plan = []
        self.is_recording = False
        self.last_click_pos = (self.canvas_width // 2, self.canvas_height // 2)
        self.TARGET_RADIUS = self.DEFAULT_TARGET_RADIUS  # 恢复默认（preset 会设置每试次 radius）

        # 若为 preset 模式，则生成试次 plan（target positions 会在 spawn 时计算）
        if self.experiment_mode.get() == "preset":
            self.prepare_preset_plan()

        # 绘制起点
        r = 30
        cx, cy = self.last_click_pos
        self.start_circle = self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=self.colors["accent"], outline="white", width=2, tags="start")
        self.canvas.create_text(cx, cy, text="Start", fill="white", font=("Helvetica", 12, "bold"), tags="start")
        self.canvas.tag_bind("start", "<Button-1>", self.first_click)
        self.info_label.config(text=f"点击蓝色起点开始测试（模式: {self.experiment_mode.get()}, 试次: {self.max_trials}）", fg=self.colors["accent"])

    def prepare_preset_plan(self):
        """基于 preset_distances 和 preset_widths 生成 trial_plan（此处生成组合并 shuffle）"""
        combos = []
        for d in self.preset_distances:
            for w in self.preset_widths:
                combos.append({"distance": d, "width": w})
        # 如果组合数量小于 max_trials，重复填充
        plan = []
        while len(plan) < self.max_trials:
            # 复制 combos 并随机打乱
            copy = combos[:]
            random.shuffle(copy)
            plan.extend(copy)
        # 截断到需要长度
        self.trial_plan = plan[:self.max_trials]
        # 目标位置会在 spawn_target 中根据上一个点和一个随机角度尝试放置

    def first_click(self, event):
        """起点点击，开始第一轮"""
        self.canvas.delete("start")
        self.last_click_pos = (event.x, event.y)
        # spawn first target
        self.spawn_target()

    def spawn_target(self):
        """生成目标并开始记录本轮"""
        self.current_trial += 1
        self.is_recording = True
        self.start_time = time.perf_counter()
        self.trajectory_data = []
        self.last_sample_time = self.start_time
        # 记录起始点（以 time.perf_counter 计时）
        self.trajectory_data.append((self.last_click_pos[0], self.last_click_pos[1], self.start_time))

        # 若为 preset 模式，基于 trial_plan[current_trial-1] 生成 target_pos
        if self.experiment_mode.get() == "preset" and (self.current_trial - 1) < len(self.trial_plan):
            plan = self.trial_plan[self.current_trial - 1]
            dist = plan.get("distance", 200)
            width = plan.get("width", 2 * self.DEFAULT_TARGET_RADIUS)
            radius = max(2, int(width / 2))
            # 尝试多个角度以在画布内放置目标
            placed = False
            attempts = 0
            while not placed and attempts < 36:
                attempts += 1
                ang = random.uniform(0, 2 * math.pi)
                tx = int(self.last_click_pos[0] + dist * math.cos(ang))
                ty = int(self.last_click_pos[1] + dist * math.sin(ang))
                margin = 10 + radius
                if margin <= tx <= self.canvas_width - margin and margin <= ty <= self.canvas_height - margin:
                    placed = True
                    break
            if not placed:
                # 退回到随机位置，但尽量保持距离
                tx, ty = self._random_target_far_from(self.last_click_pos)
            self.target_pos = (tx, ty)
            draw_radius = radius
            # 记录 trial 的 width/radius 信息
            self.trial_plan[self.current_trial - 1].update({"target_pos": self.target_pos, "radius": draw_radius})
            self.TARGET_RADIUS = draw_radius
        else:
            # 随机放置（避免靠边或过近）
            tx, ty = self._random_target_far_from(self.last_click_pos)
            self.target_pos = (tx, ty)
            self.TARGET_RADIUS = self.DEFAULT_TARGET_RADIUS

        # 绘制目标并绑定点击
        r = self.TARGET_RADIUS
        tx, ty = self.target_pos
        self.target_circle = self.canvas.create_oval(tx-r, ty-r, tx+r, ty+r, fill=self.colors["target"], outline="white", width=2, tags="target")
        self.canvas.tag_bind("target", "<Button-1>", self.handle_target_click)
        self.info_label.config(text=f"进度: {self.current_trial}/{self.max_trials} - 请点击红色目标！", fg=self.colors["target"])

    def _random_target_far_from(self, pos, min_dist=80):
        """生成一个随机目标，尽量避开 pos（最小距离 min_dist），并不靠边"""
        margin = 100
        safe_w = max(self.canvas_width - margin, margin + 1)
        safe_h = max(self.canvas_height - margin, margin + 1)
        attempts = 0
        while True:
            attempts += 1
            tx = random.randint(margin, safe_w)
            ty = random.randint(margin, safe_h)
            if math.hypot(tx - pos[0], ty - pos[1]) >= min_dist or attempts > 30:
                return tx, ty

    def record_movement(self, event):
        """记录鼠标移动（带节流）"""
        if not self.is_recording:
            return
        now = time.perf_counter()
        if (now - self.last_sample_time) >= self.min_sample_interval:
            self.trajectory_data.append((event.x, event.y, now))
            self.last_sample_time = now

    def handle_target_click(self, event):
        """点击目标后记录并分析本轮"""
        if not self.is_recording:
            return
        self.is_recording = False
        click_ts = time.perf_counter()
        # 添加最后一点
        self.trajectory_data.append((event.x, event.y, click_ts))
        # 删除目标显示
        try:
            self.canvas.delete("target")
        except Exception:
            pass

        # 分析并保存 trial 数据
        trial_metrics = self.analyze_single_trial(self.trajectory_data, self.target_pos)
        # 若使用 preset，写入 width/radius/plan info
        if self.experiment_mode.get() == "preset" and (self.current_trial - 1) < len(self.trial_plan):
            plan_info = self.trial_plan[self.current_trial - 1]
            trial_metrics.update({
                "preset_distance": plan_info.get("distance"),
                "preset_width": plan_info.get("width"),
                "preset_radius": plan_info.get("radius"),
                "preset_target_pos": plan_info.get("target_pos")
            })
        self.session_data.append(trial_metrics)

        # 更新 last_click_pos
        self.last_click_pos = (event.x, event.y)

        # 继续下一轮或结束
        if self.current_trial < self.max_trials:
            self.spawn_target()
        else:
            self.show_session_summary()

    def analyze_single_trial(self, trajectory, target_pos):
        """分析单次轨迹并返回指标字典"""
        if len(trajectory) < 2:
            return {
                "time": 0, "distance": 0, "speed": 0, "curvature": 1,
                "ideal_distance": 0, "target_x": target_pos[0], "target_y": target_pos[1],
                "id": 0, "throughput": 0, "trajectory": list(trajectory),
                "peak_velocity": 0, "reaction_time": 0
            }
        total_distance = 0.0
        velocities = []
        for i in range(1, len(trajectory)):
            x1, y1, t1 = trajectory[i-1]
            x2, y2, t2 = trajectory[i]
            d = math.hypot(x2 - x1, y2 - y1)
            dt = t2 - t1
            total_distance += d
            if dt > 0:
                velocities.append(d / dt)
        start_x, start_y, _ = trajectory[0]
        end_x, end_y, _ = trajectory[-1]
        ideal_distance = math.hypot(end_x - start_x, end_y - start_y)
        time_elapsed = trajectory[-1][2] - trajectory[0][2] if trajectory[-1][2] > trajectory[0][2] else 0.0
        avg_speed = total_distance / time_elapsed if time_elapsed > 0 else 0.0
        curvature = total_distance / ideal_distance if ideal_distance > 0 else 1.0
        peak_velocity = max(velocities) if velocities else 0.0

        # Reaction time 估计：从起点到累计位移超过阈值的时间
        move_threshold = 5.0
        acc_dist = 0.0
        reaction_time = 0.0
        t0 = trajectory[0][2]
        rt_found = False
        for i in range(1, len(trajectory)):
            x1, y1, t1 = trajectory[i-1]
            x2, y2, t2 = trajectory[i]
            acc_dist += math.hypot(x2 - x1, y2 - y1)
            if acc_dist >= move_threshold:
                reaction_time = t2 - t0
                rt_found = True
                break
        if not rt_found:
            reaction_time = 0.0

        # Fitts ID 的简化计算（W 使用目标直径）
        # 注意：更严谨的做法是使用“有效宽度 We”基于命中位置的分布来估计 W。
        width = 2 * self.TARGET_RADIUS
        index_of_difficulty = math.log2(ideal_distance / width + 1) if width > 0 else 0.0
        throughput = index_of_difficulty / time_elapsed if time_elapsed > 0 else 0.0

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
            "trajectory": list(trajectory),
            "peak_velocity": peak_velocity,
            "reaction_time": reaction_time
        }

    def save_session_files(self):
        """将 session 汇总保存为 CSV 与 JSON（包含原始轨迹和元数据）"""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(self.save_dir, f"session_{timestamp_str}.csv")
        json_path = os.path.join(self.save_dir, f"session_{timestamp_str}.json")

        headers = ["Trial_ID", "Time_Sec", "Distance_Px", "Ideal_Distance_Px", "Speed_PxSec", "Curvature", "Index_of_Difficulty_Bits", "Throughput_Bits_Sec", "Target_X", "Target_Y", "Peak_Velocity_PxSec", "Reaction_Time_Sec"]

        try:
            with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
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
                        trial['target_y'],
                        f"{trial.get('peak_velocity', 0.0):.2f}",
                        f"{trial.get('reaction_time', 0.0):.4f}"
                    ])
            # JSON 保存所有原始轨迹和元数据
            meta = {
                "created_at": datetime.now().isoformat(),
                "os": platform.platform(),
                "screen": {"width": self.canvas_width, "height": self.canvas_height},
                "target_default_radius": self.DEFAULT_TARGET_RADIUS,
                "min_sample_interval_sec": self.min_sample_interval,
                "experiment_mode": self.experiment_mode.get(),
                "trial_plan": self.trial_plan,
                "trials": self.session_data
            }
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(meta, jf, ensure_ascii=False, indent=2)
            return csv_path, json_path
        except Exception as e:
            messagebox.showerror("保存失败", f"保存数据时发生错误: {e}")
            return None, None

    def show_session_summary(self):
        """汇总、保存并展示分析与轨迹"""
        total_trials = len(self.session_data)
        if total_trials == 0:
            messagebox.showinfo("提示", "没有记录到任何试次数据。")
            return

        avg_time = sum(d["time"] for d in self.session_data) / total_trials
        avg_speed = sum(d["speed"] for d in self.session_data) / total_trials
        avg_curvature = sum(d["curvature"] for d in self.session_data) / total_trials
        avg_throughput = sum(d["throughput"] for d in self.session_data) / total_trials

        saved_csv, saved_json = self.save_session_files()
        if saved_csv and saved_json:
            msg = f"结果已保存:\nCSV: {saved_csv}\nJSON: {saved_json}"
            messagebox.showinfo("保存成功", msg)
        else:
            messagebox.showwarning("保存", "保存文件出现问题，请检查权限或路径设置。")

        result_text = (
            f"--- 测试 Session 完成 ---\n"
            f"总轮次: {total_trials}\n\n"
            f"平均耗时 (Time): {avg_time:.3f} s\n"
            f"平均速度 (Speed): {avg_speed:.0f} px/s\n"
            f"平均吞吐量 (Throughput): {avg_throughput:.2f} bits/s\n"
            f"平均轨迹曲率: {avg_curvature:.2f} (理想=1.00)\n\n"
            f"CSV: {saved_csv}\nJSON: {saved_json}"
        )
        self.info_label.config(text="测试结束，生成分析报告完成。", fg="black")
        self.plot_session_results(result_text)

    def plot_session_results(self, result_text):
        """显示轨迹叠加图与文本结果"""
        top = tk.Toplevel(self.root)
        top.title("Session 汇总分析")
        top.geometry("900x700")
        lbl_result = tk.Label(top, text=result_text, font=("SimHei", 12), justify="left", bg="#e8f5e9", padx=10, pady=10)
        lbl_result.pack(fill="x", pady=5)

        fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
        h = self.canvas_height
        num = len(self.session_data)
        for i, trial in enumerate(self.session_data):
            traj = trial.get("trajectory", [])
            if not traj:
                continue
            x_vals = [p[0] for p in traj]
            y_vals = [h - p[1] for p in traj]  # 翻转 y 轴以视觉上更直观
            alpha = 0.3 + 0.7 * (i / max(1, num - 1))
            ax.plot(x_vals, y_vals, '-', color='#2196F3', alpha=alpha, linewidth=1)
            sx, sy, _ = traj[0]
            ex, ey, _ = traj[-1]
            ax.plot([sx, ex], [h-sy, h-ey], '--', color='#F44336', alpha=0.4, linewidth=1)

        ax.set_title(f"全 Session 轨迹叠加 ({num} Trials)", fontsize=14)
        ax.set_xlabel("X (px)")
        ax.set_ylabel("Y (px)")
        ax.grid(True, linestyle=':', alpha=0.6)
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def stop_session(self):
        """允许在中途停止测试（会保存到当前已完成的试次）"""
        if self.current_trial == 0 or not self.session_data:
            # 没有数据
            self.is_recording = False
            self.canvas.delete("target")
            self.info_label.config(text="已停止（无已记录数据）。", fg="#444")
            return
        if messagebox.askyesno("停止确认", "是否停止当前 Session 并保存已记录数据？"):
            self.is_recording = False
            self.canvas.delete("target")
            self.show_session_summary()

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseTrackerApp(root)
    root.mainloop()