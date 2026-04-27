# PathMind / 路径智慧库

**自动录制产品路径 → AI 结构化分析 → 生成 RAG 就绪的知识库**

Automatically record product usage paths → AI-powered structured analysis → Generate RAG-ready knowledge base

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)]()
[![Download](https://img.shields.io/github/v/release/Cjayan/PathMind?label=Download&color=green)](https://github.com/Cjayan/PathMind/releases/latest)

> **Windows 用户可直接下载安装包，内嵌 Python 环境，开箱即用，无需任何配置：**
> **[>>> 下载 PathMind 最新版安装包 <<<](https://github.com/Cjayan/PathMind/releases/latest)**

---

## Why PathMind? / 为什么选择路径智慧库？

产品经理、测试工程师、UX 研究员在分析产品体验时面临一个共同问题：**记录散乱、分析耗时、知识无法复用**。PathMind 用一条自动化流水线解决这三个痛点：

PMs, QA engineers, and UX researchers share a common pain point: **scattered records, time-consuming analysis, and non-reusable knowledge**. PathMind solves all three with one automated pipeline:

```
  +-----------------+       +------------------+       +----------------------+
  |  1. Record      |  -->  |  2. AI Analyze   |  -->  |  3. Knowledge Base   |
  |  自动录制路径    |       |  AI 结构化分析    |       |  RAG 就绪知识库       |
  |                 |       |                  |       |                      |
  |  Screenshots    |       |  Interaction     |       |  Obsidian Markdown   |
  |  + Text desc    |       |  analysis, UX    |       |  with RAG metadata   |
  |  + Scores       |       |  scoring, and    |       |  ready for LLM       |
  |  per step       |       |  suggestions     |       |  retrieval           |
  +-----------------+       +------------------+       +----------------------+
```

> **不只是记录工具**：PathMind 的产出物是**结构化的、AI 可直接检索的知识库**，可以无缝接入 RAG 系统增强 LLM 回答质量，也可以用 Obsidian 手动浏览和管理。
>
> **More than a recording tool**: PathMind outputs a **structured, AI-retrievable knowledge base** that plugs directly into RAG pipelines to enhance LLM responses, and is also browsable in Obsidian.

---

## Three Core Capabilities / 三大核心能力

### 1. Automated Path Recording / 自动化路径录制

逐页面、逐步骤地记录产品使用路径，每一步包含截图 + 文字描述 + 评分。

- **悬浮窗录制** — 通过系统托盘打开置顶悬浮面板，可直接选择或新建流程，边操作边记录
- **自动录制模式** — 配置热键后，通过悬浮窗 REC 按钮或快捷键启动。每次鼠标左键点击自动截图，截图后输入标题或跳过即可继续，不理想的截图可在 Web 中删除
- **手动录制模式** — Ctrl+V 粘贴截图，输入描述和评分 (1-10)，精细控制每一步
- **多屏 DPI 适配** — 在不同分辨率屏幕间拖动悬浮窗自动适配

### 2. AI Structured Analysis / AI 结构化分析

调用 AI Vision 模型对每一步截图 + 描述进行**结构化专业分析**（需先在 **设置** 中配置 AI API）：

- **悬浮窗自动生成** — 悬浮窗录制模式下，每步保存后自动在后台调用 AI 生成评论，不阻塞录制流程
- **Web 端手动生成** — 在 Web 页面中可对单个步骤手动触发 AI 评论生成
- **流程 AI 总结** — 录制完成后一键生成整体流程分析报告，涵盖全局体验评估
- **后台异步 & 重试** — 失败自动重试（指数退避，最多 3 次）
- **结构化输出** — AI 结果按固定字段存储（交互描述、评分、改进建议等），便于检索和聚合

### 3. RAG-Ready Knowledge Base / RAG 就绪知识库

录制和分析的产出物不是孤立的笔记，而是**直接可用于 RAG 检索增强**的结构化知识库：

- **Obsidian 导出** — 一键导出为 Markdown + 图片到 Obsidian Vault，保留完整结构
- **RAG 元数据** — 每条记录包含产品名、流程名、步骤序号、AI 分析字段等结构化元数据，可直接被向量数据库索引
- **知识检索场景** — 接入 RAG 后，可实现："XX 产品的登录流程有哪些体验问题？""哪些步骤的评分低于 5 分？"等精准检索
- **人工友好** — 即使不接入 RAG，导出到 Obsidian 后也可用双链、标签、图谱等方式手动浏览管理

---

## Additional Features / 更多功能

| Category | Feature | Description |
|----------|---------|-------------|
| **Flow Management** | 拖拽排序、置顶、颜色标记（6 色） | 多维度组织和筛选流程 |
| **Full-text Search** | 按描述、备注、AI 评论内容搜索 | 快速定位历史记录 |
| **Data Sync** | ZIP 全量/增量导入导出 | 跨设备迁移，导入前自动备份 |
| **i18n** | 中英文界面一键切换 | 内置翻译字典，无需配置，离线可用 |
| **Beginner's Guide** | 新手指南弹窗 | 首次启动自动弹出，导航栏 "?" 可随时打开 |
| **Cross-platform** | Windows 安装包 / macOS 源码运行 | Windows 内嵌 Python，开箱即用；macOS 暂未经充分测试 |

---

## Important Notes / 重要提示

> **Environment Dependencies / 环境依赖：**
> - **Strong / 强依赖：** Python 3.10+, Windows 10/11 or macOS 12+
> - **Platform / 平台说明：** 目前仅在 **Windows** 上经过完整测试。macOS 支持为实验性质，源码可运行但未经充分测试，欢迎反馈问题。macOS support is experimental and not fully tested — issues and feedback are welcome.
> - **Floating Window / 悬浮窗依赖：** PyQt6 — 悬浮窗录制模式必需（`pip install PyQt6`）。Web 录制模式不需要。PyQt6 is required for floating window mode; web-based recording works without it.
> - **Optional / 可选：** [Snipaste](https://www.snipaste.com/) — 悬浮窗模式下增强截图体验（自动调用 Snipaste 截图），非必需。Optional but recommended for enhanced screenshot capture in floating window mode.
>
> **AI API Compatibility / AI 接口兼容性：**
> - 当前 Prompt 和响应解析**针对 LongCat (龙猫) 系列模型优化**（如 `LongCat-Flash-Omni`）
> - 使用其他 OpenAI 兼容 API（GPT-4o、Claude 等）时，**可能需要微调 Prompt 或解析逻辑**
> - 详见 `app/services/ai_service.py`
> - Currently optimized for **LongCat model family**. Other OpenAI-compatible APIs may require prompt/parsing adjustments.

---

## Quick Start / 快速开始

### Option 1: Windows Installer / Windows 安装包（推荐）

1. 从 [Releases](../../releases) 下载最新的 `PathMind_Setup_vX.X.X.exe`
2. 运行安装程序，按提示完成安装
3. 桌面快捷方式启动 → 自动打开浏览器 + 系统托盘图标常驻
4. 在**设置**页面配置 AI API（base_url, api_key, model）和录制热键
5. 首次打开会弹出新手指南，按指引操作即可快速上手

### Option 2: Run from Source / 源码运行

```bash
# Prerequisites: Python 3.10+, pip, PyQt6（悬浮窗/托盘必需）
git clone https://github.com/Cjayan/PathMind.git
cd PathMind
pip install -r requirements.txt
```

**启动方式（二选一）：**

| 方式 | 命令 | 说明 |
|---|---|---|
| **完整模式（推荐）** | 双击 `启动服务.bat` 或 `pythonw installer/launcher.pyw` | Web 服务 + 系统托盘 + 悬浮窗录制，支持全部功能 |
| **纯 Web 模式** | `python run.py` | 仅启动 Web 服务，无系统托盘和悬浮窗，适合仅需 Web 界面的场景 |

> **注意：** 悬浮窗录制、自动录制等核心功能依赖系统托盘，请使用**完整模式**启动。纯 Web 模式下这些功能不可用。

---

## Usage Workflow / 使用流程

### Standard Workflow / 标准流程

```
创建产品 → 新建流程 → 录制步骤（截图+描述+评分）→ AI 分析（悬浮窗自动/Web 手动）→ 完成录制 → 导出知识库
```

1. **创建产品** — 首页点击"新建产品"，对应你要分析的目标应用
2. **新建流程** — 进入产品页，为具体的使用路径创建流程（如"用户注册流程"）
3. **录制步骤** — 逐步上传截图、填写描述和评分；可手动触发 AI 生成单步评论（悬浮窗模式下保存后自动生成）
4. **完成录制** — 点击"完成录制"，可一键生成 AI 流程总结
5. **导出使用** — 导出到 Obsidian Vault，或通过 API 接入 RAG 系统

### Floating Window / 悬浮窗快捷录制

1. 通过 **系统托盘图标** 打开桌面悬浮窗（启动应用后托盘区会出现 PathMind 图标）
2. 在悬浮窗中 **选择产品和流程**（也可以直接新建流程）
3. **手动录制：** Ctrl+V 粘贴截图 → 输入描述 → 保存
4. **自动录制：** 需先在 [设置] 中配置开始/停止录制热键，然后通过悬浮窗 REC 按钮或快捷键启动
   - 录制期间 **每次鼠标左键点击** 都会触发截图（点击空白处也会截图）
   - 每次截图后弹出标题输入框，**输入步骤标题或跳过** 后才能继续下一次截图
   - 不理想的截图可以稍后在 Web 页面中删除
5. 录制完成后在 Web 界面查看完整的 AI 分析结果

### Data Migration / 跨设备迁移

在**设置 > 数据管理**中，支持 ZIP 格式全量/增量导入导出，导入前自动备份。

---

## Configuration / 配置

首次启动自动从 `config.yaml.example` 生成 `config.yaml`，也可在 Web 界面**设置**页面配置。

| Key | Description / 说明 | Default |
|---|---|---|
| `ai.base_url` | OpenAI-compatible API endpoint | `https://api.openai.com/v1` |
| `ai.api_key` | API key | (empty) |
| `ai.model` | Model name (must support Vision) | `gpt-4o` |
| `ai.max_tokens` | Max response tokens | `4096` |
| `ai.temperature` | Generation temperature | `0.7` |
| `obsidian.vault_path` | Obsidian Vault path / 知识库导出路径 | (empty) |
| `server.port` | Server port | `5000` |
| `recording.hotkey_start` | Start recording hotkey / 开始录制热键 | (empty) |
| `recording.hotkey_stop` | Stop recording hotkey / 停止录制热键 | (empty) |
| `recording.snipaste_path` | Snipaste executable path (Windows only) | (empty) |

---

## Adapting AI for Other Models / 适配其他 AI 模型

当前 AI 功能针对 LongCat 模型优化。使用其他模型需要修改：

1. **`app/services/ai_service.py`**
   - `_build_step_prompt()` — 单步评论 Prompt
   - `_build_summary_prompt()` — 流程总结 Prompt
   - Response parsing — 当前兼容 LongCat 的 JSON 数组返回格式
2. **`config.yaml`** — 修改 `ai.model` 为你的模型名称

---

## Project Structure / 项目结构

```
├── run.py                       # Entry point / 启动入口
├── config.yaml.example          # Config template / 配置模板
├── requirements.txt             # Python dependencies
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Config manager
│   ├── models/                  # Data models (Product, Flow, Step)
│   ├── routes/                  # API & page routes
│   ├── services/
│   │   ├── ai_service.py        # AI analysis & summary / AI 分析核心
│   │   ├── export_service.py    # Obsidian & RAG export / 知识库导出
│   │   ├── summary_service.py   # Flow summary generation / 流程总结
│   │   └── data_service.py      # Data sync & backup / 数据同步
│   ├── floating_window/         # PyQt6 floating window / 悬浮窗
│   │   ├── main_window.py       # Main floating window UI
│   │   ├── auto_recorder.py     # Auto recording logic / 自动录制
│   │   ├── ai_comment_worker.py # Background AI worker / AI 后台线程
│   │   └── screen_capture.py    # Multi-monitor screenshot / 截图
│   ├── platform/                # OS-specific code (Windows/macOS)
│   ├── templates/               # Jinja2 HTML templates
│   └── static/                  # Frontend assets (JS, CSS)
│       └── i18n/                # Translation dictionaries / 翻译字典
├── installer/                   # Installer build scripts / 安装包构建
└── data/                        # Runtime data (auto-generated)
    ├── app.db                   # SQLite database
    ├── uploads/                 # Screenshots
    └── backups/                 # Auto backups
```

---

## Tech Stack / 技术栈

| Layer | Technology |
|---|---|
| Backend | Flask 3.x, SQLAlchemy, SQLite |
| Frontend | Vanilla JS, Jinja2 Templates |
| Floating Window | PyQt6 |
| AI Integration | OpenAI-compatible API (Vision) |
| Screenshot | Pillow, Snipaste (optional), Quartz (macOS) |
| Auto Recording | pynput (mouse/keyboard listener) |
| Installer | NSIS (Windows) |

---

## Contributing / 贡献

欢迎提交 Issue 和 Pull Request!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

[MIT License](LICENSE)

---

**Author: Kai Xiao (Cjayan)**

*If this project helps you, consider giving it a star!*
*如果这个项目对你有帮助，欢迎点个 Star！*
