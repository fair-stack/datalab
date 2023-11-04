import datetime
import pickle
import pymongo

con = pymongo.MongoClient(host='mongo-0.mongo.datalab.svc.cluster.local', port=27017)


# permission: List
permission_init_data = list(con['datalab']['permission_model'].find({}))
with open('permission_model.pkl', 'wb') as f:
    pickle.dump(permission_init_data, f)


# role: List
role_init_data = list(con['datalab']['role_model'].find({"is_innate": True}))  # Filter criteria
with open('role_model.pkl', 'wb') as f:
    pickle.dump(role_init_data, f)


# user: Dict
# Note _id and Follow on skeleton / experiment Equal match
user_init_data = {'_id': '0993bc4a65fa4d638dcdcf44030f7194',
                  'name': 'admin',
                  'email': 'admin@datalab.cn',
                  'organization': 'DataLab',
                  'hashed_password': '$2b$12$Tq70sHokQoHVJY1r5c6bKuaugHC3Lt5TnB6W4s.nVKPmBPvCr0ihC',
                  'password_strength': 'strong',
                  'role': 'ADMIN',
                  'is_email_verified': True,
                  'is_active': True,
                  'is_superuser': True,
                  'from_source': 'signup',
                  'created_at': datetime.datetime(2023, 1, 4, 3, 48, 25, 915000),
                  'updated_at': datetime.datetime(2023, 1, 4, 3, 48, 37, 475000)
                  }

with open('admin_user_model.pkl', 'wb') as f:
    pickle.dump(user_init_data, f)

# Background basic information configuration-Web page configuration
# platform: Dict
platform_init_data = list(con['datalab']['platform_model'].find({}))[0]
with open('platform_model.pkl', 'wb') as f:
    pickle.dump(platform_init_data, f)

# indexui: Dict
indexui_init_data = list(con['datalab']['index_ui_model'].find({}))[0]
with open('index_ui_model.pkl', 'wb') as f:
    pickle.dump(indexui_init_data, f)

# skeletonui: Dict
skeletonui_init_data = list(con['datalab']['skeleton_ui_model'].find({}))[0]
with open('skeleton_ui_model.pkl', 'wb') as f:
    pickle.dump(skeletonui_init_data, f)

# experimentui: Dict
experimentui_init_data = list(con['datalab']['experiment_ui_model'].find({}))[0]
with open('experiment_ui_model.pkl', 'wb') as f:
    pickle.dump(experimentui_init_data, f)



# Analysis tools： Analysis tools: 47fab98b22b64acf93bb3e3d2c
# compoundstep_element: List
compoundstep_element_init_data = list(
    con['datalab']['compound_step_element_model'].find({"skeleton": "47fab98b22b64acf93bb3e3d2c"}))  # Condition
with open('compound_step_element_model.pkl', 'wb') as f:
    pickle.dump(compoundstep_element_init_data, f)

# compoundstep: List
compoundstep_init_data = list(
    con['datalab']['compound_step_model'].find({"skeleton": "47fab98b22b64acf93bb3e3d2c"}))  # Condition
with open('compound_step_model.pkl', 'wb') as f:
    pickle.dump(compoundstep_init_data, f)

# skeleton: Dict
skeleton_init_data = list(con['datalab']['skeleton_model'].find({"_id": "47fab98b22b64acf93bb3e3d2c"}))[0]  # Condition

# Working with certain fields: 'skeleton_renewed', 'skeleton_renewed_origin', 'category', 'pageviews'
skeleton_init_data['skeleton_renewed'] = None
skeleton_init_data['skeleton_renewed_origin'] = None
skeleton_init_data['category'] = None
skeleton_init_data['pageviews'] = 0

with open('skeleton_model.pkl', 'wb') as f:
    pickle.dump(skeleton_init_data, f)


# Experiment：
# Experiment-Clustering Analysis of Iris Dataset
# Three steps，Comes with default input data and parameters

# Input data preparation:
# iris.csv
# Storage locations inside containers：/home/data_storage/storage_data/0993bc4a65fa4d638dcdcf44030f7194/edaa925742f44edca5d8297b24.iris.csv

# DataFileSystem: Dict


dfs_init_data = list(con['datalab']['data_file_system'].find({"_id": "edaa925742f44edca5d8297b24"}))[0]     # Condition
with open('data_file_system.pkl', 'wb') as f:
    pickle.dump(dfs_init_data, f)

# task: List
tool_task_init_data = list(con['datalab']['tool_task_model'].find({"experiment": "11c30b52ca744c53bdbc134728"}))    # Condition
with open('tool_task_model.pkl', 'wb') as f:
    pickle.dump(tool_task_init_data, f)

# experiment: Dict
experiment_init_data = list(con['datalab']['experiment_model'].find({"_id": "11c30b52ca744c53bdbc134728"}))    # Condition
with open('experiment_model.pkl', 'wb') as f:
    pickle.dump(experiment_init_data, f)
