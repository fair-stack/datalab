# encoding=UTF-8
import requests
import pathlib
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
        # print(data)
        return {"data_path": data["path"], "name": data['path'].split('/')[-1],"data_size":data["size"] ,
                'is_dir': data["is_dir"]
                }

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




def conn_ftp(ftp_ip: str, ftp_user: str, ftp_password:str, ftp_port: int =2121):
    ftp = FTP()
    ftp.encoding = 'utf-8'
    ftp.connect(ftp_ip, ftp_port)
    ftp.login(ftp_user, ftp_password)
    return ftp


def display_dir(ftp, path='/'):
    ftp.cwd(path)
    return [i for i in ftp.nlst()]


def get_dir_name(s):
    '''
     Role：Requires a file or folder name
     parameters1：The string to truncate
     Return：File or folder name
    '''
    dir_name = ""
    k = 0
    record = ""
    for i in s:
        if (record == " " and i != " "):
            k = k + 1
        if (k >= 3):
            dir_name = dir_name + i
        record = i
    return dir_name

def download_dir(ftp, path, local_path):
    '''
     Role: Download directory
     parameters1：ftpConnection object
     parameters2：The directory to display
     parameters3：Local storage path
     Return：There is no
    '''

    # Go to the specified directory
    ftp.cwd(path)
    # Distinguish between files and folders
    dirs = []
    ftp.dir(".", dirs.append)
    for i in dirs:
        try:
            # Identify recursion for directories
            if ("<DIR>" in i):
                dir_name = get_dir_name(i)
                local_path_new = local_path + "/" + dir_name
                # Create folders locally
                pathlib.Path(local_path_new).mkdir(parents=True, exist_ok=True)
                # Download directory
                download_dir(ftp, dir_name, local_path_new)
            # Identify as a file for download
            else:
                file_name = get_dir_name(i)
                local_filename = local_path + "/" + file_name
                f = open(local_filename, "wb")
                # Downloadftpfile
                ftp.retrbinary('RETR ' + file_name, f.write)
                f.close()
        except Exception as e:
            print(e)

    # Exit the current directory
    ftp.cwd("..")


def download_file(ftp, key, path, local_path):
    '''
     Role: Downloadfile
     parameters1：ftpConnection object
     parameters2：Download
     parameters3：The directory to display
     parameters4：Local storage path
     Return：There is no
    '''

    # Go to the specified directory
    ftp.cwd(path)
    # Distinguish between files and folders
    dirs = []
    ftp.dir(".", dirs.append)
    for i in dirs:
        if (key in i):
            try:
                # Identify recursion for directories
                if ("<DIR>" in i):
                    dir_name = get_dir_name(i)
                    local_path_new = local_path + "/" + dir_name
                    # Create folders locally
                    pathlib.Path(local_path_new).mkdir(parents=True, exist_ok=True)
                    # Download directory
                    download_dir(ftp, dir_name, local_path_new)
                else:
                    file_name = get_dir_name(i)
                    local_filename = local_path + "/" + file_name
                    f = open(local_filename, "wb")
                    # Downloadftpfile
                    ftp.retrbinary('RETR ' + file_name, f.write)
                    f.close()
            except Exception as e:
                print(e)


# Setting the encoding，file


class InstDBFair:
    DATASET_LIST = "/api/fair/dataset/list"
    GET_DATASET_DETAILS= "/api/fair/dataset/details"
    ENTRY = "/api/fair/entry"
    ALLOW_PUBLIC = 'http://purl.org/coar/access_right/c_abf2'

    def __init__(self,  url:str, secret_key: str, token: str):
        self.url = url
        self.secret_key = secret_key
        self.token = token
        self.headers = {"token": token, "version": "1.0"}

    def get(self, url):
        return requests.get(url, headers=self.headers).json()

    def get_dataset_list(self):
        return self.get(self.url + self.DATASET_LIST)

    def get_dataset_detail(self,id):
        ds_detail = requests.get(self.url+ self.GET_DATASET_DETAILS+f"?id={id}", headers=self.headers).json()
        ftp_url = ds_detail.get('ftpUrlInfo')
        ftp_ip = None
        ftp_port = None
        ftp_user = None
        ftp_password = None
        if ftp_url:
            ftp_url = ftp_url['ftpUrl'].split('//')[-1]
            ftp_ip, ftp_port = ftp_url.split(':')
            ftp_user = ds_detail['ftpUrlInfo']['username']
            ftp_password = ds_detail['ftpUrlInfo']['password']
        item = {
            "id": id,
            "access": "UNDETERMINED" if ds_detail['dcterms:accessRights'] == self.ALLOW_PUBLIC else "PRIVATE",
            "label": ','.join([_['@value'] for _ in ds_detail['schema:keywords']]),
            "icon": ds_detail['schema:sourceOrganization']['schema:logo'],
            "organization_name": ds_detail['schema:sourceOrganization']['schema:name'],
            "date_published": ds_detail['schema:datePublished'],
            "author": [{"name": a['schema:name'], "email": a['schema:email'], 'org': a.get('schema:worksFor')}  for _ in ds_detail['schema:author'] for a in _['@list']],
            "description": ds_detail['schema:description'],
            "ftp_user": ftp_user,
            "ftp_password": ftp_password,
            "ftp_ip": ftp_ip,
            "ftp_port": ftp_port,
            "data_size": ds_detail['dcat:byteSize'],
            "links": self.url
         }
        name = self.datasets_name(ds_detail['schema:name'])
        item.update(name)
        item['name'] = name['name_zh']
        files = self.display_dir(item)
        item['files'] = len(files) if files else 0
        return item, files

    @classmethod
    def create_link(cls, url:str, secret_key: str):
        headers = {"secretKey": secret_key}
        resp = requests.get(url+cls.ENTRY, headers=headers)
        try:
            _data = resp.json()
            token = _data['ticket']['token']
        except Exception as e:
            return None
        else:
            return cls(url, secret_key, token)

    def datasets_meta_data(self):
        datasets_list = self.get_dataset_list()
        return [self.get_dataset_detail(_['id']) for _ in datasets_list]

    def display_dir(self, ds_detail):
        ftp_ip = ds_detail['ftp_ip']
        if ftp_ip is None:
            return
        ftp_user = ds_detail['ftp_user']
        ftp_password = ds_detail['ftp_password']
        ftp_port = int(ds_detail['ftp_port'])
        files = list()
        sf = ScanFiles(
            host=ftp_ip,
            port=ftp_port,
            username=ftp_user,
            password=ftp_password)
        try:
            files = sf.walk('/')
        finally:
            sf.quit()
        return files


    def download_file(self, id):
        ftp = conn_ftp()
        ftp.encoding = 'utf-8'
        path = "/CaseData/nc.vo.sdp.testcase.testcase.TestcaseHVO/"
        local_path = "D:/ftpDownload"
        download_file(ftp, "userbase", path, local_path)

    def datasets_name(self,data):
        name = {"name_zh": "", "name_en": ""}
        if isinstance(data, str):
            name['name_zh'] = data
        elif isinstance(data, list):
            for _ in data:
                name['name_'+_['@language']] = _['@value']
        return name

