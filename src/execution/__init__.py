# Input: ExecutionEngine
# Output: execution exports
# Pos: execution package initializer
# 一旦我被更新，务必更新我的开头注释，以及所属文件夹的MD。

"""
执行模块

导出：
- ExecutionEngine: 执行引擎
"""

from src.execution.engine import ExecutionEngine

__all__ = ["ExecutionEngine"]
