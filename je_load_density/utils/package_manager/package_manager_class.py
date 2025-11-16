from importlib import import_module
from importlib.util import find_spec
from inspect import getmembers, isfunction
from sys import stderr
from typing import Optional, Any


class PackageManager:
    """
    套件管理器
    Package Manager

    用於動態載入套件並將其函式加入到 Executor 的事件字典。
    Used to dynamically load packages and register their functions into an Executor.
    """

    def __init__(self) -> None:
        # 已載入的套件字典 (Dictionary of loaded packages)
        self.installed_package_dict: dict[str, Any] = {}
        # Executor 參考 (Reference to Executor instance)
        self.executor: Optional[Any] = None

    def load_package_if_available(self, package: str) -> Optional[Any]:
        """
        嘗試載入套件 (Try to load a package)

        :param package: 套件名稱 (Package name)
        :return: 套件模組或 None (Loaded module or None)
        """
        if package not in self.installed_package_dict:
            found_spec = find_spec(package)
            if found_spec is not None:
                try:
                    installed_package = import_module(found_spec.name)
                    self.installed_package_dict[found_spec.name] = installed_package
                except ModuleNotFoundError as error:
                    print(repr(error), file=stderr)
                    return None
            else:
                return None
        return self.installed_package_dict.get(package)

    def add_package_to_executor(self, package: str) -> None:
        """
        將套件的所有函式加入 Executor 的事件字典
        Add all functions from a package into the Executor's event dictionary

        :param package: 套件名稱 (Package name)
        """
        installed_package = self.load_package_if_available(package)
        if installed_package is not None and self.executor is not None:
            for name, function in getmembers(installed_package, isfunction):
                self.executor.event_dict[name] = function
        elif installed_package is None:
            print(repr(ModuleNotFoundError(f"Can't find package {package}")), file=stderr)
        else:
            print(f"Executor error: {self.executor}", file=stderr)


# 建立全域 PackageManager 實例
# Create global PackageManager instance
package_manager = PackageManager()