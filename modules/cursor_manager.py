"""
Windows cursor manager for voice typing application.

Handles system-wide cursor changes during recording to provide visual feedback.
Uses Windows API through ctypes to temporarily change the cursor.
"""

import ctypes
import logging
from typing import Optional
import atexit

logger = logging.getLogger(__name__)

# Windows cursor constants
IDC_ARROW = 32512      # Standard arrow cursor
IDC_APPSTARTING = 32650  # Standard arrow with small hourglass (busy)
IDC_CROSS = 32515      # Crosshair cursor
IDC_HAND = 32649       # Hand cursor

# Windows API constants
IMAGE_CURSOR = 2
LR_SHARED = 0x8000


class CursorManager:
    """Manages system-wide cursor changes on Windows."""

    def __init__(self):
        """Initialize cursor manager and save original cursor."""
        self.original_cursor: Optional[int] = None
        self.cursor_changed: bool = False
        self._user32 = ctypes.windll.user32

        # Register cleanup on exit
        atexit.register(self._cleanup)

        # Save the original cursor immediately
        self._save_original_cursor()

    def _save_original_cursor(self) -> None:
        """Save the current system cursor for later restoration."""
        try:
            # Load the current arrow cursor
            cursor = self._user32.LoadCursorW(None, IDC_ARROW)
            if cursor:
                # Make a copy of it
                self.original_cursor = self._user32.CopyImage(
                    cursor,
                    IMAGE_CURSOR,
                    0, 0,  # Use default size
                    LR_SHARED
                )
                logger.debug("Original cursor saved")
            else:
                logger.warning("Failed to load original cursor")
        except Exception as e:
            logger.error(f"Error saving original cursor: {e}")

    def set_recording_cursor(self) -> None:
        """
        Change cursor to indicate recording is active.
        Uses the Windows 'AppStarting' cursor (arrow with hourglass).
        """
        if self.cursor_changed:
            logger.debug("Cursor already set to recording mode")
            return

        try:
            # Load the AppStarting cursor (arrow with small hourglass)
            recording_cursor = self._user32.LoadCursorW(None, IDC_APPSTARTING)

            if recording_cursor:
                # Set it as the system arrow cursor
                result = self._user32.SetSystemCursor(
                    self._user32.CopyImage(recording_cursor, IMAGE_CURSOR, 0, 0, LR_SHARED),
                    IDC_ARROW
                )

                if result:
                    self.cursor_changed = True
                    logger.info("Cursor changed to recording mode")
                else:
                    logger.warning("SetSystemCursor returned False")
            else:
                logger.warning("Failed to load recording cursor")

        except Exception as e:
            logger.error(f"Error setting recording cursor: {e}", exc_info=True)

    def restore_cursor(self) -> None:
        """Restore the original cursor."""
        if not self.cursor_changed:
            logger.debug("Cursor not changed, nothing to restore")
            return

        try:
            # The easiest way to restore cursors is to reload them from system
            # This works because we're using standard Windows cursors
            self._user32.SystemParametersInfoW(0x0057, 0, None, 0)  # SPI_SETCURSORS
            self.cursor_changed = False
            logger.info("Cursor restored to default")

        except Exception as e:
            logger.error(f"Error restoring cursor: {e}", exc_info=True)

    def _cleanup(self) -> None:
        """Cleanup function called on exit to ensure cursor is restored."""
        if self.cursor_changed:
            logger.info("Cleanup: Restoring cursor on exit")
            self.restore_cursor()

        # Clean up the copied cursor if it exists
        if self.original_cursor:
            try:
                self._user32.DestroyCursor(self.original_cursor)
            except Exception as e:
                logger.debug(f"Error destroying original cursor handle: {e}")


# Global cursor manager instance
_cursor_manager: Optional[CursorManager] = None


def get_cursor_manager() -> CursorManager:
    """Get or create the global cursor manager instance."""
    global _cursor_manager
    if _cursor_manager is None:
        _cursor_manager = CursorManager()
    return _cursor_manager


def set_recording_cursor() -> None:
    """Convenience function to set recording cursor."""
    get_cursor_manager().set_recording_cursor()


def restore_cursor() -> None:
    """Convenience function to restore cursor."""
    get_cursor_manager().restore_cursor()
