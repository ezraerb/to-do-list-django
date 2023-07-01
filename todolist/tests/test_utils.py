""" Common utility methods for tests """


def strip_timestamps(model_dict):
    """
    Models contain timestamp metadata fields. To get stable tests, comparisions should normally
    be done without the timestamps. This method strips them from model dicts
    """
    if "created_at" in model_dict:
        del model_dict["created_at"]
    if "updated_at" in model_dict:
        del model_dict["updated_at"]
