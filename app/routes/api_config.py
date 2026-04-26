import os
import sys
from flask import Blueprint, request, jsonify
from app.config import config_manager

api_config_bp = Blueprint('api_config', __name__)


@api_config_bp.route('/', methods=['GET'])
def get_config():
    return jsonify(config_manager.get_safe_config())


@api_config_bp.route('/', methods=['PUT'])
def update_config():
    data = request.get_json()
    if not data:
        return jsonify({'error': '无效的请求数据'}), 400

    current = config_manager.get()

    # Update obsidian config
    if 'obsidian' in data:
        for key in ('vault_path', 'products_folder'):
            if key in data['obsidian']:
                current['obsidian'][key] = data['obsidian'][key]

    # Update AI config
    if 'ai' in data:
        for key in ('base_url', 'api_key', 'model', 'max_tokens', 'temperature'):
            if key in data['ai']:
                # Don't overwrite with masked value
                if key == 'api_key' and '****' in str(data['ai'][key]):
                    continue
                current['ai'][key] = data['ai'][key]

    # Update recording config
    if 'recording' in data:
        if 'recording' not in current:
            current['recording'] = {}
        for key in ('hotkey_start', 'hotkey_stop', 'snipaste_path'):
            if key in data['recording']:
                current['recording'][key] = data['recording'][key]

    config_manager.save(current)
    return jsonify(config_manager.get_safe_config())


@api_config_bp.route('/validate-vault', methods=['POST'])
def validate_vault():
    data = request.get_json()
    vault_path = data.get('vault_path', '') if data else ''
    if not vault_path:
        return jsonify({'valid': False, 'message': '路径不能为空'})
    if os.path.isdir(vault_path):
        return jsonify({'valid': True, 'message': '路径有效'})
    return jsonify({'valid': False, 'message': '路径不存在或不是文件夹'})


@api_config_bp.route('/validate-snipaste', methods=['POST'])
def validate_snipaste():
    data = request.get_json()
    snipaste_path = data.get('snipaste_path', '') if data else ''

    if sys.platform == 'darwin':
        # macOS uses built-in screencapture
        return jsonify({'valid': True, 'message': '使用系统内置截图工具 (screencapture)'})

    # Windows: validate Snipaste path
    if not snipaste_path:
        return jsonify({'valid': False, 'message': '路径不能为空'})
    if not os.path.isfile(snipaste_path):
        return jsonify({'valid': False, 'message': '文件不存在'})
    if not snipaste_path.lower().endswith('.exe'):
        return jsonify({'valid': False, 'message': '请选择 Snipaste.exe 文件'})
    return jsonify({'valid': True, 'message': 'Snipaste 路径有效'})


@api_config_bp.route('/platform-info', methods=['GET'])
def platform_info():
    return jsonify({'platform': sys.platform})


@api_config_bp.route('/check-floating-deps', methods=['GET'])
def check_floating_deps():
    """Check whether floating window dependencies are installed."""
    deps = []

    # PyQt6
    try:
        import PyQt6.QtWidgets  # noqa: F401
        from PyQt6.QtCore import PYQT_VERSION_STR
        deps.append({'name': 'PyQt6', 'installed': True, 'version': PYQT_VERSION_STR,
                      'pip': 'pip install PyQt6'})
    except ImportError:
        deps.append({'name': 'PyQt6', 'installed': False, 'version': None,
                      'pip': 'pip install PyQt6'})

    # pynput
    try:
        import pynput  # noqa: F401
        ver = getattr(pynput, '__version__', 'unknown')
        deps.append({'name': 'pynput', 'installed': True, 'version': ver,
                      'pip': 'pip install pynput'})
    except ImportError:
        deps.append({'name': 'pynput', 'installed': False, 'version': None,
                      'pip': 'pip install pynput'})

    # Pillow
    try:
        from PIL import Image  # noqa: F401
        import PIL
        deps.append({'name': 'Pillow', 'installed': True, 'version': PIL.__version__,
                      'pip': 'pip install Pillow'})
    except ImportError:
        deps.append({'name': 'Pillow', 'installed': False, 'version': None,
                      'pip': 'pip install Pillow'})

    # macOS-specific
    if sys.platform == 'darwin':
        try:
            import Quartz  # noqa: F401
            deps.append({'name': 'pyobjc-Quartz', 'installed': True, 'version': 'OK',
                          'pip': 'pip install pyobjc-framework-Quartz'})
        except ImportError:
            deps.append({'name': 'pyobjc-Quartz', 'installed': False, 'version': None,
                          'pip': 'pip install pyobjc-framework-Quartz'})

    all_ok = all(d['installed'] for d in deps)
    return jsonify({'ready': all_ok, 'deps': deps})
