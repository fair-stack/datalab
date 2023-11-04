import os
import yaml
import dotenv
import pickle
import pymongo
from retrying import retry
os.environ['KUBERNETES_CONFIG'] = r"/root/.kube/config"
from kubernetes.client import CoreV1Api, AppsV1Api
from kubernetes import config
from kubernetes.client.rest import ApiException
from kubernetes import client, config
from kubernetes.stream import stream
client.configuration.assert_hostname = False

kubernetes_config = os.getenv("KUBERNETES_CONFIG")
if kubernetes_config is None:
    raise Exception("DataLabInitialization failure not detectedKubernetesConfiguration files")

config.kube_config.load_kube_config(config_file=kubernetes_config)
DATALAB_NAMESPACE = "datalab"
DATALAB_NAMESPACE_BODY = {'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': DATALAB_NAMESPACE,
                                                                                'labels': {'name': DATALAB_NAMESPACE}}}
core_api = CoreV1Api()
apps_api = AppsV1Api()
namespaces = core_api.list_namespace()
if [_.metadata.name for _ in namespaces.items if _.metadata.name == DATALAB_NAMESPACE]:
    pass
else:
    core_api.create_namespace(DATALAB_NAMESPACE_BODY)


def check_middleware_exits(name) -> bool:
    flag = False
    service_flag = False
    pod_flag = False
    all_pods = [_.metadata.name for _ in core_api.list_namespaced_pod(namespace=DATALAB_NAMESPACE).items]
    all_services = [_.metadata.name for _ in core_api.list_namespaced_service(namespace=DATALAB_NAMESPACE).items]
    for _ in all_services:
        if name in _:
            service_flag=True
    for _ in all_pods:
        if name in _:
            pod_flag=True
    if service_flag and pod_flag:
        flag = True
    return flag


def create_pvc(body: dict):
    try:
        core_api.create_namespaced_persistent_volume_claim(body=body, namespace=DATALAB_NAMESPACE)
    except ApiException as e:
        raise Exception(f"Datalab PVC Creation failure {e}")


def create_deployment(source: dict):
    try:
        print(source)
        apps_api.create_namespaced_deployment(
            body=source, namespace=DATALAB_NAMESPACE)
    except ApiException as e:
        raise Exception(f"DatalabMiddleware deployment failed {e}")


def create_config_map(body: dict):
    try:
        core_api.create_namespaced_config_map(namespace=DATALAB_NAMESPACE,
                                              body=body)
    except ApiException as e:
        raise Exception(f"DatalabMiddlewareConfigMapCreation failure {e}")


def create_service(body: dict):
    try:

        core_api.create_namespaced_service(
            namespace=DATALAB_NAMESPACE,
            body=body,
        )
    except ApiException as e:
        raise Exception(f"DatalabMiddleware {e}")


def create_stateful_set(body: dict):
    try:
        apps_api.create_namespaced_stateful_set(namespace=DATALAB_NAMESPACE,
                                                body=body)
    except ApiException as e:
        raise Exception(f"DatalabMiddlewareCreation failure {e}")


def create_pod(body: dict):
    try:
        core_api.create_namespaced_pod(body=body, namespace=DATALAB_NAMESPACE)
    except ApiException as e:
        raise Exception(f"DatalabMiddlewarePodCreation failure {e}")


def deploy_redis():
    if check_middlware_exits('redis') is False:
        create_config_map(yaml.safe_load(open('yamls/redis/redis-cm')))
        create_pod(yaml.safe_load(open('yamls/redis/redis-deploment.yaml')))
        create_service(yaml.safe_load(open('yamls/redis/redis-svc')))


def deploy_mongo():
    if check_middlware_exits('mongo') is False:
        # create_config_map(yaml.safe_load(open("./yamls/mongo/mongo-cm")))
        create_stateful_set(yaml.safe_load(open('./yamls/mongo/mongo-ss')))
        create_service(yaml.safe_load(open('./yamls/mongo/mongo-svc')))


@retry(stop_max_delay=480000)
def t():
    print("ttt")
    try:
        handler = pymongo.MongoClient('mongo-0.mongo.datalab.svc.cluster.local', serverSelectionTimeoutMS=5000, socketTimeoutMS=5000)
    except Exception as e:
        print("Retry")
        raise Exception("Link failure")
    print(handler.list_databases())
    return True


deploy_mongo()
deploy_redis()
env_file = dotenv.find_dotenv()
dotenv.load_dotenv(env_file)
dotenv.set_key(env_file, "MINIO_URL", os.getenv("MINIO_URL"))
dotenv.set_key(env_file,"MINIO__ACCESS_KEY", os.getenv("MINIO__ACCESS_KEY"))
dotenv.set_key(env_file,"MINIO_SECRET_KEY", os.getenv("MINIO_SECRET_KEY"))
dotenv.set_key(env_file, "MONGODB_SERVER", "mongo-0.mongo.datalab.svc.cluster.local")
dotenv.set_key(env_file, "HARBOR_URL", os.getenv("HARBOR_URL"))
dotenv.set_key(env_file, "HARBOR_PROJECTS", os.getenv("HARBOR_URL") +"/datalab/python3.9")
dotenv.set_key(env_file, "HARBOR_ROBOT_NAME", os.getenv("HARBOR_ROBOT_NAME"))
dotenv.set_key(env_file, "HARBOR_USER", os.getenv("HARBOR_USER"))
dotenv.set_key(env_file, "HARBOR_PASSWORD", os.getenv("HARBOR_PASSWORD"))
dotenv.set_key(env_file, "SERVER_HOST", os.getenv("SERVER_HOST"))
dotenv.set_key(env_file, "CPU_CORE_NUMBER", os.getenv("CPU_CORE_NUMBER"))
dotenv.set_key(env_file, "MEMORY_SIZE_GB", os.getenv("MEMORY_SIZE_GB"))
dotenv.set_key(env_file, "STORAGE_SIZE_GB", os.getenv("STORAGE_SIZE_GB"))
dotenv.set_key(env_file, "HARBOR_URL", os.getenv("HARBOR_URL"))
dotenv.set_key(env_file, "HARBOR_PROJECTS", os.getenv("HARBOR_PROJECTS"))
dotenv.set_key(env_file, "HARBOR_ROBOT_NAME", os.getenv("HARBOR_ROBOT_NAME"))
dotenv.set_key(env_file, "HARBOR_USER", os.getenv("HARBOR_USER"))
dotenv.set_key(env_file, "HARBOR_PASSWORD", os.getenv("HARBOR_PASSWORD"))


redis_service = [_.cluster_ip for _ in [_.spec for _ in core_api.list_namespaced_service(namespace=DATALAB_NAMESPACE).items if _.metadata.name =='redis-master']]
if redis_service:
     dotenv.set_key(env_file, "REDIS_HOST", redis_service[0])

t()

print("MONGODB START ")


def check_mongodb_initialized():
    api_instance = client.CoreV1Api()
    exec_command = ['/bin/sh', '-c', "echo 'rs.status()'|/usr/bin/mongo"]
    resp = stream(api_instance.connect_get_namespaced_pod_exec, "mongo-0", "datalab",
                  container="mongo",
                  command=exec_command,
                  stderr=True, stdin=False,
                  stdout=True, tty=False)
    if "NotYetInitialized" in resp:
        print("MongoDb Cluster Initialized")
        cat_sh_file = """echo 'cfg={ _id:"rs0", members:[{ _id: 0, host :"mongo-0.mongo.datalab.svc.cluster.local:27017" },{ _id: 1, host : "mongo-1.mongo.datalab.svc.cluster.local:27017" }, { _id: 2, host : "mongo-2.mongo.datalab.svc.cluster.local:27017"}]};rs.initiate(cfg)'|/usr/bin/mongo
    echo 'rs.status()'|/data/mongodb/bin/mongo"""
        initialized_command = ['/bin/sh', '-c',
                   cat_sh_file

                               ]
        resp = stream(api_instance.connect_get_namespaced_pod_exec, "mongo-0", "datalab",
                      container="mongo",
                      command=initialized_command,
                      stderr=True, stdin=False,
                      stdout=True, tty=False)
        print(resp)


try:
    check_mongodb_initialized()
except Exception as e:
    print("MI", str(e))
print("MONGODB INITIALIZED")

con = pymongo.MongoClient('mongo-0.mongo.datalab.svc.cluster.local')
user_init_data = pickle.load(open("admin_user_model.pkl", 'rb')) #dict
permission__init_data = pickle.load(open("permission_model.pkl", 'rb')) #list
role_model_init_data = pickle.load(open("role_model.pkl", 'rb')) #list
storage_resource_allocated_init_data = pickle.load(open("storage_resource_allocated_model.pkl", 'rb')) #dict
audit_enumerate_model = pickle.load(open('audit_enumerate_model.pkl','rb'))
# Background basic information configuration-Web page configuration
platform_init_data = pickle.load(open("platform_model.pkl", 'rb'))  # Dict
indexui_init_data = pickle.load(open("index_ui_model.pkl", 'rb'))  # Dict
skeletonui_init_data = pickle.load(open("skeleton_ui_model.pkl", 'rb'))  # Dict
experimentui_init_data = pickle.load(open("experiment_ui_model.pkl", 'rb'))  # Dict
# Analysis tools： compoundstep_element
compoundstep_element_init_data = pickle.load(open("compound_step_element_model.pkl", 'rb'))  # List
# Analysis tools： compoundstep
compoundstep_init_data = pickle.load(open("compound_step_model.pkl", 'rb'))  # List
# Analysis tools： skeleton
skeleton_init_data = pickle.load(open("skeleton_model.pkl", 'rb'))  # Dict
# Experiment：DataFileSystem
dfs_init_data = pickle.load(open("data_file_system.pkl", 'rb'))  # Dict
# Experiment：task
tool_task_init_data = pickle.load(open("tool_task_model.pkl", 'rb'))  # List
# Experiment：experiment
experiment_init_data = pickle.load(open("experiment_model.pkl", 'rb'))  # Dict


#  Creating a permission tree
con['datalab']['permission_model'].find_one()
d = con['datalab']['permission_model'].find_one()
if d is None:
    print("Initialize the permission tree......")
    con['datalab']['permission_model'].insert_many(permission__init_data)


#  CreateADMIN
admin_user = con['datalab']['user_model'].find_one({"_id": "555067d443e24a1397af671e58"})
if admin_user is None:
    print("Initialize the administrator role.......")
    con['datalab']['user_model'].insert_one(user_init_data)
    print("Administrator initialization is complete  Account number: admin@datalab.cn Password:admin#U*Q!.")

#  CreateADMINStorage
storage_resource_allocated_model = con['datalab']['storage_resource_allocated_model'].find_one({"allocated_user":"555067d443e24a1397af671e58"})
if storage_resource_allocated_model is None:
    con['datalab']['storage_resource_allocated_model'].insert_one(storage_resource_allocated_init_data)

#  Create
role_model = con['datalab']['role_model'].find_one()
if role_model is None:
    print("Initialize the role tree......")
    con['datalab']['role_model'].insert_many(role_model_init_data)

#  Create
aem = con['datalab']['audit_enumerate_model'].find_one()
if aem is None:
    con['datalab']['audit_enumerate_model'].insert_many(audit_enumerate_model)

#  Create
platform = con['datalab']['platform_model'].find_one()
if platform is None:
    con['datalab']['platform_model'].insert_one(platform_init_data)

#  Create
indexui = con['datalab']['index_ui_model'].find_one()
if indexui is None:
    con['datalab']['index_ui_model'].insert_one(indexui_init_data)

#  CreateExperiment
experimentui = con['datalab']['experiment_ui_model'].find_one()
if experimentui is None:
    con['datalab']['experiment_ui_model'].insert_one(experimentui_init_data)

#  CreateAnalysis tools
skeletonui = con['datalab']['skeleton_ui_model'].find_one()
if skeletonui is None:
    con['datalab']['skeleton_ui_model'].insert_one(skeletonui_init_data)

# CreateAnalysis tools
# compoundstep_element: List
compoundstep_element = con['datalab']['compound_step_element_model'].find_one()
if compoundstep_element is None:
    con['datalab']['compound_step_element_model'].insert_many(compoundstep_element_init_data)
# compoundstep: List
compoundstep = con['datalab']['compound_step_model'].find_one()
if compoundstep is None:
    con['datalab']['compound_step_model'].insert_many(compoundstep_init_data)
# skeleton: Dict
skeleton = con['datalab']['skeleton_model'].find_one()
if skeleton is None:
    con['datalab']['skeleton_model'].insert_one(skeleton_init_data)


# CreateExperiment
# DataFileSystem: Dict
dfs = con['datalab']['data_file_system'].find_one()
if dfs is None:
    con['datalab']['data_file_system'].insert_one(dfs_init_data)
# task: List
tool_task = con['datalab']['tool_task_model'].find_one()
if tool_task is None:
    con['datalab']['tool_task_model'].insert_many(tool_task_init_data)
# experiment: Dict
experiment = con['datalab']['experiment_model'].find_one()
if experiment is None:
    con['datalab']['experiment_model'].insert_one(experiment_init_data)


faas_gateway = [_.cluster_ip for _ in [_.spec for _ in core_api.list_namespaced_service(namespace=DATALAB_NAMESPACE).items if _.metadata.name =='gateway-external']]
if faas_gateway:
     dotenv.set_key(env_file, "FaaS_GATEWAY", "http://" + faas_gateway[0] + ":8080")
     dotenv.set_key(env_file, "ASYNC_FUNCTION_DOMAIN", "http://" + faas_gateway[0] + ":8080/async-function/")
     dotenv.set_key(env_file, "FUNCTION_DOMAIN", "http://" + faas_gateway[0] + ":8080/function/")


harbor_url = os.getenv("HARBOR_URL")
harbor_user = os.getenv("HARBOR_USER")
harbor_password = os.getenv("HARBOR_PASSWORD")
os.system(f"docker login {harbor_url} -u {harbor_user} -p {harbor_password}")
s = f"kubectl create secret docker-registry harbor-secret --docker-server={harbor_url} --docker-email=test@test.com  --docker-username={harbor_user}  --docker-password={harbor_password} -n datalab"
os.system(s)
s = f"kubectl create secret docker-registry harbor-secret --docker-server={harbor_url} --docker-email=test@test.com  --docker-username={harbor_user}  --docker-password={harbor_password} -n openfaas"
os.system(s)
s = "kubectl patch sewrviceaccount default -n datalab -p " + "'{" + '"imagePullSecrets":[{'+ '"name":"harbor-secret"}]' +"}'"
os.system(s)
s = "kubectl patch serviceaccount default -n openfaas -p " + "'{" + '"imagePullSecrets":[{'+ '"name":"harbor-secret"}]' +"}'"
os.system(s)



