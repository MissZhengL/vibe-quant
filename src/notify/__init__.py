# Input: TelegramNotifier
# Output: notify exports
# Pos: notify package initializer
# 一旦我被更新，务必更新我的开头注释，以及所属文件夹的MD。

"""
通知模块

导出：
- TelegramNotifier: Telegram 通知器
"""

from src.notify.telegram import TelegramNotifier

__all__ = ["TelegramNotifier"]
