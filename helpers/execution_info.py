from helpers.load_config import load_config
config = load_config()


def create_execution_info(runtime: float, data: dict = None):
    execution_info = {
        "gpu": config.NODE_GPU,
        "node_id": config.NODE_ID
    }

    if runtime:
        execution_info.update({"runtime_ms": runtime})

    if data:
        execution_info.update(data)

    return execution_info