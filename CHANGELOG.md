# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-04-28

### Added
- **Beginner's Guide / 新手指南** — First-launch popup with 4-step guide covering workflow, floating window, auto-recording, and AI analysis. Click "?" in the nav bar to reopen anytime. / 首次启动自动弹出 4 步新手指南，导航栏 "?" 按钮可随时打开。
- **Chinese/English UI Switch / 中英文切换** — Click the language toggle button in the nav bar to instantly switch between Chinese and English. No API key required, works offline. / 导航栏一键切换中英文界面，无需配置，离线可用。
- **New Flow from Floating Window / 悬浮窗新建流程** — Create new flows directly in the floating window's flow selector dialog without switching back to the web page. / 在悬浮窗中直接新建流程，无需切换到 Web 页面。
- **Duplicate Flow Name Check / 同名流程检查** — Prevents creating flows with the same name under the same product, with both frontend and backend validation. / 同产品下禁止创建同名流程，前后端双重校验。

### Changed
- Beginner's guide content updated: corrected floating window launch method (via system tray), added detailed auto-recording screenshot instructions. / 更新新手指南内容：修正悬浮窗启动方式（通过系统托盘），新增自动录制截图详细说明。

### Removed
- Removed Baidu Translate API dependency. Language switching now uses a bundled static translation dictionary (`app/static/i18n/en.json`). / 移除百度翻译 API 依赖，改用内置静态翻译字典。

## [2.0.0] - 2026-04-27

### Added
- Project renamed from "产品使用路径知识库 / ProductKB" to **PathMind / 路径智慧库**
- Cross-platform support (macOS experimental)
- RAG-ready Obsidian export with structured metadata
- Auto-recording mode with global hotkeys and mouse click capture
- AI-powered step comments and flow summaries (OpenAI-compatible API)
- Full-text search across descriptions, notes, and AI comments
- ZIP-based data import/export with auto-backup
- Flow management: drag-sort, pin, 6-color tags
- NSIS Windows installer with embedded Python environment
