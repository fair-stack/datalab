from minio import Minio
from minio.error import S3Error
import sys
import time
import json
import urllib3
from queue import Empty, Queue
from threading import Thread
_BAR_SIZE = 20
_KILOBYTE = 1024
_FINISHED_BAR = '#'
_REMAINING_BAR = '-'
_UNKNOWN_SIZE = '?'
_STR_MEGABYTE = ' MB'
_HOURS_OF_ELAPSED = '%d:%02d:%02d'
_MINUTES_OF_ELAPSED = '%02d:%02d'
_RATE_FORMAT = '%5.2f'
_PERCENTAGE_FORMAT = '%3d%%'
_HUMANINZED_FORMAT = '%0.2f'
_DISPLAY_FORMAT = '|%s| %s/%s %s [elapsed: %s left: %s, %s MB/sec]'
_REFRESH_CHAR = '\r'
from app.core.config import settings
import redis


def main(client, bucket_name, object_name, file_path, data_id):
    con = redis.Redis(settings.REDIS_HOST, port=settings.REDIS_PORT, db=7)
    found = client.bucket_exists(bucket_name)
    if not found:
        client.make_bucket(bucket_name)
    print(bucket_name, object_name)
    result = client.fput_object(bucket_name, object_name, file_path, progress=Progress(
        con=con, data_id=data_id))

    try:
        _data = con.get(data_id)
        _data = json.loads(_data)
        _data['status'] = "Success"
        con.set(data_id, json.dumps(_data, ensure_ascii=False))
    except Exception as e:
        print(f"File push failed {e}")
    return result


class Progress(Thread):
    def __init__(self, con, data_id, interval=1, stdout=sys.stdout):
        Thread.__init__(self)
        self.daemon = True
        self.total_length = 0
        self.interval = interval
        self.object_name = None
        self.data_id = data_id
        self.last_printed_len = 0
        self.current_size = 0
        self.con = con
        self.display_queue = Queue()
        self.initial_time = time.time()
        self.stdout = stdout
        self.start()

    def set_meta(self, total_length, object_name):
        self.total_length = total_length
        self.object_name = object_name
        self.prefix = self.object_name + ': ' if self.object_name else ''

    def run(self):
        displayed_time = 0
        while True:
            try:
                # display every interval secs
                task = self.display_queue.get(timeout=self.interval)
            except Empty:
                elapsed_time = time.time() - self.initial_time
                if elapsed_time > displayed_time:
                    displayed_time = elapsed_time
                self.print_status(current_size=self.current_size,
                                  total_length=self.total_length,
                                  displayed_time=displayed_time
                                  )
                continue

            current_size, total_length = task
            displayed_time = time.time() - self.initial_time
            self.print_status(current_size=current_size,
                              total_length=total_length,
                              displayed_time=displayed_time)
            self.display_queue.task_done()
            if current_size == total_length:
                self.done_progress()
                break

    def update(self, size):
        if not isinstance(size, int):
            raise ValueError('{} type can not be displayed. '
                             'Please change it to Int.'.format(type(size)))

        self.current_size += size
        self.display_queue.put((self.current_size, self.total_length))

    def done_progress(self):

        pass

    def print_status(self, current_size, total_length, displayed_time):
        _data = format_string(current_size, total_length, displayed_time)
        self.con.set(self.data_id, json.dumps(_data, ensure_ascii=False))


def seconds_to_time(seconds):
    """
    Consistent time format to be displayed on the elapsed time in screen.
    :param seconds: seconds
    """
    minutes, seconds = divmod(int(seconds), 60)
    hours, m = divmod(minutes, 60)
    if hours:
        return _HOURS_OF_ELAPSED % (hours, m, seconds)
    else:
        return _MINUTES_OF_ELAPSED % (m, seconds)


def format_string(current_size, total_length, elapsed_time):
    n_to_mb = current_size / _KILOBYTE / _KILOBYTE
    elapsed_str = seconds_to_time(elapsed_time)

    rate = _RATE_FORMAT % (
        n_to_mb / elapsed_time) if elapsed_time else _UNKNOWN_SIZE
    frac = float(current_size) / total_length
    bar_length = int(frac * _BAR_SIZE)
    bar = (_FINISHED_BAR * bar_length +
           _REMAINING_BAR * (_BAR_SIZE - bar_length))
    percentage = frac * 100
    left_str = (
        seconds_to_time(
            elapsed_time / current_size * (total_length - current_size))
        if current_size else _UNKNOWN_SIZE)

    humanized_total = _HUMANINZED_FORMAT % (
        total_length / _KILOBYTE / _KILOBYTE) + _STR_MEGABYTE
    humanized_n = _HUMANINZED_FORMAT % n_to_mb + _STR_MEGABYTE
    return {"load_size": humanized_n, "total_size": humanized_total,
            "percentage": percentage, "used_at": elapsed_str, "left_time": left_str,
                              "rate": rate, "status":"Loading"}



if __name__ == '__main__':
    try:
        main()
    except S3Error as exc:
        print("error ouccured.", exc)
