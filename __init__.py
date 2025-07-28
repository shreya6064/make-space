
bl_info = {
    "name": "Make Space",
    "author": "Shreya Punjabi",
    "version": (2,0),
    "blender": (4, 4, 3),
    "location": "Node Editor > Operators",
    "description": "Make space quickly in node editors",
    "warning": "",
    "doc_url": "https://github.com/shreya6064/make-space",
    "category": "Node",
}

import bpy

class MakeSpace(bpy.types.Operator):
    """Move nodes based on mouse drag direction and distance"""
    bl_idname = "nodes.make_space"
    bl_label = "Make Space"
    bl_options = {'REGISTER', 'UNDO'}

    _start_cursor_x = None
    _last_cursor_x = None
    _timer = None

    def modal(self, context, event):
        region = context.region.view2d
        ui_scale = context.preferences.system.ui_scale

        if event.type == 'MOUSEMOVE':
            cursor_x, _ = region.region_to_view(event.mouse_region_x, event.mouse_region_y)
            cursor_x /= ui_scale

            delta = cursor_x - self._last_cursor_x
            self._last_cursor_x = cursor_x

            if abs(delta) < 0.001:  #ignore jitters
                return {'RUNNING_MODAL'}

            tree = context.space_data.edit_tree
            for node in tree.nodes:
                if node.type == "FRAME":
                    continue

                if delta > 0 and node.location.x > self._start_cursor_x:
                    node.location.x += delta
                elif delta < 0 and node.location.x < self._start_cursor_x:
                    node.location.x += delta  # delta is negative, so moves left

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.cancel(context)
            return {"FINISHED"}

        elif event.type == 'ESC':
            self.cancel(context)
            return {"CANCELLED"}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        region = context.region.view2d
        ui_scale = context.preferences.system.ui_scale

        cursor_x, _ = region.region_to_view(event.mouse_region_x, event.mouse_region_y)
        cursor_x /= ui_scale

        self._start_cursor_x = cursor_x
        self._last_cursor_x = cursor_x

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        try:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
        except:
            pass

    @classmethod
    def poll(cls, context):
        return context.area.type == 'NODE_EDITOR'


    
    
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
