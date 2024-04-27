import sys
import re
import os 
import json
from pfx.api.project import ProjectData
from pfx.api.shot import ShotData

class PFXShotBuilder:

    def __init__(self,
                 project: str,
                 scope: str,
                 shot_info_node = None) -> None:

        self.latest_animation_json_path = {}
        self.project = project
        self.scope = scope
        self.shot_info_node = shot_info_node
        self.suggested_depts =  ['3d_animation',
                                'layout',
                                '3d_rotomation',
                                '3d_matchmove',
                                '3d_layout']
        
        self.shot_api = ShotData()
        self.project_api = ProjectData()
        self.shot_dict = {
            "Input": [1],
            "3d_rotomation": [51],
            "2d_paint": [29],
            "3d_mayarig": [9],
            "3d_animation": [10],
            "3d_fx": [12],
            "3d_dynamics":[25],
            "layout": [18],
            "3d_layout":[37],
            "3d_matchmove": [6],
            "3d_lighting":[13],
            "3d_model": [35]
        }
        
        self.data = {
                '3d_animation': [self.shot_dict['3d_animation']],
                '3d_rotomation': [self.shot_dict['3d_rotomation']],
                '3d_matchmove': [self.shot_dict['3d_matchmove']],
                'layout': [self.shot_dict['layout']],
                '3d_layout': [self.shot_dict['3d_layout']],
                
            }

        self.proj_data = self.project_api.get_project_data(self.project)
        self.scope_data = self.shot_api.get_shot_data(self.project, self.scope)
        
        # self.proj_data = self.task_details['project_data']
        # self.scope_data = self.task_details['scope_data']
        self.collect_thadam_latest_animation_json()
        self.parse_publish_data_json()
        self.rearrange_publish_data_by_version()
        pass

    @staticmethod
    def read_json(json_file: str) -> dict:
        
        with open(json_file, 'r') as jsonfile:
            data = json.load(jsonfile)
        return data
    
    def collect_thadam_latest_animation_json(self) -> None:
        
        # For 3d_lighting datas gonna collected.
        # [10] gives all the animation data. if replace with
        # 'department' then it gives animation, layout, matchmove 
        # whatever exist 
        for suggested_depts in self.suggested_depts:
            
            versions_str = set()
            
            for department in self.data[suggested_depts]:
                shots_data = self.shot_api.collect_published_json_data(
                            self.proj_data,
                            self.scope_data,
                            type_list=department
                )
                
            # only versions added from the shots data {'V0001, 'V0002'}
            if shots_data:
                # print(suggested_depts, shots_data)
                self.latest_animation_json_path[suggested_depts] = shots_data

    
    def parse_publish_data_json(self) -> None:
        
        self.all_department_alembics = {}
        for departments, published_data_version_dict in self.latest_animation_json_path.items():
            version_dict = {}
            self.all_department_alembics[departments] ={}
            for published_version, published_data_json_path in published_data_version_dict.items():
                if published_data_json_path:
                    published_data_dict = self.read_json(published_data_json_path)
                    published_user_data_path = published_data_json_path.split('Data')[0]
                    published_alembic_path_dict = {}
                    for published_entities, published_datas in published_data_dict.items():
                        
                        if isinstance(published_datas, dict):
                            for publish_abc_label, publish_alembic_path in published_datas.items():
                                if publish_abc_label == 'abc':
                                    published_alembic_path_dict[published_entities] = \
                                                os.path.join(published_user_data_path, publish_alembic_path)
                                    version_dict[published_version] = published_alembic_path_dict

            self.all_department_alembics.update({departments: version_dict})

        # print(json.dumps(self.all_department_alembics, indent=4))
        
    def rearrange_publish_data_by_version(self) -> None:

        self.publish_data_by_version ={}
        for department,version_dict in self.all_department_alembics.items():
            asset_dict = {}
            for _, published_data_json_dict in version_dict.items():
                for asset_label,_ in published_data_json_dict.items():
                    vesrion_asset_dicts = {  version_var: asset_publish_path
                                            for version_var, publish_dict in version_dict.items()
                                            for asset_retrived_label, asset_publish_path in publish_dict.items() 
                                            if asset_label == asset_retrived_label
                                        }
                    
                    asset_dict[asset_label] = vesrion_asset_dicts

            self.publish_data_by_version[department] = asset_dict

        # print(json.dumps(self.publish_data_by_version, indent=4))
                        
    def get_publish_data(self) -> dict:
        
        return self.publish_data_by_version          

        
           
if __name__ == '__main__':
    pfx_shot_builder = PFXShotBuilder(
                    project='ind',
                    scope='Shot/SC_65_A/SC_65A_SH_8040',
                    )
    print(json.dumps(pfx_shot_builder.get_publish_data(), indent=4))