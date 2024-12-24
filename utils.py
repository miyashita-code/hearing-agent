def dict_to_string(dict):
    return "\n".join([f"{key}: {value}" for key, value in dict.items()])

def string_to_bool(input):
    if type(input) == bool:
        return input
    return input.lower() == "true"
