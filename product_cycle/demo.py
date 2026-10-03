from .fixtures import complete_fixture
from .store import Store


def create_demo(project):
    store = Store.create(project, "Dữ liệu minh họa: một sản phẩm ghi và đọc lại thông tin.", "Product Cycle · minh họa", mode="demo")
    try:
        for tid in ["analysis", "design", "architecture"]:
            complete_fixture(store, tid)
        complete_fixture(store, "plan", approve=False)
    finally:
        store.close()
