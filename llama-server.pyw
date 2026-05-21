import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import threading
import os
import webbrowser
import platform
import time
import json

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

        mode = ctk.get_appearance_mode()
        bg = "#e8e8e8" if mode == "Light" else "#2b2b2b"
        fg = "#333333" if mode == "Light" else "white"

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background=bg,
            foreground=fg,
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
                "default": "",
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
                "label": "上下文大小 (-c)",
                "key": "ctx_size",
                "type": "entry",
                "default": "4096",
                "help": "提示词和响应的最大上下文长度",
            },
            {
                "label": "API Key (--api-key)",
                "key": "api_key",
                "type": "entry",
                "default": "sk-123456",
                "help": "访问 API 所需的密钥",
            },
            {
                "label": "并行处理数 (--parallel)",
                "key": "parallel",
                "type": "entry",
                "default": "1",
                "help": "并行处理的请求数量",
            },
            {
                "label": "日志文件 (--log-file)",
                "key": "log_file",
                "type": "switch",
                "default": False,
                "help": "开启后将日志输出到 llama-server.log",
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
                "label": "批大小 (-b)",
                "key": "batch_size",
                "type": "entry",
                "default": "512",
                "help": "每次处理的提示词批处理大小",
            },
            {
                "label": "锁定内存 (--mlock)",
                "key": "mlock",
                "type": "switch",
                "default": True,
                "help": "锁定物理内存，防止模型被交换到硬盘",
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
                "label": "自动打开浏览器",
                "key": "auto_open",
                "type": "switch",
                "default": True,
                "help": "启动后自动在 Edge 浏览器中打开 API 界面",
            },
            {
                "label": "槽位数 (--slots)",
                "key": "slots",
                "type": "entry",
                "default": "",
                "help": "并发请求处理槽位数量",
            },
            {
                "label": "温度 (--temp)",
                "key": "temp",
                "type": "entry",
                "default": "0.8",
                "help": "控制生成随机性，值越高越有创意",
            },
            {
                "label": "Top-K (--top-k)",
                "key": "top_k",
                "type": "entry",
                "default": "40",
                "help": "仅从概率最高的 K 个词中采样",
            },
            {
                "label": "Top-P (--top-p)",
                "key": "top_p",
                "type": "entry",
                "default": "0.95",
                "help": "核采样阈值，累积概率达到此值时停止选择",
            },
            {
                "label": "重复惩罚 (--repeat-penalty)",
                "key": "repeat_penalty",
                "type": "entry",
                "default": "1.1",
                "help": "对重复内容的惩罚力度，值越高越不易重复",
            },
            {
                "label": "K缓存类型 (--cache-type-k)",
                "key": "cache_type_k",
                "type": "entry",
                "default": "q4_0",
                "help": "KV 缓存中 K 的数据类型",
            },
            {
                "label": "V缓存类型 (--cache-type-v)",
                "key": "cache_type_v",
                "type": "entry",
                "default": "q4_0",
                "help": "KV 缓存中 V 的数据类型",
            },
            {
                "label": "推测解码类型 (--spec-type)",
                "key": "spec_type",
                "type": "switch",
                "default": False,
                "help": "开启推测解码加速 (draft-mtp)",
            },
            {
                "label": "推测草稿数量 (--spec-draft-n-max)",
                "key": "spec_draft_n_max",
                "type": "entry",
                "default": "2",
                "help": "每次推测生成的最大草稿数量",
            },
            {
                "label": "推测草稿概率阈值 (--spec-draft-p-min)",
                "key": "spec_draft_p_min",
                "type": "entry",
                "default": "0.75",
                "help": "推测草稿的最小概率阈值",
            },
            {
                "label": "开启 Embedding (--embedding)",
                "key": "embedding",
                "type": "switch",
                "default": False,
                "help": "启用 Embedding API 支持",
            },
        ]
        
        self.load_config()

        self.inputs = {}
        self.create_ui()

    def load_config(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for item in self.config_schema:
                    if item["key"] in saved:
                        item["default"] = saved[item["key"]]
            except Exception:
                pass

    def save_config(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        config = {}
        for key, widget in self.inputs.items():
            if isinstance(widget, ctk.CTkEntry):
                config[key] = widget.get().strip()
            elif isinstance(widget, ctk.CTkSwitch):
                config[key] = widget.get()
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception:
            pass

    def create_ui(self):
        # 顶部 Header 区域
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 5))

        # 标题
        ctk.CTkLabel(
            header_frame,
            text="Llama-Server 参数配置",
            font=("Microsoft YaHei", 16, "bold"),
        ).pack(side="left")

        # 主题切换图标
        theme_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        theme_frame.pack(side="right")

        themes = [
            ("System", "💻"),
            ("Light", "☀️"),
            ("Dark", "🌙")
        ]
        
        for mode, icon in themes:
            btn = ctk.CTkButton(
                theme_frame, 
                text=icon, 
                width=35, 
                font=("Segoe UI Emoji", 16),
                command=lambda m=mode: self.change_theme(m)
            )
            btn.pack(side="left", padx=2)

        # TabView
        self.tabview = ctk.CTkTabview(self, width=680)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        # 优化标签按钮的字体和大小
        self.tabview._segmented_button.configure(
            font=("Microsoft YaHei", 14, "bold"),
            height=35
        )

        self.tabview.add("核心启动参数")
        self.tabview.add("硬件加速")
        self.tabview.add("生成控制")
        self.tabview.add("其他参数")
        self.tabview.add("命令行")

        # 定义分类
        core_keys = {"model_path", "ctx_size"}
        mtp_keys = {"spec_type", "spec_draft_n_max", "spec_draft_p_min"}
        hw_keys = {"ngl", "split", "fa", "threads", "batch_size", "mlock"}
        gen_keys = {"min_p", "metrics", "slots", "temp", "top_k", "top_p", "repeat_penalty", "cache_type_k", "cache_type_v"}
        other_keys = {"host", "port", "api_key", "auto_open", "embedding", "parallel", "log_file"}

        # 渲染 Tab
        self.render_tab(self.tabview.tab("核心启动参数"), [
            (core_keys, "#FF6B6B", "核心启动参数(必选)"),
            (mtp_keys, "#FF6B6B", "MTP参数")
        ])
        self.render_tab(self.tabview.tab("硬件加速"), [(hw_keys, "#00BFFF", "硬件加速与性能(优化)")])
        self.render_tab(self.tabview.tab("生成控制"), [(gen_keys, "#FFA500", "生成控制参数(风格)")])
        self.render_tab(self.tabview.tab("其他参数"), [(other_keys, "#32CD32", "其他参数")])
        
        # 命令行展示区域
        cmd_tab = self.tabview.tab("命令行")
        self.cmd_textbox = ctk.CTkTextbox(cmd_tab, wrap="word", font=("Consolas", 12))
        self.cmd_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        save_btn = ctk.CTkButton(cmd_tab, text="保存当前配置", command=self.save_named_config, font=("Microsoft YaHei", 13))
        save_btn.pack(pady=(0, 10))
        
        # 配置清单区域（在保存按钮下方）
        ctk.CTkLabel(cmd_tab, text="已保存的配置清单:", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", padx=10)
        self.config_list_frame = ctk.CTkScrollableFrame(cmd_tab, fg_color="transparent")
        self.config_list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.load_config_list()

        # 联动逻辑：spec_type 控制 spec_draft_n_max 和 spec_draft_p_min
        def update_spec_params_state():
            is_on = self.inputs["spec_type"].get()
            state = "normal" if is_on else "disabled"
            for key in ["spec_draft_n_max", "spec_draft_p_min"]:
                self.inputs[key].configure(state=state)

        self.inputs["spec_type"].configure(command=update_spec_params_state)
        update_spec_params_state() # 初始化状态

        # 绑定所有输入控件以实时更新命令行显示
        for key, widget in self.inputs.items():
            if isinstance(widget, ctk.CTkEntry):
                widget.bind("<KeyRelease>", lambda e: self.update_command_display())
            elif isinstance(widget, ctk.CTkSwitch):
                orig_cmd = widget.cget("command")
                def make_cmd(original):
                    return lambda: (original() if original else None, self.update_command_display())
                widget.configure(command=make_cmd(orig_cmd))
        self.update_command_display()
        
        # 绑定窗口关闭事件以保存配置
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 底部控制按钮
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

    def change_theme(self, mode):
        ctk.set_appearance_mode(mode)

    def render_tab(self, tab_frame, config_blocks):
        scroll_frame = ctk.CTkScrollableFrame(tab_frame, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)
        
        for keys, border_color, title in config_blocks:
            frame = ctk.CTkFrame(scroll_frame, border_width=3, border_color=border_color, fg_color=("#f5f5f5", "#1f2226"))
            frame.pack(fill="x", padx=5, pady=5)
            
            # 标题颜色适配：亮色模式下使用深色以保证对比度，暗色模式下使用边框色
            title_color = ("#333333", border_color)
            ctk.CTkLabel(frame, text=title, text_color=title_color, font=("Microsoft YaHei", 14, "bold")).pack(fill="x", padx=10, pady=(10, 5))
            
            for item in self.config_schema:
                if item["key"] in keys:
                    self.create_param_row(frame, item)

    def create_param_row(self, parent, item):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", pady=8, padx=10)

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
            text_color=("#0055aa", "#3b8ed0"),
            cursor="hand2",
            font=("Segoe UI Symbol", 16),
        )
        help_btn.pack(side="left", padx=5)
        ModernTooltip(help_btn, item["help"]).bind_tips()

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
            switch = ctk.CTkSwitch(row_frame, text="", progress_color="#3b8ed0")
            if item["default"]:
                switch.select()
            switch.pack(side="right")
            self.inputs[item["key"]] = switch

    def save_named_config(self):
        dialog = ctk.CTkInputDialog(text="请输入配置名称:", title="保存配置")
        name = dialog.get_input()
        if name:
            name = name.strip()
            if not name:
                return
                
            config = {}
            for key, widget in self.inputs.items():
                if isinstance(widget, ctk.CTkEntry):
                    config[key] = widget.get().strip()
                elif isinstance(widget, ctk.CTkSwitch):
                    config[key] = widget.get()
            
            list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_list.json")
            config_list = {}
            if os.path.exists(list_path):
                try:
                    with open(list_path, "r", encoding="utf-8") as f:
                        config_list = json.load(f)
                except Exception:
                    pass
            
            config_list[name] = config
            with open(list_path, "w", encoding="utf-8") as f:
                json.dump(config_list, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("成功", f"配置已保存到 config_list.json")
            self.load_config_list()

    def load_config_list(self):
        for widget in self.config_list_frame.winfo_children():
            widget.destroy()

        list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_list.json")
        if not os.path.exists(list_path):
            ctk.CTkLabel(self.config_list_frame, text="暂无保存的配置，请在“命令行”选项卡中保存配置。", text_color="gray").pack(pady=20)
            return

        try:
            with open(list_path, "r", encoding="utf-8") as f:
                config_list = json.load(f)
        except Exception:
            config_list = {}

        if not config_list:
            ctk.CTkLabel(self.config_list_frame, text="暂无保存的配置。", text_color="gray").pack(pady=20)
            return

        names = list(config_list.keys())
        for i in range(0, len(names), 2):
            row = ctk.CTkFrame(self.config_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2, anchor="w")
            
            btn1 = ctk.CTkButton(
                row, text=names[i], command=lambda n=names[i]: self.show_config_action_dialog(n), height=30, width=150
            )
            btn1.pack(side="left", padx=2)
            
            if i + 1 < len(names):
                btn2 = ctk.CTkButton(
                    row, text=names[i+1], command=lambda n=names[i+1]: self.show_config_action_dialog(n), height=30, width=150
                )
                btn2.pack(side="left", padx=2)

    def apply_config(self, name):
        list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_list.json")
        try:
            with open(list_path, "r", encoding="utf-8") as f:
                config_list = json.load(f)
            config = config_list.get(name)
            if config:
                for key, value in config.items():
                    if key in self.inputs:
                        widget = self.inputs[key]
                        if isinstance(widget, ctk.CTkEntry):
                            widget.delete(0, "end")
                            widget.insert(0, str(value))
                        elif isinstance(widget, ctk.CTkSwitch):
                            if value:
                                widget.select()
                            else:
                                widget.deselect()
                self.update_command_display()
                messagebox.showinfo("成功", f"已加载配置: {name}")
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {e}")

    def show_config_action_dialog(self, name):
        dialog = ctk.CTkToplevel(self)
        dialog.title("配置操作")
        dialog.geometry("250x150")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text=f"配置: {name}", font=("Microsoft YaHei", 12)).pack(pady=15)

        def on_load():
            self.apply_config(name)
            dialog.destroy()

        def on_delete():
            self.delete_config(name)
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="加载", command=on_load, width=80).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="删除", command=on_delete, width=80, fg_color="#c42b1c", hover_color="#a32318").pack(side="left", padx=10)

    def delete_config(self, name):
        list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_list.json")
        if os.path.exists(list_path):
            try:
                with open(list_path, "r", encoding="utf-8") as f:
                    config_list = json.load(f)
                if name in config_list:
                    del config_list[name]
                    with open(list_path, "w", encoding="utf-8") as f:
                        json.dump(config_list, f, indent=4, ensure_ascii=False)
                    self.load_config_list()
                    messagebox.showinfo("成功", f"已删除配置: {name}")
            except Exception as e:
                messagebox.showerror("错误", f"删除配置失败: {e}")

    def on_closing(self):
        self.save_config()
        self.destroy()

    def update_command_display(self):
        try:
            cmd = self.build_command()
            if cmd:
                cmd_str = " ".join(cmd)
                self.cmd_textbox.configure(state="normal")
                self.cmd_textbox.delete("1.0", "end")
                self.cmd_textbox.insert("1.0", cmd_str)
                self.cmd_textbox.configure(state="disabled")
            else:
                # 如果 build_command 返回 None (例如验证失败)，显示提示
                self.cmd_textbox.configure(state="normal")
                self.cmd_textbox.delete("1.0", "end")
                self.cmd_textbox.insert("1.0", "请检查必填项（如模型路径）...")
                self.cmd_textbox.configure(state="disabled")
        except Exception:
            pass

    def build_command(self):
        try:
            cmd = ["llama-server"]

            # Helper to add entry parameters only if not empty
            def add_entry_param(flag, key):
                val = self.inputs[key].get().strip()
                if val:
                    cmd.extend([flag, val])

            # Model path
            model_path = self.inputs["model_path"].get().strip()
            if model_path:
                if not os.path.exists(model_path):
                    raise ValueError(f"找不到模型文件: {model_path}")
                cmd.extend(["-m", model_path])

            # Core params
            add_entry_param("--host", "host")
            add_entry_param("--port", "port")
            add_entry_param("-c", "ctx_size")

            # API Key
            api_key = self.inputs["api_key"].get().strip()
            if api_key:
                cmd.extend(["--api-key", api_key])

            # Hardware
            add_entry_param("-ngl", "ngl")
            add_entry_param("--tensor-split", "split")

            if self.inputs["fa"].get():
                cmd.extend(["--flash-attn", "on"])

            add_entry_param("--threads", "threads")
            add_entry_param("-b", "batch_size")
            
            if self.inputs["mlock"].get():
                cmd.append("--mlock")

            # Generation
            add_entry_param("--min-p", "min_p")
            add_entry_param("--temp", "temp")
            add_entry_param("--top-k", "top_k")
            add_entry_param("--top-p", "top_p")
            add_entry_param("--repeat-penalty", "repeat_penalty")
            add_entry_param("--cache-type-k", "cache_type_k")
            add_entry_param("--cache-type-v", "cache_type_v")

            # MTP
            if self.inputs["spec_type"].get():
                cmd.extend(["--spec-type", "draft-mtp"])
                add_entry_param("--spec-draft-n-max", "spec_draft_n_max")
                add_entry_param("--spec-draft-p-min", "spec_draft_p_min")

            # Metrics
            if self.inputs["metrics"].get():
                cmd.append("--metrics")

            add_entry_param("--slots", "slots")

            if self.inputs["embedding"].get():
                cmd.append("--embedding")

            add_entry_param("--parallel", "parallel")

            # Log file
            if self.inputs["log_file"].get():
                base_name = "llama-server.log"
                log_dir = os.path.dirname(os.path.abspath(__file__))
                log_path = os.path.join(log_dir, base_name)
                
                if os.path.exists(log_path):
                    i = 1
                    while True:
                        name, ext = os.path.splitext(base_name)
                        new_name = f"{name}-{i}{ext}"
                        new_path = os.path.join(log_dir, new_name)
                        if not os.path.exists(new_path):
                            log_path = new_path
                            break
                        i += 1
                
                cmd.extend(["--log-file", log_path])

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
        self.save_config()
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
                    if self.inputs["auto_open"].get():
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
