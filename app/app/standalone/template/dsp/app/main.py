# -*- coding: UTF-8 -*-
"""
@author:wuzhaochen
@project:datalab-standalone-eventpoint
@module:main
@time:2023/07/04
"""
import os
import json
import time
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import toml
app = FastAPI()


@app.get("/init/{entrypoint}/{executable}/{command}")
def init_functions(entrypoint: str,
                   executable: str,
                   command: str):
    _init_params = {"entrypoint": entrypoint, "executable": executable, "command": command}
    output_file_name = "function.toml"
    with open(output_file_name, "w") as toml_file:
        toml.dump(_init_params, toml_file)


@app.post("/")
def event_entry(request: Request,
                parameters: dict
                ):

    call_back_uri = request.headers.get("X-Callback-Url")
    _time = time.time()
    parameters["ceProtocol"] = call_back_uri
    with open(f"/code/.{_time}ceProtocol", "w") as f:
        json.dump(parameters, f)
    os.popen(f"dce_run --protocol /code/.{_time}ceProtocol")
    return JSONResponse(status_code=200, content={"msg": f"dce_run --protocol /code/.{_time}ceProtocol"})


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)
