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
    bl_idname = "view3d.normal_tool"
    bl_label = "Normal Tool Kitfox"

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
            manip_normal(context, event)
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


def register():
    bpy.utils.register_class(ModalDrawOperator)


def unregister():
    bpy.utils.unregister_class(ModalDrawOperator)


if __name__ == "__main__":
    register()
