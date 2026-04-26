import os
import sys

# 确保脚本所在目录在 sys.path 中（嵌入式 Python 环境需要）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import config_manager


def main():
    application = create_app()
    config = config_manager.get()
    server = config.get('server', {})

    port = int(os.environ.get('PATHMIND_PORT', server.get('port', 5000)))
    debug = os.environ.get('FLASK_ENV') != 'production' and server.get('debug', True)

    application.run(
        host=server.get('host', '127.0.0.1'),
        port=port,
        debug=debug,
    )


if __name__ == '__main__':
    main()
