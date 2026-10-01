"""
``LD_add_package_to_executor``: je_action_core's package manager with LoadDensity's settings (functions only,
registered under their bare names, ASCII dotted names only, problems printed to stderr).
"""
from inspect import isfunction
from sys import stderr
from types import ModuleType
from typing import Any, Optional

from je_action_core import MemberNaming, PackageGate, PackageManagerSettings, is_module_name
from je_action_core import PackageManager as _CorePackageManager


def _print_error(message: str) -> None:
    print(message, file=stderr)


_SETTINGS = PackageManagerSettings(
    naming=MemberNaming.BARE,
    predicates=(isfunction,),
    name_check=is_module_name,
    # The package gate (workspace X-12) is not switched on here yet.
    gate=PackageGate.OFF,
    log_error=_print_error,
)


class PackageManager(_CorePackageManager):
    """
    套件管理器
    Package Manager

    用於動態載入套件並將其函式加入到 Executor 的事件字典。
    Loads packages and registers their functions into an Executor (je_action_core's package manager).
    """

    def __init__(self) -> None:
        super().__init__(_SETTINGS)

    def load_package_if_available(self, package: str) -> Optional[ModuleType]:
        """
        嘗試載入套件 (Try to load a package)

        :param package: 套件名稱 (Package name)
        :return: 套件模組或 None (Loaded module or None)
        """
        return self.check_package(package)

    def add_package_to_executor(self, package: Any) -> None:
        """
        將套件的所有函式加入 Executor 的事件字典
        Add all functions from a package into the Executor's event dictionary

        :param package: 套件名稱 (Package name)
        """
        super().add_package_to_executor(package)


# 建立全域 PackageManager 實例
# Create global PackageManager instance
package_manager = PackageManager()
