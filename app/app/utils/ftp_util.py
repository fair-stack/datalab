import re
from ftplib import FTP


class ScanFiles:
    __SIZE_UNITS = list(f'{_}B'.strip() for _ in ' KMGTP')

    def __init__(self, host: str, port: int, username: str, password: str):
        """InitializationFTPConnect and log in"""
        self.f = FTP()
        self.f.connect(host=host, port=port)
        self.f.encoding = 'utf-8'
        self.f.login(user=username, passwd=password)

    @staticmethod
    def convert_size(size: int):
        """File size unit conversion"""
        c = 0
        while size > 1024:
            size /= 1024
            c += 1
        return f"{size:.2f} {ScanFiles.__SIZE_UNITS[c]}"

    @staticmethod
    def analyze_ftp_line(line):
        """ParsingFTPFile system information line"""
        res = re.search(
            r'(\S*)\s*(\S*)\s*(\S*)\s*(\S*)\s*(\S*)\s*(\S*)\s*(\S*)\s*(\S*)\s(.*)',
            line)
        is_dir: bool = res.group(1).startswith('d')
        size: int = int(res.group(5))
        over_path: str = res.group(9)
        return {'is_dir': is_dir,
                'size': size,
                'item': over_path, }

    @staticmethod
    def default_callback(data: dict):
        """Default callback"""
        if data['is_dir']: return  # Opens this line without displaying the folder
        return {"data_path": data["path"], "data_size":ScanFiles.convert_size(data["size"]) }

    def walk(self, p, callback=None):
        if callback is None: callback = ScanFiles.default_callback
        files = list()
        lis = list()
        self.f.dir(p, lis.append)
        for line in lis:
            al = ScanFiles.analyze_ftp_line(line)
            al['path'] = f'{p}/{al["item"]}'.replace('\\', '/').replace('//', '/')
            _ = callback(al)
            files.append(_)
            if al['is_dir']: self.walk(al['path'], callback)
        return files
    def quit(self):
        self.f.quit()


if __name__ == '__main__':

    sf = ScanFiles(
        host='127.0.0.1',
        port=2121,
        username='Hm50Jz',
        password='rmxpOu')
    try:
        files = sf.walk('/')
        print(files)
    finally:
        sf.quit()
