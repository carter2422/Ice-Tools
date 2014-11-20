bl_info = {
    "name": "Ice Tools",
    "author": "Ian Lloyd Dela Cruz",
    "version": (2, 0),
    "blender": (2, 7, 0),
    "location": "3d View > Tool shelf",
    "description": "Retopology support",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Retopology"}

import bpy
import math
import bmesh
from bpy import ops, context
from bpy.props import *

def add_mod(mod, link, meth, offset):
    md = context.active_object.modifiers.new(mod, 'SHRINKWRAP')
    md.target = bpy.data.objects[link]
    md.wrap_method = meth
    if md.wrap_method == "PROJECT":
        md.use_negative_direction = True
    if md.wrap_method == "NEAREST_SURFACEPOINT":
        md.use_keep_above_surface = True
    md.offset = offset
    if "retopo_suppo_frozen" in context.active_object.vertex_groups:                        
        md.vertex_group = "retopo_suppo_thawed"
    md.show_on_cage = True        


def sw_Update(meshlink, wrap_offset, wrap_meth):
    activeObj = context.active_object
    wm = context.window_manager 
    oldmod = activeObj.mode
    selmod = context.tool_settings.mesh_select_mode
    modnam = "shrinkwrap_apply"
    modlist = context.object.modifiers
    modops = ops.object.modifier_move_up
        
    if selmod[0] == True: 
        oldSel = 'VERT'
    if selmod[1] == True: 
        oldSel = 'EDGE'
    if selmod[2] == True: 
        oldSel = 'FACE'
    
    context.scene.objects.active = activeObj
    ops.object.mode_set(mode='EDIT')
    ops.mesh.select_mode(type='VERT')    
    
    if "shrinkwrap_apply" in context.active_object.modifiers:
        ops.object.modifier_remove(modifier= "shrinkwrap_apply") 

    if "retopo_suppo_thawed" in context.active_object.vertex_groups:
        tv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_thawed"].index
        activeObj.vertex_groups.active_index = tv
        ops.object.vertex_group_remove(all=False)

    if "retopo_suppo_frozen" in context.active_object.vertex_groups:
        fv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_frozen"].index
        activeObj.vertex_groups.active_index = fv
        ops.mesh.select_all(action="SELECT")
        ops.object.vertex_group_deselect()
        ops.object.vertex_group_add()
        bpy.data.objects[activeObj.name].vertex_groups.active.name = "retopo_suppo_thawed"
        ops.object.vertex_group_assign()

    #add sw mod
    add_mod(modnam, meshlink, wrap_meth, wrap_offset)        

    #move sw mod up the stack
    for i in modlist:
        if modlist.find(modnam) == 0: break
        modops(modifier=modnam)
            
    #apply modifier
    ops.object.mode_set(mode='OBJECT')
    ops.object.modifier_apply(apply_as='DATA', modifier=modnam)
    ops.object.mode_set(mode='EDIT')
    
    if wm.sw_autoapply == False:
    #move the sw mod below the mirror or multires mod assuming this is your first
        add_mod(modnam, meshlink, wrap_meth, wrap_offset)   
        for i in modlist:
            if modlist.find(modnam) == 0: break
            if modlist.find(modnam) == 1:
                if modlist.find("Mirror") == 0: break
                if modlist.find("Multires") == 0: break
            modops(modifier=modnam)
                
    #clipcenter
    if "Mirror" in bpy.data.objects[activeObj.name].modifiers: 
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        for v in bm.verts:
            if wm.clipx_threshold <= 0:
                if v.co.x >= wm.clipx_threshold:
                    v.co.x = 0
            elif wm.clipx_threshold >= 0:
                if v.co.x <= wm.clipx_threshold:
                    v.co.x = 0

    ops.mesh.select_all(action='DESELECT')
    ops.mesh.select_mode(type=oldSel)
    
    if "retopo_suppo_vgroup" in context.active_object.vertex_groups:
        vg = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_vgroup"].index
        activeObj.vertex_groups.active_index = vg            
        ops.object.vertex_group_select()
        ops.object.vertex_group_remove(all=False)           
    
    ops.object.mode_set(mode=oldmod)

class SetUpRetopoMesh(bpy.types.Operator):
    '''Set up Retopology Mesh on Active Object'''
    bl_idname = "setup.retopo"
    bl_label = "Set Up Retopo Mesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == 'OBJECT'
    
    def execute(self, context):
        wm = context.window_manager 
        oldObj = context.active_object.name

        ops.view3d.snap_cursor_to_active()
        ops.mesh.primitive_plane_add(enter_editmode = True)
        
        ops.mesh.delete(type='VERT')
        ops.object.editmode_toggle()
        context.object.name = oldObj + "_retopo_mesh"    
        activeObj = context.active_object

        #place mirror mod
        md = activeObj.modifiers.new("Mirror", 'MIRROR')
        md.show_on_cage = True
        md.use_clip = True
        
        #generate grease pencil surface draw mode on retopo mesh
        ops.gpencil.data_add()
        ops.gpencil.layer_add()
        context.active_object.grease_pencil.draw_mode = 'SURFACE'
        context.active_object.grease_pencil.layers.active.line_width = 1
        bpy.data.objects[oldObj].select = True        
    
        #further mesh toggles
        ops.object.editmode_toggle()
        context.scene.tool_settings.use_snap = True
        context.scene.tool_settings.snap_element = 'FACE'
        context.scene.tool_settings.snap_target = 'CLOSEST'
        context.scene.tool_settings.use_snap_project = True
        context.object.show_all_edges = True 
        ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')

        #establish link for shrinkwrap update function
        wm.sw_target = oldObj
        wm.sw_mesh = activeObj.name
        
        for SelectedObject in context.selected_objects :
            if SelectedObject != activeObj :
                SelectedObject.select = False
        activeObj.select = True
        return {'FINISHED'}         
        
class ShrinkUpdate(bpy.types.Operator):
    '''Applies Shrinkwrap Mod on Retopo Mesh'''
    bl_idname = "shrink.update"
    bl_label = "Shrinkwrap Update"
    bl_options = {'REGISTER', 'UNDO'}
    
    apply_mod = bpy.props.BoolProperty(name = "Auto-apply Shrinkwrap", default = True)
    sw_offset = bpy.props.FloatProperty(name = "Offset:", min = -0.1, max = 0.1, step = 0.1, precision = 3, default = 0)
    sw_wrapmethod = bpy.props.EnumProperty(
        name = 'Wrap Method',
        items = (
            ('NEAREST_VERTEX', 'Nearest Vertex',""),
            ('PROJECT', 'Project',""),
            ('NEAREST_SURFACEPOINT', 'Nearest Surface Point',"")),
        default = 'PROJECT')
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        activeObj = context.active_object
        wm = context.window_manager        
        
        #establish link
        if len(context.selected_objects) == 2:
            for SelectedObject in context.selected_objects:
                if SelectedObject != activeObj:
                    wm.sw_target = SelectedObject.name
                else:
                    wm.sw_mesh = activeObj.name
                if SelectedObject != activeObj :
                    SelectedObject.select = False                    
        
        if wm.sw_mesh != activeObj.name:
            self.report({'WARNING'}, "Establish Link First!")
            return {'FINISHED'}
        else:
            if self.apply_mod == True:
               wm.sw_autoapply = True
            else:
               wm.sw_autoapply = False

            if activeObj.mode == 'EDIT':
                ops.object.vertex_group_add()
                bpy.data.objects[activeObj.name].vertex_groups.active.name = "retopo_suppo_vgroup"
                ops.object.vertex_group_assign()            

            sw_Update(wm.sw_target, self.sw_offset, self.sw_wrapmethod)
            activeObj.select = True
    
        return {'FINISHED'}

class FreezeVerts(bpy.types.Operator):
    '''Immunize verts from shrinkwrap update'''
    bl_idname = "freeze_verts.retopo"
    bl_label = "Freeze Vertices"
    bl_options = {'REGISTER', 'UNDO'}    

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == 'EDIT'

    def execute(self, context):
        activeObj = context.active_object
        
        if "retopo_suppo_frozen" in context.active_object.vertex_groups:
            fv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_frozen"].index
            activeObj.vertex_groups.active_index = fv
            ops.object.vertex_group_assign()
        else:                                    
            ops.object.vertex_group_add()
            bpy.data.objects[activeObj.name].vertex_groups.active.name = "retopo_suppo_frozen"
            ops.object.vertex_group_assign()
        
        return {'FINISHED'} 

class ThawFrozenVerts(bpy.types.Operator):
    '''Remove frozen verts'''
    bl_idname = "thaw_freeze_verts.retopo"
    bl_label = "Thaw Frozen Vertices"
    bl_options = {'REGISTER', 'UNDO'}    

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == 'EDIT'

    def execute(self, context):
        activeObj = context.active_object

        if "retopo_suppo_frozen" in context.active_object.vertex_groups:    
            tv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_frozen"].index
            activeObj.vertex_groups.active_index = tv
            ops.object.vertex_group_remove_from()

        return {'FINISHED'}  

class ShowFrozenVerts(bpy.types.Operator):
    '''Show frozen verts'''
    bl_idname = "show_freeze_verts.retopo"
    bl_label = "Show Frozen Vertices"
    bl_options = {'REGISTER', 'UNDO'}    

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == 'EDIT'

    def execute(self, context):
        activeObj = context.active_object

        if "retopo_suppo_frozen" in context.active_object.vertex_groups:
            ops.mesh.select_mode(type='VERT')  
            fv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_frozen"].index
            activeObj.vertex_groups.active_index = fv
            ops.mesh.select_all(action='DESELECT')
            ops.object.vertex_group_select()
                   
        return {'FINISHED'}

class PolySculpt(bpy.types.Operator):
    '''Polysculpt retopology mesh'''
    bl_idname = "polysculpt.retopo"
    bl_label = "Sculpts Retopo Mesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        activeObj = context.active_object        
        wm = context.window_manager
        
        if wm.sw_mesh != activeObj.name:
            self.report({'WARNING'}, "Establish Link First!")
        else:
            context.space_data.show_only_render = False            
            context.object.show_wire = True            
            ops.object.mode_set(mode='SCULPT')

        return {'FINISHED'}     
    
class RetopoSupport(bpy.types.Panel):
    """Retopology Support Functions"""
    bl_label = "Ice Tools"
    bl_idname = "OBJECT_PT_retosuppo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Retopology'

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        row_sw = layout.row(align=True)
        row_sw.alignment = 'EXPAND'
        row_sw.operator("setup.retopo", "Set Up Retopo Mesh")
        row_sw = layout.row(align=True)
        row_sw.alignment = 'EXPAND'
        row_sw.operator("shrink.update", "Shrinkwrap Update")
        row_sw.operator("polysculpt.retopo", "", icon = "SCULPTMODE_HLT")
        row_sw = layout.row(align=True)
        row_sw.prop(wm, "clipx_threshold", "Clip X Threshold")
        
        row_fv = layout.row(align=True)
        row_fv.alignment = 'EXPAND'
        row_fv.operator("freeze_verts.retopo", "Freeze")
        row_fv.operator("thaw_freeze_verts.retopo", "Thaw")
        row_fv.operator("show_freeze_verts.retopo", "Show") 
        
        if context.active_object is not None:
            row_view = layout.row(align=True)
            row_sw.alignment = 'EXPAND'
            row_view.prop(context.object, "show_wire", toggle =False)
            row_view.prop(context.object, "show_x_ray", toggle =False)
            row_view.prop(context.space_data, "show_occlude_wire", toggle =False)              

def register():
    bpy.utils.register_module(__name__)
    
    bpy.types.WindowManager.sw_mesh= StringProperty()
    bpy.types.WindowManager.sw_target= StringProperty()
    bpy.types.WindowManager.sw_use_onlythawed = BoolProperty(default=False)      
    bpy.types.WindowManager.sw_autoapply = BoolProperty(default=True)          
    bpy.types.WindowManager.clipx_threshold = FloatProperty(min = -0.1, max = 0.1, step = 0.1, precision = 3, default = 0)
  
def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()
