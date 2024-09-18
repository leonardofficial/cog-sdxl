from helpers.load_config import load_config
config = load_config()


def create_execution_metadata(runtime: float, data: dict = None):
    execution_metadata = {
        "gpu": config.NODE_GPU,
        "node_id": config.NODE_ID
    }

    if runtime is not None:
        execution_metadata["runtime"] = runtime

    if data is not None:
        execution_metadata.update(data)

    return execution_metadata