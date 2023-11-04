# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:dockerfile_generator
@time:2022/08/11
"""
import json
from dataclasses import dataclass
from typing import IO, Optional, List, Dict, Union


class DockerFileOrderException(Exception):
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message

    def __str__(self):
        return self.message


def parcel(strings: str):
    return f"{strings}" if ' ' in strings else strings


class DockerFileBase:
    def into(self, file: IO):
        raise NotImplemented


@dataclass
class DockerFileFrom(DockerFileBase):
    tag: str
    platform: Optional[str]

    def into(self, file: IO):
        col: List[str] = ['FROM', self.tag]
        if self.platform is not None:
            col.append(f'--platform={self.platform}')
        _s = ' '.join(col)
        file.write(f"{_s}\n")


@dataclass
class DockerFileMaintainer(DockerFileBase):
    author: str

    def into(self, file: IO):
        file.write(f"MAINTAINER {self.author}\n")


@dataclass
class DockerFileLabel(DockerFileBase):
    label_dict: Dict[str, str]

    def into(self, file: IO):
        labels: str = ' '.join([f'{key}={parcel(val)}' for key, val in self.label_dict.items()])
        file.write(f'LABEL {labels}\n')


@dataclass
class DockerFileCopy(DockerFileBase):
    source: Union[str, List[str]]
    target: str
    user: Optional[str]
    group: Optional[str]

    def into(self, file: IO):
        chown = f'--chown={self.user}:{self.group} ' if self.user is not None and self.group is not None else ''
        if isinstance(self.source, list):
            file.write(f'COPY {chown}{" ".join(parcel(s) for s in self.source)} {parcel(self.target)}\n')
        else:
            file.write(f'COPY {chown}{parcel(self.source)} {parcel(self.target)}\n')


@dataclass
class DockerFileEnv(DockerFileBase):
    env_dict: Dict[str, str]

    def into(self, file: IO):
        labels: str = ' '.join([f'{key}={parcel(val)}' for key, val in self.env_dict.items()])
        file.write(f'ENV {labels}\n')


@dataclass
class DockerFileRun(DockerFileBase):
    commands: Union[str, List[str]]

    def into(self, file: IO):
        if isinstance(self.commands, list):
            file.write(f'RUN {json.dumps(self.commands)}\n')
        else:
            file.write(f"RUN {self.commands}\n")


@dataclass
class DockerFileWorkDir(DockerFileBase):
    workdir_path: str

    def into(self, file: IO):
        file.write(f"WORKDIR {self.workdir_path}\n")


@dataclass
class DockerFileArg(DockerFileBase):
    arg_key: str
    arg_val: Union[str]

    def into(self, file: IO):
        _string = self.arg_key
        if self.arg_val:
            _string = f"{self.arg_key}={self.arg_val}"
        file.write(f"ARG {_string}\n")


@dataclass
class DockerFileOnBuild(DockerFileBase):
    on_build: str

    def into(self, file: IO):
        file.write(f"ONBUILD {self.on_build}\n")


@dataclass
class DockerFileCmd(DockerFileBase):
    ...


class DockerFileGenerator:
    lines = list()

    def images_from(self, tag: str, platform: Optional[str] = None):
        self.lines.append(DockerFileFrom(tag, platform))

    def images_maintainer(self, author: str):
        self.lines.append(DockerFileMaintainer(author))

    def images_label(self, **args):
        self.lines.append(DockerFileLabel(dict(**args)))

    def images_env(self, **args):
        self.lines.append(DockerFileEnv(dict(**args)))

    def images_run(self, commands: Union[List[str], str]):
        self.lines.append(DockerFileRun(commands))

    def images_copy(self, source: Union[str, List[str]], target: str, user: Optional[str] = None, group: Optional[str] = None):
        self.lines.append(DockerFileCopy(source, target, user, group))

    def images_workdir(self, workdir: str):
        self.lines.append(DockerFileWorkDir(workdir))

    def output(self, file: Union[IO[str], str]):
        self.check_order()
        if isinstance(file, str):
            file = open(file, 'w', encoding='UTF-8')
        for line_instance in self.lines:
            line_instance.into(file)

    def check_order(self):
        try:
            assert self.lines and isinstance(self.lines[0], DockerFileFrom)
        except AssertionError:
            raise DockerFileOrderException('The first line is not "From", Failed to write DockerFile')


def python3_base_images(file="Dockerfile"):
    dfg = DockerFileGenerator()
    dfg.images_from(tag='python3.9:')
    dfg.images_maintainer('zcwu')
    dfg.images_run("""set -ex \\ 
        # Pre-install the required components
        && yum install -y wget tar libffi-devel zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gcc make initscripts \\ 
        && wget https://www.python.org/ftp/python/3.9.0/Python-3.9.0.tgz \\ 
        && tar -zxvf Python-3.9.0.tgz \\ 
        && cd Python-3.9.0 \\ 
        && ./configure prefix=/usr/local/python3 \\ 
        && make \\ 
        && make install \\ 
        && make clean \\ 
        && rm -rf /Python-3.9.0* \\ 
        && yum install -y epel-release \\ 
        && yum install -y python-pip""")
    dfg.images_run("""set -ex \\ 
        # Backing up old versionspython
        && mv /usr/bin/python /usr/bin/python27 \\
        && mv /usr/bin/pip /usr/bin/pip27 \\
        # The default configuration ispython3
        && ln -s /usr/local/python3/bin/python3.9 /usr/bin/python \\
        && ln -s /usr/local/python3/bin/pip3 /usr/bin/pip""")
    dfg.images_run("""set -ex \\
        && sed -i "s#/usr/bin/python#/usr/bin/python2.7#" /usr/bin/yum \\
        && sed -i "s#/usr/bin/python#/usr/bin/python2.7#" /usr/libexec/urlgrabber-ext-down \\
        && yum install -y deltarpm""")
    dfg.images_run("""set -ex \\
        # Change the system time zone to East zone 8
        && rm -rf /etc/localtime \\
        && ln -s /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \\
        && yum install -y vim \\
        # Install the timed task component
        && yum -y install cronie""")
    dfg.images_run("""yum install kde-l10n-Chinese -y && localedef -c -f UTF-8 -i zh_CN zh_CN.utf8""")
    dfg.images_run("pip install --upgrade pip")
    dfg.images_env(LC_ALL="zh_CN.UTF-8")
    dfg.output(file)

