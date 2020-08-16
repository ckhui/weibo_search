import os
from datetime import datetime
from WeiboModel import HEADER
import settings
import csv

class WeiboWritter(object):
    def __init__(self, name):
        super().__init__()
        base_dir =  settings.OUTFILE_FOLDER
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir)
        self.file_path = base_dir + os.sep + name + '.csv'
        if not os.path.isfile(self.file_path):
            self.is_first_write = True
        else:
            self.is_first_write = False

    def write(self, item):
        with open(self.file_path, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            if self.is_first_write:
                writer.writerow(HEADER)
                self.is_first_write = False
            writer.writerow(item.data())

class TokenLog(object):
    def __init__(self):
        super().__init__()
        base_dir =  'log'
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir)
        self.file_path = base_dir + os.sep + 'TokenLogs' + '.txt'
        with open(self.file_path, 'a+') as f:
            f.write(f"\n===== START LOG =====\n")

    def write(self, key):
        with open(self.file_path, 'a+') as f:
            f.write(f"{datetime.now()} Token Invalid: {key}\n")

class CompletionLog(object):
    def __init__(self):
        super().__init__()
        base_dir =  'log'
        if not os.path.isdir(base_dir):
            os.makedirs(base_dir)
        self.file_path = base_dir + os.sep + 'completedLog' + '.txt'

    def write(self, str):
        with open(self.file_path, 'a+') as f:
            f.write(f"{datetime.now()} Complete Hour: {str}\n")