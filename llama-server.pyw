import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import threading
import os
import sys
import webbrowser
import platform
import json

# ── 主题与外观 ────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ── 全局设计 Token ────────────────────────────────────────────────────────────
FONT_FAMILY = "Microsoft YaHei UI"
FONT_MONO = "Cascadia Code"
FONT_EMOJI = "Segoe UI Emoji"

# 字号层级
FONT_SIZE_TITLE     = 18
FONT_SIZE_SUBTITLE  = 13
FONT_SIZE_BODY      = 13
FONT_SIZE_BODY_BOLD = 13
FONT_SIZE_CAPTION   = 12
FONT_SIZE_SMALL     = 11
FONT_SIZE_TINY      = 10

# 圆角
RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 10
RADIUS_XL = 12

# 间距
PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 20

# 控件尺寸
BTN_HEIGHT_SM  = 30
BTN_HEIGHT_MD  = 36
BTN_HEIGHT_LG  = 40
ENTRY_HEIGHT   = 34
HEADER_HEIGHT  = 60
FOOTER_HEIGHT  = 58
TAB_BTN_HEIGHT = 36

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
CONFIG_LIST_PATH = os.path.join(APP_DIR, "config_list.json")

# 双主题色板
THEMES = {
    "Dark": {
        "bg_deep":       "#0d1117",
        "bg_card":       "#161b22",
        "bg_input":      "#1c2333",
        "border":        "#30363d",
        "accent_blue":   "#58a6ff",
        "accent_green":  "#3fb950",
        "accent_red":    "#f85149",
        "accent_orange": "#d29922",
        "accent_purple": "#bc8cff",
        "text_primary":  "#e6edf3",
        "text_muted":    "#7d8590",
        "text_on_accent":"#ffffff",
        "text_on_light": "#e6edf3",
        "tab_selected_bg":        "#58a6ff",
        "tab_selected_hover_bg":  "#79b8ff",
        "theme_btn_border":       "#484f58",
        "tag_core":  "#ff7b72",
        "tag_hw":    "#79c0ff",
        "tag_gen":   "#d29922",
        "tag_other": "#56d364",
        "card_hover":  "#1c2333",
        "shadow":      "#000000",
    },
    "Light": {
        "bg_deep":       "#f6f8fa",
        "bg_card":       "#ffffff",
        "bg_input":      "#f6f8fa",
        "border":        "#d0d7de",
        "accent_blue":   "#0969da",
        "accent_green":  "#1a7f37",
        "accent_red":    "#cf222e",
        "accent_orange": "#9a6700",
        "accent_purple": "#8250df",
        "text_primary":  "#1f2328",
        "text_muted":    "#656d76",
        "text_on_accent":"#ffffff",
        "text_on_light": "#1f2328",
        "tab_selected_bg":        "#0969da",
        "tab_selected_hover_bg":  "#218bff",
        "theme_btn_border":       "#d0d7de",
        "tag_core":  "#cf222e",
        "tag_hw":    "#0969da",
        "tag_gen":   "#9a6700",
        "tag_other": "#1a7f37",
        "card_hover":  "#f6f8fa",
        "shadow":      "#d0d7de",
    },
}

TAB_NAMES = ("核心启动参数", "硬件加速", "生成控制", "其他参数", "命令行")

# 参数分类
PARAM_GROUPS = {
    "核心启动参数": [
        ({"model_path", "mmproj", "model_draft", "ctx_size"}, "tag_core", "🔴  核心启动参数（必选）"),
        ({"spec_type", "spec_draft_n_max", "spec_draft_p_min"}, "accent_orange", "🚀  MTP / DFlash 推测解码"),
    ],
    "硬件加速": [
        ({"ngl", "split", "sm", "fa", "threads", "tb", "batch_size", "no_mmap", "mlock"}, "tag_hw", "🔵  硬件加速与性能"),
    ],
    "生成控制": [
        ({"min_p", "metrics", "slots", "temp", "top_k", "top_p",
          "repeat_penalty", "cache_type_k", "cache_type_v",
          "chat_template_kwargs", "jinja", "reasoning"}, "tag_gen", "🟠  生成控制参数"),
    ],
    "其他参数": [
        ({"host", "port", "api_key", "auto_open", "embedding",
          "parallel", "log_file"}, "tag_other", "🟢  其他参数"),
    ],
}

CONFIG_SCHEMA = [
    {"label": "模型路径 (-m)",               "key": "model_path",           "type": "entry",   "default": "",       "help": "GGUF 模型的完整文件路径"},
    {"label": "多模态投影 (-mmproj)",         "key": "mmproj",              "type": "entry",   "default": "",       "help": "多模态投影模型的 GGUF 文件路径"},
    {"label": "草稿模型 (--model-draft)",     "key": "model_draft",         "type": "entry",   "default": "",       "help": "推测解码使用的草稿模型文件路径 (GGUF)"},
    {"label": "监听地址 (--host)",            "key": "host",                "type": "entry",   "default": "127.0.0.1", "help": "监听的 IP 地址"},
    {"label": "监听端口 (--port)",            "key": "port",                "type": "entry",   "default": "8080",   "help": "监听的端口号"},
    {"label": "上下文大小 (-c)",              "key": "ctx_size",            "type": "entry",   "default": "4096",   "help": "提示词和响应的最大上下文长度"},
    {"label": "API Key (--api-key)",         "key": "api_key",             "type": "entry",   "default": "sk-123456", "help": "访问 API 所需的密钥"},
    {"label": "并行处理数 (--parallel)",      "key": "parallel",            "type": "entry",   "default": "1",      "help": "并行处理的请求数量"},
    {"label": "日志文件 (--log-file)",        "key": "log_file",            "type": "switch",  "default": False,    "help": "开启后将日志输出到 llama-server.log"},
    {"label": "GPU层数 (-ngl)",              "key": "ngl",                 "type": "entry",   "default": "99",     "help": "将多少层模型卸载到 GPU (99 表示全量)"},
    {"label": "张量分割 (--tensor-split)",    "key": "split",               "type": "entry",   "default": "2,1",    "help": "多显卡权重分配，如 '1,1' 或 '2,1'"},
    {"label": "分割模式 (-sm)",               "key": "sm",                   "type": "option",  "default": "layer", "options": ["none", "layer", "row"], "help": "多 GPU 模型分割方式：none 不分割只用单卡，layer 按层分割（默认），row 按行分割"},
    {"label": "Flash Attention (--flash-attn)", "key": "fa",               "type": "switch",  "default": True,     "help": "启用 Flash Attention 加速计算"},
    {"label": "线程数 (--threads)",           "key": "threads",             "type": "entry",   "default": "10",     "help": "使用的 CPU 线程数"},
    {"label": "物理批大小 (-tb)",             "key": "tb",                  "type": "entry",   "default": "",       "help": "单次前向传播的最大 token 数 (ubatch)，影响显存占用和推理速度"},
    {"label": "批大小 (-b)",                 "key": "batch_size",          "type": "entry",   "default": "512",    "help": "每次处理的提示词批处理大小"},
    {"label": "禁止内存映射 (--no-mmap)",    "key": "no_mmap",             "type": "switch",  "default": True,     "help": "禁止内存映射，使用普通内存分配方式加载模型"},
    {"label": "锁定内存 (--mlock)",          "key": "mlock",               "type": "switch",  "default": True,     "help": "锁定物理内存，防止模型被交换到硬盘"},
    {"label": "Min-P 采样 (--min-p)",        "key": "min_p",               "type": "entry",   "default": "0.05",   "help": "采样过滤阈值，控制生成多样性"},
    {"label": "指标统计 (--metrics)",         "key": "metrics",             "type": "switch",  "default": True,     "help": "在服务器中开启性能指标统计"},
    {"label": "自动打开浏览器",              "key": "auto_open",           "type": "switch",  "default": True,     "help": "启动后自动在 Edge 浏览器中打开 API 界面"},
    {"label": "槽位数 (--slots)",            "key": "slots",               "type": "entry",   "default": "",       "help": "并发请求处理槽位数量"},
    {"label": "温度 (--temp)",               "key": "temp",                "type": "entry",   "default": "0.8",    "help": "控制生成随机性，值越高越有创意"},
    {"label": "Top-K (--top-k)",            "key": "top_k",               "type": "entry",   "default": "40",     "help": "仅从概率最高的 K 个词中采样"},
    {"label": "Top-P (--top-p)",            "key": "top_p",               "type": "entry",   "default": "0.95",   "help": "核采样阈值，累积概率达到此值时停止选择"},
    {"label": "重复惩罚 (--repeat-penalty)", "key": "repeat_penalty",      "type": "entry",   "default": "1.1",    "help": "对重复内容的惩罚力度，值越高越不易重复"},
    {"label": "K缓存类型 (--cache-type-k)", "key": "cache_type_k",        "type": "option",  "default": "q4_0", "options": ["q4_0", "q8_0"], "help": "KV 缓存中 K 的数据类型，q8_0 精度更高但占用更多显存"},
    {"label": "V缓存类型 (--cache-type-v)", "key": "cache_type_v",        "type": "option",  "default": "q4_0", "options": ["q4_0", "q8_0"], "help": "KV 缓存中 V 的数据类型，q8_0 精度更高但占用更多显存"},
    {"label": "关闭思考模式 (--chat-template-kwargs)", "key": "chat_template_kwargs", "type": "switch", "default": False, "help": "开启后传递 {\"enable_thinking\":false}，关闭模型的思考/推理模式"},
    {"label": "Jinja模板 (--jinja)",         "key": "jinja",               "type": "switch",  "default": False,    "help": "启用 Jinja2 模板引擎处理聊天模板，支持更复杂的模板语法"},
    {"label": "推理模式 (--reasoning)",        "key": "reasoning",           "type": "switch",  "default": False,    "help": "启用推理模式，模型会在回复中输出思考链（thinking/reasoning），适用于需要逻辑推导的复杂任务"},
    {"label": "推测解码类型 (--spec-type)",   "key": "spec_type",           "type": "option",  "default": "关闭", "options": ["关闭", "MTP (draft-mtp)", "DFlash (draft-dflash)"], "help": "选择推测解码类型：MTP 或 DFlash"},
    {"label": "推测草稿数量 (--spec-draft-n-max)", "key": "spec_draft_n_max", "type": "entry", "default": "2",   "help": "每次推测生成的最大草稿数量"},
    {"label": "推测草稿概率阈值 (--spec-draft-p-min)", "key": "spec_draft_p_min", "type": "entry", "default": "0.75", "help": "推测草稿的最小概率阈值"},
    {"label": "开启 Embedding (--embedding)","key": "embedding",           "type": "switch",  "default": False,    "help": "启用 Embedding API 支持"},
]

# 需要文件浏览按钮的 entry keys
BROWSE_KEYS = {"model_path", "mmproj", "model_draft"}


def P(key: str) -> str:
    """根据当前主题动态取色"""
    mode = ctk.get_appearance_mode()
    theme = THEMES.get(mode, THEMES["Dark"])
    return theme.get(key, THEMES["Dark"].get(key, "#000000"))


# ── 工具类 ────────────────────────────────────────────────────────────────────

class ModernTooltip:
    """轻量级悬浮提示"""

    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tw: tk.Toplevel | None = None

    def show(self):
        if self.tw or not self.text:
            return
        self.tw = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        tw.wm_attributes("-alpha", 0.96)

        x = self.widget.winfo_pointerx() + 14
        y = self.widget.winfo_pointery() + 14
        tw.wm_geometry(f"+{x}+{y}")

        mode = ctk.get_appearance_mode()
        bg = "#ffffff" if mode == "Light" else "#1c2333"
        fg = P("text_primary")
        border = P("accent_blue")

        outer = tk.Frame(tw, background=border, padx=1, pady=1)
        outer.pack()
        tk.Label(
            outer, text=self.text, justify="left",
            background=bg, foreground=fg,
            font=(FONT_FAMILY, FONT_SIZE_SMALL), padx=10, pady=6, wraplength=280,
        ).pack()

    def hide(self):
        if self.tw:
            self.tw.destroy()
            self.tw = None

    def bind_tips(self):
        self.widget.bind("<Enter>", lambda _: self.show())
        self.widget.bind("<Leave>", lambda _: self.hide())


class OptionSpinner(ctk.CTkFrame):
    """上下箭头选择器：左侧显示当前选项文字，右侧上下箭头切换"""

    def __init__(self, master, values: list[str], default: str = None, command=None, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._values = values
        self._index = 0
        self._command = command

        if default and default in values:
            self._index = values.index(default)

        # 左侧：带边框的选项文字
        self._value_frame = ctk.CTkFrame(
            self, corner_radius=RADIUS_SM, border_width=1,
            fg_color=P("bg_input"), border_color=P("border"))
        self._value_frame.pack(side="left", padx=(0, PAD_XS))

        self._label = ctk.CTkLabel(
            self._value_frame, text=self._values[self._index], anchor="w",
            font=(FONT_FAMILY, FONT_SIZE_CAPTION), width=50,
            fg_color="transparent")
        self._reg_label(self._label)
        self._label.pack(padx=6, pady=3)

        # 右侧：上下箭头垂直排列
        self._up_btn = ctk.CTkButton(
            self, text="▲", width=20, height=13,
            font=(FONT_FAMILY, 8), corner_radius=3,
            fg_color=P("bg_input"), hover_color=P("border"),
            border_width=1, border_color=P("border"),
            command=self._go_up)
        self._up_btn.pack(side="top", pady=(0, 1))

        self._down_btn = ctk.CTkButton(
            self, text="▼", width=20, height=13,
            font=(FONT_FAMILY, 8), corner_radius=3,
            fg_color=P("bg_input"), hover_color=P("border"),
            border_width=1, border_color=P("border"),
            command=self._go_down)
        self._down_btn.pack(side="top")

    def _reg_label(self, widget):
        """让外部 _reg 可以作用于内部 label"""
        self._label_ref = widget

    def _go_up(self):
        if self._index > 0:
            self._index -= 1
            self._update_display()

    def _go_down(self):
        if self._index < len(self._values) - 1:
            self._index += 1
            self._update_display()

    def _update_display(self):
        self._label.configure(text=self._values[self._index])
        if self._command:
            self._command(self._values[self._index])

    def get(self) -> str:
        return self._values[self._index]

    def set(self, value: str):
        if value in self._values:
            self._index = self._values.index(value)
            self._label.configure(text=value)


class StatusDot(tk.Canvas):
    """三态动画圆点：stopped / starting / running"""

    COLORS = {
        "stopped":  "#6b7280",
        "starting": "#f39c12",
        "running":  "#2ecc71",
    }

    def __init__(self, master, **kw):
        super().__init__(master, width=14, height=14,
                         bg=P("bg_card"), highlightthickness=0, **kw)
        self._state = "stopped"
        self._alpha = 1.0
        self._dir = -1
        self._dot = self.create_oval(2, 2, 12, 12, fill=self.COLORS["stopped"], outline="")
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


# ── 主程序 ────────────────────────────────────────────────────────────────────

class LlamaServerApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Llama Server 控制面板")
        self.geometry("800x720")
        self.minsize(740, 640)
        self.process: subprocess.Popen | None = None
        self.target_url = ""

        self.config_schema = CONFIG_SCHEMA

        self.load_config()
        self.inputs: dict[str, ctk.CTkEntry | ctk.CTkSwitch | OptionSpinner] = {}
        self._theme_widgets: list[tuple[tk.Widget, dict]] = []
        self._tab_scroll_frames: list[ctk.CTkScrollableFrame] = []
        self._theme_btns: list[tuple[ctk.CTkButton, str]] = []

        self.create_ui()

    # ── 配置持久化 ───────────────────────────────────────────────────────────
    def load_config(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for item in self.config_schema:
                if item["key"] in saved:
                    item["default"] = saved[item["key"]]
        except (json.JSONDecodeError, OSError):
            pass

    def save_config(self):
        config = self._collect_widget_values()
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except OSError:
            pass

    def _collect_widget_values(self) -> dict:
        """从所有 input 控件中收集当前值"""
        config = {}
        for key, widget in self.inputs.items():
            if isinstance(widget, ctk.CTkEntry):
                config[key] = widget.get().strip()
            elif isinstance(widget, ctk.CTkSwitch):
                config[key] = widget.get()
            elif isinstance(widget, OptionSpinner):
                config[key] = widget.get()
        return config

    def _apply_config_dict(self, config: dict):
        """将配置字典应用到所有 input 控件"""
        for key, value in config.items():
            if key not in self.inputs:
                continue
            w = self.inputs[key]
            if isinstance(w, ctk.CTkEntry):
                w.delete(0, "end")
                w.insert(0, str(value))
            elif isinstance(w, ctk.CTkSwitch):
                (w.select if value else w.deselect)()
            elif isinstance(w, OptionSpinner):
                w.set(str(value))

    def _load_named_config_list(self) -> dict:
        if not os.path.exists(CONFIG_LIST_PATH):
            return {}
        try:
            with open(CONFIG_LIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_named_config_list(self, data: dict):
        with open(CONFIG_LIST_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # ── 主题联动注册 ─────────────────────────────────────────────────────────
    def _reg(self, widget: tk.Widget, **color_map: str):
        """注册控件及其颜色映射，切换主题时自动更新"""
        self._theme_widgets.append((widget, color_map))
        self._apply_colors(widget, color_map)

    @staticmethod
    def _apply_colors(widget: tk.Widget, color_map: dict):
        for attr, key in color_map.items():
            try:
                widget.configure(**{attr: P(key)})
            except (tk.TclError, AttributeError):
                pass

    # ── UI 构建 ──────────────────────────────────────────────────────────────
    def create_ui(self):
        self._build_header()
        self._build_separator()
        self._build_footer()
        self._build_tabview()
        self._build_command_tab()
        self._setup_widget_bindings()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<<ServerStopped>>", lambda _: self.reset_ui())
        self.configure(fg_color=P("bg_deep"))

    # ── 顶部 Header ─────────────────────────────────────────────────────────
    def _build_header(self):
        header = ctk.CTkFrame(self, corner_radius=0, height=HEADER_HEIGHT)
        self._reg(header, fg_color="bg_card")
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # 左侧 Logo + 标题
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=PAD_XL)

        logo = ctk.CTkLabel(left, text="⚡", font=(FONT_EMOJI, 24))
        self._reg(logo, text_color="accent_blue")
        logo.pack(side="left", padx=(0, 10))

        title1 = ctk.CTkLabel(left, text="Llama Server",
                               font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"))
        self._reg(title1, text_color="text_primary")
        title1.pack(side="left")

        title2 = ctk.CTkLabel(left, text="  控制面板",
                               font=(FONT_FAMILY, FONT_SIZE_SUBTITLE))
        self._reg(title2, text_color="text_muted")
        title2.pack(side="left")

        # 右侧主题切换
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=PAD_LG)

        for mode, icon, tip in [("System", "💻", "跟随系统"),
                                ("Light", "☀️", "浅色"),
                                ("Dark", "🌙", "深色")]:
            btn = ctk.CTkButton(
                right, text=icon, width=36, height=30,
                font=(FONT_EMOJI, 16),
                fg_color="transparent",
                hover_color=P("bg_input"),
                border_width=1,
                border_color=P("theme_btn_border"),
                corner_radius=RADIUS_SM,
                command=lambda m=mode: self.change_theme(m),
            )
            btn.pack(side="left", padx=PAD_XS)
            ModernTooltip(btn, tip).bind_tips()
            self._theme_btns.append((btn, mode))

        self._highlight_active_theme_btn(ctk.get_appearance_mode())

    def _build_separator(self):
        sep = ctk.CTkFrame(self, height=1)
        self._reg(sep, fg_color="border")
        sep.pack(fill="x", pady=(PAD_XS, 0))

    # ── 底部状态栏 ───────────────────────────────────────────────────────────
    def _build_footer(self):
        sep = ctk.CTkFrame(self, height=1)
        self._reg(sep, fg_color="border")
        sep.pack(fill="x", side="bottom")

        self.footer = ctk.CTkFrame(self, corner_radius=0, height=FOOTER_HEIGHT)
        self._reg(self.footer, fg_color="bg_card")
        self.footer.pack(fill="x", side="bottom")
        self.footer.pack_propagate(False)

        # 状态指示
        status_area = ctk.CTkFrame(self.footer, fg_color="transparent")
        status_area.pack(side="left", padx=PAD_XL, pady=10)

        self.status_dot = StatusDot(status_area)
        self.status_dot.pack(side="left", padx=(0, PAD_SM))

        self.status_label = ctk.CTkLabel(
            status_area, text="已停止",
            font=(FONT_FAMILY, FONT_SIZE_BODY))
        self._reg(self.status_label, text_color="text_muted")
        self.status_label.pack(side="left")

        # 操作按钮
        btn_area = ctk.CTkFrame(self.footer, fg_color="transparent")
        btn_area.pack(side="right", padx=PAD_LG)

        self.stop_btn = ctk.CTkButton(
            btn_area, text="⏹  停止", width=120, height=BTN_HEIGHT_MD,
            font=(FONT_FAMILY, FONT_SIZE_BODY_BOLD, "bold"),
            fg_color=P("accent_red"), hover_color="#da3633",
            corner_radius=RADIUS_MD, state="disabled", command=self.stop_server,
        )
        self._reg(self.stop_btn, text_color="text_on_accent")
        self.stop_btn.pack(side="right", padx=(PAD_SM, 0))

        self.start_btn = ctk.CTkButton(
            btn_area, text="▶  启动 Server", width=150, height=BTN_HEIGHT_MD,
            font=(FONT_FAMILY, FONT_SIZE_BODY_BOLD, "bold"),
            fg_color=P("accent_green"), hover_color="#238636",
            corner_radius=RADIUS_MD, command=self.start_server_thread,
        )
        self._reg(self.start_btn, text_color="text_on_accent")
        self.start_btn.pack(side="right")

    # ── TabView 主体 ─────────────────────────────────────────────────────────
    def _build_tabview(self):
        self.tabview = ctk.CTkTabview(
            self,
            segmented_button_selected_hover_color=P("tab_selected_hover_bg"),
            border_width=0,
        )
        self.tabview.pack(padx=PAD_LG, pady=(PAD_SM, 0), fill="both", expand=True)
        self._reg(self.tabview,
                  fg_color="bg_deep",
                  segmented_button_fg_color="bg_card",
                  segmented_button_selected_color="tab_selected_bg",
                  segmented_button_unselected_color="bg_card",
                  segmented_button_unselected_hover_color="bg_input")

        self.tabview._segmented_button.configure(
            font=(FONT_FAMILY, FONT_SIZE_BODY_BOLD, "bold"), height=TAB_BTN_HEIGHT,
        )

        for tab in TAB_NAMES:
            self.tabview.add(tab)

        self._fix_tab_text_colors()

        for tab_name, blocks in PARAM_GROUPS.items():
            rendered = [
                (keys, P(color_key), title)
                for keys, color_key, title in blocks
            ]
            self.render_tab(self.tabview.tab(tab_name), rendered)

    # ── 命令行 Tab ───────────────────────────────────────────────────────────
    def _build_command_tab(self):
        cmd_tab = self.tabview.tab("命令行")

        cmd_label = ctk.CTkLabel(cmd_tab, text="生成的命令行",
                                 font=(FONT_FAMILY, FONT_SIZE_CAPTION, "bold"), anchor="w")
        self._reg(cmd_label, text_color="accent_blue")
        cmd_label.pack(fill="x", padx=PAD_MD, pady=(PAD_MD, PAD_SM))

        self.cmd_textbox = ctk.CTkTextbox(
            cmd_tab, wrap="word", font=(FONT_MONO, FONT_SIZE_CAPTION),
            border_width=1, corner_radius=RADIUS_MD, height=240,
        )
        self._reg(self.cmd_textbox,
                  fg_color="bg_card", text_color="accent_blue", border_color="border")
        self.cmd_textbox.pack(fill="x", padx=PAD_MD, pady=(0, PAD_MD))

        # 按钮行
        btn_row = ctk.CTkFrame(cmd_tab, fg_color="transparent")
        btn_row.pack(padx=PAD_MD, pady=(0, PAD_MD), fill="x")

        save_btn = ctk.CTkButton(
            btn_row, text="💾  保存配置", width=140, height=BTN_HEIGHT_SM,
            font=(FONT_FAMILY, FONT_SIZE_BODY),
            fg_color=P("accent_blue"), hover_color="#1f6feb",
            corner_radius=RADIUS_MD, command=self.save_named_config,
        )
        self._reg(save_btn, text_color="text_on_accent")
        save_btn.pack(side="left", padx=(0, PAD_SM))

        copy_btn = ctk.CTkButton(
            btn_row, text="📋  复制", width=100, height=BTN_HEIGHT_SM,
            font=(FONT_FAMILY, FONT_SIZE_BODY),
            hover_color=P("border"), border_width=1, corner_radius=RADIUS_MD,
            command=self._copy_command,
        )
        self._reg(copy_btn, fg_color="bg_input", border_color="border",
                  text_color="text_on_light")
        copy_btn.pack(side="left")

        # 分隔线
        sep = ctk.CTkFrame(cmd_tab, height=1)
        self._reg(sep, fg_color="border")
        sep.pack(fill="x", padx=PAD_MD, pady=(PAD_SM, PAD_MD))

        cfg_label = ctk.CTkLabel(cmd_tab, text="已保存的配置",
                                 font=(FONT_FAMILY, FONT_SIZE_CAPTION, "bold"), anchor="w")
        self._reg(cfg_label, text_color="accent_blue")
        cfg_label.pack(fill="x", padx=PAD_MD, pady=(0, PAD_SM))

        self.config_list_frame = ctk.CTkScrollableFrame(cmd_tab, fg_color=P("bg_deep"))
        self._reg(self.config_list_frame, fg_color="bg_deep")
        self.config_list_frame.pack(fill="both", expand=True, padx=PAD_MD, pady=(0, PAD_MD))
        self.load_config_list()

    def _copy_command(self):
        self.clipboard_clear()
        self.clipboard_append(self.cmd_textbox.get("1.0", "end").strip())

    # ── 控件事件绑定 ─────────────────────────────────────────────────────────
    def _setup_widget_bindings(self):
        """为所有 input 控件绑定实时更新事件"""
        for key, widget in self.inputs.items():
            if isinstance(widget, ctk.CTkEntry):
                widget.bind("<KeyRelease>", lambda _: self.update_command_display())
            elif isinstance(widget, ctk.CTkSwitch):
                orig_cmd = widget.cget("command")
                widget.configure(command=self._make_switch_handler(orig_cmd))
            # OptionSpinner 在创建时已绑定 command

        self.update_command_display()

    def _make_switch_handler(self, original):
        def handler():
            if original:
                original()
            self.update_command_display()
        return handler

    def _update_spec_params_state(self):
        state = "normal" if self.inputs["spec_type"].get() != "关闭" else "disabled"
        for k in ("spec_draft_n_max", "spec_draft_p_min"):
            self.inputs[k].configure(state=state)

    # ── 修复标签页文字颜色 ───────────────────────────────────────────────────
    def _fix_tab_text_colors(self):
        try:
            sb = self.tabview._segmented_button
            tc = P("text_primary")
            sb._sb_text_color = [tc, tc]
            for name, btn in sb._buttons_dict.items():
                btn.configure(text_color=tc)
        except (AttributeError, tk.TclError):
            pass

    # ── 主题切换 ─────────────────────────────────────────────────────────────
    def _highlight_active_theme_btn(self, mode: str):
        for btn, btn_mode in self._theme_btns:
            if btn_mode == mode:
                btn.configure(fg_color=P("tab_selected_bg"),
                              border_color=P("tab_selected_bg"))
            else:
                btn.configure(fg_color="transparent",
                              border_color=P("theme_btn_border"))

    def change_theme(self, mode: str):
        ctk.set_appearance_mode(mode)
        self._highlight_active_theme_btn(mode)
        self._refresh_theme_colors()
        self.configure(fg_color=P("bg_deep"))

    def _refresh_theme_colors(self):
        """刷新所有需要主题联动的控件颜色"""
        for widget, color_map in self._theme_widgets:
            self._apply_colors(widget, color_map)

        # StatusDot 背景
        try:
            self.status_dot.configure(bg=P("bg_card"))
        except (tk.TclError, AttributeError):
            pass

        # 主题按钮 hover 颜色
        for btn, _ in self._theme_btns:
            try:
                btn.configure(hover_color=P("bg_input"))
            except (tk.TclError, AttributeError):
                pass

        # TabView 分段按钮
        self._refresh_tabview_segmented_button()

        # Tab 内容区背景
        for tab_name in TAB_NAMES:
            try:
                self.tabview.tab(tab_name).configure(fg_color=P("bg_deep"))
            except (tk.TclError, AttributeError):
                pass

        # 配置清单滚动区域
        self._refresh_scroll_frame_bg(self.config_list_frame)

        # 命令行文本框
        try:
            self.cmd_textbox.configure(fg_color=P("bg_card"))
        except (tk.TclError, AttributeError):
            pass

        # 选项卡内滚动框架
        for sf in self._tab_scroll_frames:
            self._refresh_scroll_frame_bg(sf)

        self._fix_tab_text_colors()

    def _refresh_tabview_segmented_button(self):
        try:
            sb = self.tabview._segmented_button
            sb.configure(
                fg_color=P("bg_card"),
                selected_color=P("tab_selected_bg"),
                selected_hover_color=P("tab_selected_hover_bg"),
                unselected_color=P("bg_card"),
                unselected_hover_color=P("bg_input"),
            )
            # 更新分段按钮文字颜色
            tc = P("text_primary")
            sb._sb_text_color = [tc, tc]
            for name, btn in sb._buttons_dict.items():
                btn.configure(text_color=tc, font=(FONT_FAMILY, FONT_SIZE_BODY_BOLD, "bold"))
        except (AttributeError, tk.TclError):
            pass

    @staticmethod
    def _refresh_scroll_frame_bg(scroll_frame: ctk.CTkScrollableFrame):
        bg = P("bg_deep")
        try:
            scroll_frame.configure(fg_color=bg)
            scroll_frame._parent_frame.configure(fg_color=bg)
            scroll_frame._parent_canvas.configure(bg=bg)
        except (AttributeError, tk.TclError):
            pass

    # ── Tab 渲染 ─────────────────────────────────────────────────────────────
    def render_tab(self, tab_frame, config_blocks):
        scroll = ctk.CTkScrollableFrame(tab_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        self._tab_scroll_frames.append(scroll)

        for keys, color, title in config_blocks:
            outer = ctk.CTkFrame(scroll, fg_color="transparent")
            outer.pack(fill="x", padx=PAD_SM, pady=PAD_SM)

            # 左侧色条
            ctk.CTkFrame(outer, width=4, fg_color=color,
                         corner_radius=0).pack(side="left", fill="y")

            # 卡片容器
            card = ctk.CTkFrame(outer, border_width=0, corner_radius=RADIUS_LG)
            self._reg(card, fg_color="bg_card")
            card.pack(side="left", fill="both", expand=True)

            # 卡片标题行
            title_row = ctk.CTkFrame(card, fg_color="transparent")
            title_row.pack(fill="x", padx=PAD_MD, pady=(PAD_MD, PAD_SM))

            ctk.CTkLabel(
                title_row, text=title,
                font=(FONT_FAMILY, FONT_SIZE_BODY_BOLD, "bold"),
                text_color=color, anchor="w",
            ).pack(side="left")

            # 分隔线
            divider = ctk.CTkFrame(card, height=1)
            self._reg(divider, fg_color="border")
            divider.pack(fill="x", padx=PAD_MD, pady=(0, PAD_SM))

            for item in self.config_schema:
                if item["key"] in keys:
                    self._create_param_row(card, item)

            # 底部留白
            ctk.CTkFrame(card, height=PAD_MD, fg_color="transparent").pack()

    def _create_param_row(self, parent, item):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=PAD_MD, pady=4)

        lbl = ctk.CTkLabel(
            row, text=item["label"], width=290, anchor="w",
            font=(FONT_FAMILY, FONT_SIZE_CAPTION))
        self._reg(lbl, text_color="accent_blue")
        lbl.pack(side="left")

        help_lbl = ctk.CTkLabel(
            row, text="?", width=20, height=20,
            font=(FONT_FAMILY, FONT_SIZE_TINY, "bold"), corner_radius=10)
        self._reg(help_lbl, text_color="accent_blue", fg_color="bg_input")
        help_lbl.pack(side="left", padx=(0, PAD_SM))
        ModernTooltip(help_lbl, item["help"]).bind_tips()

        widget_type = item["type"]
        if widget_type == "entry":
            self._create_entry_widget(row, item)
        elif widget_type == "option":
            self._create_option_widget(row, item)
        else:
            self._create_switch_widget(row, item)

    def _create_entry_widget(self, row, item):
        key = item["key"]
        if key in BROWSE_KEYS:
            container = ctk.CTkFrame(row, fg_color="transparent")
            container.pack(side="right", expand=True, fill="x")

            entry = ctk.CTkEntry(
                container, border_width=1, corner_radius=RADIUS_SM, height=ENTRY_HEIGHT,
                placeholder_text="选择或粘贴 .gguf 路径…",
                font=(FONT_FAMILY, FONT_SIZE_CAPTION))
            self._reg(entry, fg_color="bg_input", border_color="border",
                      text_color="text_primary")
            entry.insert(0, item["default"])
            entry.pack(side="left", expand=True, fill="x", padx=(0, PAD_SM))

            browse_btn = ctk.CTkButton(
                container, text="…", width=34, height=ENTRY_HEIGHT,
                font=(FONT_FAMILY, FONT_SIZE_BODY),
                hover_color=P("border"), border_width=1, corner_radius=RADIUS_SM,
                command=lambda e=entry: self.browse_file(e))
            self._reg(browse_btn, fg_color="bg_input", border_color="border")
            browse_btn.pack(side="right")
            self.inputs[key] = entry
        else:
            entry = ctk.CTkEntry(row, width=240, border_width=1, corner_radius=RADIUS_SM,
                                  height=ENTRY_HEIGHT,
                                  font=(FONT_FAMILY, FONT_SIZE_CAPTION))
            self._reg(entry, fg_color="bg_input", border_color="border",
                      text_color="text_primary")
            entry.insert(0, item["default"])
            entry.pack(side="right", expand=True, fill="x")
            self.inputs[key] = entry

    def _create_option_widget(self, row, item):
        key = item["key"]

        def on_change(val):
            self.update_command_display()
            if key == "spec_type":
                self._update_spec_params_state()

        spinner = OptionSpinner(
            row, values=item["options"], default=item["default"],
            command=on_change)
        spinner.pack(side="left", padx=(PAD_SM, 0))
        self.inputs[key] = spinner

    def _create_switch_widget(self, row, item):
        switch = ctk.CTkSwitch(
            row, text="",
            button_color="#ffffff", button_hover_color="#e0e0e0",
            border_width=2, border_color=P("border"))
        self._reg(switch, progress_color="accent_blue", border_color="border")
        if item["default"]:
            switch.select()
        switch.pack(side="left", padx=(PAD_SM, 0))
        self.inputs[item["key"]] = switch

    # ── 已保存配置管理 ───────────────────────────────────────────────────────
    def save_named_config(self):
        dialog = ctk.CTkInputDialog(text="请输入配置名称:", title="保存配置")
        name = dialog.get_input()
        if not name or not name.strip():
            return

        config = self._collect_widget_values()
        config_list = self._load_named_config_list()
        config_list[name.strip()] = config
        self._save_named_config_list(config_list)
        messagebox.showinfo("成功", f'配置 "{name.strip()}" 已保存')
        self.load_config_list()

    def load_config_list(self):
        for w in self.config_list_frame.winfo_children():
            w.destroy()

        config_list = self._load_named_config_list()

        if not config_list:
            hint = '暂无保存的配置，请在"命令行"选项卡中保存配置。'
            lbl = ctk.CTkLabel(self.config_list_frame, text=hint,
                               font=(FONT_FAMILY, FONT_SIZE_CAPTION))
            self._reg(lbl, text_color="text_muted")
            lbl.pack(pady=24)
            return

        names = list(config_list.keys())
        for i in range(0, len(names), 3):
            row = ctk.CTkFrame(self.config_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=PAD_XS, anchor="w")
            for j in range(3):
                if i + j < len(names):
                    n = names[i + j]
                    btn = ctk.CTkButton(
                        row, text=n, height=BTN_HEIGHT_SM, width=170,
                        font=(FONT_FAMILY, FONT_SIZE_CAPTION),
                        hover_color=P("border"), border_width=1, corner_radius=RADIUS_SM,
                        command=lambda _n=n: self.show_config_action_dialog(_n))
                    self._reg(btn, fg_color="bg_input", border_color="border",
                              text_color="text_on_light")
                    btn.pack(side="left", padx=PAD_XS)

    def show_config_action_dialog(self, name):
        dialog = ctk.CTkToplevel(self)
        dialog.title("配置操作")
        dialog.geometry("380x170")
        self._reg(dialog, fg_color="bg_card")
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        dlg_lbl = ctk.CTkLabel(dialog, text=f"📄  {name}",
                                font=(FONT_FAMILY, FONT_SIZE_BODY_BOLD, "bold"))
        self._reg(dlg_lbl, text_color="text_primary")
        dlg_lbl.pack(pady=(20, PAD_LG))

        bf = ctk.CTkFrame(dialog, fg_color="transparent")
        bf.pack()

        btn_specs = [
            ("保存", "accent_blue",  "#1f6feb", lambda: (self.overwrite_config(name), dialog.destroy())),
            ("加载", "accent_green", "#238636", lambda: (self.apply_config(name), dialog.destroy())),
            ("删除", "accent_red",   "#da3633", lambda: (self.delete_config(name), dialog.destroy())),
        ]
        for text, color_key, hover, cmd in btn_specs:
            btn = ctk.CTkButton(
                bf, text=text, width=100, height=BTN_HEIGHT_SM,
                font=(FONT_FAMILY, FONT_SIZE_BODY),
                fg_color=P(color_key), hover_color=hover,
                corner_radius=RADIUS_MD, command=cmd)
            self._reg(btn, text_color="text_on_accent")
            btn.pack(side="left", padx=PAD_SM)

    def apply_config(self, name):
        config_list = self._load_named_config_list()
        config = config_list.get(name)
        if config:
            self._apply_config_dict(config)
            self.update_command_display()
            messagebox.showinfo("成功", f"已加载配置: {name}")
        else:
            messagebox.showwarning("警告", f"未找到配置: {name}")

    def overwrite_config(self, name):
        config = self._collect_widget_values()
        try:
            config_list = self._load_named_config_list()
            config_list[name] = config
            self._save_named_config_list(config_list)
            messagebox.showinfo("成功", f"已将当前配置覆盖保存到: {name}")
            self.load_config_list()
        except OSError as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    def delete_config(self, name):
        try:
            config_list = self._load_named_config_list()
            if name in config_list:
                del config_list[name]
                self._save_named_config_list(config_list)
                self.load_config_list()
                messagebox.showinfo("成功", f"已删除配置: {name}")
        except OSError as e:
            messagebox.showerror("错误", f"删除配置失败: {e}")

    # ── 命令行展示 ───────────────────────────────────────────────────────────
    def update_command_display(self):
        try:
            cmd = self.build_command()
            self.cmd_textbox.configure(state="normal")
            self.cmd_textbox.delete("1.0", "end")
            self.cmd_textbox.insert("1.0", " ".join(cmd) if cmd else "请检查必填项（如模型路径）…")
            self.cmd_textbox.configure(state="disabled")
        except (tk.TclError, AttributeError):
            pass

    def build_command(self) -> list[str] | None:
        try:
            cmd = ["llama-server"]

            def add(flag, key):
                val = self.inputs[key].get().strip()
                if val:
                    cmd.extend([flag, val])

            def add_flag(key):
                if self.inputs[key].get():
                    cmd.append(f"--{key.replace('_', '-')}")

            # 模型路径（必填）
            model_path = self.inputs["model_path"].get().strip()
            if not model_path:
                return cmd
            if not os.path.exists(model_path):
                raise ValueError(f"找不到模型文件: {model_path}")
            cmd.extend(["-m", model_path])

            # 可选路径参数
            add("--mmproj", "mmproj")
            add("--model-draft", "model_draft")

            # 网络与上下文
            add("--host", "host")
            add("--port", "port")
            add("-c", "ctx_size")

            api_key = self.inputs["api_key"].get().strip()
            if api_key:
                cmd.extend(["--api-key", api_key])

            # GPU 与性能
            add("-ngl", "ngl")
            add("--tensor-split", "split")
            add("-sm", "sm")

            if self.inputs["fa"].get():
                cmd.extend(["--flash-attn", "on"])

            add("--threads", "threads")
            add("-tb", "tb")
            add("-b", "batch_size")

            # 内存控制
            if self.inputs["no_mmap"].get():
                cmd.append("--no-mmap")
            if self.inputs["mlock"].get():
                cmd.append("--mlock")

            # 采样参数
            add("--min-p", "min_p")
            add("--temp", "temp")
            add("--top-k", "top_k")
            add("--top-p", "top_p")
            add("--repeat-penalty", "repeat_penalty")
            add("--cache-type-k", "cache_type_k")
            add("--cache-type-v", "cache_type_v")

            # 模板与思考
            if self.inputs["chat_template_kwargs"].get():
                cmd.extend(["--chat-template-kwargs", '{"enable_thinking":false}'])
            if self.inputs["jinja"].get():
                cmd.append("--jinja")

            # 推理模式
            if self.inputs["reasoning"].get():
                cmd.append("--reasoning")

            # 推测解码
            spec_type_val = self.inputs["spec_type"].get()
            if spec_type_val == "MTP (draft-mtp)":
                cmd.extend(["--spec-type", "draft-mtp"])
            elif spec_type_val == "DFlash (draft-dflash)":
                cmd.extend(["--spec-type", "draft-dflash"])
            if spec_type_val != "关闭":
                add("--spec-draft-n-max", "spec_draft_n_max")
                add("--spec-draft-p-min", "spec_draft_p_min")

            # 功能开关
            if self.inputs["metrics"].get():
                cmd.append("--metrics")
            add("--slots", "slots")
            if self.inputs["embedding"].get():
                cmd.append("--embedding")
            add("--parallel", "parallel")

            # 日志
            if self.inputs["log_file"].get():
                cmd.extend(["--log-file", self._resolve_log_path()])

            return cmd
        except ValueError as e:
            messagebox.showerror("配置错误", str(e))
            return None

    @staticmethod
    def _resolve_log_path() -> str:
        base_name = "llama-server.log"
        log_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else APP_DIR
        log_path = os.path.join(log_dir, base_name)

        if not os.path.exists(log_path):
            return log_path

        i = 1
        while True:
            name, ext = os.path.splitext(base_name)
            new_path = os.path.join(log_dir, f"{name}-{i}{ext}")
            if not os.path.exists(new_path):
                return new_path
            i += 1

    def browse_file(self, entry_widget: ctk.CTkEntry):
        file_path = filedialog.askopenfilename(
            title="选择模型文件",
            filetypes=[("GGUF Files", "*.gguf"), ("All Files", "*.*")],
        )
        if file_path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, file_path)

    # ── 服务器控制 ───────────────────────────────────────────────────────────
    def start_server_thread(self):
        self.save_config()
        host = self.inputs["host"].get().strip()
        port = self.inputs["port"].get().strip()
        self.target_url = f"http://{host}:{port}"

        cmd = self.build_command()
        if not cmd:
            return

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_dot.set_state("starting")
        self.status_label.configure(text="正在启动…", text_color=P("accent_orange"))

        threading.Thread(target=self.run_server, args=(cmd,), daemon=True).start()

    def open_edge_browser(self):
        try:
            if platform.system() == "Windows":
                subprocess.Popen(f"start msedge {self.target_url}", shell=True)
            else:
                webbrowser.open(self.target_url)
        except Exception:
            webbrowser.open(self.target_url)

    def run_server(self, cmd: list[str]):
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
                    self.after(0, self._on_server_ready)
                    if self.inputs["auto_open"].get():
                        self.after(0, self.open_edge_browser)
            self.process.wait()
        except Exception as e:
            print(f"❌ 错误: {e}")
        finally:
            self.process = None
            self.event_generate("<<ServerStopped>>")

    def _on_server_ready(self):
        self.status_dot.set_state("running")
        self.status_label.configure(text="运行中 · 已就绪", text_color=P("accent_green"))

    def reset_ui(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_dot.set_state("stopped")
        self.status_label.configure(text="已停止", text_color=P("text_muted"))

    def stop_server(self):
        if self.process:
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                shell=True,
            )
            print("🛑 已强制停止服务器")

    def on_closing(self):
        self.save_config()
        self.destroy()


if __name__ == "__main__":
    app = LlamaServerApp()
    app.mainloop()
