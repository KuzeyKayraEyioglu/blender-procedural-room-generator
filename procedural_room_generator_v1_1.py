bl_info = {
    "name": "Procedural Room Generator",
    "author": "Kuzey Kayra Eyioğlu",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Generator",
    "description": "Create editable procedural rooms with custom sides, walls, holes, roofs, frames, doors, window lights, and procedural/custom materials.",
    "category": "Add Mesh",
}

import bpy
import math
from mathutils import Vector, Matrix

# Clean old registered classes while testing in Blender Text Editor.
for cls_name in [
    "ROOMGEN_PT_panel", "ROOMGEN_OT_create", "RoomGenSettings",
    "GENERATOR_PT_panel", "GENERATOR_OT_create",
    "GeneratorSettings", "GeneratorRoomProps",
    "GeneratorPartProps", "GeneratorHoleProps",
    "GENERATOR_OT_add_hole", "GENERATOR_OT_remove_hole",
]:
    cls = getattr(bpy.types, cls_name, None)
    if cls:
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

for prop in ["roomgen_settings", "generator_settings"]:
    if hasattr(bpy.types.Scene, prop):
        try:
            delattr(bpy.types.Scene, prop)
        except Exception:
            pass

for prop in ["generator_room", "generator_part"]:
    if hasattr(bpy.types.Object, prop):
        try:
            delattr(bpy.types.Object, prop)
        except Exception:
            pass


def get_shape_rotation(sides):
    if sides == 3:
        return math.pi / 2
    if sides == 4:
        return math.pi / 4
    if sides == 5:
        return math.pi / 2
    if sides == 6:
        return math.pi / 6
    return math.pi / sides


def get_hole_vertices(shape):
    if shape == "TRIANGLE":
        return 3
    if shape == "PENTAGON":
        return 5
    if shape == "HEXAGON":
        return 6
    if shape == "ROUND":
        return 48
    return 4


def delete_recursive(obj):
    for child in list(obj.children):
        delete_recursive(child)
    bpy.data.objects.remove(obj, do_unlink=True)


def remove_cutters_frames_and_booleans(obj):
    for mod in list(obj.modifiers):
        if mod.type == "BOOLEAN":
            obj.modifiers.remove(mod)

    for child in list(obj.children):
        if child.name.startswith("Hole_Cutter") or child.name.startswith("Frame_") or child.name.startswith("Door_") or child.name.startswith("Window_Light_"):
            delete_recursive(child)


def update_hole_item(self, context):
    obj = self.id_data
    if obj and hasattr(obj, "generator_part"):
        update_part_cut(obj.generator_part, context)


class GeneratorHoleProps(bpy.types.PropertyGroup):
    shape: bpy.props.EnumProperty(
        name="Shape",
        items=[
            ("SQUARE", "Square", ""),
            ("ROUND", "Round", ""),
            ("TRIANGLE", "Triangle", ""),
            ("PENTAGON", "Pentagon", ""),
            ("HEXAGON", "Hexagon", ""),
        ],
        default="SQUARE",
        update=update_hole_item,
    )

    width: bpy.props.FloatProperty(name="Width", default=1.0, min=0.1, update=update_hole_item)
    depth: bpy.props.FloatProperty(name="Depth", default=1.0, min=0.05, update=update_hole_item)
    height: bpy.props.FloatProperty(name="Height", default=1.0, min=0.1, update=update_hole_item)

    x: bpy.props.FloatProperty(name="X", default=0, update=update_hole_item)
    y: bpy.props.FloatProperty(name="Y", default=0, update=update_hole_item)
    z: bpy.props.FloatProperty(name="Z", default=0, update=update_hole_item)

    rotation: bpy.props.FloatProperty(name="Rotation", default=0, update=update_hole_item)

    frame_type: bpy.props.EnumProperty(
        name="Frame",
        items=[
            ("NONE", "None", "No frame"),
            ("DOOR", "Door Frame", "Add a simple door frame around this wall hole"),
            ("WINDOW", "Window Frame", "Add a window frame with a center cross around this wall hole"),
        ],
        default="NONE",
        update=update_hole_item,
    )

    frame_sides: bpy.props.EnumProperty(
        name="Door Frame Side",
        items=[
            ("ONE", "One Sided", "Create the door frame on one side of the wall"),
            ("TWO", "Two Sided", "Create the door frame on both sides of the wall"),
        ],
        default="ONE",
        update=update_hole_item,
    )

    frame_thickness: bpy.props.FloatProperty(
        name="Frame Thickness",
        default=0.08,
        min=0.01,
        update=update_hole_item,
    )

    frame_depth: bpy.props.FloatProperty(
        name="Frame Depth",
        default=0.2001,
        min=0.01,
        update=update_hole_item,
    )

    frame_offset: bpy.props.FloatProperty(
        name="Frame Offset",
        default=0.4,
        description="Move the frame forward/backward on the wall surface",
        update=update_hole_item,
    )

    enable_door: bpy.props.BoolProperty(
        name="Enable Door",
        default=False,
        description="Create a simple door panel inside this wall hole",
        update=update_hole_item,
    )

    door_hinge: bpy.props.EnumProperty(
        name="Door Hinge",
        items=[
            ("LEFT", "Left", "Hinge marker on the left side"),
            ("RIGHT", "Right", "Hinge marker on the right side"),
            ("TOP", "Top", "Hinge marker on the top side"),
            ("BOTTOM", "Bottom", "Hinge marker on the bottom side"),
        ],
        default="LEFT",
        update=update_hole_item,
    )

    enable_window_light: bpy.props.BoolProperty(
        name="Window Area Light",
        default=False,
        description="Create an area light shining through this window hole",
        update=update_hole_item,
    )

    window_light_power: bpy.props.FloatProperty(
        name="Light Power",
        default=450.0,
        min=0.0,
        update=update_hole_item,
    )

    window_light_size: bpy.props.FloatProperty(
        name="Light Size",
        default=2.0,
        min=0.05,
        update=update_hole_item,
    )

    window_light_distance: bpy.props.FloatProperty(
        name="Light Distance",
        default=0.55,
        min=0.0,
        update=update_hole_item,
    )

    window_light_angle: bpy.props.FloatProperty(
        name="Light Down Angle",
        default=0.0,
        min=-90.0,
        max=90.0,
        update=update_hole_item,
    )

    door_open_angle: bpy.props.FloatProperty(
        name="Door Open Angle",
        default=0.0,
        min=-180.0,
        max=180.0,
        update=update_hole_item,
    )


class GeneratorPartProps(bpy.types.PropertyGroup):
    holes: bpy.props.CollectionProperty(type=GeneratorHoleProps)


def create_square_cutter(obj, name, local_location, dimensions, rotation_euler):
    bpy.ops.mesh.primitive_cube_add(size=1)

    cutter = bpy.context.object
    cutter.name = name
    cutter.parent = obj
    cutter.location = local_location
    cutter.rotation_euler = rotation_euler
    cutter.scale = dimensions

    cutter.display_type = "WIRE"
    cutter.hide_render = True
    cutter.hide_select = True
    cutter.hide_viewport = True

    mod = obj.modifiers.new(name=name + "_Boolean", type="BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "FAST"


def create_polygon_cutter(obj, name, local_location, scale, rotation_euler, vertices):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=0.5, depth=1)

    cutter = bpy.context.object
    cutter.name = name
    cutter.parent = obj
    cutter.location = local_location
    cutter.rotation_euler = rotation_euler
    cutter.scale = scale

    cutter.display_type = "WIRE"
    cutter.hide_render = True
    cutter.hide_select = True
    cutter.hide_viewport = True

    mod = obj.modifiers.new(name=name + "_Boolean", type="BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "FAST"


def create_oriented_box_cutter(obj, name, center, axis_x, axis_y, axis_z, dimensions):
    """Create a cube cutter whose local X/Y/Z axes follow custom vectors."""
    axis_x = axis_x.normalized()
    axis_y = axis_y.normalized()
    axis_z = axis_z.normalized()
    sx, sy, sz = dimensions

    bpy.ops.mesh.primitive_cube_add(size=1)
    cutter = bpy.context.object
    cutter.name = name

    mat = Matrix((
        (axis_x.x * sx, axis_y.x * sy, axis_z.x * sz, center.x),
        (axis_x.y * sx, axis_y.y * sy, axis_z.y * sz, center.y),
        (axis_x.z * sx, axis_y.z * sy, axis_z.z * sz, center.z),
        (0, 0, 0, 1),
    ))
    cutter.matrix_world = obj.matrix_world @ mat
    cutter.parent = obj
    cutter.matrix_parent_inverse = obj.matrix_world.inverted()

    cutter.display_type = "WIRE"
    cutter.hide_render = True
    cutter.hide_select = True
    cutter.hide_viewport = True

    mod = obj.modifiers.new(name=name + "_Boolean", type="BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "FAST"


def set_principled_value(principled, input_name, value):
    if input_name in principled.inputs:
        principled.inputs[input_name].default_value = value


def set_principled_value(principled, input_name, value):
    if input_name in principled.inputs:
        principled.inputs[input_name].default_value = value


def make_rgba(color):
    try:
        if len(color) == 3:
            return (color[0], color[1], color[2], 1.0)
        if len(color) == 4:
            return tuple(color)
    except Exception:
        pass
    return (0.8, 0.8, 0.8, 1.0)


def load_image_safe(filepath):
    if not filepath:
        return None
    try:
        path = bpy.path.abspath(filepath)
        if not path:
            return None
        # Reuse already-loaded image if possible.
        for img in bpy.data.images:
            if img.filepath and bpy.path.abspath(img.filepath) == path:
                return img
        return bpy.data.images.load(path, check_existing=True)
    except Exception:
        return None


def create_basic_material(name, color, metallic=0.0, smoothness=0.35, procedural="NONE", image_path="", texture_scale=18.0, texture_distortion=8.0):
    """Create/update a material with Unity-like Color / Metallic / Smoothness and optional image texture."""
    color = make_rgba(color)

    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)

    mat.diffuse_color = color
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")

    set_principled_value(principled, "Base Color", color)
    set_principled_value(principled, "Metallic", metallic)
    set_principled_value(principled, "Roughness", max(0.0, min(1.0, 1.0 - smoothness)))
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    img = load_image_safe(image_path)
    if img:
        texcoord = nodes.new("ShaderNodeTexCoord")
        mapping = nodes.new("ShaderNodeMapping")
        tex_image = nodes.new("ShaderNodeTexImage")
        tex_image.image = img
        if "Scale" in mapping.inputs:
            mapping.inputs["Scale"].default_value[0] = max(texture_scale, 0.001)
            mapping.inputs["Scale"].default_value[1] = max(texture_scale, 0.001)
            mapping.inputs["Scale"].default_value[2] = 1.0
        links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex_image.inputs["Vector"])
        links.new(tex_image.outputs["Color"], principled.inputs["Base Color"])
        return mat

    if procedural == "PARQUET":
        wave = nodes.new("ShaderNodeTexWave")
        wave.inputs["Scale"].default_value = max(texture_scale, 0.001)
        wave.inputs["Distortion"].default_value = texture_distortion

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.25
        ramp.color_ramp.elements[0].color = (0.35, 0.18, 0.07, 1)
        ramp.color_ramp.elements[1].position = 1.0
        ramp.color_ramp.elements[1].color = color

        links.new(wave.outputs["Color"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], principled.inputs["Base Color"])

    elif procedural == "WALL":
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = max(texture_scale, 0.001)
        noise.inputs["Detail"].default_value = 8
        noise.inputs["Roughness"].default_value = 0.55

        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.035
        bump.inputs["Distance"].default_value = 0.08

        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        if "Normal" in principled.inputs:
            links.new(bump.outputs["Normal"], principled.inputs["Normal"])

    elif procedural == "DOOR":
        wave = nodes.new("ShaderNodeTexWave")
        wave.inputs["Scale"].default_value = max(texture_scale, 0.001)
        wave.inputs["Distortion"].default_value = texture_distortion

        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.20
        ramp.color_ramp.elements[0].color = (0.25, 0.12, 0.04, 1)
        ramp.color_ramp.elements[1].position = 1.0
        ramp.color_ramp.elements[1].color = color

        links.new(wave.outputs["Color"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], principled.inputs["Base Color"])

    return mat

def get_or_create_frame_material():
    return create_basic_material("RoomGen_Frame_Material", (0.55, 0.32, 0.16, 1.0), 0.0, 0.35, "DOOR")


def get_room_materials(room_props):
    floor_mat = create_basic_material(
        "RoomGen_Auto_Parquet_Floor",
        room_props.floor_color,
        room_props.floor_metallic,
        room_props.floor_smoothness,
        "PARQUET" if room_props.auto_floor_texture else "NONE",
        room_props.floor_image_path if room_props.floor_material_mode == "IMAGE" else "",
        room_props.floor_texture_scale,
        room_props.floor_texture_distortion,
    )
    wall_mat = create_basic_material(
        "RoomGen_Auto_Wall",
        room_props.wall_color,
        room_props.wall_metallic,
        room_props.wall_smoothness,
        "WALL" if room_props.auto_wall_texture else "NONE",
        room_props.wall_image_path if room_props.wall_material_mode == "IMAGE" else "",
        room_props.wall_texture_scale,
        0.0,
    )
    door_mat = create_basic_material(
        "RoomGen_Auto_Door",
        room_props.door_color,
        room_props.door_metallic,
        room_props.door_smoothness,
        "DOOR" if room_props.auto_door_texture else "NONE",
        room_props.door_image_path if room_props.door_material_mode == "IMAGE" else "",
        room_props.door_texture_scale,
        room_props.door_texture_distortion,
    )
    return floor_mat, wall_mat, door_mat

def add_box_to_mesh(verts, faces, center, dimensions):
    cx, cy, cz = center
    sx, sy, sz = dimensions
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2

    base = len(verts)
    verts.extend([
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ])
    faces.extend([
        [base + 0, base + 1, base + 2, base + 3],
        [base + 4, base + 7, base + 6, base + 5],
        [base + 0, base + 4, base + 5, base + 1],
        [base + 1, base + 5, base + 6, base + 2],
        [base + 2, base + 6, base + 7, base + 3],
        [base + 3, base + 7, base + 4, base + 0],
    ])


def create_frame_mesh(parent, name, boxes):
    """Create one selectable frame object from many non-overlapping box parts."""
    verts = []
    faces = []
    for center, dimensions in boxes:
        add_box_to_mesh(verts, faces, center, dimensions)

    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent

    mat = get_or_create_frame_material()
    obj.data.materials.append(mat)

    obj.display_type = "TEXTURED"
    obj.hide_render = False
    obj.hide_select = False
    obj.hide_viewport = False
    return obj


def door_frame_y_positions(hole):
    d = hole.frame_depth
    front_y = -hole.depth / 2 - d / 2 + hole.frame_offset
    if hole.frame_sides == "TWO":
        back_y = hole.depth / 2 + d / 2 - hole.frame_offset
        return [("Front", front_y), ("Back", back_y)]
    return [("Front", front_y)]


def create_door_frame(parent, hole, index):
    # Single mesh per side. Pieces touch each other, but do not overlap.
    t = hole.frame_thickness
    d = hole.frame_depth

    side_h = hole.height
    top_w = hole.width + t * 2

    left_x = hole.x - hole.width / 2 - t / 2
    right_x = hole.x + hole.width / 2 + t / 2
    side_z = hole.z
    top_z = hole.z + hole.height / 2 + t / 2

    for suffix, y in door_frame_y_positions(hole):
        boxes = [
            ((left_x, y, side_z), (t, d, side_h)),
            ((right_x, y, side_z), (t, d, side_h)),
            ((hole.x, y, top_z), (top_w, d, t)),
        ]
        create_frame_mesh(parent, f"Frame_Door_Hole_{index + 1}_{suffix}", boxes)


def create_window_frame(parent, hole, index):
    # One selectable mesh. Blocks are laid out to touch, not intersect.
    t = hole.frame_thickness
    d = hole.frame_depth
    y = -hole.depth / 2 - d / 2 + hole.frame_offset

    outer_h = hole.height + t * 2

    left_x = hole.x - hole.width / 2 - t / 2
    right_x = hole.x + hole.width / 2 + t / 2
    bottom_z = hole.z - hole.height / 2 - t / 2
    top_z = hole.z + hole.height / 2 + t / 2

    # Outer frame: side pieces include the corner height, top/bottom stay between them.
    boxes = [
        ((left_x, y, hole.z), (t, d, outer_h)),
        ((right_x, y, hole.z), (t, d, outer_h)),
        ((hole.x, y, top_z), (hole.width, d, t)),
        ((hole.x, y, bottom_z), (hole.width, d, t)),
    ]

    # Center plus: vertical piece and two horizontal arms. No cube stacks at the middle.
    inner_w_each_side = max((hole.width - t) / 2, 0.01)
    boxes.extend([
        ((hole.x, y, hole.z), (t, d, hole.height)),
        ((hole.x - (t / 2 + inner_w_each_side / 2), y, hole.z), (inner_w_each_side, d, t)),
        ((hole.x + (t / 2 + inner_w_each_side / 2), y, hole.z), (inner_w_each_side, d, t)),
    ])

    create_frame_mesh(parent, f"Frame_Window_Hole_{index + 1}", boxes)


def get_parent_room(obj):
    current = obj
    while current:
        if hasattr(current, "generator_room") and current.generator_room.is_room:
            return current
        current = current.parent
    return None


def create_door_panel(parent, hole, index):
    """Create a simple door panel inside the wall hole. Object origin is placed on the chosen hinge."""
    room = get_parent_room(parent)
    door_mat = None
    if room:
        _, _, door_mat = get_room_materials(room.generator_room)
    if door_mat is None:
        door_mat = create_basic_material("RoomGen_Auto_Door", (0.42, 0.22, 0.08, 1), 0.0, 0.35, "DOOR")

    door_gap = 0.035
    door_w = max(hole.width - door_gap * 2, 0.05)
    door_h = max(hole.height - door_gap * 2, 0.05)
    door_d = min(max(hole.depth * 0.55, 0.035), 0.08)
    hinge_t = 0.035

    # Door center in wall-local coordinates.
    center = Vector((hole.x, 0, hole.z))

    # Put the object's origin on the hinge edge, not in the middle.
    if hole.door_hinge == "LEFT":
        origin = Vector((hole.x - door_w / 2, 0, hole.z))
        panel_center = (door_w / 2, 0, 0)
        hinge_center = (hinge_t / 2, -door_d / 2 - 0.006, 0)
        hinge_dims = (hinge_t, 0.018, door_h)
        rot_axis = 'Z'
    elif hole.door_hinge == "RIGHT":
        origin = Vector((hole.x + door_w / 2, 0, hole.z))
        panel_center = (-door_w / 2, 0, 0)
        hinge_center = (-hinge_t / 2, -door_d / 2 - 0.006, 0)
        hinge_dims = (hinge_t, 0.018, door_h)
        rot_axis = 'Z'
    elif hole.door_hinge == "TOP":
        origin = Vector((hole.x, 0, hole.z + door_h / 2))
        panel_center = (0, 0, -door_h / 2)
        hinge_center = (0, -door_d / 2 - 0.006, -hinge_t / 2)
        hinge_dims = (door_w, 0.018, hinge_t)
        rot_axis = 'X'
    else:  # BOTTOM
        origin = Vector((hole.x, 0, hole.z - door_h / 2))
        panel_center = (0, 0, door_h / 2)
        hinge_center = (0, -door_d / 2 - 0.006, hinge_t / 2)
        hinge_dims = (door_w, 0.018, hinge_t)
        rot_axis = 'X'

    boxes = [
        (panel_center, (door_w, door_d, door_h)),
        (hinge_center, hinge_dims),
    ]

    door = create_frame_mesh(parent, f"Door_Panel_Hole_{index + 1}", boxes)
    door.location = origin
    door.data.materials.clear()
    door.data.materials.append(door_mat)

    if rot_axis == 'Z':
        angle = math.radians(hole.door_open_angle)
        if hole.door_hinge == "RIGHT":
            angle *= -1
        door.rotation_euler.z = angle
    else:
        angle = math.radians(hole.door_open_angle)
        if hole.door_hinge == "BOTTOM":
            angle *= -1
        door.rotation_euler.x = angle

    return door

def create_window_area_light(parent, hole, index):
    """Create a controllable area light through the window. Parent space keeps it attached to the wall."""
    light_data = bpy.data.lights.new(f"Window_Light_Hole_{index + 1}", type="AREA")
    light_data.energy = hole.window_light_power
    light_data.size = 0.001  # hard-shadow style: never use soft area shadows
    light_data.use_shadow = True

    light_obj = bpy.data.objects.new(f"Window_Light_Hole_{index + 1}", light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.parent = parent

    # In local wall space: center it on the hole and place it slightly outside the wall.
    # The distance value makes the patch more stable and easier to tune.
    light_obj.location = (hole.x, -hole.depth / 2 - hole.window_light_distance + hole.frame_offset, hole.z)

    # Area lights emit from their local -Z side. This rotation points it through the window and slightly downward.
    light_obj.rotation_euler = (math.radians(90 + hole.window_light_angle), 0, 0)
    return light_obj

def create_pyramid_side_cutter(obj, hole, index):
    verts = [obj.data.vertices[i].co.copy() for i in range(len(obj.data.vertices))]
    if len(verts) < 3:
        return

    sorted_verts = sorted(verts, key=lambda v: v.z)
    b1 = sorted_verts[0]
    b2 = sorted_verts[1]
    peak = sorted_verts[-1]

    edge = b2 - b1
    if edge.length == 0:
        return
    edge_dir = edge.normalized()

    base_mid = (b1 + b2) / 2
    slope = peak - base_mid
    if slope.length == 0:
        return
    slope_dir = slope.normalized()

    normal = edge_dir.cross(slope_dir)
    if normal.length == 0:
        return
    normal = normal.normalized()

    # Rotate hole axes around the roof normal, like rotating a hole on a sloped wall.
    rot = Matrix.Rotation(math.radians(hole.rotation), 4, normal)
    axis_x = rot @ edge_dir
    axis_y = rot @ slope_dir
    axis_z = normal

    # X moves along roof side, Y moves up/down the roof slope. This keeps the hole on the roof plane.
    center = base_mid + edge_dir * hole.x + slope_dir * hole.y
    create_oriented_box_cutter(obj, f"Hole_Cutter_{index + 1}", center, axis_x, axis_y, axis_z, (hole.width, hole.height, hole.depth))


def create_cone_cutter(obj, hole, index):
    radius = max(obj.dimensions.x, obj.dimensions.y) / 2
    h = max(obj.dimensions.z, 0.01)
    if radius <= 0:
        return

    x = hole.x
    y = hole.y
    r = math.sqrt(x * x + y * y)
    r = min(max(r, 0.001), radius * 0.98)
    angle = math.atan2(y, x)

    # Cone local z range is approximately -h/2 to +h/2.
    z = h / 2 - (r / radius) * h
    center = Vector((math.cos(angle) * r, math.sin(angle) * r, z))

    tangent = Vector((-math.sin(angle), math.cos(angle), 0)).normalized()
    radial_down = Vector((math.cos(angle), math.sin(angle), -h / radius)).normalized()
    normal = tangent.cross(radial_down).normalized()

    rot = Matrix.Rotation(math.radians(hole.rotation), 4, normal)
    axis_x = rot @ tangent
    axis_y = rot @ radial_down
    axis_z = normal

    create_oriented_box_cutter(obj, f"Hole_Cutter_{index + 1}", center, axis_x, axis_y, axis_z, (hole.width, hole.height, hole.depth))


def update_part_cut(self, context):
    obj = self.id_data
    remove_cutters_frames_and_booleans(obj)

    for index, hole in enumerate(self.holes):
        cutter_name = f"Hole_Cutter_{index + 1}"
        rot = math.radians(hole.rotation)

        if obj.name == "Floor":
            local_location = (hole.x, hole.y, 0)

            if hole.shape == "SQUARE":
                create_square_cutter(obj, cutter_name, local_location, (hole.width, hole.depth, 2), (0, 0, rot))
            else:
                create_polygon_cutter(obj, cutter_name, local_location, (hole.width, hole.depth, 2), (0, 0, rot), get_hole_vertices(hole.shape))

        elif obj.name.startswith("Roof_Flat"):
            roof_height = max(obj.dimensions.z, 0.1)
            local_location = (hole.x, hole.y, roof_height / 2)

            if hole.shape == "SQUARE":
                create_square_cutter(obj, cutter_name, local_location, (hole.width, hole.depth, roof_height + 1), (0, 0, rot))
            else:
                create_polygon_cutter(obj, cutter_name, local_location, (hole.width, hole.depth, roof_height + 1), (0, 0, rot), get_hole_vertices(hole.shape))

        elif obj.name.startswith("Roof_PyramidSide"):
            # Square cutter is most stable for sloped roof holes.
            create_pyramid_side_cutter(obj, hole, index)

        elif obj.name.startswith("Roof_Cone"):
            # Experimental: X/Y choose point on cone footprint, cutter snaps to cone slope.
            create_cone_cutter(obj, hole, index)

        elif obj.name.startswith("Wall_"):
            local_location = (hole.x, 0, hole.z)

            if hole.shape == "SQUARE":
                create_square_cutter(obj, cutter_name, local_location, (hole.width, hole.depth, hole.height), (0, rot, 0))
            else:
                create_polygon_cutter(obj, cutter_name, local_location, (hole.width, hole.height, hole.depth), (math.pi / 2, 0, rot), get_hole_vertices(hole.shape))

            # Frames are only generated for wall holes.
            # When a frame is enabled, push it forward by default so it visibly sits on the wall surface.
            if hole.frame_type != "NONE" and abs(hole.frame_offset) < 0.0001:
                hole.frame_offset = 0.4

            if hole.frame_type == "DOOR":
                create_door_frame(obj, hole, index)
            elif hole.frame_type == "WINDOW":
                create_window_frame(obj, hole, index)
                if hole.enable_window_light:
                    create_window_area_light(obj, hole, index)

            if hole.enable_door:
                create_door_panel(obj, hole, index)


class GENERATOR_OT_add_hole(bpy.types.Operator):
    bl_idname = "generator.add_hole"
    bl_label = "Add Hole"
    bl_description = "Add a new editable hole to the selected room part"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if obj:
            hole = obj.generator_part.holes.add()
            hole.shape = "SQUARE"
            hole.width = 1.0
            hole.depth = 1.0
            hole.height = 1.0
            hole.x = 0
            hole.y = 0
            hole.z = 0
            hole.rotation = 0
            hole.frame_type = "NONE"
            hole.frame_sides = "ONE"
            hole.frame_thickness = 0.08
            hole.frame_depth = 0.2001
            hole.frame_offset = 0.4
            hole.enable_door = False
            hole.door_hinge = "LEFT"
            hole.enable_window_light = False
            hole.window_light_power = 450.0
            hole.window_light_size = 2.0
            hole.window_light_distance = 0.55
            hole.window_light_angle = 0.0
            hole.door_open_angle = 0.0
            update_part_cut(obj.generator_part, context)

        return {'FINISHED'}


class GENERATOR_OT_remove_hole(bpy.types.Operator):
    bl_idname = "generator.remove_hole"
    bl_label = "Remove Hole"
    bl_description = "Remove this hole from the room part"

    object_name: bpy.props.StringProperty()
    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if obj and 0 <= self.index < len(obj.generator_part.holes):
            obj.generator_part.holes.remove(self.index)
            update_part_cut(obj.generator_part, context)

        return {'FINISHED'}


def create_flat_roof(room, context, points, top_z, roof_height, overhang):
    center_points = []

    for x, y in points:
        length = math.sqrt(x * x + y * y)
        if length > 0:
            x += (x / length) * overhang
            y += (y / length) * overhang
        center_points.append((x, y))

    sides = len(center_points)

    bottom = [(x, y, 0) for x, y in center_points]
    top = [(x, y, roof_height) for x, y in center_points]

    verts = bottom + top

    faces = []
    faces.append(list(range(sides)))
    faces.append(list(range(sides, sides * 2)))

    for i in range(sides):
        faces.append([
            i,
            (i + 1) % sides,
            ((i + 1) % sides) + sides,
            i + sides,
        ])

    mesh = bpy.data.meshes.new("FlatRoofMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    roof = bpy.data.objects.new("Roof_Flat", mesh)
    context.collection.objects.link(roof)
    roof.parent = room
    roof.location.z = top_z

    return roof


def create_pyramid_roof(room, context, points, top_z, roof_height, overhang):
    adjusted_points = []

    for x, y in points:
        length = math.sqrt(x * x + y * y)
        if length > 0:
            x += (x / length) * overhang
            y += (y / length) * overhang
        adjusted_points.append((x, y))

    sides = len(adjusted_points)
    peak = (0, 0, top_z + roof_height)
    roof_sides = []

    # Create each pyramid side as its own selectable object, so each side can have its own roof hole.
    for i in range(sides):
        p1 = adjusted_points[i]
        p2 = adjusted_points[(i + 1) % sides]
        verts = [(p1[0], p1[1], top_z), (p2[0], p2[1], top_z), peak]
        faces = [[0, 1, 2]]

        mesh = bpy.data.meshes.new(f"PyramidRoofSideMesh_{i + 1}")
        mesh.from_pydata(verts, [], faces)
        mesh.update()

        side = bpy.data.objects.new(f"Roof_PyramidSide_{i + 1}", mesh)
        context.collection.objects.link(side)
        side.parent = room
        roof_sides.append(side)

    return roof_sides


def create_cone_roof(room, context, points, top_z, roof_height, overhang):
    max_radius = max(math.sqrt(x * x + y * y) for x, y in points) + overhang

    bpy.ops.mesh.primitive_cone_add(
        vertices=48,
        radius1=max_radius,
        radius2=0,
        depth=roof_height,
        location=(0, 0, top_z + roof_height / 2),
        rotation=(0, 0, 0),
    )

    roof = bpy.context.object
    roof.name = "Roof_Cone"
    roof.parent = room

    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass

    return roof


def create_roof(room, context, points, height, thickness, roof_type, roof_height, roof_overhang):
    if roof_type == "NONE":
        return None

    top_z = height - thickness / 2

    if roof_type == "FLAT":
        return create_flat_roof(room, context, points, top_z, roof_height, roof_overhang)

    if roof_type == "PYRAMID":
        return create_pyramid_roof(room, context, points, top_z, roof_height, roof_overhang)

    if roof_type == "CONE":
        return create_cone_roof(room, context, points, top_z, roof_height, roof_overhang)

    return None


def copy_holes_from_old_data(obj, old_part_data, key, context):
    if key not in old_part_data:
        return

    for data in old_part_data[key]:
        hole = obj.generator_part.holes.add()
        hole.shape = data.get("shape", "SQUARE")
        hole.width = data.get("width", 1.0)
        hole.depth = data.get("depth", 1.0)
        hole.height = data.get("height", 1.0)
        hole.x = data.get("x", 0)
        hole.y = data.get("y", 0)
        hole.z = data.get("z", 0)
        hole.rotation = data.get("rotation", 0)
        hole.frame_type = data.get("frame_type", "NONE")
        hole.frame_sides = data.get("frame_sides", "ONE")
        hole.frame_thickness = data.get("frame_thickness", 0.08)
        hole.frame_depth = data.get("frame_depth", 0.2001)
        hole.frame_offset = data.get("frame_offset", 0.4)
        hole.enable_door = data.get("enable_door", False)
        hole.door_hinge = data.get("door_hinge", "LEFT")
        hole.enable_window_light = data.get("enable_window_light", False)
        hole.window_light_power = data.get("window_light_power", 450.0)
        hole.window_light_size = data.get("window_light_size", 2.0)
        hole.window_light_distance = data.get("window_light_distance", 0.55)
        hole.window_light_angle = data.get("window_light_angle", 0.0)
        hole.door_open_angle = data.get("door_open_angle", 0.0)

    update_part_cut(obj.generator_part, context)


def update_room(self, context):
    room = self.id_data

    sides = self.sides
    width = self.width
    depth = self.depth
    height = self.height
    thickness = self.thickness

    roof_type = self.roof_type
    roof_height = self.roof_height
    roof_overhang = self.roof_overhang

    old_part_data = {}

    for child in list(room.children):
        base_name = child.name.split(".")[0]

        if base_name == "Floor" or base_name.startswith("Wall_") or base_name.startswith("Roof_"):
            old_part_data[base_name] = []

            for hole in child.generator_part.holes:
                old_part_data[base_name].append({
                    "shape": hole.shape,
                    "width": hole.width,
                    "depth": hole.depth,
                    "height": hole.height,
                    "x": hole.x,
                    "y": hole.y,
                    "z": hole.z,
                    "rotation": hole.rotation,
                    "frame_type": hole.frame_type,
                    "frame_sides": hole.frame_sides,
                    "frame_thickness": hole.frame_thickness,
                    "frame_depth": hole.frame_depth,
                    "frame_offset": hole.frame_offset,
                    "enable_door": hole.enable_door,
                    "door_hinge": hole.door_hinge,
                    "enable_window_light": hole.enable_window_light,
                    "window_light_power": hole.window_light_power,
                    "window_light_size": hole.window_light_size,
                    "window_light_distance": hole.window_light_distance,
                    "window_light_angle": hole.window_light_angle,
                    "door_open_angle": hole.door_open_angle,
                })

    for child in list(room.children):
        delete_recursive(child)

    base_rotation = get_shape_rotation(sides)

    points = []
    for i in range(sides):
        angle = (2 * math.pi / sides) * i + base_rotation
        x = math.cos(angle) * width / 2
        y = math.sin(angle) * depth / 2
        points.append((x, y))

    mesh = bpy.data.meshes.new("FloorMesh")
    verts = [(x, y, -thickness / 2) for x, y in points]
    faces = [list(range(sides))]
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    floor = bpy.data.objects.new("Floor", mesh)
    context.collection.objects.link(floor)
    floor.parent = room

    floor_mat, wall_mat, door_mat = get_room_materials(self)
    floor.data.materials.append(floor_mat)

    copy_holes_from_old_data(floor, old_part_data, "Floor", context)
    update_part_cut(floor.generator_part, context)

    for i in range(sides):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % sides]

        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        angle = math.atan2(y2 - y1, x2 - x1)

        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(mid_x, mid_y, height / 2 - thickness / 2),
            rotation=(0, 0, angle),
        )

        wall = bpy.context.object
        wall.name = f"Wall_{i + 1}"
        wall.dimensions = (length, thickness, height)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        wall.parent = room
        wall.data.materials.append(wall_mat)

        key = f"Wall_{i + 1}"
        copy_holes_from_old_data(wall, old_part_data, key, context)
        update_part_cut(wall.generator_part, context)

    roof = create_roof(
        room,
        context,
        points,
        height,
        thickness,
        roof_type,
        roof_height,
        roof_overhang,
    )

    if roof:
        if isinstance(roof, list):
            for side in roof:
                copy_holes_from_old_data(side, old_part_data, side.name.split(".")[0], context)
                update_part_cut(side.generator_part, context)
        else:
            copy_holes_from_old_data(roof, old_part_data, roof.name.split(".")[0], context)
            update_part_cut(roof.generator_part, context)


class GeneratorRoomProps(bpy.types.PropertyGroup):
    is_room: bpy.props.BoolProperty(default=False)

    show_room_settings: bpy.props.BoolProperty(name="Room Settings", default=True)
    show_roof_settings: bpy.props.BoolProperty(name="Roof Settings", default=True)
    show_material_settings: bpy.props.BoolProperty(name="Materials", default=True)
    show_contents: bpy.props.BoolProperty(name="Contents", default=False)

    sides: bpy.props.IntProperty(
        name="Custom Sides",
        default=4,
        min=3,
        max=64,
        update=update_room,
    )

    width: bpy.props.FloatProperty(name="Width", default=6, min=1, update=update_room)
    depth: bpy.props.FloatProperty(name="Depth", default=6, min=1, update=update_room)
    height: bpy.props.FloatProperty(name="Height", default=3, min=1, update=update_room)
    thickness: bpy.props.FloatProperty(name="Wall Thickness", default=0.2, min=0.05, update=update_room)

    roof_type: bpy.props.EnumProperty(
        name="Roof Type",
        items=[
            ("NONE", "None", ""),
            ("FLAT", "Flat Roof", ""),
            ("PYRAMID", "Pyramid Roof", ""),
            ("CONE", "Smooth Cone Roof", ""),
        ],
        default="NONE",
        update=update_room,
    )

    roof_height: bpy.props.FloatProperty(
        name="Roof Height",
        default=0.35,
        min=0.05,
        update=update_room,
    )

    roof_overhang: bpy.props.FloatProperty(
        name="Roof Overhang",
        default=0.15,
        min=0.0,
        update=update_room,
    )



# Unity-like material values.
GeneratorRoomProps.__annotations__['auto_floor_texture'] = bpy.props.BoolProperty(
    name="Auto Parquet Floor",
    default=True,
    update=update_room,
)
GeneratorRoomProps.__annotations__['floor_color'] = bpy.props.FloatVectorProperty(
    name="Floor Color",
    subtype="COLOR",
    default=(0.55, 0.30, 0.12),
    size=3,
    min=0.0,
    max=1.0,
    update=update_room,
)
GeneratorRoomProps.__annotations__['floor_metallic'] = bpy.props.FloatProperty(name="Floor Metallic", default=0.0, min=0.0, max=1.0, update=update_room)
GeneratorRoomProps.__annotations__['floor_smoothness'] = bpy.props.FloatProperty(name="Floor Smoothness", default=0.28, min=0.0, max=1.0, update=update_room)

GeneratorRoomProps.__annotations__['auto_wall_texture'] = bpy.props.BoolProperty(
    name="Auto Wall Texture",
    default=True,
    update=update_room,
)
GeneratorRoomProps.__annotations__['wall_color'] = bpy.props.FloatVectorProperty(
    name="Wall Color",
    subtype="COLOR",
    default=(0.72, 0.70, 0.66),
    size=3,
    min=0.0,
    max=1.0,
    update=update_room,
)
GeneratorRoomProps.__annotations__['wall_metallic'] = bpy.props.FloatProperty(name="Wall Metallic", default=0.0, min=0.0, max=1.0, update=update_room)
GeneratorRoomProps.__annotations__['wall_smoothness'] = bpy.props.FloatProperty(name="Wall Smoothness", default=0.18, min=0.0, max=1.0, update=update_room)

GeneratorRoomProps.__annotations__['auto_door_texture'] = bpy.props.BoolProperty(
    name="Auto Door Texture",
    default=True,
    update=update_room,
)
GeneratorRoomProps.__annotations__['door_color'] = bpy.props.FloatVectorProperty(
    name="Door Color",
    subtype="COLOR",
    default=(0.42, 0.22, 0.08),
    size=3,
    min=0.0,
    max=1.0,
    update=update_room,
)
GeneratorRoomProps.__annotations__['door_metallic'] = bpy.props.FloatProperty(name="Door Metallic", default=0.0, min=0.0, max=1.0, update=update_room)
GeneratorRoomProps.__annotations__['door_smoothness'] = bpy.props.FloatProperty(name="Door Smoothness", default=0.35, min=0.0, max=1.0, update=update_room)

GeneratorRoomProps.__annotations__['floor_texture_scale'] = bpy.props.FloatProperty(name="Floor Tile Scale", default=8.0, min=0.1, max=100.0, update=update_room)
GeneratorRoomProps.__annotations__['floor_texture_distortion'] = bpy.props.FloatProperty(name="Floor Wood Waves", default=2.5, min=0.0, max=30.0, update=update_room)
GeneratorRoomProps.__annotations__['floor_material_mode'] = bpy.props.EnumProperty(name="Floor Material Source", items=[("AUTO", "Auto", "Use generated material"), ("IMAGE", "Image File", "Use an image texture file")], default="AUTO", update=update_room)
GeneratorRoomProps.__annotations__['floor_image_path'] = bpy.props.StringProperty(name="Floor Image", subtype="FILE_PATH", default="", update=update_room)

GeneratorRoomProps.__annotations__['wall_texture_scale'] = bpy.props.FloatProperty(name="Wall Texture Scale", default=35.0, min=0.1, max=100.0, update=update_room)
GeneratorRoomProps.__annotations__['wall_material_mode'] = bpy.props.EnumProperty(name="Wall Material Source", items=[("AUTO", "Auto", "Use generated material"), ("IMAGE", "Image File", "Use an image texture file")], default="AUTO", update=update_room)
GeneratorRoomProps.__annotations__['wall_image_path'] = bpy.props.StringProperty(name="Wall Image", subtype="FILE_PATH", default="", update=update_room)

GeneratorRoomProps.__annotations__['door_texture_scale'] = bpy.props.FloatProperty(name="Door Texture Scale", default=9.0, min=0.1, max=100.0, update=update_room)
GeneratorRoomProps.__annotations__['door_texture_distortion'] = bpy.props.FloatProperty(name="Door Wood Waves", default=8.0, min=0.0, max=30.0, update=update_room)
GeneratorRoomProps.__annotations__['door_material_mode'] = bpy.props.EnumProperty(name="Door Material Source", items=[("AUTO", "Auto", "Use generated material"), ("IMAGE", "Image File", "Use an image texture file")], default="AUTO", update=update_room)
GeneratorRoomProps.__annotations__['door_image_path'] = bpy.props.StringProperty(name="Door Image", subtype="FILE_PATH", default="", update=update_room)


class GENERATOR_OT_create(bpy.types.Operator):
    bl_idname = "generator.create"
    bl_label = "Create Room"
    bl_description = "Create a new procedural room"

    def execute(self, context):
        rooms = [
            obj for obj in context.scene.objects
            if obj.type == "EMPTY" and obj.generator_room.is_room
        ]

        parent = bpy.data.objects.new(f"Room {len(rooms) + 1}", None)
        context.collection.objects.link(parent)

        parent.generator_room.is_room = True
        parent.generator_room.sides = 4
        parent.generator_room.width = 6
        parent.generator_room.depth = 6
        parent.generator_room.height = 3
        parent.generator_room.thickness = 0.2
        parent.generator_room.roof_type = "NONE"
        parent.generator_room.roof_height = 0.35
        parent.generator_room.roof_overhang = 0.15
        parent.generator_room.auto_floor_texture = True
        parent.generator_room.auto_wall_texture = True
        parent.generator_room.auto_door_texture = True
        parent.generator_room.floor_texture_scale = 8.0
        parent.generator_room.floor_texture_distortion = 2.5
        parent.generator_room.wall_texture_scale = 35.0
        parent.generator_room.door_texture_scale = 9.0
        parent.generator_room.door_texture_distortion = 8.0
        parent.generator_room.floor_material_mode = "AUTO"
        parent.generator_room.wall_material_mode = "AUTO"
        parent.generator_room.door_material_mode = "AUTO"

        update_room(parent.generator_room, context)

        return {'FINISHED'}


class GENERATOR_PT_panel(bpy.types.Panel):
    bl_label = "Procedural Room Generator"
    bl_idname = "GENERATOR_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Generator"

    def draw(self, context):
        layout = self.layout

        header_box = layout.box()
        header_box.label(text="Create")
        header_box.operator("generator.create", text="Create Room", icon="MESH_CUBE")
        layout.separator()

        rooms = [
            obj for obj in context.scene.objects
            if obj.type == "EMPTY" and obj.generator_room.is_room
        ]

        if not rooms:
            layout.label(text="No rooms created yet.")
            return

        for room in rooms:
            box = layout.box()

            row = box.row()
            row.label(text=room.name, icon="HOME")

            props = room.generator_room

            room_box = box.box()
            room_box.prop(
                props,
                "show_room_settings",
                text="Room Settings",
                icon="TRIA_DOWN" if props.show_room_settings else "TRIA_RIGHT",
            )

            if props.show_room_settings:
                room_box.prop(props, "sides")
                room_box.prop(props, "width")
                room_box.prop(props, "depth")
                room_box.prop(props, "height")
                room_box.prop(props, "thickness")

            roof_box = box.box()
            roof_box.prop(
                props,
                "show_roof_settings",
                text="Roof Settings",
                icon="TRIA_DOWN" if props.show_roof_settings else "TRIA_RIGHT",
            )

            if props.show_roof_settings:
                roof_box.prop(props, "roof_type")

                if props.roof_type != "NONE":
                    roof_box.prop(props, "roof_height")
                    roof_box.prop(props, "roof_overhang")

                    if props.roof_type == "PYRAMID":
                        roof_box.label(text="Pyramid roof creates separate RoofSide parts.", icon="INFO")
                    elif props.roof_type == "CONE":
                        roof_box.label(text="Cone roof holes are experimental.", icon="INFO")

            material_box = box.box()
            material_box.prop(
                props,
                "show_material_settings",
                text="Materials",
                icon="TRIA_DOWN" if props.show_material_settings else "TRIA_RIGHT",
            )

            if props.show_material_settings:
                material_box.label(text="Floor / Parquet", icon="MATERIAL")
                material_box.prop(props, "floor_material_mode")
                if props.floor_material_mode == "IMAGE":
                    material_box.prop(props, "floor_image_path")
                else:
                    material_box.prop(props, "auto_floor_texture")
                material_box.prop(props, "floor_color")
                material_box.prop(props, "floor_texture_scale")
                material_box.prop(props, "floor_texture_distortion")
                material_box.prop(props, "floor_smoothness")
                material_box.prop(props, "floor_metallic")

                material_box.separator()
                material_box.label(text="Wall", icon="MATERIAL")
                material_box.prop(props, "wall_material_mode")
                if props.wall_material_mode == "IMAGE":
                    material_box.prop(props, "wall_image_path")
                else:
                    material_box.prop(props, "auto_wall_texture")
                material_box.prop(props, "wall_color")
                material_box.prop(props, "wall_texture_scale")
                material_box.prop(props, "wall_smoothness")
                material_box.prop(props, "wall_metallic")

                material_box.separator()
                material_box.label(text="Door", icon="MATERIAL")
                material_box.prop(props, "door_material_mode")
                if props.door_material_mode == "IMAGE":
                    material_box.prop(props, "door_image_path")
                else:
                    material_box.prop(props, "auto_door_texture")
                material_box.prop(props, "door_color")
                material_box.prop(props, "door_texture_scale")
                material_box.prop(props, "door_texture_distortion")
                material_box.prop(props, "door_smoothness")
                material_box.prop(props, "door_metallic")

            contents_box = box.box()
            contents_box.prop(
                props,
                "show_contents",
                text="Contents / Holes",
                icon="TRIA_DOWN" if props.show_contents else "TRIA_RIGHT",
            )

            if props.show_contents:
                for child in room.children:
                    if child.name.startswith("Hole_Cutter") or child.name.startswith("Frame_") or child.name.startswith("Door_") or child.name.startswith("Window_Light_"):
                        continue

                    part_box = contents_box.box()
                    part_box.label(text=child.name, icon="MESH_DATA")

                    add_btn = part_box.operator("generator.add_hole", text="Add Hole", icon="ADD")
                    add_btn.object_name = child.name

                    part = child.generator_part

                    for i, hole in enumerate(part.holes):
                        hole_box = part_box.box()

                        row = hole_box.row()
                        row.label(text=f"Hole {i + 1}", icon="MOD_BOOLEAN")
                        remove_btn = row.operator("generator.remove_hole", text="", icon="X")
                        remove_btn.object_name = child.name
                        remove_btn.index = i

                        hole_box.prop(hole, "shape")
                        hole_box.prop(hole, "width")
                        hole_box.prop(hole, "depth")

                        if child.name == "Floor" or child.name.startswith("Roof_Flat") or child.name.startswith("Roof_Cone"):
                            hole_box.prop(hole, "x")
                            hole_box.prop(hole, "y")
                            if child.name.startswith("Roof_Cone"):
                                hole_box.prop(hole, "height", text="Hole Slope Size")
                            hole_box.prop(hole, "rotation")

                        elif child.name.startswith("Roof_PyramidSide"):
                            hole_box.prop(hole, "height", text="Hole Slope Size")
                            hole_box.prop(hole, "x", text="Side X")
                            hole_box.prop(hole, "y", text="Slope Y")
                            hole_box.prop(hole, "rotation")

                        elif child.name.startswith("Wall_"):
                            hole_box.prop(hole, "height")
                            hole_box.prop(hole, "x")
                            hole_box.prop(hole, "z")
                            hole_box.prop(hole, "rotation")
                            hole_box.separator()
                            hole_box.prop(hole, "frame_type")
                            if hole.frame_type != "NONE":
                                if hole.frame_type == "DOOR":
                                    hole_box.prop(hole, "frame_sides")
                                hole_box.prop(hole, "frame_thickness")
                                hole_box.prop(hole, "frame_depth")
                                hole_box.prop(hole, "frame_offset")

                            hole_box.separator()
                            hole_box.prop(hole, "enable_door")
                            if hole.enable_door:
                                hole_box.prop(hole, "door_hinge")
                                hole_box.prop(hole, "door_open_angle")

                            if hole.frame_type == "WINDOW":
                                hole_box.separator()
                                hole_box.prop(hole, "enable_window_light")
                                if hole.enable_window_light:
                                    hole_box.prop(hole, "window_light_power")
                                    hole_box.prop(hole, "window_light_distance")
                                    hole_box.prop(hole, "window_light_angle")


def register():
    bpy.utils.register_class(GeneratorHoleProps)
    bpy.utils.register_class(GeneratorPartProps)
    bpy.utils.register_class(GeneratorRoomProps)
    bpy.utils.register_class(GENERATOR_OT_add_hole)
    bpy.utils.register_class(GENERATOR_OT_remove_hole)
    bpy.utils.register_class(GENERATOR_OT_create)
    bpy.utils.register_class(GENERATOR_PT_panel)

    bpy.types.Object.generator_part = bpy.props.PointerProperty(type=GeneratorPartProps)
    bpy.types.Object.generator_room = bpy.props.PointerProperty(type=GeneratorRoomProps)


def unregister():
    del bpy.types.Object.generator_part
    del bpy.types.Object.generator_room

    bpy.utils.unregister_class(GENERATOR_PT_panel)
    bpy.utils.unregister_class(GENERATOR_OT_create)
    bpy.utils.unregister_class(GENERATOR_OT_remove_hole)
    bpy.utils.unregister_class(GENERATOR_OT_add_hole)
    bpy.utils.unregister_class(GeneratorRoomProps)
    bpy.utils.unregister_class(GeneratorPartProps)
    bpy.utils.unregister_class(GeneratorHoleProps)


if __name__ == "__main__":
    register()
