import datetime
from hashlib import sha256
import os

# extract the timeWindow argument from the request URL
def getTimeLimit(time_window) :
        # lower bound of time window
    if time_window is not None and time_window != 'null':
        time_window = datetime.timedelta(seconds=int(time_window))
        time_limit = datetime.datetime.now() - time_window
    else:
        time_limit = None
    return time_limit

def get_time_boundaries(request_args):
    t1_str = request_args.get('t1', None)
    t2_str = request_args.get('t2', None)
    t1 = datetime.datetime.fromisoformat(t1_str[:-1]) if t1_str else None
    t2 = datetime.datetime.fromisoformat(t2_str[:-1]) if t2_str else None
    return t1, t2

def get_fetch_real_time(request_args, t_end):
    if t_end is not None:
        return False
    else:
        # returning True if displayRealTime is not defined
        return request_args.get('displayRealTime', 'true') == 'true'

def hash_user_id_with_salt(prehashed_id): 
    return sha256(prehashed_id.encode('utf-8') + os.environ.get('SECRET_SALT').encode('utf-8')).hexdigest()