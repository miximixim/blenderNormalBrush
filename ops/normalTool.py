import bpy
import bgl
import blf
import gpu
import mathutils
import math
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils


circleSegs = 64
circleCoords = [(math.sin(((2 * math.pi * i) / circleSegs)), math.cos((math.pi * 2 * i) / circleSegs), 0) for i in range(circleSegs + 1)]

vecZ = mathutils.Vector((0, 0, 1))
vecX = mathutils.Vector((1, 0, 0))

def calc_gizmo_transform(obj, coord, normal, ray_origin):
    pos = obj.matrix_world @ coord

    norm = normal.copy()
    norm.resize_4d()
    norm.w = 0
    mIT = obj.matrix_world.copy()
    mIT.invert()
    mIT.transpose()
    norm = mIT @ norm
    norm.resize_3d()
    norm.normalize()

    eye_offset = pos - ray_origin
#                    eye_offset_along_view = eye_offset.project(view_vector)
#                    print(eye_offset_along_view)
#                    radius = eye_offset_along_view.length / 5
    radius = eye_offset.length / 5
    mS = mathutils.Matrix.Scale(radius, 4)
    
    axis = norm.cross(vecZ)
    if axis.length_squared < .0001:
        axis = matutils.Vector(vecX)
    else:
        axis.normalize()
    angle = -math.acos(norm.dot(vecZ))
    
    quat = mathutils.Quaternion(axis, angle)
#                    print (quat)

    mR = quat.to_matrix()
#                    print (mR)
    mR.resize_4x4()
#                    print (mR)
    
    mT = mathutils.Matrix.Translation(pos)
#                    print (mT)

    m = mT @ mR @ mS
    return m


def draw_callback(self, context):
#    print("draw_callback_px");
    ctx = bpy.context

    region = context.region
    rv3d = context.region_data
#    coord = event.mouse_region_x, event.mouse_region_y

    viewport_center = (region.x + region.width / 2, region.y + region.height / 2)
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, viewport_center)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, viewport_center)

    # get the ray from the viewport and mouse
#    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
#    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)


    coords = [(0, 0, 0), (0, 0, 1)]
    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": coords})
    batchCircle = batch_for_shader(shader, 'LINE_STRIP', {"pos": circleCoords})

    shader.bind();
    shader.uniform_float("color", (1, 1, 0, 1))


    for obj in ctx.selected_objects:
        if obj.type == 'MESH':
            success = obj.update_from_editmode()
            mesh = obj.data

    
#            bm = bmesh.new()
#            bm.from_mesh(mesh)
#            for v in bm.verts:
#bm.to_mesh(me)
#bm.free()

            for v in mesh.vertices:
                if v.select:
                    
                    m = calc_gizmo_transform(obj, v.co, v.normal, ray_origin)

            
                    gpu.matrix.push()
                    gpu.matrix.multiply_matrix(m)
                    shader.uniform_float("color", (1, 1, 0, 1))
                    batch.draw(shader)
                    
                    gpu.matrix.push()
                    gpu.matrix.multiply_matrix(mathutils.Matrix.Rotation(math.radians(90.0), 4, 'Y'))
                    shader.uniform_float("color", (1, 0, 0, 1))
                    batchCircle.draw(shader)
                    gpu.matrix.pop()
                    
                    gpu.matrix.push()
                    gpu.matrix.multiply_matrix(mathutils.Matrix.Rotation(math.radians(90.0), 4, 'X'))
                    shader.uniform_float("color", (0, 1, 0, 1))
                    batchCircle.draw(shader)
                    gpu.matrix.pop()

                    shader.uniform_float("color", (0, 0, 1, 1))
                    batchCircle.draw(shader)
                    
                    gpu.matrix.pop()


#    print("mouse points", len(self.mouse_path))

#    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
#    blf.position(font_id, 15, 30, 0)
#    blf.size(font_id, 20, 72)
#    blf.draw(font_id, "Hello Word " + str(len(self.mouse_path)))

    # 50% alpha, 2 pixel width line
#    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
#    bgl.glEnable(bgl.GL_BLEND)
#    bgl.glLineWidth(2)
#    batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": self.mouse_path})
#    shader.bind()
#    shader.uniform_float("color", (0.0, 0.0, 0.0, 0.5))
#    batch.draw(shader)

    # restore opengl defaults
#    bgl.glLineWidth(1)
#    bgl.glDisable(bgl.GL_BLEND)

def manip_normal(context, event):
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

    ray_target = ray_origin + view_vector


class ModalDrawOperator(bpy.types.Operator):
    """Draw a line with the mouse"""
    bl_idname = "kitfox.normal_tool"
    bl_label = "Normal Tool Kitfox"


    prop_brush_type : bpy.props.EnumProperty(
        items=(
            ('FIXED', "Fixed", "Normals are in a fixed direction"),
            ('ATTRACT', "Attract", "Normals point toward target object"),
            ('REPEL', "Repel", "Normals point away from target object")
        ),
        default='FIXED'
    )
    
    prop_strength : bpy.props.FloatProperty(
        name="Strength", description="Amount to adjust mesh normal", default = 1, min=0, max = 1
    )

    prop_normal = bpy.props.FloatVectorProperty(name="Normal", description="Direction of normal in Fixed mode", default = (0, 1, 0))
    prop_target = bpy.props.StringProperty(name="Target", description="Object Attract and Repel mode reference", default="")
    
    dragging = False

    def mouse_down(self, context, event):
        mouse_pos = (event.mouse_region_x, event.mouse_region_y)

        ctx = bpy.context

        region = context.region
        rv3d = context.region_data
    #    coord = event.mouse_region_x, event.mouse_region_y

#        viewport_center = (region.x + region.width / 2, region.y + region.height / 2)
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse_pos)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse_pos)
        
        center = None
        center_count = 0

        for obj in ctx.selected_objects:
            if obj.type == 'MESH':
                success = obj.update_from_editmode()
                mesh = obj.data
                mesh.use_auto_smooth = True
                
                for v in mesh.vertices:
                    if v.select:
                        if center_count == 0:
                            center = v.co
                        else:
                            center += v.co
                        center_count += 1
                        
                        m = calc_gizmo_transform(obj, v.co, v.normal, ray_origin)


        self.drag_start_pos = mouse_pos
            
        pass

    def modal(self, context, event):
#        self._context = context

#        for obj in context.selected_objects:
#            if obj.type == 'MESH':
#                mesh = obj.data
#                success = mesh.update_from_editmode()
            
        context.area.tag_redraw()

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            # allow navigation
            return {'PASS_THROUGH'}

        elif event.type == 'MOUSEMOVE':
#            self.mouse_path.append((event.mouse_region_x, event.mouse_region_y))
            pass
        elif event.type == 'LEFTMOUSE':
#            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
#            return {'FINISHED'}
            self.mouse_down(context, event)
#            manip_normal(context, event)
            pass

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            print("norm tool cancelled")
            return {'CANCELLED'}

        return {'PASS_THROUGH'}
#        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            # the arguments we pass the the callback
            args = (self, context)
            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._context = context
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback, args, 'WINDOW', 'POST_VIEW')

            self.mouse_path = []

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


class NormalToolPanel(bpy.types.Panel):

    """Panel for the Normal Tool on tool shelf"""
    bl_label = "Normal Tool Panel"
    bl_idname = "3D_VIEW_PT_normal_tool"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
#    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        obj = context.object

        row = layout.row()
        row.operator("kitfox.normal_tool")

class NormalToolPropsPanel(bpy.types.Panel):

    """Properties Panel for the Normal Tool on tool shelf"""
    bl_label = "Normal Tool Properties Panel"
    bl_idname = "3D_VIEW_PT_normal_tool_props"
    bl_space_type = 'VIEW_3D'
#    bl_region_type = 'TOOL_PROPS'
    bl_region_type = 'UI'
#    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        obj = context.object

#        row = layout.row()
#        row.label(text="Tool Settings", icon='WORLD_DATA')

#        row = layout.row()
#        row.label(text="Active object is: " + obj.name)
#        row = layout.row()
#        row.prop(obj, "name")

#        row = layout.row()
#        row.label(text="walla - Tool Properties", icon='WORLD_DATA')

        props = layout.operator(ModalDrawOperator.bl_idname)

        row = layout.row()
        row.prop(obj, "kitfox_nt_brush_type", expand=True)
        props.prop_brush_type = obj.kitfox_nt_brush_type

        row = layout.row()
        row.prop(obj, "kitfox_nt_strength", expand=True)
        props.prop_strength = obj.kitfox_nt_strength

        row = layout.row()
        row.prop(obj, "kitfox_nt_normal", expand=True)
        props.prop_normal = obj.kitfox_nt_normal

        row = layout.row()
        row.prop(obj, "kitfox_nt_target", expand=True)
        props.prop_target = obj.kitfox_nt_target
        
#        row = layout.row()
#        row.operator("kitfox.normal_tool")


def register():
    bpy.types.Object.kitfox_nt_brush_type = bpy.props.EnumProperty(
        items=(
            ('FIXED', "Fixed", "Normals are in a fixed direction"),
            ('ATTRACT', "Attract", "Normals point toward target object"),
            ('REPEL', "Repel", "Normals point away from target object")
        ),
        default='FIXED'
    )
    bpy.types.Object.kitfox_nt_strength = bpy.props.FloatProperty(name="Strength", description="Amount to adjust mesh normal", default = 1, min=0, max = 1)
    bpy.types.Object.kitfox_nt_normal = bpy.props.FloatVectorProperty(name="Normal", description="Direction of normal in Fixed mode", default = (0, 1, 0))
    bpy.types.Object.kitfox_nt_target = bpy.props.StringProperty(name="Target", description="Object Attract and Repel mode reference", default="")
    
    bpy.utils.register_class(ModalDrawOperator)
    bpy.utils.register_class(NormalToolPanel)
    bpy.utils.register_class(NormalToolPropsPanel)



def unregister():
    bpy.utils.unregister_class(ModalDrawOperator)
    bpy.utils.unregister_class(NormalToolPanel)
    bpy.utils.unregister_class(NormalToolPropsPanel)
    
    del bpy.types.Object.kitfox_nt_brush_type
    del bpy.types.Object.kitfox_nt_strength
    del bpy.types.Object.kitfox_nt_normal
    del bpy.types.Object.kitfox_nt_target


if __name__ == "__main__":
    register()
