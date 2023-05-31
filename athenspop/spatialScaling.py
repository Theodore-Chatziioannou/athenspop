import lxml.etree as ET
import os
import math
import pandas as pd

def hordist(x1, y1, x0 = 0, y0 = 0):
    dx = x1 - x0
    dy = y1 - y0
    return math.sqrt(dx**2 + dy**2)

# scales down the plan file
# based on the minimum horizontal distance - closest node of the provided

def distmagn(x, y, nodes):
    x = float(x)
    y = float(y)
    minm = 999999999
    sel = 0
    for i in range(0, len(nodes)):
        x0 = nodes.loc[i, "x"]
        y0 = nodes.loc[i, "y"]
        dist = hordist(float(x), float(y), x0, y0)
        if dist < minm:
            minm = dist
            sel = i
        else: continue
    
    nid = nodes.loc[sel, "id"]
    nx = nodes.loc[sel, "x"]
    ny = nodes.loc[sel, "y"]
    return nid, nx, ny

def spatialScaling(plans, nodes):
    df = pd.DataFrame(columns = ['id', 'xbef', 'ybef', 'node', 'xaft', 'yaft'])
    t = 0
    for i in range(0, len(plans)):
        for j in range(0, len(plans[i][1])):
            if  plans[i][1].attrib == {'selected': 'yes'}: 
                if plans[i][1][j].tag == "activity":
                    x = plans[i][1][j].attrib['x']
                    y = plans[i][1][j].attrib['y']
                    
                    # checker, checker
                    df.loc[t, 'id'] = t + 1
                    df.loc[t, 'xbef'] = x
                    df.loc[t, 'ybef'] = y
                    df.loc[t, "node"] = distmagn(x, y, nodes)[0]
                    df.loc[t, 'xaft'] = distmagn(x, y, nodes)[1]
                    df.loc[t, 'yaft'] = distmagn(x, y, nodes)[2]
                    t = t + 1
                    
                    # updater              
                    plans[i][1][j].attrib['x'] = str(distmagn(x, y, nodes)[1])
                    plans[i][1][j].attrib['y'] = str(distmagn(x, y, nodes)[2])
    
    # save the checker dataframe for gis check
    df.to_csv(os.path.join(root_dir, "cropped_act_points.csv"))                
    return plans
    
root_dir = "C:/Users/panos_000/Desktop/athenspop_outputs"
net_dir = "C:/Users/panos_000/Desktop"
plan = ET.parse(os.path.join(root_dir, "plans.xml"))
nodes = pd.read_csv(os.path.join(net_dir, 'scenario_Athens_nodes.csv'))
plans = plan.getroot()
plans = spatialScaling(plans, nodes)[0]
plan.write(os.path.join(root_dir, "cropped_plans.xml"))