from .node_admin_auth import is_node_admin


def node_admin(request):
    return {"is_node_admin": is_node_admin(request)}
