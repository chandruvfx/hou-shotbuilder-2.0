
import hou 
import ast
import json
from .build_subnet_mod import SHOTBUILDER_STATE_FILE


class HoudiniBuildNodes:
    
    def __init__(self,
                 build_node: hou.Node,
                 department: str,
                 shot_info_node: hou.Node) -> None:
        
        self.build_node_hda = build_node
        self.department = department
        self.shot_info_node = hou.node(f"/obj/{shot_info_node}")
        self.write_parm_entries()
    
    def write_parm_entries(self):
        
        shotbuild_status_dict ={}
        for parm in self.build_node_hda.parms():
            if not parm.name().endswith('_name'):
                    if parm.name().endswith('_version'):
                        shotbuild_status_dict[parm.name()] = parm.menuItems()[parm.eval()]
                    else:
                        shotbuild_status_dict[parm.name()] = parm.eval()
                        
        with open(SHOTBUILDER_STATE_FILE, "w") as shotbuild_file:
            json.dump(shotbuild_status_dict, shotbuild_file, indent=4)
    
    def build(self):
        
        build = True
        master_null_node = None
        
        for nodes in hou.node("/obj").children():
            if 'master_null' in nodes.userDataDict():
                master_null_node = nodes
                build = False
                break
            else:
                build = True
                    
        if build:  
            master_null_node = hou.node('/obj').createNode('null')
            master_null_node.setUserData('nodeshape', 'circle')
            master_null_node.setUserData('master_null', 'True')
            master_null_node.setName('MASTER_NULL', unique_name=True)
            master_null_node.parm('scale').set(self.shot_info_node.parm('pfx_scene_scale').eval())
            master_null_node.move([ self.build_node_hda.position()[0],  self.build_node_hda.position()[-1]-2])
     
        self.all_parm_dict ={}
        parm_list = []
        grp_parm_list= []
        for parm in self.build_node_hda.parms():
            if self.department in parm.name():
                if parm.name().endswith('_toggle'):
                    parm_list = []
                if parm.parmTemplate().type() != hou.parmTemplateType.Button \
                                and '_enable_all' not in parm.name() \
                                and '_full_geo_all' not in parm.name():
                    if parm not in parm_list  :
                        parm_list.append(parm)
                if parm_list:
                    if parm_list not in grp_parm_list:
                        grp_parm_list.append(parm_list)

        for parms in grp_parm_list:
            self.all_parm_dict[parms[0]] = parms[1:]
            
        toggle_parm = set()
        for toggle_parms in grp_parm_list:
            if toggle_parms[0].eval():
                toggle_parm.add(True)
            else:
                toggle_parm.add(False)
                
        if any(toggle_parm):   
            make_subnet = True
            for nodes in hou.node("/obj").children():
                if self.department in nodes.userDataDict():
                    dept_subnet = nodes
                    dept_subnet.setInput(0, master_null_node)
                    dept_subnet.moveToGoodPosition()
                    make_subnet = False  
            if make_subnet:
                make_subnet = True
                dept_subnet = hou.node("/obj").createNode('subnet')
                dept_subnet.setName(self.department, unique_name=True)
                dept_subnet.setUserData(self.department, "True")
                dept_subnet.setInput(0, master_null_node)
                dept_subnet.moveToGoodPosition()
                # dept_subnet.move([master_null_node.position()[0], master_null_node.position()[-1]-3])
                
                # Hide Subnet existing Parameters
                default_parm_grp = dept_subnet.parmTemplateGroup()
                for parmlabel in default_parm_grp.entries():
                    default_parm_grp.hideFolder(parmlabel.label(), True)
                dept_subnet.setParmTemplateGroup(default_parm_grp)
            
            all_nodes = set() 
            for toggle_parm, asset_parm_list in self.all_parm_dict.items():
                if toggle_parm.eval():
                    
                    asset_alembic_path = [asset_alembic_path.eval() 
                                        for asset_alembic_path in asset_parm_list 
                                        if asset_alembic_path.name().endswith('_alembic_path') 
                                        ][0]
                    alembic_node_name =  [asset_alembic_path.eval() 
                                        for asset_alembic_path in asset_parm_list 
                                        if asset_alembic_path.name().endswith('_name') 
                                        ][0]
                    alembic_display_menu =  [asset_alembic_path.eval() 
                                        for asset_alembic_path in asset_parm_list 
                                        if asset_alembic_path.name().endswith('_menu') 
                                        ][0]
                    
                    if asset_alembic_path.endswith('_CAMERA.abc') or asset_alembic_path.endswith('_camera.abc'):
                        
                        camera_proceed = True
                        department_subnet = None
                        for dept_subnet in hou.node("/obj").children():
                            if self.department in dept_subnet.userDataDict(): 
                                department_subnet = dept_subnet
                                for dept_subnet_children in dept_subnet.children():
                                    if alembic_node_name in dept_subnet_children.userDataDict(): 
                                        camera_alembic_archive = dept_subnet_children
                                        camera_alembic_archive.parm('fileName').set(asset_alembic_path)
                                        camera_alembic_archive.parm('buildHierarchy').pressButton()
                                        if alembic_display_menu == 0:  
                                            camera_alembic_archive.parm('viewportlod').set(2)
                                        elif alembic_display_menu == 1:
                                            camera_alembic_archive.parm('viewportlod').set(0)
                                        camera_proceed = False
                                hou.node(f"/obj/{dept_subnet}").layoutChildren()
                                        
                        if camera_proceed:
                            camera_alembic_archive = department_subnet.createNode("alembicarchive")
                            camera_alembic_archive.parm('fileName').set(asset_alembic_path)
                            camera_alembic_archive.parm('buildHierarchy').pressButton()
                            if alembic_display_menu == 0:  
                                camera_alembic_archive.parm('viewportlod').set(2)
                            elif alembic_display_menu == 1:
                                camera_alembic_archive.parm('viewportlod').set(0)
                            
                            camera_alembic_archive.setName(alembic_node_name)
                            camera_alembic_archive.setUserData(alembic_node_name, "True")
                            camera_alembic_archive.setInput(0, hou.item(f'/obj/{department_subnet.name()}/1'))
                            all_nodes.add(camera_alembic_archive)
                    else:
                        mesh_proceed = True
                        department_subnet = None
                        for dept_subnet in hou.node("/obj").children():
                            if self.department in dept_subnet.userDataDict(): 
                                department_subnet = dept_subnet
                                for dept_subnet_mesh_nodes in dept_subnet.children():
                                    if alembic_node_name in dept_subnet_mesh_nodes.userDataDict():
                                        for alembic_mesh_nodes in dept_subnet_mesh_nodes.children(): 
                                            if alembic_node_name in alembic_mesh_nodes.userDataDict():
                                                alembic_node = alembic_mesh_nodes
                                                alembic_node.parm('fileName').set(asset_alembic_path)
                                                alembic_node.parm('reload').pressButton()
                                                if alembic_display_menu == 0:  
                                                    alembic_node.parm('viewportlod').set(2)
                                                elif alembic_display_menu == 1:
                                                    alembic_node.parm('viewportlod').set(0)
                                                mesh_proceed = False
                                hou.node(f"/obj/{dept_subnet}").layoutChildren()
               
                        if mesh_proceed: 
                            geo = department_subnet.createNode('geo')
                            alembic_node = geo.createNode('alembic')
                            alembic_node.setName(alembic_node_name, unique_name=True)
                            alembic_node.setUserData(alembic_node_name, "True")
                            alembic_node.parm('fileName').set(asset_alembic_path)
                            alembic_node.parm('abcxform').set(1)
                            alembic_node.parm('reload').pressButton()
                            
                            if alembic_display_menu == 0:  
                                alembic_node.parm('viewportlod').set(2)
                            elif alembic_display_menu == 1:
                                alembic_node.parm('viewportlod').set(0)
                            
                            prim_attr = geo.createNode('attribcreate::2.0')
                            prim_attr.setName('OUT_ATTR')
                            prim_attr.parm('name1').set('asset_name')
                            prim_attr.parm('class1').set(1)
                            prim_attr.parm('type1').set(3)
                            prim_attr.parm('string1').set(alembic_node_name)
                            prim_attr.setUserData('OUT_ATTR', "True")
                            prim_attr.move([alembic_node.position().x(), alembic_node.position().y() - 1])
                            prim_attr.setDisplayFlag(True)
                            prim_attr.setRenderFlag(True)
                            
                            prim_attr.setInput(0, alembic_node)
                            geo.setInput(0, hou.item(f'/obj/{department_subnet.name()}/1'))
                            
                            geo.setName(alembic_node_name, unique_name=True)
                            geo.setUserData(alembic_node_name, "True")
                            all_nodes.add(geo)

                else:
                    alembic_node_name =  [asset_alembic_path.eval() 
                                        for asset_alembic_path in asset_parm_list 
                                        if asset_alembic_path.name().endswith('_name') 
                                        ][0]
                    for dept_subnet in hou.node("/obj").children():
                        if self.department in dept_subnet.userDataDict(): 
                            for dept_subnet_children in dept_subnet.children():
                                if alembic_node_name in dept_subnet_children.userDataDict():
                                    dept_subnet_children.destroy()
                                
                                
                if make_subnet:      
                    hou.node(f"/obj/{dept_subnet}").layoutChildren()
        else:
            hou.ui.displayMessage("No Toggle Were Selected", title='Shot builder')
                
                
        # else:
        #     hou.ui.displayMessage("Master Null Not Found!!\nCreate master null from Shot info", 
        #                           title='Shot builder')
    
    def build_usd_stage(self):
        
     
        self.all_parm_dict ={}
        parm_list = []
        grp_parm_list= []
        for parm in self.build_node_hda.parms():
            if self.department in parm.name():
                if parm.name().endswith('_toggle'):
                    parm_list = []
                if parm.parmTemplate().type() != hou.parmTemplateType.Button \
                                and '_enable_all' not in parm.name() \
                                and '_full_geo_all' not in parm.name():
                    if parm not in parm_list  :
                        parm_list.append(parm)
                if parm_list:
                    if parm_list not in grp_parm_list:
                        grp_parm_list.append(parm_list)

        for parms in grp_parm_list:
            self.all_parm_dict[parms[0]] = parms[1:]
        
            
        toggle_parm = set()
        for toggle_parms in grp_parm_list:
            if toggle_parms[0].eval():
                toggle_parm.add(True)
            else:
                toggle_parm.add(False)
                
        if any(toggle_parm):   
            make_subnet = True
            for nodes in hou.node("/stage").children():
                if self.department in nodes.userDataDict():
                    dept_subnet = nodes
                    dept_subnet.moveToGoodPosition()
                    make_subnet = False  
            if make_subnet:
                make_subnet = True
                dept_subnet = hou.node("/stage").createNode('subnet')
                dept_subnet.setName(self.department, unique_name=True)
                dept_subnet.setUserData(self.department, "True")
                dept_subnet.moveToGoodPosition()
                
                default_parm_grp = dept_subnet.parmTemplateGroup()
                for parmlabel in default_parm_grp.entries():
                    default_parm_grp.hideFolder(parmlabel.label(), True)
                dept_subnet.setParmTemplateGroup(default_parm_grp)
                
                dept_subnet.node('output0').destroy()
            
            sublayers = set()   
            for toggle_parm, asset_parm_list in self.all_parm_dict.items():
                if toggle_parm.eval():
                    
                    asset_alembic_path = [asset_alembic_path.eval() 
                                        for asset_alembic_path in asset_parm_list 
                                        if asset_alembic_path.name().endswith('_alembic_path') 
                                        ][0]
                    alembic_node_name =  [asset_alembic_path.eval() 
                                        for asset_alembic_path in asset_parm_list 
                                        if asset_alembic_path.name().endswith('_name') 
                                        ][0]
                    
                    layer_creation_proceed = True
                    department_subnet = None
                    for dept_subnet in hou.node("/stage").children():
                        if self.department in dept_subnet.userDataDict(): 
                            department_subnet = dept_subnet
                            for dept_subnet_mesh_nodes in dept_subnet.children():
                                if dept_subnet_mesh_nodes.userDataDict():
                                    if alembic_node_name in dept_subnet_mesh_nodes.userDataDict():
                                            sublayer_alembics = dept_subnet_mesh_nodes
                                            sublayer_alembics.parm('filepath1').set(asset_alembic_path)
                                            sublayer_alembics.parm('reload').pressButton()
                                            sublayers.add(sublayer_alembics)
                                            layer_creation_proceed = False
                            hou.node(f"/stage/{dept_subnet}").layoutChildren()

                    
                    if layer_creation_proceed:
                        sublayer_alembics = department_subnet.createNode('sublayer')
                        sublayer_alembics.setName(alembic_node_name, unique_name=True)
                        sublayer_alembics.setUserData(alembic_node_name, "True")
                        sublayer_alembics.parm('filepath1').set(asset_alembic_path)
                        sublayers.add(sublayer_alembics)
             
                else:
                    alembic_node_name =  [asset_alembic_path.eval() 
                                        for asset_alembic_path in asset_parm_list 
                                        if asset_alembic_path.name().endswith('_name') 
                                        ][0]
                    for dept_subnet in hou.node("/stage").children():
                        if self.department in dept_subnet.userDataDict(): 
                            for dept_subnet_children in dept_subnet.children():
                                if alembic_node_name in dept_subnet_children.userDataDict():
                                    dept_subnet_children.destroy()
                
                merge_exist = True
                for nodes in dept_subnet.children():
                    if  'merge' in nodes.userDataDict():
                        merge = nodes
                        merge_exist = False
                
                if merge_exist:
                    merge = dept_subnet.createNode('merge')
                    merge.setUserData("merge", "True")
                    
                node_index = 0
                for sublayer in sublayers:
                    merge.setInput(node_index, sublayer)
                    node_index = node_index + 1
                    
                merge.setDisplayFlag(1)
                
                if make_subnet:  
                    hou.node(f"/stage/{dept_subnet}").layoutChildren()
                    
        else:
            hou.ui.displayMessage("No Toggle Were Selected", title='Shot builder')

                    
