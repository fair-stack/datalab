from fastapi import APIRouter

from app.api.endpoints.admin import (
    analyses2,
    experiments,
    permissions,
    roles,
    skeletons2,
    sysconf,
    tools,
    ui,
    users,
    audit,
    resources,
    public_data,
    microservices
)

from app.api.endpoints.admin import audit
# from app.api.endpoints.admin.deprecated import skeletons, analyses

router = APIRouter()


router.include_router(ui.router, prefix="/base/ui", tags=['admin/base/ui'])
router.include_router(sysconf.router, prefix="/base/sysconf", tags=['admin/base/sysconf'])
router.include_router(experiments.router, prefix="/experiments", tags=['admin/experiments'])
router.include_router(permissions.router, prefix="/permissions", tags=['admin/permissions'])
# router.include_router(skeletons.router, prefix="/skel_adm", tags=['admin/skel_adm'])                    # deprecated
router.include_router(skeletons2.router, prefix="/skel_adm", tags=['admin/skel_adm'])
# router.include_router(analyses.router, prefix="/skel_adm/analyses", tags=['admin/skel_adm/analyses'])   # deprecated
router.include_router(analyses2.router, prefix="/skel_adm/analyses", tags=['admin/skel_adm/analyses'])
router.include_router(tools.router, prefix="/tool_adm", tags=['admin/tool_adm'])
router.include_router(roles.router, prefix="/user_adm/roles", tags=['admin/user_adm/roles'])
router.include_router(users.router, prefix="/user_adm/users", tags=['admin/user_adm/users'])
router.include_router(audit.router, prefix="/audit", tags=['admin/audit'])
router.include_router(resources.router, prefix="/res_adm", tags=['admin/res_adm'])
router.include_router(public_data.router, prefix="/res_adm/data", tags=['admin/res_adm/data'])
router.include_router(microservices.router, prefix="/microservices", tags=["admin/microservices"])
