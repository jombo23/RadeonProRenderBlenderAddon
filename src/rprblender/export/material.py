import bpy

from rprblender.engine.context import RPRContext
from rprblender.nodes.blender_nodes import ShaderNodeOutputMaterial

from rprblender.utils import logging
log = logging.Log(tag='export.Material')


def key(material: (str, tuple), *, input_socket_key='Surface'):
    if input_socket_key == 'Surface':
        return material

    return (material, input_socket_key)


def get_material_output_node(material):
    """ Finds output node in material tree and exports it """
    if not material.node_tree:
        # there could be a situation when node_tree is None
        return None

    return next((node for node in material.node_tree.nodes
                 if node.bl_idname == 'ShaderNodeOutputMaterial' and node.is_active_output),
                None)


def get_material_nodes_by_type(material, bl_idname):
    """ Find material nodes with bl_idname type name """
    return (node for node in material.node_tree.nodes if node.bl_idname == bl_idname)


def has_uv_map_node(material) -> bool:
    """ Check if material has any UV Map node """
    uv_map_node = next(get_material_nodes_by_type(material, 'ShaderNodeUVMap'), None)
    return uv_map_node is not None


def get_material_input_node(material, input_socket_key: str):
    """ Find the material node attached to output node 'input_socket_key' input """
    output_node = get_material_output_node(material)
    if not output_node:
        return None

    socket_in = output_node.inputs[input_socket_key]
    if not socket_in.is_linked or not socket_in.links[0].is_valid:
        return None

    return socket_in.links[0].from_node


def sync(rpr_context: RPRContext, material: bpy.types.Material, input_socket_key='Surface', *,
         obj: bpy.types.Object = None):
    """
    If material exists: returns existing material unless force_update is used
    In other cases: returns None
    """

    log(f"sync {material} '{input_socket_key}'; obj {obj}")

    if isinstance(obj, bpy.types.Mesh) and has_uv_map_node(material):
        # only Mesh objects have UV mapping and RPR data field
        mat_key = key((material.name, obj.data.rpr.uv_sets_names), input_socket_key=input_socket_key)
    else:
        mat_key = key(material.name, input_socket_key=input_socket_key)

    rpr_material = rpr_context.materials.get(mat_key, None)
    if rpr_material:
        return rpr_material

    output_node = get_material_output_node(material)
    if not output_node:
        log("No output node", material)
        return None

    node_parser = ShaderNodeOutputMaterial(rpr_context, material, output_node, None, obj=obj, material_key=mat_key)
    rpr_material = node_parser.final_export(input_socket_key)

    if rpr_material:
        rpr_context.set_material_node_as_material(mat_key, rpr_material)

    return rpr_material


def sync_update(rpr_context: RPRContext, material: bpy.types.Material, obj: bpy.types.Object = None):
    """ Recreates existing material """

    log("sync_update", material)

    if isinstance(obj, bpy.types.Mesh) and has_uv_map_node(material):
        # only Mesh objects have UV mapping and RPR data field
        mat_key = key((material.name, obj.data.rpr.uv_sets_names),)
    else:
        mat_key = key(material.name)

    if mat_key in rpr_context.materials:
        rpr_context.remove_material(mat_key)

    sync(rpr_context, material, obj=obj)

    displacement_key = key(mat_key, input_socket_key='Displacement')
    if displacement_key in rpr_context.materials:
        rpr_context.remove_material(displacement_key)

    sync(rpr_context, material, input_socket_key='Displacement')

    return True
