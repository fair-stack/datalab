from app.core.config import settings


API_STR = settings.API_STR


# invalid set: Not included False， Because False It could be a value
INVALID_UPDATE_VALUE_TYPES = [None, "", [], {}, (), [{}], [()], [[]]]


# Access control related
ENDPOINTS_FOR_UNAUTHORIZED = [
    f'{settings.API_STR}/emailVerify',
    f'{settings.API_STR}/index/skeletons/',
    f'{settings.API_STR}/index/skeletons/detail',
    f'{settings.API_STR}/index/skeletons/aggs',
    f'{settings.API_STR}/login',
    f'{settings.API_STR}/passwordForget',
    f'{settings.API_STR}/passwordReset',
    f'{settings.API_STR}/roles/',
    f'{settings.API_STR}/skeletons/',
    f'{settings.API_STR}/ui/experimentui',
    f'{settings.API_STR}/ui/indexui',
    f'{settings.API_STR}/ui/indexui/file',
    f'{settings.API_STR}/ui/platform',
    f'{settings.API_STR}/ui/skeletonui',
    f'{settings.API_STR}/users/',
    f'{settings.API_STR}/board/',
]


# {role_code: dict()}
PERMISSION_MAP = {
    # <level-1>
    "L1-01": {"name": "Analysis tools",  "is_group": True, "checked": True, "uri": f"{API_STR}/skeletons/"},
    "L1-02": {"name": "Experiment",     "is_group": True, "checked": True, "uri": f"{API_STR}/experiments/"},
    "L1-03": {"name": "Managing Configuration",  "is_group": True, "checked": False, "uri": f"{API_STR}/admin/"},

    # <level-2>
    # L1-01:
    #
    "L2-01": {"name": "Analysis tools", "is_group": False, "checked": True, "uri": f"{API_STR}/analyses/"},      # Analysis tools，You can do the analysis：analyses
    # L1-02:
    "L2-02": {"name": "Experiment", "is_group": False, "checked": True, "uri":  f"{API_STR}/experiments/"},
    "L2-03": {"name": "Publishing tools", "is_group": False, "checked": True, "uri": f"{API_STR}/skeletons/"},
    # L1-03:
    "L2-04": {"name": "Basic information", "is_group": True, "checked": False, "uri": f"{API_STR}/admin/base/"},
    "L2-05": {"name": "User management", "is_group": True, "checked": False, "uri":  f"{API_STR}/admin/user_adm/"},
    "L2-06": {"name": "Tool management", "is_group": True, "checked": False, "uri": f"{API_STR}/admin/skel_adm/"},
    "L2-07": {"name": "Experiment", "is_group": True, "checked": False, "uri": f"{API_STR}/admin/expt_adm/"},
    "L2-08": {"name": "Resource management", "is_group": True, "checked": False, "uri": f"{API_STR}/admin/res_adm/"},
    "L2-09": {"name": "Component management", "is_group": True, "checked": False, "uri": f"{API_STR}/admin/tool_adm/"},

    # <level-3>
    # L2-04:
    "L3-01": {"name": "Statistical information", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/base/stats/"},
    "L3-02": {"name": "Web page configuration", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/base/ui/"},
    "L3-03": {"name": "System configuration", "is_group": False, "checked": False, "uri":  f"{API_STR}/admin/base/sysconf/"},
    # L2-05:
    "L3-04": {"name": "User management", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/user_adm/users/"},
    "L3-05": {"name": "Role management", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/user_adm/roles/"},
    # L2-06:
    "L3-06": {"name": "Tool management", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/skel_adm/skeletons/"},
    "L3-07": {"name": "Audit tool", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/skel_adm/audit/"},
    "L3-16": {"name": "Analysis management", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/skel_adm/analyses/"},
    # incrementallyL3
    # L2-07:
    "L3-08": {"name": "Experiment", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/experiments/"},
    # L2-08:
    "L3-09": {"name": "Resource management",  "is_group": False, "checked": False, "uri":  f"{API_STR}/admin/res_adm/data/"},
    "L3-10": {"name": "Resource management", "is_group": False, "checked": False, "uri":  f"{API_STR}/admin/res_adm/computing/"},
    "L3-11": {"name": "Resource management", "is_group": False, "checked": False, "uri":  f"{API_STR}/admin/res_adm/storage/"},
    "L3-12": {"name": "Resource audit",   "is_group": False, "checked": False, "uri":  f"{API_STR}/admin/res_adm/audit/"},
    # L2-09:
    "L3-13": {"name": "Analyzing class Components", "is_group": True, "checked": False, "uri": f"{API_STR}/admin/tool_adm/analysis/"},
    "L3-14": {"name": "Visual components", "is_group": True, "checked": False, "uri": f"{API_STR}/admin/tool_adm/visualization/"},
    "L3-15": {"name": "Component auditing",   "is_group": False, "checked": False, "uri": f"{API_STR}/admin/tool_adm/audit/"},

    # <level-4>
    # L3-13:
    "L4-01": {"name": "Component list",    "is_group": False, "checked": False, "uri": f"{API_STR}/admin/tool_adm/analysis/"},
    "L4-02": {"name": "Component Directory Configuration", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/tool_adm/components_tree/tree"},
    # L3-14:
    "L4-03": {"name": "Component list",    "is_group": False, "checked": False, "uri": f"{API_STR}/admin/tool_adm/visualization/"},
    "L4-04": {"name": "Component Directory Configuration", "is_group": False, "checked": False, "uri": f"{API_STR}/admin/tool_adm/visualization/"},

}


PERMISSION_TOPOLOGY = [
    {
        "code": "L1-01",
        "name": "Analysis tools",
        "children": [
            {"code": "L2-01", "name": "Analysis tools"}
        ]
    },

    {
        "code": "L1-02",
        "name": "Experiment",
        "children": [
            {"code": "L2-02", "name": "Experiment"},
            {"code": "L2-03", "name": "Publishing tools"}
        ]
    },

    {
        "code": "L1-03",
        "name": "Managing Configuration",
        "children": [
            {
                "code": "L2-04",
                "name": "Basic information",
                "children": [
                    {"code": "L3-01", "name": "Statistical information"},
                    {"code": "L3-02", "name": "Web page configuration"},
                    {"code": "L3-03", "name": "System configuration"},
                ]
            },
            {
                "code": "L2-05",
                "name": "User management",
                "children": [
                    {"code": "L3-04", "name": "User management"},
                    {"code": "L3-05", "name": "Role management"},
                ]
            },
            {
                "code": "L2-06",
                "name": "Tool management",
                "children": [
                    {"code": "L3-06", "name": "Tool management"},
                    {"code": "L3-07", "name": "Audit tool"},
                    {"code": "L3-16", "name": "Analysis management"},
                ]
            },
            {
                "code": "L2-07",
                "name": "Experiment",
                "children": [
                    {"code": "L3-08", "name": "Experiment"}
                ]
            },
            {
                "code": "L2-08",
                "name": "Resource management",
                "children": [
                    {"code": "L3-09", "name": "Resource management"},
                    {"code": "L3-10", "name": "Resource management"},
                    {"code": "L3-11", "name": "Resource management"},
                    {"code": "L3-12", "name": "Resource audit"}
                ]
            },
            {
                "code": "L2-09",
                "name": "Component management",
                "children": [
                    {
                        "code": "L3-13",
                        "name": "Analyzing class Components",
                        "children": [
                            {"code": "L4-01", "name": "Component list"},
                            {"code": "L4-02", "name": "Component Directory Configuration"},
                        ]
                    },
                    {
                        "code": "L3-14",
                        "name": "Visual components",
                        "children": [
                            {"code": "L4-03", "name": "Component list"},
                            {"code": "L4-04", "name": "Component Directory Configuration"}
                        ]
                    },
                    {
                        "code": "L3-15",
                        "name": "Component auditing"
                    }
                ]
            },
        ]
    }

]


# Preset roles
ROLES_INNATE_MAP = {
    'ADMIN': {
        "code": "ADMIN",
        "name": "Super admin"
    },
    'USER_SENIOR': {
        "code": "USER_SENIOR",
        "name": "Advanced User"
    },
    'USER_NORMAL': {
        "code": "USER_NORMAL",
        "name": "Regular users"
    }
}


# Skeleton
SKELETON_COMPOUNDSTEPS_MULTITASK_MODES = ['ALL', 'SELECT', 'MULTI_SELECT']


# Analysis
ANALYSIS_STATES = ['COMPLETED', 'INCOMPLETED']
ANALYSIS_STEP_STATES = ['READY', 'SUCCESS', 'ERROR', 'PENDING']


# caching cache
# prefix: skeleton
CACHE_PREFIX_SKELETON = "skeleton"
CACHE_PREFIX_ADMIN_SKELETON = "admin_skeleton"
CACHE_PREFIX_ADMIN_SKELETON_AUDIT = "admin_skeleton_audit"
# prefix: auth
CACHE_PREFIX_LOGIN = "login"
CACHE_PREFIX_PASSWORD_FORGET = "passwordForget"
CACHE_PREFIX_PASSWORD_RESET = "passwordReset"
CACHE_PREFIX_BearerTokenAuthBackend = "BearerTokenAuthBackend"


# Menu logo menu
MENU_SKELETON = 'skeleton'
MENU_ADMIN_SKELETON = 'admin_skeleton'
MENU_ADMIN_SKELETON_AUDIT = 'admin_skeleton_audit'
