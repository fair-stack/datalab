# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab
@module:gateway
@time:2023/02/16
"""
import requests
from pydantic import BaseModel
from app.core.config import settings


class JupyterUpstreamKeepalive(BaseModel):
    size: int = 320
    idle_timeout: int = 60
    requests: int = 1000


class JupyterUpstreamTimeOut(BaseModel):
    connect: int = 6
    send: int = 6
    read: int = 6


class JupyterUpstream(BaseModel):
    name: str
    type: str = "roundrobin"
    pass_host: str = "pass"
    scheme: str = "http"
    timeout: JupyterUpstreamTimeOut
    keepalive_pool: JupyterUpstreamKeepalive
    nodes: dict


class JupyterRouter(BaseModel):
    name: str
    desc: str
    enable_websocket: bool = True
    status: int = 1
    uris: list
    methods = list
    priority: int = 0
    labels: dict = {}
    upstream_id: str


class ApiSix:
    headers = {"X-API-KEY": ""}
    upstream_url = settings.NOTEBOOK_GATEWAY_ADMIN_UPSTREAM
    router_url = settings.NOTEBOOK_GATEWAY_ADMIN_ROUTER
    methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "CONNECT", "TRACE", "PURGE"]

    def create_upstream(self, name: str, host: str, upstream_type: str = "roundrobin", scheme: str = "http",
                        pass_host="pass", connect: int = 6, send: int = 6, read: int = 6, size: int = 320,
                        idle_timeout: int = 60, requests_keepalive: int = 1000):
        timeout_settings = JupyterUpstreamTimeOut(connect=connect, send=send, read=read)
        keepalive_pool = JupyterUpstreamKeepalive(size=size, idle_timeout=idle_timeout, requests=requests_keepalive)
        upstream_node = {host: 1}
        upstream_settings = JupyterUpstream(
            name=name, type=upstream_type, pass_host=pass_host, scheme=scheme,
            timeout=timeout_settings, keepalive_pool=keepalive_pool, nodes=upstream_node)
        return upstream_settings.dict()

    def create_router(self, name: str, uris: list, upstream_id: str, desc: str = "", enable_websocket: bool = True):
        print(upstream_id)
        print(self.upstream_url)
        router_settings = JupyterRouter(name=name, upstream_id=upstream_id,
                                        methods=self.methods, uris=uris,
                                        desc=desc, enable_websocket=enable_websocket)
        return router_settings.dict()

    def register_upstream(self, name: str, host: str):
        if "http:" in host:
            host = host.replace("http://", "")
        if "https:" in host:
            host = host.replace("https://", "")
        upstream_data = self.create_upstream(name, host)
        resp = requests.post(self.upstream_url, json=upstream_data, headers=self.headers)
        print(resp.text)
        upstream_id = resp.json()['value']['id']
        upstream_data['upstream_id'] = upstream_id
        return upstream_id

    def register_router(self, name, jupyter_id, upstream_id):
        uris = ['/dupyter/'+jupyter_id, f"/dupyter/{jupyter_id}/*"]
        router_data = self.create_router(name=name, uris=uris, upstream_id=upstream_id)
        resp = requests.post(self.router_url, json=router_data, headers=self.headers)
        if resp.status_code != 200:
            return "Registration failed"

    def register_jupyterlab_service(self, upstream_name: str, host: str, router_name: str, jupyter_id):
        _upstream_id = self.register_upstream(upstream_name, host)
        self.register_router(router_name, jupyter_id, _upstream_id)
