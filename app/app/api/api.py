from fastapi import APIRouter

from app.api.endpoints import (
    admin,
    analyses2,
    auth,
    datasets,
    datasets_s3,
    experiments,
    index,
    roles,
    skeletons2,
    tasks,
    tool_source,
    tools,
    ui,
    umt,
    users,
    notebook,
    digital_asset,
    microservices,

)

from app.api.center import (
    msg,
    storage as center_storage,
    resources,
    audit as center_audit
)
from app.api.images import docker_images
from app.api.labboard import results as datalab_dashboard
from app.api.component import (
    components,
    component_chain,
    functions_deploy,
    serialize,
    standalone
)
from app.api.center import fairlink
api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(admin.router, prefix="/admin")
api_router.include_router(analyses2.router, prefix="/analyses", tags=["analyses"])
# api_router.include_router(analyses_steps.router, prefix="/analyses/steps", tags=["analyses/steps"])    # deprecated
# api_router.include_router(analyses_steps_elements.router, prefix="/analyses/steps/elements", tags=["analyses/steps/elements"])    # deprecated
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])   # FIXME: Deprecated: Use the datasets_s3 substitution
api_router.include_router(datasets_s3.router, prefix="/datasets_s3", tags=["datasets"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
api_router.include_router(index.router, prefix="/index", tags=["index"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
# api_router.include_router(skeletons.router, prefix="/skeletons", tags=["skeletons"])  # deprecated
api_router.include_router(skeletons2.router, prefix="/skeletons", tags=["skeletons"])
# api_router.include_router(skeletons_compoundsteps.router, prefix="/skeletons/compoundsteps", tags=["skeletons/compoundsteps"])    # deprecated
# api_router.include_router(skeletons_compoundsteps_elements.router, prefix="/skeletons/compoundsteps/elements", tags=["skeletons/compoundsteps/elements"])  # deprecated
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(tool_source.router, prefix="/toolsource", tags=["toolsource"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(ui.router, prefix="/ui", tags=["ui"])
api_router.include_router(umt.router, prefix="/umt", tags=["umt"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(docker_images.router, prefix="/images", tags=["images"])
api_router.include_router(components.router, prefix="/components", tags=["components"])
api_router.include_router(functions_deploy.router, prefix="/deploy", tags=['function_deploy'])
api_router.include_router(standalone.router, prefix="/standalone_deploy", tags=['function_deploy'])
api_router.include_router(center_storage.router, prefix='/data_center', tags=['personal_data_center'])
api_router.include_router(center_audit.router, prefix='/audit_center', tags=['personal_audit_center'])
api_router.include_router(datalab_dashboard.router, prefix='/board', tags=['datalab_dashboard'])
api_router.include_router(resources.router, prefix='/resource', tags=['personal_resource'])
api_router.include_router(component_chain.router, prefix='/flow', tags=['component_chain'])
api_router.include_router(fairlink.router, prefix='/fair', tags=["personal center fair data"])
api_router.include_router(msg.router, prefix='/msg', tags=["personal center message"])
api_router.include_router(serialize.router, prefix='/serialize', tags=["serialize functions"])
api_router.include_router(notebook.router, prefix='/notebook', tags=["Online Edit Code"])
api_router.include_router(digital_asset.router, prefix="/digital", tags=["Digital Asset"])
api_router.include_router(microservices.router, prefix="/microservices", tags=["microservices"])
