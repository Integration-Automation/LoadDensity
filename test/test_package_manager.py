from je_load_density.utils.package_manager.package_manager_class import PackageManager


class TestPackageManager:

    def test_load_builtin_package(self):
        pm = PackageManager()
        result = pm.load_package_if_available("json")
        assert result is not None
        assert "json" in pm.installed_package_dict

    def test_load_nonexistent_package(self):
        pm = PackageManager()
        result = pm.load_package_if_available("nonexistent_package_xyz_123")
        assert result is None

    def test_load_cached(self):
        pm = PackageManager()
        first = pm.load_package_if_available("json")
        second = pm.load_package_if_available("json")
        assert first is second

    def test_add_package_to_executor(self):
        pm = PackageManager()

        class FakeExecutor:
            def __init__(self):
                self.event_dict = {}

        pm.executor = FakeExecutor()
        pm.add_package_to_executor("json")
        assert len(pm.executor.event_dict) > 0

    def test_add_package_no_executor(self):
        pm = PackageManager()
        pm.executor = None
        # Should not raise, just prints to stderr
        pm.add_package_to_executor("json")
        assert "json" in pm.installed_package_dict
