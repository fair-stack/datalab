# import json
# import heapq
# import requests
# from requests.auth import HTTPBasicAuth
# from requests.adapters import HTTPAdapter
# from requests.packages.urllib3.util.retry import Retry
#
# from time import sleep, time
# import traceback
#
#
# class Harbor(object):
#     def __init__(self, api_url, user, num, exclude):
#         """
#         Initialize some basic parameters
#         :param auth: login password authority management
#         :param head: change user-agent
#         :param url: harbor server api url
#         :param project_exclude: Exclude project team
#         :param num_limit: Limit the number of retained versions
#         :param project_special: project dict id and repo total
#         :param project_state: project dict name and id
#         :param repo_state: repo dict name and tag total
#         :param repo_dispose: Count the number of tag processing
#         :param tag_state: tag dict repo_name and tag
#         """
#         self.auth = user
#         self.head = {"user_agent": "Mozilla/5.0"}
#         self.url = api_url
#         self.project_exclude = exclude
#         self.num_limit = int(num)
#         self.project_special = {}
#         self.project_state = {}
#         self.repo_state = {}
#         self.repo_dispose_count = 0
#         self.tag_state = {}
#
#     def setting(self):
#         self.session = requests.Session()
#         self.session.auth = self.auth
#         retry = Retry(connect=3, backoff_factor=1)
#         adapter = HTTPAdapter(max_retries=retry)
#         self.session.mount('https://', adapter)
#         self.session.keep_alive = False
#
#     def list_project(self):
#         try:
#             print("{}/projects".format(self.url))
#             r_project = self.session.get("{}/projects".format(self.url), headers=self.head, verify=False)
#             r_project.raise_for_status()
#             # Convert the resulting text to a format
#             project_data = json.loads(r_project.text)
#             for i in project_data:
#                 # Name of the project team
#                 project_name = i.get('name')
#                 # Project teamid
#                 project_id = i.get('project_id')
#                 # Project team
#                 project_repo = i.get('repo_count')
#                 # Using a dictionary, the project name vsidCorrespond to
#                 self.project_state[project_name] = project_id
#                 # Due to request limitations，Use another dictionary,correspondenceidinrepoTotal
#                 self.project_special[project_id] = project_repo
#                 print("\033[0;32mProject Name:{}\tProject Number:{}\tWarehouse statistics under the project:{}\033[0m".format(project_name, project_id, project_repo))
#             print("\033[0;36mproject:Project teamcorrespondenceidLists:{}\033[0m".format(self.project_state))
#             print("\033[0;36mproject:Projectidcorrespondence:{}\033[0m".format(self.project_special))
#         except:
#             traceback.print_exc()
#             raise
#
#
#
#
# def main(api_url, login, num, exclude):
#     start = time()
#     try:
#         # beginGetting started
#         har = Harbor(api_url=api_url, user=login, num=num, exclude=exclude)
#         # Configuration
#         har.setting()
#         # Project team
#         har.list_project()
#         print('3')
#
#         print("All operations are completed！")
#         end = time()
#         allTime = end - start
#         print("Total elapsed time at the end of the run:{:.2f}s".format(allTime))
#     except:
#         end = time()
#         allTime = end - start
#         # traceback.print_exc()
#         print('Cleaning up errors！')
#         print("Total elapsed time at the end of the run:{:.2f}s".format(allTime))
#
#


# api_url = "https://127.0.0.1:30443/api/v2.0"
# # Login ,change username and password
# login = HTTPBasicAuth('admin', 'Harbor12345')
# session = requests.Session()
# session.auth = login
# r_project = session.get("https://127.0.0.1:30443/api/v2.0/projects", verify=False)
# # Project team，Change according to the situation，Or empty
# exclude = ['k8s', 'basic', 'library']
# # Too many versions under repository，The number of recent versions to keep
# keep_num = 3
# # StartupStart the engine
# main(api_url=api_url, login=login, num=keep_num, exclude=exclude)
#
#
# import pymongo
# import pickle
# con = pymongo.MongoClient('127.0.0.1')
# db = con['datalab']
# dir_path = r'~/data'
# user_model = db['user_model'].find_one({'email': 'admin@datalab.cn'})
# pickle.dump(user_model,open('admin_user_model.pkl', 'wb'))
# storage_resource_allocated_model = db['storage_resource_allocated_model'].find_one({'_id': "abea7aa40e0d4e0d99d217da89"})
# pickle.dump(storage_resource_allocated_model,open('storage_resource_allocated_model.pkl', 'wb'))
#
#
#
#
"Data and compute synergy computing DCSC dcsc "
"Data and computility synergy engine DCSE dacsae dcs."
from datetime import datetime
a = datetime.now()
print(a.timestamp(), a.strftime("%Y-%m-%d %H:%M:%S.%f"))
