from helpers.load_config import load_config
config = load_config()


def create_execution_info(runtime: float, data: dict = None):
    execution_info = {
        "gpu": config.NODE_GPU,
        "node_id": config.NODE_ID
    }

    if runtime is not None:
        execution_info["runtime"] = runtime

    if data is not None:
        execution_info.update(data)

    return execution_info