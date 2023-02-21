bl_info = {
    "name": "Make Space",
    "author": "Shreya Punjabi",
    "version": (1,0),
    "blender": (3, 4, 1),
    "location": "Node Editor > Operators",
    "description": "Make space quickly in node editors",
    "warning": "",
    "doc_url": "",
    "category": "Node",
}

import bpy


class MakeSpace(bpy.types.Operator):
    "Move nodes on either side of the cursor to make space in the editor"
    bl_idname = "nodes.make_space"
    bl_label = "Make Space"
    bl_options = {'REGISTER', 'UNDO'}
    
    x: bpy.props.FloatProperty()
    y: bpy.props.FloatProperty()
    dist: bpy.props.IntProperty()
    
    _timer = None

    def __init__(self):
        pass
        #print("Start")

    def __del__(self):
        pass
        #print("End")
        

    def execute(self, context):

        tree = bpy.context.space_data.edit_tree
        
        
        for n in tree.nodes:
            if (n.type == "FRAME"):
                continue

            if (n.location.x > self.x):

                n.location.x += self.dist
            else:
                n.location.x -= self.dist
        
                
        return {'FINISHED'}


    def modal(self, context, event):
        self.dist =20

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            pass
     
            
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.cancel(context)
            return {"FINISHED"}

        
        if event.type == 'TIMER':

            self.execute(context)
            
        elif event.type == "ESC":
            self.cancel(context)
            return {"FINISHED"}

        

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        
        region = context.region.view2d
        ui_scale = context.preferences.system.ui_scale
        
        a, b = region.region_to_view(event.mouse_region_x, event.mouse_region_y)
        
        self.x = a/ui_scale
        self.y = b/ui_scale
        
        
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.05, window=context.window)


        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    #has to be explicitly called
    def cancel(self, context):
        try:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
        except:
            pass
        
    @classmethod
    def poll(self, context):
        for area in bpy.context.screen.areas:
            if area.type == 'NODE_EDITOR':
                return True
        return False

    
    
addon_keymaps = []

def register():
    bpy.utils.register_class(MakeSpace)

    global addon_keymaps
    
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc and (len(addon_keymaps)==0):
        km = wm.keyconfigs.addon.keymaps.new(name = "Node Editor", space_type = "NODE_EDITOR")
        kmi = km.keymap_items.new(MakeSpace.bl_idname, type = "LEFTMOUSE", value = 'PRESS', ctrl = True)
        
        
        
        addon_keymaps.append((km, kmi))
        
        
    
def unregister():
    bpy.utils.unregister_class(MakeSpace)
    
    
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
        
    addon_keymaps.clear()
    

    
if __name__ == "__main__":
    register()
    #unregister()