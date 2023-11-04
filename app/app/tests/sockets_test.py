# # -*- coding: UTF-8 -*-
# """
# @author:wuzhaochen
# @project:datalab
# @module:sockets_test
# @time:2022/08/31
# """
# import threading
# import time
# import websocket
# from fastapi import WebSocketDisconnect
# from fastapi.testclient import TestClient
#
#
# def when_message(ws, message):
#     print('The received message：' + message)
#
#
# def when_open(ws):
#     def run():
#         while True:
#             a = input('Sending server：')
#             ws.send(a)
#             time.sleep(0.5)
#             if a == 'close':
#                 ws.close()
#                 break
#
#     t = threading.Thread(target=run)
#     t.start()
#
#
# def when_close(ws):
#     print('Connection closure')
#
#
# def test_websocket():
#     client = TestClient(app)
#     with client.websocket_connect("/api/components/ws/e2bed94859104f029d1c7f3317") as websocket:
#         while True:
#             try:
#                 data = websocket.receive_json()
#                 print(data)
#             except WebSocketDisconnect:
#                 break
#
#
# # if __name__ == '__main__':
# "ws://127.0.0.1/api/deploy/ws/1c3ff2fb883d4bee91e273a593"
# "ws://127.0.0.1/api/deploy/ws/671d629d81024b40890b0bbb21"
#
# "ws://127.0.0.1:8000/api/deploy/ws/1c3ff2fb883d4bee91e273a593"
# "ws://127.0.0.1:8000/api/deploy/ws/a17ea61fcca141c79a49135b58"
# ws = websocket.WebSocketApp("ws://127.0.0.1:8000/api/components/ws/e2bed94859104f029d1c7f3317",
#                             on_message=when_message,
#                             on_open=when_open,
#                             on_close=when_close)
# # ws.run_forever()
#
# # raise TypeError
# #
# #
# # from minio import Minio
# # client = Minio('127.0.0.1:9000', access_key='admin', secret_key='admin123', secure=False)
# # client.fput_object('datalabdev', 'index.py', 'index.py')
# # client.fput_object('datalabdev', 'mycache.py', 'mycache.py')
#
# # import pymongo
# # import pickle
# # con = pymongo.MongoClient('127.0.0.1')
# # db = con['datalab']
# # con = pymongo.MongoClient('mongo-0.mongo.datalab.svc.cluster.local')
# # user_init_data = pickle.load(open("admin_user_model.pkl", 'rb')) #dict
# # permission__init_data = pickle.load(open("permission_model.pkl", 'rb')) #list
# # role_model_init_data = pickle.load(open("role_model.pkl", 'rb')) #list
# # storage_resource_allocated_init_data = pickle.load(open("storage_resource_allocated_model.pkl", 'rb')) #dict
# #
# # con['datalab']['permission_model'].find_one()
# # d = con['datalab']['permission_model'].find_one()
# # if d is None:
# #     con['datalab']['permission_model'].insert_many(permission__init_data)
# #
# # admin_user = con['datalab']['user_model'].find_one({"role": "ADMIN"})
# # if admin_user is None:
# #    con['datalab']['user_model'].insert_one(user_init_data)
# #
# # storage_resource_allocated_model = con['datalab']['storage_resource_allocated_model'].find_one({"allocated_user":"0993bc4a65fa4d638dcdcf44030f7194"})
# # if storage_resource_allocated_model is None:
# #     con['datalab']['storage_resource_allocated_model'].insert_one(storage_resource_allocated_init_data)
# #
# # role_model = con['datalab']['role_model'].find_one()
# # if role_model is None:
# #     con['datalab']['role_model'].insert_many(role_model_init_data)
#
#
#
# # role_model = db['role_model'].find()
# # admin_user_model = db['user_model'].find_one({'name': "Administrator"})
# # storage_resource_allocated_model = db['storage_resource_allocated_model'].find_one({"allocated_user":"0993bc4a65fa4d638dcdcf44030f7194"})
# # data = list()
# # for _ in role_model:
# #     data.append(_)
# #
# # dir = r"C:\Users\Admin\Desktop\init_data"
# #
# # import os
# # pickle.dump(data, open(os.path.join(dir, 'role_model.pkl'), 'wb'))
# # pickle.dump(admin_user_model, open(os.path.join(dir, 'admin_user_model.pkl'), 'wb'))
# # pickle.dump(storage_resource_allocated_model, open(os.path.join(dir, 'storage_resource_allocated_model.pkl'), 'wb'))

import pymongo
con = pymongo.MongoClient('mongo-0.mongo.datalab.svc.cluster.local')['datalab']
cols = [
    'storage_resource_allocated_model',
    'storage_quota_rule_model',
    'platform_resource_model',
    'user_quota_model',
    'platform_model',
    'storage_resource_model',
    'experiment_ui_model',
    'experiment_model',
    'computing_quota_rule_model',
    'computing_resource_allocated_model',
    'index_ui_model',
    'computing_resource_model',
    'audit_enumerate_model',
    'quota_resource_model',
    'user_model',
    'permission_model',
    'tools_tree_model',
    'skeleton_category_model',
    'role_model',
    'public_dataset_option_model']

import pickle
for _col in cols:
    con[_col].insert_many(pickle.load(open(f"init_data/{_col}.pkl", 'rb')))
    # pickle.dump([i for i in con[_col].find()], open(f"./init_data/{_col}.pkl", 'wb'))
