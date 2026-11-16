bl_info = {
    "name": "Make Space",
    "author": "Shreya Punjabi",
    "version": (3, 1, 1),
    "blender": (5, 2, 0),
    "location": "Node Editor > Ctrl + Left Mouse Drag",
    "description": "Make space in all node editors with adjustable influence",
    "doc_url": "https://github.com/shreya6064/make-space",
    "category": "Node",
}

import math
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

addon_keymaps = []
_active = []
_last_radius = 500.0
_last_use_radius = True


def absolute_location(node):
    """Canvas coordinates, including every parent frame transform."""
    position = node.location.copy()
    parent = node.parent
    while parent:
        position += parent.location
        parent = parent.parent
    return position


def depth(node):
    result = 0
    while node.parent:
        result += 1
        node = node.parent
    return result


class MakeSpace(bpy.types.Operator):
    """Ctrl-drag to make space; wheel adjusts radius; X/Y locks axis"""
    bl_idname = "nodes.make_space"
    bl_label = "Make Space"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    @classmethod
    def poll(cls, context):
        return bool(context.area and context.area.type == 'NODE_EDITOR'
                    and context.region and context.region.type == 'WINDOW'
                    and context.space_data.edit_tree
                    and context.space_data.edit_tree.is_editable)

    def _mouse(self, event):
        # Use window coordinates so crossing into another region stays consistent.
        x, y = self._region.view2d.region_to_view(
            event.mouse_x - self._region.x, event.mouse_y - self._region.y)
        return Vector((x / self._scale, y / self._scale))

    def invoke(self, context, event):
        if not self.poll(context):
            return {'CANCELLED'}
        self._area = context.area
        self._region = context.region
        self._tree = context.space_data.edit_tree
        self._scale = context.preferences.system.ui_scale
        self._start = self._mouse(event)
        self._current = self._start.copy()
        self._start_pixel = Vector((event.mouse_x, event.mouse_y))
        self._axis = None
        self._radius = _last_radius
        self._use_radius = _last_use_radius
        self._handle = None
        self._closed = False
        #keep all frame positions too, for cancellation. Positions on framed
        #nodes are local. absolute coordinates are essential for side tests
        self._original = [
            (n, absolute_location(n))
            for n in sorted(self._tree.nodes, key=depth)
        ]
        self._nodes = []
        for node, position in self._original:
            if node.type == 'FRAME':
                continue
            size = node.dimensions / self._scale
            center = position + Vector((size.x / 2, -size.y / 2))
            # d to original node rectangle, not origin
            dx = max(position.x - self._start.x,
                     self._start.x - position.x - size.x, 0.0)
            dy = max(self._start.y - position.y,
                     position.y - size.y - self._start.y, 0.0)
            self._nodes.append((node, position, center, math.hypot(dx, dy)))
        try:
            self._shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
            self._handle = bpy.types.SpaceNodeEditor.draw_handler_add(
                self._draw, (), 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
            _active.append(self)
            self._status()
        except Exception:
            self._cleanup()
            raise
        return {'RUNNING_MODAL'}

    @staticmethod
    def _place(node, absolute):
        # - the CURRENT frame origin
        parent = node.parent
        node.location = absolute - absolute_location(parent) if parent else absolute

    def _apply(self):
        axis = 0 if self._axis == 'X' else 1
        amount = self._current[axis] - self._start[axis] if self._axis else 0.0
        for node, original, center, distance in self._nodes:
            on_side = (center[axis] - self._start[axis]) * amount > 0
            in_range = not self._use_radius or distance <= self._radius
            target = original.copy()
            if on_side and in_range:
                target[axis] += amount
            self._place(node, target)
        self._area.tag_redraw()

    def _restore(self):
        for node, position in self._original:
            self._place(node, position)

    def _status(self):
        radius = f'{self._radius:.0f}' if self._use_radius else 'Unlimited'
        self._area.header_text_set(
            f'Make Space | Axis: {self._axis or "Auto"} | Radius: {radius} '
            f'| Wheel: radius | X/Y: axis | O: radius on/off '
            '| Release LMB / Enter: confirm | Esc / RMB: cancel')
        self._area.tag_redraw()

    def modal(self, context, event):
        if self._closed:
            return {'CANCELLED'}
        try:
            if (context.area != self._area or context.space_data.edit_tree != self._tree
                    or event.type == 'WINDOW_DEACTIVATE'):
                self.cancel(context)
                return {'CANCELLED'}
            if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
                self.cancel(context)
                return {'CANCELLED'}
            if ((event.type == 'LEFTMOUSE' and event.value == 'RELEASE')
                    or (event.type in {'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS')):
                self._cleanup()
                return {'FINISHED'}
            if event.type == 'MOUSEMOVE':
                self._current = self._mouse(event)
                if self._axis is None:
                    pixels = Vector((event.mouse_x, event.mouse_y)) - self._start_pixel
                    if pixels.length < 6 * self._scale:
                        return {'RUNNING_MODAL'}
                    self._axis = 'X' if abs(pixels.x) >= abs(pixels.y) else 'Y'
                self._apply()
                self._status()
            elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and event.value == 'PRESS':
                factor = 1.15 if event.type == 'WHEELUPMOUSE' else 1 / 1.15
                self._radius = min(100000.0, max(10.0, self._radius * factor))
                self._apply()
                self._status()
            elif event.value == 'PRESS' and event.type in {'X', 'Y', 'O'}:
                if event.type in {'X', 'Y'}:
                    self._axis = event.type
                elif event.type == 'O':
                    self._use_radius = not self._use_radius
                self._apply()
                self._status()
        except (ReferenceError, RuntimeError):
            self.cancel(context)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def _draw(self):
        context = bpy.context
        if (self._closed or context.area != self._area
                or context.region != self._region or not self._use_radius):
            return
        view = self._region.view2d
        coords = []
        for i in range(97):
            angle = math.tau * i / 96
            point = self._start + self._radius * Vector((math.cos(angle), math.sin(angle)))
            x, y = view.view_to_region(point.x * self._scale,
                                       point.y * self._scale, clip=False)
            coords.append((float(x), float(y), 0.0))
        batch = batch_for_shader(self._shader, 'LINE_STRIP', {'pos': coords})
        old_blend = gpu.state.blend_get()
        try:
            gpu.state.blend_set('ALPHA')
            self._shader.bind()
            self._shader.uniform_float('viewportSize', gpu.state.viewport_get()[2:])
            self._shader.uniform_float('lineWidth', 1.5 * self._scale)
            self._shader.uniform_float('color', (0.35, 0.75, 1.0, 0.8))
            batch.draw(self._shader)
        finally:
            gpu.state.blend_set(old_blend)

    def _cleanup(self):
        global _last_radius, _last_use_radius
        if self._closed:
            return
        self._closed = True
        _last_radius = self._radius
        _last_use_radius = self._use_radius
        if self._handle is not None:
            bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
        try:
            self._area.header_text_set(None)
            self._area.tag_redraw()
        except ReferenceError:
            pass
        if self in _active:
            _active.remove(self)

    def cancel(self, context):
        if self._closed:
            return
        try:
            self._restore()
        except (ReferenceError, RuntimeError):
            pass
        finally:
            self._cleanup()


def register():
    bpy.utils.register_class(MakeSpace)
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
        kmi = km.keymap_items.new(MakeSpace.bl_idname, 'LEFTMOUSE', 'PRESS', ctrl=True)
        addon_keymaps.append((km, kmi))


def unregister():
    for operator in list(_active):
        operator.cancel(bpy.context)
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    bpy.utils.unregister_class(MakeSpace)


if __name__ == '__main__':
    register()
