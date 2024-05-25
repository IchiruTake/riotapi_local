from time import perf_counter
from typing import Sequence


def convertBytesToHumanReadable(size: int, divisor: int = 1024, scales_constraint: Sequence[str] | None = None) \
        -> tuple[int, int | float, str]:
    """
    This function is to convert bytes to human-readable format
    For example:
    bytes = 1024
    The function will return 1.0
    """
    if size < 0:
        raise ValueError("bytes must be a non-negative number")
    if divisor == 1024:
        scales: Sequence[str] = scales_constraint or ["KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    elif divisor == 1000:
        scales: Sequence[str] = scales_constraint or ["KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    else:
        raise ValueError("divisor must be 1000 or 1024")
    if size < divisor:
        return size, size, "bytes"

    size_int: int = size
    size_float: int | float = size
    c_scale = scales[0]
    for idx, scale in enumerate(scales):
        size_int //= divisor
        size_float /= divisor
        c_scale = scale
        if size_int < divisor:
            break
    return size_int, size_float, c_scale


def castToBytes(size: str) -> int:
    if "i" in size:
        scales = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
        divisor = 1024
    else:
        scales = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
        divisor = 1000
    if all(scale not in size for scale in scales):
        raise ValueError(f"The size {size} is invalid, expecting a valid size.")

    index = 0
    for idx, char in enumerate(size):
        if not char.isdigit() and char != "." and char != ",":
            index = idx
            break
    unit = size[index:]  # Extract the unit
    datasize = size[:index]  # Extract the size

    try:
        scale_index = scales.index(unit)  # Raise ValueError if the unit is not found
    except ValueError:
        raise ValueError(f"The unit {unit} is invalid, expecting a valid unit.")
    result = float(datasize) * (divisor ** scale_index)
    if isinstance(result, float) and not result.is_integer():
        raise ValueError(f"The number of {datasize} is invalid, expecting a valid size.")
    final_result = int(result)
    if final_result < 0:
        raise ValueError(f"The size {size} is invalid, expecting a non-negative size.")
    return final_result

def formatFloat(value: int | float, precision: int = 2, max_number: int = 3) -> str:
    """
    This function is to format the float number
    """
    if max_number < 1:
        raise ValueError("max_number must be a positive integer")
    if precision < 0:
        raise ValueError("precision must be a non-negative integer")
    if max_number < precision:
        raise ValueError("max_number must be greater than precision")

    try:
        result = f"{float(value):.{precision}f}"  # Use naive method to format the float number
        if "." in result and len(result) <= max_number + 1:
            return result
        if "." not in result and len(result) <= max_number:
            return result
    except ValueError:
        raise ValueError("The value must be a valid number")

    # Split the number and do the counting if the number is too long (rare-case but I don't
    # guarantee that it will not happen)
    counter: int = 0
    result = []
    for idx, char in enumerate(str(value)):
        result.append(char)
        if char.isdigit():
            counter += 1
        if counter == max_number:
            next_char = str(value)[idx + 1]
            break
    return "".join(result)


def GetDurationOfPerfCounterInMs(t: float) -> float:
    return 1e3 * (perf_counter() - t)