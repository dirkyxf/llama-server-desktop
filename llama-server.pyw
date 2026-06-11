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

# ── 全局设计 Token ─────────────────────────────────────────────────────────────
FONT_FAMILY   = "Microsoft YaHei"
FONT_MONO     = "Consolas"
FONT_EMOJI    = "Segoe UI Emoji"

# 双主题色板
THEMES = {
    "Dark": {
        "bg_deep":      "#0f1117",
        "bg_card":      "#1a1d27",
        "bg_input":     "#22263a",
        "border":       "#2d3150",
        "accent_blue":  "#4f8ef7",
        "accent_green": "#2ecc71",
        "accent_red":   "#e74c3c",
        "accent_orange":"#f39c12",
        "text_primary": "#e8eaf6",
        "text_muted":   "#848c98",
        "text_on_accent":"#ffffff",
        "text_on_light":"#e8eaf6",
        "tab_selected_bg":"#4f8ef7",
        "tab_selected_hover_bg":"#3a7de0",
        "theme_btn_border":"#6b7280",
        "tag_core":     "#ff7b7b",
        "tag_hw":       "#6dcff7",
        "tag_gen":      "#ffa726",
        "tag_other":    "#66bb6a",
    },
    "Light": {
        "bg_deep":      "#f0f2f8",
        "bg_card":      "#ffffff",
        "bg_input":     "#f5f6fa",
        "border":       "#dfe2ea",
        "accent_blue":  "#2563eb",
        "accent_green": "#16a34a",
        "accent_red":   "#dc2626",
        "accent_orange":"#d97706",
        "text_primary": "#1e293b",
        "text_muted":   "#64748b",
        "text_on_accent":"#ffffff",
        "text_on_light":"#1e293b",
        "tab_selected_bg":"#93bbfd",
        "tab_selected_hover_bg":"#7aacfa",
        "theme_btn_border":"#94a3b8",
        "tag_core":     "#dc2626",
        "tag_hw":       "#1d4ed8",
        "tag_gen":      "#b45309",
        "tag_other":    "#15803d",
    },
}


def P(key):
    """根据当前主题动态取色"""
    mode = ctk.get_appearance_mode()
    theme = THEMES.get(mode, THEMES["Dark"])
    return theme.get(key, THEMES["Dark"].get(key, "#000000"))


# ── 现代化 Tooltip ─────────────────────────────────────────────────────────────
class ModernTooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None

    def show(self):
        if self.tw or not self.text:
            return
        self.tw = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-alpha", 0.95)

        x = self.widget.winfo_pointerx() + 16
        y = self.widget.winfo_pointery() + 16
        tw.wm_geometry(f"+{x}+{y}")

        mode = ctk.get_appearance_mode()
        bg = "#ffffff" if mode == "Light" else "#1e2130"
        fg = "#1e293b" if mode == "Light" else "#e8eaf6"
        border = "#3b82f6" if mode == "Light" else "#4f8ef7"

        outer = tk.Frame(tw, background=border, padx=1, pady=1)
        outer.pack()
        tk.Label(
            outer, text=self.text, justify="left",
            background=bg, foreground=fg,
            font=(FONT_FAMILY, 10), padx=10, pady=5, wraplength=260,
        ).pack()

    def hide(self):
        if self.tw:
            self.tw.destroy()
            self.tw = None

    def bind_tips(self):
        self.widget.bind("<Enter>", lambda e: self.show())
        self.widget.bind("<Leave>", lambda e: self.hide())


# ── 状态指示灯 ─────────────────────────────────────────────────────────────────
class StatusDot(tk.Canvas):
    """三态动画圆点：stopped / starting / running"""
    COLORS = {
        "stopped":  "#6b7280",
        "starting": "#f39c12",
        "running":  "#2ecc71",
    }

    def __init__(self, master, **kw):
        super().__init__(master, width=12, height=12,
                         bg=P("bg_card"),
                         highlightthickness=0, **kw)
        self._state = "stopped"
        self._alpha = 1.0
        self._dir = -1
        self._dot = self.create_oval(1, 1, 11, 11, fill=self.COLORS["stopped"], outline="")
        self._job = None

    def set_state(self, state: str):
        self._state = state
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        if state == "starting":
            self._alpha = 1.0
            self._dir = -1
            self._pulse()
        else:
            self.itemconfig(self._dot, fill=self.COLORS.get(state, "#6b7280"))

    def _pulse(self):
        if self._state != "starting":
            return
        self._alpha = max(0.3, min(1.0, self._alpha + self._dir * 0.07))
        if self._alpha <= 0.3 or self._alpha >= 1.0:
            self._dir *= -1
        base = (243, 156, 18)
        mode = ctk.get_appearance_mode()
        dark = (240, 242, 248) if mode == "Light" else (40, 44, 52)
        r = int(dark[0] + (base[0] - dark[0]) * self._alpha)
        g = int(dark[1] + (base[1] - dark[1]) * self._alpha)
        b = int(dark[2] + (base[2] - dark[2]) * self._alpha)
        self.itemconfig(self._dot, fill=f"#{r:02x}{g:02x}{b:02x}")
        self._job = self.after(60, self._pulse)


# ── 主程序 ─────────────────────────────────────────────────────────────────────
class LlamaServerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Llama Server 控制面板")
        self.geometry("740x680")
        self.minsize(700, 600)
        self.process = None
        self.target_url = ""

        self.config_schema = [
            {"label": "模型路径 (-m)", "key": "model_path", "type": "entry", "default": "", "help": "GGUF 模型的完整文件路径"},
            {"label": "多模态投影 (-mmproj)", "key": "mmproj", "type": "entry", "default": "", "help": "多模态投影模型的 GGUF 文件路径"},
            {"label": "草稿模型 (--model-draft)", "key": "model_draft", "type": "entry", "default": "", "help": "推测解码使用的草稿模型文件路径 (GGUF)"},
            {"label": "监听地址 (--host)", "key": "host", "type": "entry", "default": "127.0.0.1", "help": "监听的 IP 地址"},
            {"label": "监听端口 (--port)", "key": "port", "type": "entry", "default": "8080", "help": "监听的端口号"},
            {"label": "上下文大小 (-c)", "key": "ctx_size", "type": "entry", "default": "4096", "help": "提示词和响应的最大上下文长度"},
            {"label": "API Key (--api-key)", "key": "api_key", "type": "entry", "default": "sk-123456", "help": "访问 API 所需的密钥"},
            {"label": "并行处理数 (--parallel)", "key": "parallel", "type": "entry", "default": "1", "help": "并行处理的请求数量"},
            {"label": "日志文件 (--log-file)", "key": "log_file", "type": "switch", "default": False, "help": "开启后将日志输出到 llama-server.log"},
            {"label": "GPU层数 (-ngl)", "key": "ngl", "type": "entry", "default": "99", "help": "将多少层模型卸载到 GPU (99 表示全量)"},
            {"label": "张量分割 (--tensor-split)", "key": "split", "type": "entry", "default": "2,1", "help": "多显卡权重分配，如 '1,1' 或 '2,1'"},
            {"label": "Flash Attention (--flash-attn)", "key": "fa", "type": "switch", "default": True, "help": "启用 Flash Attention 加速计算"},
            {"label": "线程数 (--threads)", "key": "threads", "type": "entry", "default": "10", "help": "使用的 CPU 线程数"},
            {"label": "物理批大小 (-tb)", "key": "tb", "type": "entry", "default": "", "help": "单次前向传播的最大 token 数 (ubatch)，影响显存占用和推理速度"},
            {"label": "批大小 (-b)", "key": "batch_size", "type": "entry", "default": "512", "help": "每次处理的提示词批处理大小"},
            {"label": "禁止内存映射 (--no-mmap)", "key": "no_mmap", "type": "switch", "default": True, "help": "禁止内存映射，使用普通内存分配方式加载模型"},
            {"label": "锁定内存 (--mlock)", "key": "mlock", "type": "switch", "default": True, "help": "锁定物理内存，防止模型被交换到硬盘"},
            {"label": "Min-P 采样 (--min-p)", "key": "min_p", "type": "entry", "default": "0.05", "help": "采样过滤阈值，控制生成多样性"},
            {"label": "指标统计 (--metrics)", "key": "metrics", "type": "switch", "default": True, "help": "在服务器中开启性能指标统计"},
            {"label": "自动打开浏览器", "key": "auto_open", "type": "switch", "default": True, "help": "启动后自动在 Edge 浏览器中打开 API 界面"},
            {"label": "槽位数 (--slots)", "key": "slots", "type": "entry", "default": "", "help": "并发请求处理槽位数量"},
            {"label": "温度 (--temp)", "key": "temp", "type": "entry", "default": "0.8", "help": "控制生成随机性，值越高越有创意"},
            {"label": "Top-K (--top-k)", "key": "top_k", "type": "entry", "default": "40", "help": "仅从概率最高的 K 个词中采样"},
            {"label": "Top-P (--top-p)", "key": "top_p", "type": "entry", "default": "0.95", "help": "核采样阈值，累积概率达到此值时停止选择"},
            {"label": "重复惩罚 (--repeat-penalty)", "key": "repeat_penalty", "type": "entry", "default": "1.1", "help": "对重复内容的惩罚力度，值越高越不易重复"},
            {"label": "K缓存类型 (--cache-type-k)", "key": "cache_type_k", "type": "entry", "default": "q4_0", "help": "KV 缓存中 K 的数据类型"},
            {"label": "V缓存类型 (--cache-type-v)", "key": "cache_type_v", "type": "entry", "default": "q4_0", "help": "KV 缓存中 V 的数据类型"},
            {"label": "关闭思考模式 (--chat-template-kwargs)", "key": "chat_template_kwargs", "type": "switch", "default": False, "help": "开启后传递 {\"enable_thinking\":false}，关闭模型的思考/推理模式"},
            {"label": "Jinja模板 (--jinja)", "key": "jinja", "type": "switch", "default": False, "help": "启用 Jinja2 模板引擎处理聊天模板，支持更复杂的模板语法"},
            {"label": "推测解码类型 (--spec-type)", "key": "spec_type", "type": "switch", "default": False, "help": "开启推测解码加速 (draft-mtp)"},
            {"label": "推测草稿数量 (--spec-draft-n-max)", "key": "spec_draft_n_max", "type": "entry", "default": "2", "help": "每次推测生成的最大草稿数量"},
            {"label": "推测草稿概率阈值 (--spec-draft-p-min)", "key": "spec_draft_p_min", "type": "entry", "default": "0.75", "help": "推测草稿的最小概率阈值"},
            {"label": "开启 Embedding (--embedding)", "key": "embedding", "type": "switch", "default": False, "help": "启用 Embedding API 支持"},
        ]

        self.load_config()
        self.inputs = {}
        self._theme_widgets = []  # 需要在主题切换时更新颜色的控件列表
        self._tab_scroll_frames = []  # 存储选项卡内滚动框架引用
        self._theme_btns = []  # 存储主题切换按钮引用
        self.create_ui()

    # ── 配置持久化 ─────────────────────────────────────────────────────────────
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

    # ── 注册需要主题联动的控件 ──────────────────────────────────────────────────
    def _reg(self, widget, **color_map):
        """注册控件及其颜色映射，切换主题时自动更新"""
        self._theme_widgets.append((widget, color_map))
        # 立即应用当前主题颜色
        self._apply_colors(widget, color_map)

    @staticmethod
    def _apply_colors(widget, color_map):
        for attr, key in color_map.items():
            try:
                widget.configure(**{attr: P(key)})
            except Exception:
                pass

    # ── UI 构建 ────────────────────────────────────────────────────────────────
    def create_ui(self):
        # ── 顶部 Header ──────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, corner_radius=0, height=56)
        self._reg(header, fg_color="bg_card")
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # 左侧 Logo + 标题
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=20)

        logo = ctk.CTkLabel(left, text="⚡", font=(FONT_EMOJI, 22))
        self._reg(logo, text_color="accent_blue")
        logo.pack(side="left", padx=(0, 8))

        title1 = ctk.CTkLabel(left, text="Llama Server", font=(FONT_FAMILY, 16, "bold"))
        self._reg(title1, text_color="text_primary")
        title1.pack(side="left")

        title2 = ctk.CTkLabel(left, text=" 控制面板", font=(FONT_FAMILY, 13))
        self._reg(title2, text_color="text_muted")
        title2.pack(side="left")

        # 右侧主题切换
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=16)

        for mode, icon, tip in [("System", "💻", "跟随系统"),
                                ("Light", "☀️", "浅色"),
                                ("Dark", "🌙", "深色")]:
            btn = ctk.CTkButton(
                right, text=icon, width=34, height=28,
                font=(FONT_EMOJI, 15),
                fg_color="transparent",
                hover_color=P("bg_input"),
                border_width=1,
                border_color=P("theme_btn_border"),
                corner_radius=6,
                command=lambda m=mode: self.change_theme(m),
            )
            btn.pack(side="left", padx=2)
            ModernTooltip(btn, tip).bind_tips()
            self._theme_btns.append((btn, mode))
        self._highlight_active_theme_btn(ctk.get_appearance_mode())

        # 细分割线
        sep1 = ctk.CTkFrame(self, height=1)
        self._reg(sep1, fg_color="border")
        sep1.pack(fill="x")

        # ── 底部状态栏（先 pack 以预留空间）────────────────────────────────────
        sep3 = ctk.CTkFrame(self, height=1)
        self._reg(sep3, fg_color="border")
        sep3.pack(fill="x", side="bottom")

        self.footer = ctk.CTkFrame(self, corner_radius=0, height=56)
        self._reg(self.footer, fg_color="bg_card")
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)

        # 状态指示
        status_area = ctk.CTkFrame(self.footer, fg_color="transparent")
        status_area.pack(side="left", padx=20, pady=10)

        self.status_dot = StatusDot(status_area)
        self.status_dot.pack(side="left", padx=(0, 8))

        self.status_label = ctk.CTkLabel(
            status_area, text="已停止", font=(FONT_FAMILY, 13))
        self._reg(self.status_label, text_color="text_muted")
        self.status_label.pack(side="left")

        # 操作按钮
        btn_area = ctk.CTkFrame(self.footer, fg_color="transparent")
        btn_area.pack(side="right", padx=16)

        self.stop_btn = ctk.CTkButton(
            btn_area, text="⏹  停止", width=110, height=36,
            font=(FONT_FAMILY, 13, "bold"),
            fg_color=P("accent_red"), hover_color="#c0392b",
            corner_radius=8, state="disabled", command=self.stop_server,
        )
        self._reg(self.stop_btn, text_color="text_on_accent")
        self.stop_btn.pack(side="right", padx=(8, 0))

        self.start_btn = ctk.CTkButton(
            btn_area, text="▶  启动 Server", width=140, height=36,
            font=(FONT_FAMILY, 13, "bold"),
            fg_color=P("accent_green"), hover_color="#27ae60",
            corner_radius=8, command=self.start_server_thread,
        )
        self._reg(self.start_btn, text_color="text_on_accent")
        self.start_btn.pack(side="right")

        # ── TabView 主体 ──────────────────────────────────────────────────────
        self.tabview = ctk.CTkTabview(
            self,
            segmented_button_selected_hover_color=P("tab_selected_hover_bg"),
            border_width=0,
        )
        self.tabview.pack(padx=16, pady=(10, 0), fill="both", expand=True)
        self._reg(self.tabview,
                  fg_color="bg_deep",
                  segmented_button_fg_color="bg_card",
                  segmented_button_selected_color="tab_selected_bg",
                  segmented_button_unselected_color="bg_card",
                  segmented_button_unselected_hover_color="bg_input")

        self.tabview._segmented_button.configure(
            font=(FONT_FAMILY, 13, "bold"), height=34,
        )

        for tab in ["核心启动参数", "硬件加速", "生成控制", "其他参数", "命令行"]:
            self.tabview.add(tab)

        # 修复标签页文字颜色（customtkinter 默认 #DCE4EE 在浅色下看不清）
        self._fix_tab_text_colors()

        core_keys  = {"model_path", "mmproj", "model_draft", "ctx_size"}
        mtp_keys   = {"spec_type", "spec_draft_n_max", "spec_draft_p_min"}
        hw_keys    = {"ngl", "split", "fa", "threads", "tb", "batch_size", "no_mmap", "mlock"}
        gen_keys   = {"min_p", "metrics", "slots", "temp", "top_k", "top_p",
                      "repeat_penalty", "cache_type_k", "cache_type_v",
                      "chat_template_kwargs", "jinja"}
        other_keys = {"host", "port", "api_key", "auto_open", "embedding",
                      "parallel", "log_file"}

        self.render_tab(self.tabview.tab("核心启动参数"), [
            (core_keys, P("tag_core"), "🔴  核心启动参数（必选）"),
            (mtp_keys,  P("accent_orange"), "🚀  MTP 推测解码"),
        ])
        self.render_tab(self.tabview.tab("硬件加速"),   [(hw_keys,   P("tag_hw"),   "🔵  硬件加速与性能")])
        self.render_tab(self.tabview.tab("生成控制"),   [(gen_keys,  P("tag_gen"),  "🟠  生成控制参数")])
        self.render_tab(self.tabview.tab("其他参数"),   [(other_keys, P("tag_other"), "🟢  其他参数")])

        # ── 命令行 Tab ────────────────────────────────────────────────────────
        cmd_tab = self.tabview.tab("命令行")

        cmd_label = ctk.CTkLabel(cmd_tab, text="生成的命令行",
                                 font=(FONT_FAMILY, 12, "bold"), anchor="w")
        self._reg(cmd_label, text_color="accent_blue")
        cmd_label.pack(fill="x", padx=8, pady=(8, 4))

        self.cmd_textbox = ctk.CTkTextbox(
            cmd_tab, wrap="word", font=(FONT_MONO, 12),
            border_width=1, corner_radius=8, height=220,
        )
        self._reg(self.cmd_textbox,
                  fg_color="bg_card", text_color="accent_blue", border_color="border")
        self.cmd_textbox.pack(fill="x", padx=8, pady=(0, 8))

        btn_row = ctk.CTkFrame(cmd_tab, fg_color="transparent")
        btn_row.pack(padx=8, pady=(0, 8), fill="x")

        save_btn = ctk.CTkButton(
            btn_row, text="💾  保存配置", width=130, height=32,
            font=(FONT_FAMILY, 13),
            fg_color=P("accent_blue"), hover_color="#3a7de0",
            corner_radius=7, command=self.save_named_config,
        )
        self._reg(save_btn, text_color="text_on_accent")
        save_btn.pack(side="left", padx=(0, 8))

        copy_btn = ctk.CTkButton(
            btn_row, text="📋  复制", width=90, height=32,
            font=(FONT_FAMILY, 13),
            hover_color=P("border"), border_width=1, corner_radius=7,
            command=lambda: (
                self.clipboard_clear(),
                self.clipboard_append(self.cmd_textbox.get("1.0", "end").strip())
            ),
        )
        self._reg(copy_btn, fg_color="bg_input", border_color="border",
                  text_color="text_on_light")
        copy_btn.pack(side="left")

        # 已保存配置清单
        sep2 = ctk.CTkFrame(cmd_tab, height=1)
        self._reg(sep2, fg_color="border")
        sep2.pack(fill="x", padx=8, pady=(4, 8))

        cfg_label = ctk.CTkLabel(cmd_tab, text="已保存的配置",
                                 font=(FONT_FAMILY, 12, "bold"), anchor="w")
        self._reg(cfg_label, text_color="accent_blue")
        cfg_label.pack(fill="x", padx=8, pady=(0, 4))

        self.config_list_frame = ctk.CTkScrollableFrame(cmd_tab, fg_color=P("bg_deep"))
        self._reg(self.config_list_frame, fg_color="bg_deep")
        self.config_list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.load_config_list()

        # ── 联动逻辑 ──────────────────────────────────────────────────────────
        def update_spec_params_state():
            is_on = self.inputs["spec_type"].get()
            state = "normal" if is_on else "disabled"
            for k in ["spec_draft_n_max", "spec_draft_p_min"]:
                self.inputs[k].configure(state=state)

        self.inputs["spec_type"].configure(command=update_spec_params_state)
        update_spec_params_state()

        # 实时更新命令行
        for key, widget in self.inputs.items():
            if isinstance(widget, ctk.CTkEntry):
                widget.bind("<KeyRelease>", lambda e: self.update_command_display())
            elif isinstance(widget, ctk.CTkSwitch):
                orig = widget.cget("command")
                def make_cmd(original):
                    return lambda: (original() if original else None,
                                    self.update_command_display())
                widget.configure(command=make_cmd(orig))

        self.update_command_display()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 初始主题应用
        self.configure(fg_color=P("bg_deep"))

    # ── 修复标签页文字颜色 ─────────────────────────────────────────────────────
    def _fix_tab_text_colors(self):
        """CTkSegmentedButton 默认文字色 #DCE4EE 在浅色下看不清，需手动设置"""
        try:
            sb = self.tabview._segmented_button
            tc = P("text_primary")   # 选中标签文字色
            utc = P("text_primary")  # 未选中标签文字色
            # 更新内部颜色列表（影响后续创建/重绘）
            sb._sb_text_color = [utc, utc]
            # 立即刷新已有按钮
            for name, btn in sb._buttons_dict.items():
                if name == sb._current_value:
                    btn.configure(text_color=tc)
                else:
                    btn.configure(text_color=utc)
        except Exception:
            pass

    # ── 主题切换 ───────────────────────────────────────────────────────────────
    def _highlight_active_theme_btn(self, mode):
        """高亮当前选中的主题按钮"""
        for btn, btn_mode in self._theme_btns:
            if btn_mode == mode:
                btn.configure(fg_color=P("tab_selected_bg"),
                              border_color=P("tab_selected_bg"))
            else:
                btn.configure(fg_color="transparent",
                              border_color=P("theme_btn_border"))

    def change_theme(self, mode):
        ctk.set_appearance_mode(mode)
        # 高亮当前主题按钮
        self._highlight_active_theme_btn(mode)
        # 刷新所有注册控件的颜色
        for widget, color_map in self._theme_widgets:
            self._apply_colors(widget, color_map)
        # 刷新窗口自身背景
        self.configure(fg_color=P("bg_deep"))
        # 刷新 StatusDot 背景（tk.Canvas 不在 _reg 体系中）
        try:
            self.status_dot.configure(bg=P("bg_card"))
        except Exception:
            pass
        # 刷新主题切换按钮边框
        try:
            for btn, _ in self._theme_btns:
                btn.configure(hover_color=P("bg_input"))
        except Exception:
            pass
        # 刷新 TabView 分段按钮颜色
        try:
            sb = self.tabview._segmented_button
            sb.configure(
                fg_color=P("bg_card"),
                selected_color=P("tab_selected_bg"),
                selected_hover_color=P("tab_selected_hover_bg"),
                unselected_color=P("bg_card"),
                unselected_hover_color=P("bg_input"),
            )
        except Exception:
            pass
        # 刷新 Tab 标签页内容区背景
        try:
            for tab_name in ["核心启动参数", "硬件加速", "生成控制", "其他参数", "命令行"]:
                tab_frame = self.tabview.tab(tab_name)
                tab_frame.configure(fg_color=P("bg_deep"))
        except Exception:
            pass
        # 刷新配置清单滚动区域背景
        try:
            bg = P("bg_deep")
            self.config_list_frame.configure(fg_color=bg)
            self.config_list_frame._parent_frame.configure(fg_color=bg)
            self.config_list_frame._parent_canvas.configure(bg=bg)
        except Exception:
            pass
        # 刷新命令行文本框内部画布
        try:
            self.cmd_textbox.configure(fg_color=P("bg_card"))
        except Exception:
            pass
        # 刷新选项卡内滚动框架背景
        try:
            bg = P("bg_deep")
            for sf in self._tab_scroll_frames:
                sf.configure(fg_color=bg)
                sf._parent_frame.configure(fg_color=bg)
                sf._parent_canvas.configure(bg=bg)
        except Exception:
            pass
        # 刷新 Tab 标签页文字颜色
        self._fix_tab_text_colors()

    # ── Tab 渲染 ───────────────────────────────────────────────────────────────
    def render_tab(self, tab_frame, config_blocks):
        scroll = ctk.CTkScrollableFrame(tab_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._tab_scroll_frames.append(scroll)

        for keys, color, title in config_blocks:
            # 外层容器
            outer = ctk.CTkFrame(scroll, fg_color="transparent")
            outer.pack(fill="x", padx=6, pady=6)

            # 左侧色条
            ctk.CTkFrame(outer, width=4, fg_color=color,
                         corner_radius=0).pack(side="left", fill="y")

            # 卡片容器
            card = ctk.CTkFrame(outer, border_width=0, corner_radius=6)
            self._reg(card, fg_color="bg_card")
            card.pack(side="left", fill="both", expand=True)

            # 卡片标题行
            title_row = ctk.CTkFrame(card, fg_color="transparent")
            title_row.pack(fill="x", padx=12, pady=(10, 4))

            ctk.CTkLabel(
                title_row, text=title,
                font=(FONT_FAMILY, 13, "bold"),
                text_color=color, anchor="w",
            ).pack(side="left")

            # 分隔线
            divider = ctk.CTkFrame(card, height=1)
            self._reg(divider, fg_color="border")
            divider.pack(fill="x", padx=12, pady=(0, 4))

            for item in self.config_schema:
                if item["key"] in keys:
                    self.create_param_row(card, item)

            # 底部留白
            ctk.CTkFrame(card, height=16, fg_color="transparent").pack()

    def create_param_row(self, parent, item):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=5)

        # 标签
        lbl = ctk.CTkLabel(
            row, text=item["label"], width=195, anchor="w",
            font=(FONT_FAMILY, 12))
        self._reg(lbl, text_color="accent_blue")
        lbl.pack(side="left")

        # 帮助图标
        help_lbl = ctk.CTkLabel(
            row, text="?", width=20, height=20,
            font=(FONT_FAMILY, 10, "bold"), corner_radius=10)
        self._reg(help_lbl, text_color="accent_blue", fg_color="bg_input")
        help_lbl.pack(side="left", padx=(0, 8))
        ModernTooltip(help_lbl, item["help"]).bind_tips()

        if item["type"] == "entry":
            if item["key"] in ("model_path", "mmproj", "model_draft"):
                ec = ctk.CTkFrame(row, fg_color="transparent")
                ec.pack(side="right", expand=True, fill="x")

                entry = ctk.CTkEntry(
                    ec, border_width=1, corner_radius=6,
                    placeholder_text="选择或粘贴 .gguf 路径…")
                self._reg(entry, fg_color="bg_input", border_color="border",
                          text_color="text_primary")
                entry.insert(0, item["default"])
                entry.pack(side="left", expand=True, fill="x", padx=(0, 6))

                browse_btn = ctk.CTkButton(
                    ec, text="…", width=32, height=28,
                    font=(FONT_FAMILY, 13),
                    hover_color=P("border"), border_width=1, corner_radius=6,
                    command=lambda e=entry: self.browse_file(e))
                self._reg(browse_btn, fg_color="bg_input", border_color="border")
                browse_btn.pack(side="right")
                self.inputs[item["key"]] = entry
            else:
                entry = ctk.CTkEntry(
                    row, width=220, border_width=1, corner_radius=6)
                self._reg(entry, fg_color="bg_input", border_color="border",
                          text_color="text_primary")
                entry.insert(0, item["default"])
                entry.pack(side="right", expand=True, fill="x")
                self.inputs[item["key"]] = entry
        else:
            switch = ctk.CTkSwitch(
                row, text="",
                button_color="#ffffff", button_hover_color="#e0e0e0",
                border_width=2, border_color=P("border"))
            self._reg(switch, progress_color="accent_blue", border_color="border")
            if item["default"]:
                switch.select()
            switch.pack(side="right")
            self.inputs[item["key"]] = switch

    # ── 已保存配置管理 ─────────────────────────────────────────────────────────
    def save_named_config(self):
        dialog = ctk.CTkInputDialog(text="请输入配置名称:", title="保存配置")
        name = dialog.get_input()
        if not name:
            return
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
        messagebox.showinfo("成功", f'配置 "{name}" 已保存')
        self.load_config_list()

    def load_config_list(self):
        for w in self.config_list_frame.winfo_children():
            w.destroy()

        list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_list.json")
        if not os.path.exists(list_path):
            lbl = ctk.CTkLabel(self.config_list_frame,
                               text='暂无保存的配置，请在"命令行"选项卡中保存配置。',
                               font=(FONT_FAMILY, 12))
            self._reg(lbl, text_color="text_muted")
            lbl.pack(pady=20)
            return

        try:
            with open(list_path, "r", encoding="utf-8") as f:
                config_list = json.load(f)
        except Exception:
            config_list = {}

        if not config_list:
            lbl = ctk.CTkLabel(self.config_list_frame, text="暂无保存的配置。",
                               font=(FONT_FAMILY, 12))
            self._reg(lbl, text_color="text_muted")
            lbl.pack(pady=20)
            return

        names = list(config_list.keys())
        for i in range(0, len(names), 3):
            row = ctk.CTkFrame(self.config_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=3, anchor="w")
            for j in range(3):
                if i + j < len(names):
                    n = names[i + j]
                    btn = ctk.CTkButton(
                        row, text=n, height=30, width=160,
                        font=(FONT_FAMILY, 12),
                        hover_color=P("border"), border_width=1, corner_radius=6,
                        command=lambda _n=n: self.show_config_action_dialog(_n))
                    self._reg(btn, fg_color="bg_input", border_color="border",
                              text_color="text_on_light")
                    btn.pack(side="left", padx=3)

    def apply_config(self, name):
        list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_list.json")
        try:
            with open(list_path, "r", encoding="utf-8") as f:
                config_list = json.load(f)
            config = config_list.get(name)
            if config:
                for key, value in config.items():
                    if key in self.inputs:
                        w = self.inputs[key]
                        if isinstance(w, ctk.CTkEntry):
                            w.delete(0, "end")
                            w.insert(0, str(value))
                        elif isinstance(w, ctk.CTkSwitch):
                            w.select() if value else w.deselect()
                self.update_command_display()
                messagebox.showinfo("成功", f"已加载配置: {name}")
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {e}")

    def overwrite_config(self, name):
        list_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_list.json")
        config = {}
        for key, widget in self.inputs.items():
            if isinstance(widget, ctk.CTkEntry):
                config[key] = widget.get().strip()
            elif isinstance(widget, ctk.CTkSwitch):
                config[key] = widget.get()
        try:
            config_list = {}
            if os.path.exists(list_path):
                with open(list_path, "r", encoding="utf-8") as f:
                    config_list = json.load(f)
            config_list[name] = config
            with open(list_path, "w", encoding="utf-8") as f:
                json.dump(config_list, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("成功", f"已将当前配置覆盖保存到: {name}")
            self.load_config_list()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    def show_config_action_dialog(self, name):
        dialog = ctk.CTkToplevel(self)
        dialog.title("配置操作")
        dialog.geometry("360x160")
        self._reg(dialog, fg_color="bg_card")  # type: ignore
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        dlg_lbl = ctk.CTkLabel(dialog, text=f"📄  {name}",
                                font=(FONT_FAMILY, 13, "bold"))
        self._reg(dlg_lbl, text_color="text_primary")
        dlg_lbl.pack(pady=(20, 12))

        bf = ctk.CTkFrame(dialog, fg_color="transparent")
        bf.pack()

        save_btn = ctk.CTkButton(bf, text="保存", width=90, height=32,
                      font=(FONT_FAMILY, 13),
                      fg_color=P("accent_blue"), hover_color="#3a7de0",
                      corner_radius=7,
                      command=lambda: (self.overwrite_config(name), dialog.destroy()),
                      )
        self._reg(save_btn, text_color="text_on_accent")
        save_btn.pack(side="left", padx=8)

        load_btn = ctk.CTkButton(bf, text="加载", width=90, height=32,
                      font=(FONT_FAMILY, 13),
                      fg_color=P("accent_green"), hover_color="#1a9c4c",
                      corner_radius=7,
                      command=lambda: (self.apply_config(name), dialog.destroy()),
                      )
        self._reg(load_btn, text_color="text_on_accent")
        load_btn.pack(side="left", padx=8)

        del_btn = ctk.CTkButton(bf, text="删除", width=90, height=32,
                      font=(FONT_FAMILY, 13),
                      fg_color=P("accent_red"), hover_color="#c0392b",
                      corner_radius=7,
                      command=lambda: (self.delete_config(name), dialog.destroy()),
                      )
        self._reg(del_btn, text_color="text_on_accent")
        del_btn.pack(side="left", padx=8)

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

    # ── 命令行展示 ─────────────────────────────────────────────────────────────
    def update_command_display(self):
        try:
            cmd = self.build_command()
            self.cmd_textbox.configure(state="normal")
            self.cmd_textbox.delete("1.0", "end")
            if cmd:
                self.cmd_textbox.insert("1.0", " ".join(cmd))
            else:
                self.cmd_textbox.insert("1.0", "请检查必填项（如模型路径）…")
            self.cmd_textbox.configure(state="disabled")
        except Exception:
            pass

    def build_command(self):
        try:
            cmd = ["llama-server"]

            def add(flag, key):
                val = self.inputs[key].get().strip()
                if val:
                    cmd.extend([flag, val])

            model_path = self.inputs["model_path"].get().strip()
            if model_path:
                if not os.path.exists(model_path):
                    raise ValueError(f"找不到模型文件: {model_path}")
                cmd.extend(["-m", model_path])

            add("--mmproj", "mmproj")
            add("--model-draft", "model_draft")

            add("--host", "host")
            add("--port", "port")
            add("-c", "ctx_size")

            api_key = self.inputs["api_key"].get().strip()
            if api_key:
                cmd.extend(["--api-key", api_key])

            add("-ngl", "ngl")
            add("--tensor-split", "split")

            if self.inputs["fa"].get():
                cmd.extend(["--flash-attn", "on"])

            add("--threads", "threads")
            add("-tb", "tb")
            add("-b", "batch_size")

            if self.inputs["no_mmap"].get():
                cmd.append("--no-mmap")
            if self.inputs["mlock"].get():
                cmd.append("--mlock")

            add("--min-p", "min_p")
            add("--temp", "temp")
            add("--top-k", "top_k")
            add("--top-p", "top_p")
            add("--repeat-penalty", "repeat_penalty")
            add("--cache-type-k", "cache_type_k")
            add("--cache-type-v", "cache_type_v")

            if self.inputs["chat_template_kwargs"].get():
                cmd.extend(["--chat-template-kwargs", '{"enable_thinking":false}'])

            if self.inputs["jinja"].get():
                cmd.append("--jinja")

            if self.inputs["spec_type"].get():
                cmd.extend(["--spec-type", "draft-mtp"])
                add("--spec-draft-n-max", "spec_draft_n_max")
                add("--spec-draft-p-min", "spec_draft_p_min")

            if self.inputs["metrics"].get():
                cmd.append("--metrics")

            add("--slots", "slots")

            if self.inputs["embedding"].get():
                cmd.append("--embedding")

            add("--parallel", "parallel")

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

    # ── 服务器控制 ─────────────────────────────────────────────────────────────
    def start_server_thread(self):
        self.save_config()
        self.update_target_url()
        cmd = self.build_command()
        if not cmd:
            return

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_dot.set_state("starting")
        self.status_label.configure(text="正在启动…",
                                    text_color=P("accent_orange"))

        threading.Thread(target=self.run_server, args=(cmd,), daemon=True).start()

    def open_edge_browser(self):
        try:
            if platform.system() == "Windows":
                subprocess.Popen(f"start msedge {self.target_url}", shell=True)
            else:
                webbrowser.open(self.target_url)
        except Exception:
            webbrowser.open(self.target_url)

    def run_server(self, cmd):
        ready_detected = False
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, shell=False, bufsize=1, creationflags=creationflags,
            )
            for line in self.process.stdout:
                clean = line.strip()
                print(f"[Server] {clean}")
                if not ready_detected and self.target_url in clean:
                    ready_detected = True
                    self.after(0, lambda: (
                        self.status_dot.set_state("running"),
                        self.status_label.configure(
                            text="运行中 · 已就绪",
                            text_color=P("accent_green")),
                    ))
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
        self.status_dot.set_state("stopped")
        self.status_label.configure(text="已停止", text_color=P("text_muted"))
        messagebox.showinfo("提示", "Server 进程已结束")

    def stop_server(self):
        if self.process:
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                shell=True,
            )
            print("🛑 已强制停止服务器")


if __name__ == "__main__":
    app = LlamaServerApp()
    app.mainloop()
