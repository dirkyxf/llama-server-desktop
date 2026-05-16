import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import threading
import os
import webbrowser
import platform
import time

# 设置主题和颜色
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# --- 现代化的 Tooltip 类 ---
class ModernTooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None

    def show(self):
        if self.tooltip_window or not self.text:
            return

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-alpha", 0.9)

        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 15
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#2b2b2b",
            foreground="white",
            relief="solid",
            borderwidth=1,
            font=("Microsoft YaHei", 10),
            padx=8,
            pady=4,
        )
        label.pack()

    def hide(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def bind_tips(self):
        self.widget.bind("<Enter>", lambda e: self.show())
        self.widget.bind("<Leave>", lambda e: self.hide())


# --- 主程序类 ---
class LlamaServerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Llama-Server 控制面板")
        self.geometry("700x650")
        self.process = None
        self.target_url = ""

        self.config_schema = [
            {
                "label": "模型路径 (-m)",
                "key": "model_path",
                "type": "entry",
                "default": r"C:\Users\admin\.lmstudio\models\lmstudio-community\gemma-4-26B-A4B\gemma-4-26B-A4B-it-UD-IQ4_XS.gguf",
                "help": "GGUF 模型的完整文件路径",
            },
            {
                "label": "监听地址 (--host)",
                "key": "host",
                "type": "entry",
                "default": "127.0.0.1",
                "help": "监听的 IP 地址",
            },
            {
                "label": "监听端口 (--port)",
                "key": "port",
                "type": "entry",
                "default": "8080",
                "help": "监听的端口号",
            },
            {
                "label": "API Key (--api-key)",
                "key": "api_key",
                "type": "entry",
                "default": "sk-123456",
                "help": "访问 API 所需的密钥",
            },
            {
                "label": "GPU层数 (-ngl)",
                "key": "ngl",
                "type": "entry",
                "default": "99",
                "help": "将多少层模型卸载到 GPU (99 表示全量)",
            },
            {
                "label": "张量分割 (--tensor-split)",
                "key": "split",
                "type": "entry",
                "default": "2,1",
                "help": "多显卡权重分配，如 '1,1' 或 '2,1'",
            },
            {
                "label": "Flash Attention (--flash-attn)",
                "key": "fa",
                "type": "switch",
                "default": True,
                "help": "启用 Flash Attention 加速计算",
            },
            {
                "label": "线程数 (--threads)",
                "key": "threads",
                "type": "entry",
                "default": "10",
                "help": "使用的 CPU 线程数",
            },
            {
                "label": "Min-P 采样 (--min-p)",
                "key": "min_p",
                "type": "entry",
                "default": "0.05",
                "help": "采样过滤阈值，控制生成多样性",
            },
            {
                "label": "指标统计 (--metrics)",
                "key": "metrics",
                "type": "switch",
                "default": True,
                "help": "在服务器中开启性能指标统计",
            },
            {
                "label": "槽位数 (--slots)",
                "key": "slots",
                "type": "entry",
                "default": "",
                "help": "并发请求处理槽位数量",
            },
        ]

        self.inputs = {}
        self.create_ui()

    def create_ui(self):
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, label_text="Llama-Server 参数配置"
        )
        self.scrollable_frame.pack(padx=20, pady=(20, 10), fill="both", expand=True)

        for i, item in enumerate(self.config_schema):
            row_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=8, padx=5)

            lbl = ctk.CTkLabel(
                row_frame,
                text=item["label"],
                width=180,
                anchor="w",
                font=("Microsoft YaHei", 13),
            )
            lbl.pack(side="left")

            help_btn = ctk.CTkLabel(
                row_frame,
                text="❓",
                text_color="#3b8ed0",
                cursor="hand2",
                font=("Segoe UI Symbol", 16),
            )
            help_btn.pack(side="left", padx=5)
            tooltip = ModernTooltip(help_btn, item["help"])
            tooltip.bind_tips()

            if item["type"] == "entry":
                if item["key"] == "model_path":
                    entry_container = ctk.CTkFrame(row_frame, fg_color="transparent")
                    entry_container.pack(side="right", expand=True, fill="x")

                    entry = ctk.CTkEntry(entry_container)
                    entry.insert(0, item["default"])
                    entry.pack(side="left", expand=True, fill="x", padx=(0, 5))

                    browse_btn = ctk.CTkButton(
                        entry_container,
                        text="...",
                        width=30,
                        command=lambda e=entry: self.browse_file(e),
                    )
                    browse_btn.pack(side="right")
                    self.inputs[item["key"]] = entry
                else:
                    entry = ctk.CTkEntry(row_frame, width=300)
                    entry.insert(0, item["default"])
                    entry.pack(side="right", expand=True, fill="x")
                    self.inputs[item["key"]] = entry
            else:
                switch_val = item["default"]
                switch = ctk.CTkSwitch(row_frame, text="", progress_color="#3b8ed0")
                if switch_val:
                    switch.select()
                switch.pack(side="right")
                self.inputs[item["key"]] = switch

        control_frame = ctk.CTkFrame(self, fg_color="transparent")
        control_frame.pack(padx=20, pady=20, fill="x")

        self.status_label = ctk.CTkLabel(
            control_frame, text="状态: 已停止", text_color="gray"
        )
        self.status_label.pack(side="left")

        self.start_btn = ctk.CTkButton(
            control_frame,
            text="启动 Server",
            command=self.start_server_thread,
            fg_color="#2fa572",
            hover_color="#107c41",
            font=("Microsoft YaHei", 14, "bold"),
        )
        self.start_btn.pack(side="right", padx=10)

        self.stop_btn = ctk.CTkButton(
            control_frame,
            text="停止 Server",
            command=self.stop_server,
            state="disabled",
            fg_color="#c42b1c",
            hover_color="#a32318",
            font=("Microsoft YaHei", 14, "bold"),
        )
        self.stop_btn.pack(side="right")

    def build_command(self):
        try:
            cmd = ["llama-server"]
            model_path = self.inputs["model_path"].get().strip()
            if not os.path.exists(model_path):
                raise ValueError(f"找不到模型文件: {model_path}")
            cmd.extend(["-m", model_path])

            # New parameters
            cmd.extend(["--host", self.inputs["host"].get().strip()])
            cmd.extend(["--port", self.inputs["port"].get().strip()])

            api_key = self.inputs["api_key"].get().strip()
            if api_key:
                cmd.extend(["--api-key", api_key])

            cmd.extend(["-ngl", self.inputs["ngl"].get()])
            cmd.extend(["--tensor-split", self.inputs["split"].get()])

            if self.inputs["fa"].get():
                cmd.extend(["--flash-attn", "on"])

            cmd.extend(["--threads", self.inputs["threads"].get()])
            cmd.extend(["--min-p", self.inputs["min_p"].get()])

            if self.inputs["metrics"].get():
                cmd.append("--metrics")

            slots_val = self.inputs["slots"].get().strip()
            if slots_val:
                cmd.extend(["--slots", slots_val])

            return cmd
        except Exception as e:
            messagebox.showerror("配置错误", str(e))
            return None

    def browse_file(self, entry_widget):
        file_path = filedialog.askopenfilename(
            title="选择模型文件",
            filetypes=[("GGUF Files", "*.gguf"), ("All Files", "*.*")],
        )
        if file_path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, file_path)

    def update_target_url(self):
        host = self.inputs["host"].get().strip()
        port = self.inputs["port"].get().strip()
        self.target_url = f"http://{host}:{port}"

    def start_server_thread(self):
        self.update_target_url()
        cmd = self.build_command()
        if not cmd:
            return

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="状态: 正在启动...", text_color="#3b8ed0")

        threading.Thread(target=self.run_server, args=(cmd,), daemon=True).start()

    def open_edge_browser(self):
        """尝试调用 Edge 浏览器打开指定的 URL"""
        print(f"🌐 正在尝试打开浏览器: {self.target_url}")
        try:
            if platform.system() == "Windows":
                # Windows 专用：显式调用 msedge
                subprocess.Popen(f"start msedge {self.target_url}", shell=True)
            else:
                # 其他系统使用默认浏览器
                webbrowser.open(self.target_url)
        except Exception as e:
            print(f"无法打开浏览器: {e}")
            # 如果显式调用失败，退而求其次使用默认浏览器
            webbrowser.open(self.target_url)

    def run_server(self, cmd):
        print(f"🚀 启动命令: {' '.join(cmd)}")
        ready_detected = False

        try:
            # Windows 下隐藏控制台窗口
            creationflags = 0
            if platform.system() == "Windows":
                creationflags = subprocess.CREATE_NO_WINDOW

            # 不使用 shell=True，直接传入命令列表，这样可以更彻底地隐藏窗口
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=False,
                bufsize=1,  # 行缓冲
                creationflags=creationflags,
            )

            # 实时读取输出流
            for line in self.process.stdout:
                clean_line = line.strip()
                print(f"[Server] {clean_line}")

                # 核心逻辑：检测是否包含 URL 关键词
                if not ready_detected and self.target_url in clean_line:
                    ready_detected = True
                    self.status_label.configure(
                        text="状态: 运行中 (已就绪)", text_color="#2fa572"
                    )
                    # 在子线程中通过 after 安全地调用 GUI 的浏览器打开功能
                    self.after(0, self.open_edge_browser)

            self.process.wait()
        except Exception as e:
            print(f"❌ 错误: {e}")
        finally:
            self.process = None
            self.after(0, self.reset_ui)

    def reset_ui(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="状态: 已停止", text_color="gray")
        messagebox.showinfo("提示", "Server 进程已结束")

    def stop_server(self):
        if self.process:
            # 使用 taskkill 确保彻底杀死进程及其子进程
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(self.process.pid)], shell=True
            )
            print("🛑 已强制停止服务器")


if __name__ == "__main__":
    app = LlamaServerApp()
    app.mainloop()
