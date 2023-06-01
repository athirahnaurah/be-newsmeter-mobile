import time, datetime

def convert_to_string(time_now):
    time_now_str = datetime.datetime.fromtimestamp(time_now).strftime(
        "%Y-%m-%d %H:%M:%S.%f")
    return time_now_str