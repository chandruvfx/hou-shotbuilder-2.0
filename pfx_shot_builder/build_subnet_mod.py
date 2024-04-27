    
    
import re
import os
import ast
import json
from imp import reload
from . import pfx_shot_build
reload(pfx_shot_build)
try:
    import hou
except ImportError:
    print("Cannot import houdini Modules")

FILE_DIR = os.path.dirname(__file__)
ICON_DIR = os.path.join(FILE_DIR, 'icons')
project_name = hou.hscriptExpression('$PFX_SHOW')
prod_name = hou.hscriptExpression('$PFX_PRDSTEP')
seq_name = hou.hscriptExpression('$PFX_SEQ')
shot_name = hou.hscriptExpression('$PFX_SHOT')

STATE_FILE_NAME = f"shotbuild_state_{project_name}_{prod_name}_{seq_name}_{shot_name}.json"
SHOTBUILDER_STATE_FILE = fr"C:\Users\{os.environ['USERNAME']}\AppData\Local\Temp\{STATE_FILE_NAME}"

    
class BuildSubNetWork:
    
    """
    Create a subnet in the obj level and necessary parameters of the 
    collceted published entities for the given scope and project code.
    
    Creates folder template for respective downstream dept like
    3d_animation, layout, 3d_matchmove, 3d_rotomation. Each tab folder
    have respective publish entity parameters. The parameters segregated into 
    two part. per-department master control parm and per published asset controls. 
    

    """
    def __init__(self,
                project: str,
                scope: str,
                shot_info_node = None) -> None:
        
        self.project = project
        self.scope = scope
        self.shot_info_node = shot_info_node
        
        pfx_shot_builder = pfx_shot_build.PFXShotBuilder(
                    project=self.project,
                    scope=self.scope,
                    shot_info_node=self.shot_info_node
        )
        self.publish_data_by_version = pfx_shot_builder.get_publish_data()
        
    @staticmethod
    def read_shotbuilder_parm_data():
        
        with open(SHOTBUILDER_STATE_FILE, "r") as shotbuild_file:
            return json.load(shotbuild_file)
            
    def build_shot_builder_subnetwork(self) -> None:
        
        shotbuild_status_dict = {}
        shotbuid_node = None
        proceed = True
        for nodes in hou.node("/obj").children():
            if 'shotbuilder' in nodes.userDataDict():
                shotbuid_node = nodes
                proceed = False
                for parm in nodes.parms():
                    if not parm.name().endswith('_name'):
                        if list(filter(lambda x: x in parm.name(), list(self.publish_data_by_version.keys()))):
                            if parm.name().endswith('_version'):
                                shotbuild_status_dict[parm.name()] = parm.menuItems()[parm.eval()]
                            else:
                                shotbuild_status_dict[parm.name()] = parm.eval()
        if proceed:
            if os.path.exists(SHOTBUILDER_STATE_FILE):
                shotbuilder_parm_data = self.read_shotbuilder_parm_data()
                shotbuild_status_dict = shotbuilder_parm_data
        
        if shotbuild_status_dict:
            if shotbuid_node:
                shotbuid_node.destroy()     

        self.shotbuild_subnet = hou.node("/obj").createNode('subnet')
        self.shotbuild_subnet.setName("shot_builder", unique_name=True)
        self.shotbuild_subnet.setUserData('shotbuilder', "True")
        self.shotbuild_subnet.setUserData('published_data', str(self.publish_data_by_version))
        self.shotbuild_subnet.move([self.shot_info_node.position()[0], self.shot_info_node.position()[-1]-2])
        
        
        # Hide Subnet existing Parameters
        default_parm_grp = self.shotbuild_subnet.parmTemplateGroup()
        for parmlabel in default_parm_grp.entries():
            default_parm_grp.hideFolder(parmlabel.label(), True)
        self.shotbuild_subnet.setParmTemplateGroup(default_parm_grp)
        
        # Create Parameters
        new_parm_grp = self.shotbuild_subnet.parmTemplateGroup()
        for department, published_alembic_dict in self.publish_data_by_version.items():
            folder_name = "f{department}"
            folder_label= "%s" %department.title()
            
            department_folders = hou.FolderParmTemplate(
                folder_name, folder_label, folder_type=hou.folderType.Tabs
            )
            select_all = hou.ToggleParmTemplate(
                            department + "_enable_all",
                            "Enable All",
                            join_with_next=True,
                            script_callback_language=hou.scriptLanguage.Python,
            )
            select_all.setDefaultValue(True)
            select_all.setTags(
                {'select_all': department}
            )
            select_all.setScriptCallback(
                        f"from imp import reload;from pfx_shot_builder import build_subnet_mod as bsm;\
                        reload(bsm);bsm.ToggleManipulations(kwargs[\"node\"],\"{department}\").display_toggle()"
            )
            department_folders.addParmTemplate(select_all)
            
            
            full_geo_toggle = hou.ToggleParmTemplate(
                            department + "_full_geo_all",
                            "Full Geometry",
                            join_with_next=True,
                            script_callback_language=hou.scriptLanguage.Python,
            )
            full_geo_toggle.setTags(
                {'select_all': department}
            )
            full_geo_toggle.setScriptCallback(
                        f"from imp import reload;from pfx_shot_builder import build_subnet_mod as bsm;\
                        reload(bsm);bsm.ToggleManipulations(kwargs[\"node\"],\"{department}\").full_geo_toggle()"
            )
            department_folders.addParmTemplate(full_geo_toggle)

            build_button = hou.ButtonParmTemplate(
                    department + "_load", 
                    "Load/Update",
                    join_with_next=True,
                    script_callback_language=hou.scriptLanguage.Python 
            )
            build_button.setTags({'build_department': department})
            build_button.setScriptCallback(
                f"from imp import reload;from pfx_shot_builder import houdini_build_nodes as hbn;\
                reload(hbn);hbn.HoudiniBuildNodes(kwargs[\"node\"],\"{department}\", \"{self.shot_info_node}\").build()"
            )
            department_folders.addParmTemplate(build_button)
            
            build_usd_button = hou.ButtonParmTemplate(
                    department + "_build_stage", 
                    "Build Stage",
                    script_callback_language=hou.scriptLanguage.Python 
            )
            build_usd_button.setTags({'build_department': department})
            build_usd_button.setScriptCallback(
                f"from imp import reload;from pfx_shot_builder import houdini_build_nodes as hbn;\
                reload(hbn);hbn.HoudiniBuildNodes(kwargs[\"node\"],\"{department}\", \"{self.shot_info_node}\").build_usd_stage()"
            )
            department_folders.addParmTemplate(build_usd_button)
            
            separator =  hou.SeparatorParmTemplate(
                    department + "_seperator",
            )
            department_folders.addParmTemplate(separator)
             
            if published_alembic_dict:
                for asset_name, published_asset_dict in published_alembic_dict.items():  
                    max_version = max([int(re.sub(r"\D", " ", version_str)) for version_str in list(published_asset_dict.keys())])
                    for version, published_asset_path in published_asset_dict.items():
                        if max_version ==  int(re.sub(r"\D", " ", version)):
                            
                            asset_parm_name = asset_name.lower() +  "_" + department + "_name"
                            asset_version_parm_name = asset_name.lower() +  "_" + department + "_version"
                            asset_alembic_path_parm_name = asset_name.lower() +  "_" + department + "_alembic_path"
                            asslet_display_parm_name = asset_name.lower() +  "_" + department + "_menu"
                            asset_version_status_button_name = asset_name.lower() +  "_" + department + "_version_status"
                            
                            toggle_parm_name = asset_name.lower() + "_" + department + "_toggle"
                            
                            asset_toggle = hou.ToggleParmTemplate(
                                toggle_parm_name,
                                "Enable",
                                join_with_next=True,
                            )
                            asset_toggle.setDefaultValue(True)
                            asset_toggle.setTags(
                                {toggle_parm_name: asset_name}
                            )
                            department_folders.addParmTemplate(asset_toggle)
                            
                            asset_name_text = hou.StringParmTemplate(
                                    asset_parm_name,
                                    "Asset_Name", 
                                    1,
                                    default_value=(asset_name,),
                                    join_with_next=True
                            )
                            asset_name_text.setConditional(hou.parmCondType.DisableWhen,
                                                        '{ %s == 0 }' %toggle_parm_name)
                            department_folders.addParmTemplate(asset_name_text)
                            
                            asset_version_menu = hou.MenuParmTemplate(
                                asset_version_parm_name,
                                "versions", 
                                (list(published_asset_dict.keys())[::-1]),
                                join_with_next=True,
                                script_callback_language=hou.scriptLanguage.Python,
                            )
                            asset_version_menu.setTags({'department': department, 
                                                        'asset_name': asset_name,
                                                        "max_version": str(max_version),
                                                        "version_indicator_button": asset_version_status_button_name})
                            asset_version_menu.setScriptCallback(
                                "from imp import reload;from pfx_shot_builder import build_subnet_mod as bsm;\
                                reload(bsm);bsm.VersionContrls(kwargs[\"node\"]).update_path_parm_by_user_selected_version()"
                            )
                            
                            asset_version_menu.setConditional(hou.parmCondType.DisableWhen,
                                                        '{ %s == 0 }' %toggle_parm_name)
                            department_folders.addParmTemplate(asset_version_menu)
                            
                            version_indicator_button = hou.ButtonParmTemplate(
                                    asset_version_status_button_name, 
                                    "",
                                    script_callback_language=hou.scriptLanguage.Python 
                            )
                            version_indicator_button.hideLabel(True)
                            check_button_png = ICON_DIR.replace('\\', '/') + '/check.png'
                            version_indicator_button.setTags({'button_icon': check_button_png,
                                                              'version_parm': asset_version_parm_name})
                            version_indicator_button.setConditional(hou.parmCondType.DisableWhen,
                                                        '{ %s == 0 }' %toggle_parm_name)
                            department_folders.addParmTemplate(version_indicator_button)
                            
                            asset_alembic_path = hou.StringParmTemplate(
                                asset_alembic_path_parm_name,
                                "Path",
                                1, 
                                default_value=(published_asset_path,),
                            )
                            asset_alembic_path.setConditional(hou.parmCondType.DisableWhen,
                                                        '{ %s == 0 }' %toggle_parm_name)
                            department_folders.addParmTemplate(asset_alembic_path)
                            
                            asset_display_menu = hou.MenuParmTemplate(
                                asslet_display_parm_name, 
                                "Display", 
                                (['Bounding Box', 'Full Geometry']),
                            )
                            asset_display_menu.setConditional(hou.parmCondType.DisableWhen,
                                                        '{ %s == 0 }' %toggle_parm_name)
                            department_folders.addParmTemplate(asset_display_menu)
                            
                            separator =  hou.SeparatorParmTemplate(
                                    asset_name.lower() +  "_" + department + "_seperator",
                            )
                            department_folders.addParmTemplate(separator)
                        
                
                        
                new_parm_grp.append(department_folders)
                self.shotbuild_subnet.setParmTemplateGroup(new_parm_grp)
                
            for parm in self.shotbuild_subnet.parms():
                if 'department' in parm.name():
                    parm.lock(True)
                if list(filter(parm.name().endswith, ['_name', '_alembic_path',])):
                    parm.lock(True)
        
        # with open(SHOTBUILDER_STATE_FILE, "r") as shotbuild_file:
        #     shotbuild_status_dict = json.load(shotbuild_file)
            
        for parm, value in shotbuild_status_dict.items():
            shot_build_parms = hou.parm(f'/obj/{self.shotbuild_subnet}/{parm}')

            if shot_build_parms.name().endswith('_version'):
                current_max_version = int(shot_build_parms.parmTemplate().tags()["max_version"])
                current_version_indicator = shot_build_parms.parmTemplate().tags()["version_indicator_button"]
                version_indicator_parm = hou.parm(f'/obj/{self.shotbuild_subnet}/{current_version_indicator}')
                version_indicator_parm_name = version_indicator_parm.name()
                
                selected_version_index = shot_build_parms.menuLabels().index(value)
                current_selected_version = int(re.sub(r"\D", " ", shot_build_parms.menuItems()[selected_version_index])) 

                p = self.shotbuild_subnet.parmTemplateGroup()
                if current_selected_version != current_max_version:
                    
                    version_indicator_button = hou.ButtonParmTemplate(
                            version_indicator_parm_name, 
                            "",
                            script_callback_language=hou.scriptLanguage.Python 
                    )
                    version_indicator_button.hideLabel(True)
                    warning_button_png = ICON_DIR.replace('\\', '/') + '/warning.png'
                    version_indicator_button.setTags({'button_icon': warning_button_png})

                else:
                    version_indicator_button = hou.ButtonParmTemplate(
                            version_indicator_parm_name, 
                            "",
                            script_callback_language=hou.scriptLanguage.Python 
                    )
                    version_indicator_button.hideLabel(True)
                    check_button_png = ICON_DIR.replace('\\', '/') + '/check.png'
                    
                    version_indicator_button.setTags({'button_icon': check_button_png})
                p.replace(current_version_indicator, version_indicator_button)
                self.shotbuild_subnet.setParmTemplateGroup(p)
            
            if shot_build_parms.name().endswith('_alembic_path'):
                
                shot_build_parms.lock(False)
                shot_build_parms.set(value)
                shot_build_parms.lock(True)
            else:   
                shot_build_parms.set(value)
            
                    
    
class VersionContrls:
    
    def __init__(self,
                 shot_builder_node: hou.Node) -> None:
        
        self.shot_builder_node = shot_builder_node
        pass
    
    def update_path_parm_by_user_selected_version(self) -> None:

        published_data_dict = \
                    ast.literal_eval(self.shot_builder_node.userDataDict()['published_data'])
        

        for parm in self.shot_builder_node.parms():
            if parm.name().endswith('_version'):
                current_department = parm.parmTemplate().tags()['department']
                current_assetname = parm.parmTemplate().tags()['asset_name']
                current_max_version = int(parm.parmTemplate().tags()["max_version"])
                current_version_indicator = parm.parmTemplate().tags()["version_indicator_button"]
                user_selected_version = parm.evalAsString()
                version_value = parm.eval()
                current_selected_version = parm.menuItems()[version_value]
               
               
            if parm.name().endswith('_alembic_path'):
                current_published_parm = parm
                current_published_path = parm.eval()
                
                for department, published_alembic_dict in published_data_dict.items():
                    if department == current_department:
                        if published_alembic_dict:
                            for asset_name, published_asset_dict in published_alembic_dict.items():
                                if asset_name == current_assetname:
                                    for version, published_asset_path in published_asset_dict.items():
                                        if version == user_selected_version:
                                            if published_asset_path != current_published_path:
                                                current_published_parm.lock(False)
                                                current_published_parm.set(published_asset_path)
                                                current_published_parm.lock(True)
                                                
                                                version_indicator_node = hou.parm(f"/obj/{self.shot_builder_node}/{current_version_indicator}")
                                                version_indicator_node_name = version_indicator_node.name()
                                                current_version = int(re.sub(r"\D", " ", version))

                                                p = self.shot_builder_node.parmTemplateGroup()
                                                if current_version != current_max_version:
                                                    
                                                    version_indicator_button = hou.ButtonParmTemplate(
                                                            version_indicator_node_name, 
                                                            "",
                                                            script_callback_language=hou.scriptLanguage.Python 
                                                    )
                                                    version_indicator_button.hideLabel(True)
                                                    warning_button_png = ICON_DIR.replace('\\', '/') + '/warning.png'
                                                    version_indicator_button.setTags({'button_icon': warning_button_png})

                                                else:
                                                    version_indicator_button = hou.ButtonParmTemplate(
                                                            version_indicator_node_name, 
                                                            "",
                                                            script_callback_language=hou.scriptLanguage.Python 
                                                    )
                                                    version_indicator_button.hideLabel(True)
                                                    check_button_png = ICON_DIR.replace('\\', '/') + '/check.png'
                                                    
                                                    version_indicator_button.setTags({'button_icon': check_button_png})
                                                p.replace(current_version_indicator, version_indicator_button)
                                                self.shot_builder_node.setParmTemplateGroup(p)
                                                

class ToggleManipulations:
    
    def __init__(self,
                 build_node: hou.Node,
                 department: str = '') -> None:
        
        self.build_node_hda = build_node
        self.department = department

    def display_toggle(self):
        
        toggle_parm_list = []
        select_all_parm = []
        toggle_dict = {}
        for parm in self.build_node_hda.parms():
            if self.department in parm.name():
                if parm.name().endswith('_toggle'):
                    toggle_parm_list.append(parm)
                if '_enable_all' in  parm.name():
                    select_all_parm.append(parm)
        toggle_dict[select_all_parm[0]] = toggle_parm_list

        for select_all_toggle, toggle_list in toggle_dict.items():
            for toggles in toggle_list:
                if select_all_toggle.eval():
                    toggles.set(True)
                else:
                    toggles.set(False)
    
    def full_geo_toggle(self):
        
        menu_parm_list = []
        full_geo_selection_parms = []
        full_geo_display_dict = {}
        for parm in self.build_node_hda.parms():
            if self.department in parm.name():
                if parm.name().endswith('_menu'):
                    menu_parm_list.append(parm)
                if '_full_geo_all' in  parm.name():
                    full_geo_selection_parms.append(parm)
        full_geo_display_dict[full_geo_selection_parms[0]] = menu_parm_list 
        
        for full_geo_all_toggle, full_geo_menu_lists in full_geo_display_dict.items():
            for full_geo_menu_list in full_geo_menu_lists:
                if full_geo_all_toggle.eval() == 0:
                    full_geo_menu_list.set(0)
                elif full_geo_all_toggle.eval() == 1:
                    full_geo_menu_list.set(1)
                    
                
               
        

