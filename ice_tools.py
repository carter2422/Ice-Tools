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
from bpy.props import *

def sw_Update(meshlink, clipcenter, wrap_offset, wrap_meth):
    activeObj = bpy.context.active_object
    wm = bpy.context.window_manager 
    oldMode = activeObj.mode
    selmod = bpy.context.tool_settings.mesh_select_mode
        
    if selmod[0] == True: 
        oldSel = 'VERT'
    if selmod[1] == True: 
        oldSel = 'EDGE'
    if selmod[2] == True: 
        oldSel = 'FACE'
    
    bpy.context.scene.objects.active = activeObj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='VERT')    
    
    if "retopo_suppo_thawed" in bpy.context.active_object.vertex_groups:
        tv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_thawed"].index
        activeObj.vertex_groups.active_index = tv
        bpy.ops.object.vertex_group_remove(all=False)

    if "shrinkwrap_apply" in bpy.context.active_object.modifiers:
        bpy.ops.object.modifier_remove(modifier= "shrinkwrap_apply") 

    if "retopo_suppo_frozen" in bpy.context.active_object.vertex_groups:
        fv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_frozen"].index
        activeObj.vertex_groups.active_index = fv
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.object.vertex_group_deselect()
        bpy.ops.object.vertex_group_add()
        bpy.data.objects[activeObj.name].vertex_groups.active.name = "retopo_suppo_thawed"
        bpy.ops.object.vertex_group_assign()

    md = activeObj.modifiers.new('shrinkwrap_apply', 'SHRINKWRAP')
    md.target = bpy.data.objects[meshlink]
    md.wrap_method = wrap_meth
    if md.wrap_method == "PROJECT":
        md.use_negative_direction = True
    if md.wrap_method == "NEAREST_SURFACEPOINT":
        md.use_keep_above_surface = True
    md.offset = wrap_offset
    if "retopo_suppo_frozen" in bpy.context.active_object.vertex_groups:                        
        md.vertex_group = "retopo_suppo_thawed"
    md.show_on_cage = True        

    modnam = "shrinkwrap_apply"
    modlist = bpy.context.object.modifiers
    modops = bpy.ops.object.modifier_move_up
    
    if wm.sw_autoapply == True:
    #move the sw mod up the stack
        for i in modlist:
            if modlist.find(modnam) == 0: break
            modops(modifier=modnam)    
    #apply the modifier
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier="shrinkwrap_apply")
        bpy.ops.object.mode_set(mode='EDIT')
    else:
    #move the sw mod below the mirror mod assuming this is your first
        for i in modlist:
            if modlist.find(modnam) == 0: break
            if modlist.find("Mirror") == 0:
                if modlist.find(modnam) == 1: break
            modops(modifier=modnam)    
    #clipcenter
    if clipcenter == "True":
        obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        for v in bm.verts:
            if wm.clipx_threshold <= 0:
                if v.co.x >= wm.clipx_threshold:
                    v.co.x = 0
            elif wm.clipx_threshold >= 0:
                if v.co.x <= wm.clipx_threshold:
                    v.co.x = 0

    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_mode(type=oldSel)
    
    if "retopo_suppo_vgroup" in bpy.context.active_object.vertex_groups:
        vg = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_vgroup"].index
        activeObj.vertex_groups.active_index = vg            
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_remove(all=False)           
    
    bpy.ops.object.mode_set(mode=oldMode)
    
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

        bpy.ops.view3d.snap_cursor_to_active()
        bpy.ops.mesh.primitive_plane_add(enter_editmode = True)
        
        bpy.ops.mesh.delete(type='VERT')
        bpy.ops.object.editmode_toggle()
        bpy.context.object.name = oldObj + "_retopo_mesh"    
        activeObj = context.active_object

        #place mirror mod
        md = activeObj.modifiers.new("Mirror", 'MIRROR')
        md.show_on_cage = True
        md.use_clip = True
        
        #generate grease pencil surface draw mode on retopo mesh
        bpy.ops.gpencil.data_add()
        bpy.ops.gpencil.layer_add()
        context.active_object.grease_pencil.draw_mode = 'SURFACE'
        bpy.context.active_object.grease_pencil.layers.active.line_width = 1
        bpy.data.objects[oldObj].select = True        
    
        bpy.ops.object.editmode_toggle()
        bpy.context.scene.tool_settings.use_snap = True
        bpy.context.scene.tool_settings.snap_element = 'FACE'
        bpy.context.scene.tool_settings.snap_target = 'CLOSEST'
        bpy.context.scene.tool_settings.use_snap_project = True
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')

        #establish link for shrinkwrap update function
        wm.sw_target = oldObj
        wm.sw_mesh = activeObj.name
        
        for SelectedObject in bpy.context.selected_objects :
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
    sw_clipx = bpy.props.FloatProperty(name = "Clip X Threshold", min = -0.05, max = 0.05, step = 0.1, precision = 3, default = -0.05) 
    sw_offset = bpy.props.FloatProperty(name = "Offset:", min = -0.1, max = 0.1, default = 0)
    sw_wrapmethod = bpy.props.EnumProperty(
        name = 'Wrap Method',
        items = (
            ('NEAREST_VERTEX', 'Nearest Vertex',""),
            ('PROJECT', 'Project',""),
            ('NEAREST_SURFACEPOINT', 'Nearest Surface Point',"")),
        default = 'PROJECT')
    sw_clipx = bpy.props.FloatProperty(name = "Clip X Threshold", min = -0.1, max = 0.1, step = 0.1, precision = 3, default = -0.05)        
        
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        activeObj = context.active_object
        wm = context.window_manager        
        oldMode = activeObj.mode
        
        wm.clipx_threshold = self.sw_clipx
        
        if activeObj.mode == 'EDIT':
            bpy.ops.object.vertex_group_add()
            bpy.data.objects[activeObj.name].vertex_groups.active.name = "retopo_suppo_vgroup"
            bpy.ops.object.vertex_group_assign()            

        if self.apply_mod == True:
           wm.sw_autoapply = True
        else:
           wm.sw_autoapply = False
                            
        if len(bpy.context.selected_objects) == 2:
            for SelectedObject in bpy.context.selected_objects:
                if SelectedObject != activeObj:
                    wm.sw_target = SelectedObject.name
                else:
                    wm.sw_mesh = activeObj.name
            if wm.sw_mesh != None and wm.sw_target != None:
                if not "Mirror" in bpy.data.objects[activeObj.name].modifiers:             
                    sw_Update(wm.sw_target, "False", self.sw_offset, self.sw_wrapmethod)
                else:
                    sw_Update(wm.sw_target, "True", self.sw_offset, self.sw_wrapmethod)
        else:
            if wm.sw_mesh=="" or wm.sw_target=="":
                self.report({'WARNING'}, "Establish Link First!")
                return {'FINISHED'}
            if wm.sw_mesh != activeObj.name:
                self.report({'WARNING'}, "Not Active Link Mesh!")
                return {'FINISHED'}
            else:
                if not "Mirror" in bpy.data.objects[activeObj.name].modifiers:             
                    sw_Update(wm.sw_target, "False", self.sw_offset, self.sw_wrapmethod)
                else:
                    sw_Update(wm.sw_target, "True", self.sw_offset, self.sw_wrapmethod)

        for SelectedObject in bpy.context.selected_objects :
            if SelectedObject != activeObj :
                SelectedObject.select = False
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
        activeObj = bpy.context.active_object
        wm = bpy.context.window_manager        
        
        if "retopo_suppo_frozen" in bpy.context.active_object.vertex_groups:
            fv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_frozen"].index
            activeObj.vertex_groups.active_index = fv
            bpy.ops.object.vertex_group_assign()
        else:                                    
            bpy.ops.object.vertex_group_add()
            bpy.data.objects[activeObj.name].vertex_groups.active.name = "retopo_suppo_frozen"
            bpy.ops.object.vertex_group_assign()
        
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
        activeObj = bpy.context.active_object
        wm = bpy.context.window_manager        

        if "retopo_suppo_frozen" in bpy.context.active_object.vertex_groups:    
            tv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_frozen"].index
            activeObj.vertex_groups.active_index = tv
            bpy.ops.object.vertex_group_remove_from()

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
        activeObj = bpy.context.active_object
        wm = bpy.context.window_manager        
        
        if "retopo_suppo_frozen" in bpy.context.active_object.vertex_groups:
            bpy.ops.mesh.select_mode(type='VERT')  
            fv = bpy.data.objects[activeObj.name].vertex_groups["retopo_suppo_frozen"].index
            activeObj.vertex_groups.active_index = fv
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.vertex_group_select()
                   
        return {'FINISHED'}

class PolySculpt(bpy.types.Operator):
    '''Polysculpt Retopology Mesh'''
    bl_idname = "polysculpt.retopo"
    bl_label = "Sculpts Retopo Mesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        activeObj = context.active_object        
        wm = context.window_manager 
        
        if wm.sw_mesh=="":
            self.report({'WARNING'}, "Establish Link First!")
            return {'FINISHED'}
        if wm.sw_mesh != activeObj.name:
            self.report({'WARNING'}, "Not Active Retopo Mesh!")
        else:
            bpy.context.object.show_all_edges = True
            bpy.context.object.show_wire = True
            bpy.ops.object.mode_set(mode='SCULPT')
            bpy.context.space_data.show_only_render = False

        return {'FINISHED'}     
    
class MeshViewToggle(bpy.types.Operator):
    '''Turn on/off all view toggles for mesh'''
    bl_idname = "meshview_toggle.retopo"
    bl_label = "Mesh View Toggle"
    bl_options = {'REGISTER', 'UNDO'}    

    view_showwire = bpy.props.BoolProperty(name = "Show Wire", default = False)
    view_xray = bpy.props.BoolProperty(name = "X-Ray", default = False)
    view_hiddenwire = bpy.props.BoolProperty(name = "Hidden Wire", default = False)
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        activeObj = context.active_object
        wm = context.window_manager        
        
        if self.view_showwire == True:
            bpy.context.space_data.show_only_render = False            
            bpy.data.objects[activeObj.name].show_all_edges = True
        else:
            bpy.data.objects[activeObj.name].show_all_edges = False            
        bpy.data.objects[activeObj.name].show_wire = self.view_showwire
        bpy.context.object.show_x_ray = self.view_xray
        bpy.context.space_data.show_occlude_wire = self.view_hiddenwire
        return {'FINISHED'}
    
class GpencilSpacing(bpy.types.Operator):
    '''Turn on/off all view toggles for mesh'''
    bl_idname = "gpencil_spacing.retopo"
    bl_label = "Gpencil Spacing"
    bl_options = {'REGISTER', 'UNDO'}

    gpencil_spacing = bpy.props.FloatProperty(name = "Spacing",
        description = "Gpencil spacing",
        default = 10,
        min = 0,
        max = 100,
        precision = 0,
        subtype = 'PERCENTAGE')
    gpencil_smooth = bpy.props.BoolProperty(name = "Smooth", default = False)
    gpencil_simp_stroke = bpy.props.BoolProperty(name = "Simplify", default = False)                   

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        activeObj = context.active_object
        wm = context.window_manager        
        edit = context.user_preferences.edit

        edit.grease_pencil_manhattan_distance = math.ceil(4*(.25*self.gpencil_spacing))
        edit.grease_pencil_euclidean_distance = math.ceil(2*(.25*self.gpencil_spacing))
        
        edit.use_grease_pencil_smooth_stroke = self.gpencil_smooth
        edit.use_grease_pencil_simplify_stroke = self.gpencil_simp_stroke        
                           
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
        edit = context.user_preferences.edit
        
        wm = context.window_manager
        
        row_sw = layout.row(align=True)
        row_sw.alignment = 'EXPAND'
        row_sw.operator("setup.retopo", "Set Up Retopo Mesh")
        row_sw = layout.row(align=True)
        row_sw.alignment = 'EXPAND'
        row_sw.operator("shrink.update", "Shrinkwrap Update")          
        
        box = layout.box().column(align=True)                      
        if wm.expand_sw_freeze_verts == False: 
            box.prop(wm, "expand_sw_freeze_verts", icon="TRIA_RIGHT", icon_only=True, text="Frozen Verts")
        else:
            box.prop(wm, "expand_sw_freeze_verts", icon="TRIA_DOWN", icon_only=True, text="Frozen Verts")
            box.separator()
            boxrow = box.row(align=True)
            boxrow.operator("freeze_verts.retopo", "Freeze Verts")
            boxrow = box.row(align=True)
            boxrow.operator("thaw_freeze_verts.retopo", "Thaw Frozen Verts")
            boxrow = box.row(align=True)
            boxrow.operator("show_freeze_verts.retopo", "Show Frozen Verts")        

        row_options = layout.row(align=True)
        row_options.alignment = 'EXPAND'
        row_options.operator("polysculpt.retopo", "Polysculpt")
        row_options.operator("meshview_toggle.retopo", "View Toggles")
        row_options.operator("gpencil_spacing.retopo", "Gpencil Spacing")

def register():
    bpy.utils.register_module(__name__)
    
    bpy.types.WindowManager.sw_mesh= StringProperty()
    bpy.types.WindowManager.sw_target= StringProperty()
    bpy.types.WindowManager.sw_use_onlythawed = BoolProperty(default=False)      
    bpy.types.WindowManager.sw_autoapply = BoolProperty(default=True)          
    bpy.types.WindowManager.expand_sw_freeze_verts = BoolProperty(default=False) 
    bpy.types.WindowManager.clipx_threshold = FloatProperty(min = -0.1, max = 0.1, step = 0.1, precision = 3, default = -0.05)
  
def unregister():
    bpy.utils.unregister_module(__name__)
    
if __name__ == "__main__":
    register()















