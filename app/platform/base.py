"""
base.py - Abstract base class for platform-specific operations.

Defines the interface that Windows and macOS implementations must provide.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class WindowInfo:
    """Platform-agnostic window information."""
    id: int              # Window identifier (HWND on Windows, CGWindowID on macOS)
    title: str           # Window title
    rect: tuple          # (left, top, right, bottom) in screen coordinates
    owner_pid: int = 0   # Owner process PID


class PlatformHelper(ABC):
    """Abstract interface for platform-specific window and system operations."""

    @abstractmethod
    def get_foreground_window(self):
        """Get information about the current foreground window.

        Returns:
            WindowInfo or None if unavailable.
        """

    @abstractmethod
    def get_window_at_point(self, x, y):
        """Find the window at the given screen coordinates.

        Returns:
            WindowInfo or None if no window found.
        """

    @abstractmethod
    def get_root_window_id(self, window_id):
        """Get the root/ancestor window ID for a given window.

        Returns:
            int: root window ID, or the same ID if already root.
        """

    @abstractmethod
    def get_native_window_id(self, qt_widget):
        """Get the native window identifier from a Qt widget.

        Returns:
            int: native window handle/ID, or 0 on failure.
        """

    @abstractmethod
    def create_subprocess_kwargs(self):
        """Get platform-specific kwargs for subprocess.Popen/run.

        Returns:
            dict: e.g. {'creationflags': CREATE_NO_WINDOW} on Windows, {} on macOS.
        """

    @abstractmethod
    def validate_screenshot_tool(self, path):
        """Validate a screenshot tool path for the current platform.

        Args:
            path: Tool path (e.g. Snipaste.exe on Windows, ignored on macOS).

        Returns:
            tuple: (is_valid: bool, message: str)
        """

    @abstractmethod
    def get_data_directory(self, app_name):
        """Get the platform-standard user data directory.

        Returns:
            str: e.g. %APPDATA%/<app_name> on Windows,
                 ~/Library/Application Support/<app_name> on macOS.
        """

    @abstractmethod
    def show_fatal_error(self, title, message):
        """Show a fatal error dialog to the user."""

    @abstractmethod
    def is_same_process_window(self, window_info):
        """Check if a WindowInfo belongs to the current process.

        Args:
            window_info: WindowInfo instance.

        Returns:
            bool
        """
