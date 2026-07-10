import json

def serialize(bodies, joints, camera_data=None, scene_script_path=None) -> dict:
    body_to_id = {}
    for b in bodies:
        if not hasattr(b, 'id'):
            import time
            b.id = str(int(time.time() * 1000)) + str(id(b))[-4:]
        body_to_id[b] = b.id
        
    data = {"bodies": [], "joints": []}
    
    for b in bodies:
        d = b.to_dict()
        d["id"] = body_to_id[b]
        data["bodies"].append(d)
        
    for j in joints:
        jd = j.to_dict()
        jd["body_a"] = body_to_id[j.a]
        jd["body_b"] = body_to_id[j.b] if j.b else None
        data["joints"].append(jd)
        
    if camera_data:
        data["camera"] = camera_data
        
    if scene_script_path:
        data["script_path"] = scene_script_path
        
    return data

def deserialize(data: dict, offset_x=0.0, offset_y=0.0):
    id_to_body = {}
    bodies = []
    joints = []
    
    for bd in data.get("bodies", []):
        # We need a copy so we don't mutate the loaded dict if it's used multiple times
        bd_c = dict(bd)
        bid = bd_c.pop("id", None)
        
        bd_c["x"] = bd_c.get("x", 0) + offset_x
        bd_c["y"] = bd_c.get("y", 0) + offset_y
        
        if "points" in bd_c:
            bd_c["points"] = [[px + offset_x, py + offset_y] for px, py in bd_c["points"]]
            
        if "_init" in bd_c:
            bd_c["_init"] = dict(bd_c["_init"])
            bd_c["_init"]["x"] += offset_x
            bd_c["_init"]["y"] += offset_y
            
        from classes.body import Body
        b = Body.from_dict(bd_c)
        if b:
            if bid:
                id_to_body[bid] = b
                b.id = bid
            bodies.append(b)
            
    for jd in data.get("joints", []):
        jd_c = dict(jd)
        a_id = jd_c.pop("body_a", None)
        b_id = jd_c.pop("body_b", None)
        
        # If the joint is attached to the world, its local_b is actually a world coordinate
        if b_id is None and "local_b" in jd_c:
            jd_c["local_b"] = [jd_c["local_b"][0] + offset_x, jd_c["local_b"][1] + offset_y]
            
        if a_id in id_to_body:
            a = id_to_body[a_id]
            b = id_to_body[b_id] if b_id and b_id in id_to_body else None
            from classes.joints import MotorJoint
            j = MotorJoint.from_dict(jd_c, a, b)
            joints.append(j)
            
    camera_data = data.get("camera", {})
    script_path = data.get("script_path", None)
    return bodies, joints, camera_data, script_path

def save_to_file(filepath: str, bodies: list, joints: list, camera_data: dict = None, scene_script_path: str = None):
    with open(filepath, 'w') as f:
        json.dump(serialize(bodies, joints, camera_data, scene_script_path), f, indent=2)

def load_from_file(filepath: str, offset_x=0.0, offset_y=0.0):
    with open(filepath, 'r') as f:
        data = json.load(f)
    return deserialize(data, offset_x, offset_y)

def get_save_path():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    root.destroy()
    return path

def get_open_path():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    root.destroy()
    return path

def get_script_path():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askopenfilename(defaultextension=".py", filetypes=[("Python files", "*.py")])
    root.destroy()
    return path
