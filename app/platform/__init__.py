"""
platform - Cross-platform abstraction layer.

Factory function that returns the correct platform implementation
based on sys.platform. Uses lazy imports so Windows never loads
macOS code and vice versa.
"""
import sys

_instance = None


def get_platform():
    """Get the platform helper singleton.

    Returns:
        PlatformHelper: Windows or macOS implementation.

    Raises:
        NotImplementedError: on unsupported platforms.
    """
    global _instance
    if _instance is None:
        if sys.platform == 'win32':
            from app.platform.windows import WindowsPlatform
            _instance = WindowsPlatform()
        elif sys.platform == 'darwin':
            from app.platform.macos import MacOSPlatform
            _instance = MacOSPlatform()
        else:
            raise NotImplementedError(f'Unsupported platform: {sys.platform}')
    return _instance
