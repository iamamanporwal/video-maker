import bpy
s = bpy.data.scenes["HAND"]
for f in (480, 526, 560):
    s.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    for o in s.objects:
        if "catwire" in o.name:
            e = o.evaluated_get(s.view_layers[0].depsgraph) if False else o
            vl = s.view_layers[0]
            vl.update()
            ev = o.evaluated_get(vl.depsgraph)
            print(f, o.name, [m.type for m in o.modifiers], len(ev.data.polygons), o.hide_render, o.parent and o.parent.name, [round(x,2) for x in ev.dimensions])
