bl_info = {
    "name": "Procedural Room Generator",
    "author": "Kuzey Kayra Eyioğlu",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Generator",
    "description": "Create editable procedural rooms with floors, walls, and boolean-based holes.",
    "category": "Add Mesh",
}

import bpy
import math


# Clean old prototype classes if this script is re-run in Blender
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
    return 0


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


def remove_cutters_and_booleans(obj):
    for mod in list(obj.modifiers):
        if mod.type == "BOOLEAN":
            obj.modifiers.remove(mod)

    for child in list(obj.children):
        if child.name.startswith("Hole_Cutter"):
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


def update_part_cut(self, context):
    obj = self.id_data
    remove_cutters_and_booleans(obj)

    for index, hole in enumerate(self.holes):
        cutter_name = f"Hole_Cutter_{index + 1}"
        rot = math.radians(hole.rotation)

        if obj.name == "Floor":
            local_location = (hole.x, hole.y, 0)

            if hole.shape == "SQUARE":
                create_square_cutter(
                    obj,
                    cutter_name,
                    local_location,
                    (hole.width, hole.depth, 2),
                    (0, 0, rot),
                )
            else:
                create_polygon_cutter(
                    obj,
                    cutter_name,
                    local_location,
                    (hole.width, hole.depth, 2),
                    (0, 0, rot),
                    get_hole_vertices(hole.shape),
                )

        elif obj.name.startswith("Wall_"):
            local_location = (hole.x, 0, hole.z)

            if hole.shape == "SQUARE":
                create_square_cutter(
                    obj,
                    cutter_name,
                    local_location,
                    (hole.width, hole.depth, hole.height),
                    (0, rot, 0),
                )
            else:
                create_polygon_cutter(
                    obj,
                    cutter_name,
                    local_location,
                    (hole.width, hole.height, hole.depth),
                    (math.pi / 2, 0, rot),
                    get_hole_vertices(hole.shape),
                )


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


def update_room(self, context):
    room = self.id_data

    sides = int(self.shape)
    width = self.width
    depth = self.depth
    height = self.height
    thickness = self.thickness

    old_part_data = {}

    for child in list(room.children):
        base_name = child.name.split(".")[0]

        if base_name == "Floor" or base_name.startswith("Wall_"):
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

    if "Floor" in old_part_data:
        for data in old_part_data["Floor"]:
            hole = floor.generator_part.holes.add()
            hole.shape = data["shape"]
            hole.width = data["width"]
            hole.depth = data["depth"]
            hole.height = data["height"]
            hole.x = data["x"]
            hole.y = data["y"]
            hole.z = data["z"]
            hole.rotation = data["rotation"]

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

        key = f"Wall_{i + 1}"

        if key in old_part_data:
            for data in old_part_data[key]:
                hole = wall.generator_part.holes.add()
                hole.shape = data["shape"]
                hole.width = data["width"]
                hole.depth = data["depth"]
                hole.height = data["height"]
                hole.x = data["x"]
                hole.y = data["y"]
                hole.z = data["z"]
                hole.rotation = data["rotation"]

        update_part_cut(wall.generator_part, context)


class GeneratorRoomProps(bpy.types.PropertyGroup):
    is_room: bpy.props.BoolProperty(default=False)
    show_contents: bpy.props.BoolProperty(name="Contents", default=False)

    shape: bpy.props.EnumProperty(
        name="Shape",
        items=[
            ("3", "Triangle", ""),
            ("4", "Square", ""),
            ("5", "Pentagon", ""),
            ("6", "Hexagon", ""),
        ],
        default="4",
        update=update_room,
    )

    width: bpy.props.FloatProperty(name="Width", default=6, min=1, update=update_room)
    depth: bpy.props.FloatProperty(name="Depth", default=6, min=1, update=update_room)
    height: bpy.props.FloatProperty(name="Height", default=3, min=1, update=update_room)
    thickness: bpy.props.FloatProperty(name="Thickness", default=0.2, min=0.05, update=update_room)


class GeneratorSettings(bpy.types.PropertyGroup):
    create_type: bpy.props.EnumProperty(
        name="Create Type",
        items=[
            ("ROOM", "Room", ""),
            ("FLOOR", "Floor", "Coming soon"),
            ("MOUNTAIN", "Mountain", "Coming soon"),
        ],
        default="ROOM",
    )


class GENERATOR_OT_create(bpy.types.Operator):
    bl_idname = "generator.create"
    bl_label = "Create"
    bl_description = "Create a new procedural object"

    def execute(self, context):
        settings = context.scene.generator_settings

        if settings.create_type == "ROOM":
            rooms = [
                obj for obj in context.scene.objects
                if obj.type == "EMPTY" and obj.generator_room.is_room
            ]

            parent = bpy.data.objects.new(f"Room {len(rooms) + 1}", None)
            context.collection.objects.link(parent)

            parent.generator_room.is_room = True
            parent.generator_room.shape = "4"
            parent.generator_room.width = 6
            parent.generator_room.depth = 6
            parent.generator_room.height = 3
            parent.generator_room.thickness = 0.2

            update_room(parent.generator_room, context)

        return {'FINISHED'}


class GENERATOR_PT_panel(bpy.types.Panel):
    bl_label = "Generator"
    bl_idname = "GENERATOR_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Generator"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.generator_settings

        layout.prop(settings, "create_type")
        layout.operator("generator.create", text="Create")
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
            box.label(text=room.name)

            props = room.generator_room
            box.prop(props, "shape")
            box.prop(props, "width")
            box.prop(props, "depth")
            box.prop(props, "height")
            box.prop(props, "thickness")

            box.separator()
            box.prop(props, "show_contents", text="Contents")

            if props.show_contents:
                for child in room.children:
                    if child.name.startswith("Hole_Cutter"):
                        continue

                    part_box = box.box()
                    part_box.label(text=child.name)

                    add_btn = part_box.operator("generator.add_hole", text="Add Hole")
                    add_btn.object_name = child.name

                    part = child.generator_part

                    for i, hole in enumerate(part.holes):
                        hole_box = part_box.box()

                        row = hole_box.row()
                        row.label(text=f"Hole {i + 1}")
                        remove_btn = row.operator("generator.remove_hole", text="X")
                        remove_btn.object_name = child.name
                        remove_btn.index = i

                        hole_box.prop(hole, "shape")
                        hole_box.prop(hole, "width")
                        hole_box.prop(hole, "depth")

                        if child.name == "Floor":
                            hole_box.prop(hole, "x")
                            hole_box.prop(hole, "y")
                            hole_box.prop(hole, "rotation")

                        elif child.name.startswith("Wall_"):
                            hole_box.prop(hole, "height")
                            hole_box.prop(hole, "x")
                            hole_box.prop(hole, "z")
                            hole_box.prop(hole, "rotation")


def register():
    bpy.utils.register_class(GeneratorHoleProps)
    bpy.utils.register_class(GeneratorPartProps)
    bpy.utils.register_class(GeneratorRoomProps)
    bpy.utils.register_class(GeneratorSettings)
    bpy.utils.register_class(GENERATOR_OT_add_hole)
    bpy.utils.register_class(GENERATOR_OT_remove_hole)
    bpy.utils.register_class(GENERATOR_OT_create)
    bpy.utils.register_class(GENERATOR_PT_panel)

    bpy.types.Object.generator_part = bpy.props.PointerProperty(type=GeneratorPartProps)
    bpy.types.Object.generator_room = bpy.props.PointerProperty(type=GeneratorRoomProps)
    bpy.types.Scene.generator_settings = bpy.props.PointerProperty(type=GeneratorSettings)


def unregister():
    del bpy.types.Object.generator_part
    del bpy.types.Object.generator_room
    del bpy.types.Scene.generator_settings

    bpy.utils.unregister_class(GENERATOR_PT_panel)
    bpy.utils.unregister_class(GENERATOR_OT_create)
    bpy.utils.unregister_class(GENERATOR_OT_remove_hole)
    bpy.utils.unregister_class(GENERATOR_OT_add_hole)
    bpy.utils.unregister_class(GeneratorSettings)
    bpy.utils.unregister_class(GeneratorRoomProps)
    bpy.utils.unregister_class(GeneratorPartProps)
    bpy.utils.unregister_class(GeneratorHoleProps)


if __name__ == "__main__":
    register()
