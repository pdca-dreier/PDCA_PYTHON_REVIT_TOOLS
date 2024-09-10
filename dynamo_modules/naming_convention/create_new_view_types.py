import clr
import sys
sys.path.append('C:\Program Files (x86)\IronPython 2.7\Lib')
import System
from System import Array
from System.Collections.Generic import *
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *
clr.AddReference("RevitNodes")
import Revit
clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)
clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager 
from RevitServices.Transactions import TransactionManager 

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

import Autodesk 
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import *

doc = DocumentManager.Instance.CurrentDBDocument
uiapp = DocumentManager.Instance.CurrentUIApplication 
app = uiapp.Application 
uidoc = uiapp.ActiveUIDocument

#######OK NOW YOU CAN CODE########

class Singleton(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls._instance


class ParameterUtils(object):

    @classmethod
    def get_sh_parameter_value_by_name(cls, element, parameter_name, empty_value=""):
        try:
            parameter_value = element.LookupParameter(parameter_name)
            parameter_type = parameter_value.StorageType
            if parameter_type == StorageType.String:
                parameter_value = parameter_value.AsString()
                if parameter_value == "" or parameter_value is "":
                    parameter_value = empty_value
            if parameter_type == StorageType.Integer:
                parameter_value = parameter_value.AsInteger()
            if parameter_type == StorageType.Double:
                parameter_value = parameter_value.AsDouble()
            if parameter_type == StorageType.ElementId:
                parameter_value = parameter_value.AsElementId()
            if element.LookupParameter(parameter_name).HasValue is False:
                parameter_value = False
                if parameter_type == StorageType.String:
                    parameter_value = empty_value
        except Exception:
            parameter_value = False
        return parameter_value

    @classmethod
    def get_sh_parameter_value_by_name_or_empty_value(cls, element, parameter_name, empty_value=""):
        parameter_value = cls.get_sh_parameter_value_by_name(element, parameter_name, empty_value)
        parameter_value = empty_value if parameter_value is False else parameter_value
        return parameter_value

    @classmethod
    def get_parameter_by_parameter_list(cls, element, parameter_list, empty_value="XX", check_project_info=False):
        parameter_values = []
        for i in parameter_list:
            if type(i) is list:
                sub_parameter_values = []
                for sub_i in i:
                    sub_value = cls.get_sh_parameter_value_by_name(element, sub_i, empty_value)
                    if sub_value is False:
                        if check_project_info:
                            sub_value = cls.get_sh_parameter_value_by_name(doc.ProjectInformation, sub_i,
                                                                           empty_value="")
                    sub_parameter_values.append(sub_value)
                parameter_values.append(sub_parameter_values)
            else:
                parameter_value = cls.get_sh_parameter_value_by_name(element, i, empty_value)
                if parameter_value is False:
                    if check_project_info:
                        parameter_value = cls.get_sh_parameter_value_by_name(doc.ProjectInformation, i, empty_value="")
                parameter_values.append(parameter_value)
        return parameter_values

    @classmethod
    def get_nc_parameter_by_parameter_list(cls, element, parameter_list, empty_value="", check_project_info=True):
        parameter_values = []
        for i in parameter_list:
            if type(i) is list:
                sub_parameter_values = []
                for sub_i in i:
                    sub_value = cls.get_sh_parameter_value_by_name(element, sub_i, empty_value)
                    if sub_value is False:
                        if check_project_info:
                            sub_value = cls.get_sh_parameter_value_by_name(doc.ProjectInformation, sub_i, empty_value)
                    sub_parameter_values.append(sub_value)
                parameter_values.append(sub_parameter_values)
            else:
                parameter_value = cls.get_sh_parameter_value_by_name(element, i, empty_value)
                if parameter_value is False:
                    if check_project_info:
                        parameter_value = cls.get_sh_parameter_value_by_name(doc.ProjectInformation, i, empty_value)
                parameter_values.append(parameter_value)
        return parameter_values

    @classmethod
    def get_view_nc_parameter_by_parameter_list(cls, element,
                                                parameter_list,
                                                pm_revit_view_type_codes_by_revit_type_dicts,
                                                pm_revit_level__code_dicts,
                                                empty_value="",
                                                check_project_info=True):
        parameter_values = []
        for i in parameter_list:
            if type(i) is list:
                sub_parameter_values = []
                for sub_i in i:
                    sub_value = cls.get_sh_parameter_value_by_name(element, sub_i, empty_value)
                    if sub_value is False:
                        if check_project_info:
                            sub_value = cls.get_sh_parameter_value_by_name(doc.ProjectInformation, sub_i, empty_value)
                    if update_view_type_parameter_by_revit:
                        if sub_i == view_type_parameter_name and sub_value == "XX":
                            sub_value = pm_revit_view_type_codes_by_revit_type_dicts.get(str(element.ViewType),
                                                                                         sub_value)
                    if update_spatial_parameter_by_level:
                        if sub_i == spatial_parameter_name:
                            try:
                                view_level_name = element.get_Parameter(BuiltInParameter.PLAN_VIEW_LEVEL).AsString()
                                if not view_level_name == "":
                                    sub_value = view_level_name
                            except:
                                pass
                    sub_parameter_values.append(sub_value)
                parameter_values.append(sub_parameter_values)
            else:
                parameter_value = cls.get_sh_parameter_value_by_name(element, i, empty_value)
                if parameter_value is False:
                    if check_project_info:
                        parameter_value = cls.get_sh_parameter_value_by_name(doc.ProjectInformation, i, empty_value)
                if update_view_type_parameter_by_revit:
                    if i == view_type_parameter_name and parameter_value == "XX":
                        parameter_value = pm_revit_view_type_codes_by_revit_type_dicts.get(str(element.ViewType),
                                                                                           parameter_value)
                if update_spatial_parameter_by_level:
                    if i == spatial_parameter_name:
                        try:
                            view_level_name = element.get_Parameter(BuiltInParameter.PLAN_VIEW_LEVEL).AsString()
                            if not view_level_name == "":
                                parameter_value = view_level_name
                        except:
                            pass
                parameter_values.append(parameter_value)
        return parameter_values

    @classmethod
    def set_parameter_by_name(cls, element, parameter_name, value):
        global doc
        try:
            if element.LookupParameter(parameter_name).IsReadOnly is False:
                TransactionManager.Instance.EnsureInTransaction(doc)
                p = element.LookupParameter(parameter_name)
                p.Set(value)
                TransactionManager.Instance.TransactionTaskDone()
                return element
            else:
                return element
        except:
            failed_set_parameters_list.append((element, parameter_name, value))

    @classmethod
    def set_nc_parameter_by_name(cls, element, parameter_name, value):
        global doc
        try:
            if element.LookupParameter(parameter_name).IsReadOnly is False:
                TransactionManager.Instance.EnsureInTransaction(doc)
                p = element.LookupParameter(parameter_name)
                p.Set(value)
                TransactionManager.Instance.TransactionTaskDone()
                return element
            else:
                return element
        except:
            return element

    @classmethod
    def set_parameter_by_parameter_list(cls, element, parameter_list, parameter_value_list):
        for i, (parameter_name, parameter_value) in enumerate(zip(parameter_list, parameter_value_list)):
            cls.set_parameter_by_name(element, parameter_name, parameter_value)
        return element

    @classmethod
    def set_nc_parameter_by_parameter_list(cls, element, parameter_list, parameter_value_list):
        for i, (parameter_name, parameter_value) in enumerate(zip(parameter_list, parameter_value_list)):
            try:
                cls.set_parameter_by_name(element, parameter_name, parameter_value)
            except:
                pass
        return element


class ViewTemplatePy(object):
    instances = []

    def __new__(cls, element_id):
        for instance in cls.instances:
            if instance.element_id == element_id:
                return instance
        new_instance = super(ViewTemplatePy, cls).__new__(cls)
        cls.instances.append(new_instance)
        return new_instance

    def __init__(self, element_id):
        global doc
        self.element_id = element_id
        self.rvt_element = doc.GetElement(element_id)
        self.name = Element.Name.__get__(self.rvt_element)

        # View Template specific properties
        self.view_template_name = self.rvt_element.Name
        self.view_template_id = self.rvt_element.Id

        # Extract Scale
        try:
            self.scale = self.rvt_element.get_Parameter(BuiltInParameter.VIEW_SCALE).AsInteger()
        except:
            self.scale = None

        # Extract Discipline (if applicable)
        try:
            self.discipline = ParameterUtils.get_sh_parameter_value_by_name(self.rvt_element, "Discipline")
        except:
            self.discipline = "Not Defined"

        # Extract BEP Parameters
        self.bep_parameters = ViewTypesUtils()._bep_codes_list()
        try:
            self.bep_values = ParameterUtils.get_parameter_by_parameter_list(
                self.rvt_element,
                ViewTypesUtils()._bep_codes_list()
            )
        except:
            self.bep_values = ["N/A", "N/A", "N/A", "N/A"]

        # Extract CDE Status
        try:
            self.cde_status = ParameterUtils.get_sh_parameter_value_by_name(self.rvt_element, "CDE KOD")
        except:
            self.cde_status = "XX"

    def get_attributes(self):
        """
        Returns the dictionary of the instance's attributes for easier access.
        """
        return vars(self)


class ViewTypePy(object):
    instances = []

    def __new__(cls, element_id):
        for instance in cls.instances:
            if instance.element_id == element_id:
                return instance
        new_instance = super(ViewTypePy, cls).__new__(cls)
        cls.instances.append(new_instance)
        return new_instance

    def __init__(self, element_id):
        global doc
        self.element_id = element_id
        self.rvt_element = doc.GetElement(element_id)
        self.name = Element.Name.__get__(self.rvt_element)
        self.view_type_family_type_name = self.rvt_element.FamilyName
        self.view_type_family_type_number = ViewTypesUtils()._view_types_dict().get(self.view_type_family_type_name, "900")
        self.default_view_template_element_id = self.rvt_element.get_Parameter(BuiltInParameter.DEFAULT_VIEW_TEMPLATE).AsElementId()
        self.default_view_template_rvt_element = doc.GetElement(self.default_view_template_element_id)
        if self.default_view_template_element_id != ElementId(-1):
            self.default_view_template_rvt_element_name = self.default_view_template_rvt_element.Name
        else:
            self.default_view_template_rvt_element_name = None
        # Get Scale
        try:
            self.default_view_template_rvt_element_scale = "1*" + str(self.default_view_template_rvt_element.get_Parameter(BuiltInParameter.VIEW_SCALE).AsInteger())
        except:
            self.default_view_template_rvt_element_scale = ""
        # Get CDE Status
        try:
            self.default_view_template_rvt_element_cde_status = ParameterUtils.get_sh_parameter_value_by_name(
                self.default_view_template_rvt_element, "CDE KOD"
            )
        except:
            self.default_view_template_rvt_element_cde_status = "XX"
        # Get BEP Values
        self.default_view_template_rvt_element_bep_parameters = ViewTypesUtils()._bep_codes_list()
        try:

            self.default_view_template_rvt_element_bep_parameters_values = ParameterUtils.get_parameter_by_parameter_list(
                self.default_view_template_rvt_element,
                ViewTypesUtils()._bep_codes_list()
            )
        except:
            self.default_view_template_rvt_element_bep_parameters_values = ["XX", "XX", self.view_type_family_type_number, "XXX"]

    def get_attributes(self):
        return vars(self)


class ViewTypesUtils(Singleton):

    @staticmethod
    def _view_types_dict():
        _view_types_dict = {
            "Area Plan": "700",
            "Ceiling Plan": "110",
            "Floor Plan": "100",
            "Structural Plan": "400",
            "Detail View": "500",
            "Drafting View": "500",
            "Elevation": "300",
            "Legend": "900",
            "Schedule": "600",
            "Section": "200",
            "3D View": "800",
            "Sheet": "000"
        }
        return _view_types_dict

    @staticmethod
    def _view_templates_to_view_types_dict():
        _view_types_dict = {
            "0": "Floor Plan",
            "10": "Floor Plan",
            "11": "Ceiling Plan",
            "8": "3D View",
            "2" :"Building Elevation",
            "3": "Building Section",
            "6": "Schedule",
        }
        return _view_types_dict

    @staticmethod
    def _bep_codes_list():
        _nc_policy_codes_list = [
            # "MIEJSCE KOD",
            # "BUDYNEK KOD",
            "FAZA KOD",
            "BRANŻA KOD",
            "TYP KOD",
            # "STREFA KOD",
            "NUMER KOD",
        ]
        return _nc_policy_codes_list

    @staticmethod
    def _default_view_types_list_names():
        dvt_list = [
            "Floor Plan",
            "Ceiling Plan",
            "3D View",
            "Building Elevation",
            "Building Section",
            "Schedule"
        ]
        return dvt_list

    @staticmethod
    def create_view_types_instances():
        view_collector = FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
        for view_type in view_collector:
            ViewTypePy(view_type.Id)

    @staticmethod
    def create_view_templates_instances():
        all_views = FilteredElementCollector(doc).OfClass(View).ToElements()
        for view in all_views:
            if view.IsTemplate:
                ViewTemplatePy(view.Id)

    @classmethod
    def get_default_view_templates_dict(cls):

        cls.create_view_templates_instances()

        default_dict = {}

        for view_template_py in ViewTemplatePy.instances:
            view_template_name = view_template_py.name
            if view_template_name in cls._default_view_types_list_names():  # Check if the name is in your list
                default_dict[view_template_name] = view_template_py

        return default_dict

    @classmethod
    def get_default_view_types_dict(cls):

        cls.create_view_templates_instances()
        cls.create_view_types_instances()

        default_dict = {}

        for view_type_py in ViewTypePy.instances:
            view_type_name = view_type_py.name
            if view_type_name in cls._default_view_types_list_names():  # Check if the name is in your list
                default_dict[view_type_name] = view_type_py

        return default_dict

    @staticmethod
    def copy_view_type(default_element_id, new_name="new_name"):
        TransactionManager.Instance.EnsureInTransaction(doc)
        new_vt = doc.GetElement(Autodesk.Revit.DB.ElementTransformUtils.CopyElement(doc, default_element_id, XYZ(0, 0, 0))[0])
        try:
            new_vt.Name = new_name
        except:
            new_vt.Name = "USUN-" + str(new_vt.Id)
        TransactionManager.Instance.TransactionTaskDone()
        return new_vt

    @classmethod
    def create_new_view_types_by_view_templates(cls):

        cls.create_view_types_instances()
        cls.create_view_templates_instances()

        output_list = []

        for view_template_py in ViewTemplatePy.instances:
            view_template_name = view_template_py.name
            view_template_id = view_template_py.element_id
            view_template_type_code = ParameterUtils.get_sh_parameter_value_by_name(view_template_py.rvt_element, "TYP KOD", "---")

            if view_template_type_code != "---":
                if view_template_type_code != False:
                    if view_template_type_code.startswith("1"):
                        view_template_type_code = view_template_type_code[:2]
                    else:
                        view_template_type_code = view_template_type_code[0]
                    default_view_type_name = cls._view_templates_to_view_types_dict().get(view_template_type_code, False)
                    if default_view_type_name != False:
                        default_view_type_py_instance = cls.get_default_view_types_dict().get(default_view_type_name, False)
                        if default_view_type_py_instance != False:
                            vti = cls.copy_view_type(default_view_type_py_instance.element_id, new_name=view_template_name)
                            # output_list.append((view_template_type_code, view_template_id))
                            try:
                                TransactionManager.Instance.EnsureInTransaction(doc)
                                # Set New Default View Template
                                p = vti.get_Parameter(BuiltInParameter.DEFAULT_VIEW_TEMPLATE)
                                p.Set(view_template_id)
                                TransactionManager.Instance.TransactionTaskDone()
                            except:
                                pass
                            output_list.append(vti)

        return output_list


    @staticmethod
    def set_new_default_view_template_to_view_type_instance(view_type_instance, new_default_view_template_id):
        vti = view_type_instance.rvt_element
        TransactionManager.Instance.EnsureInTransaction(doc)
        # Set New Default View Template
        p = vti.get_Parameter(BuiltInParameter.DEFAULT_VIEW_TEMPLATE)
        p.Set(new_default_view_template_id)
        TransactionManager.Instance.TransactionTaskDone()

    @staticmethod
    def set_new_name_to_view_type_instance(view_type_instance, new_name):
        vti = view_type_instance.rvt_element
        TransactionManager.Instance.EnsureInTransaction(doc)
        # Set New name for view type
        vti.Name = new_name
        TransactionManager.Instance.TransactionTaskDone()

    @staticmethod
    def create_view_template_to_view_types_dict():
        template_dict = {}

        for view_type_py in ViewTypePy.instances:
            default_template_id = view_type_py.default_view_template_element_id
            if default_template_id != ElementId(-1):
                default_template_id = int(str(default_template_id))
                if default_template_id not in template_dict:
                    template_dict[default_template_id] = []
                template_dict[default_template_id].append(view_type_py)

        return template_dict

    @staticmethod
    def view_templates_with_with_referencing_view_types():
        output_list = []
        for key, value in ViewTypesUtils.create_view_template_to_view_types_dict().items():
            # View Templates Element
            key = doc.GetElement(ElementId(int(key)))
            # ViewTypePy ist  variable value
            output_list.append((key, value))
        return output_list


def clean_spaces(input_string):
    return ' '.join(input_string.split())

create_view_types = True
if create_view_types:
    new_view_types_list = ViewTypesUtils.create_new_view_types_by_view_templates()

ViewTypesUtils.create_view_types_instances()
ViewTypesUtils.get_default_view_templates_dict()

view_templates_with_view_types = ViewTypesUtils.view_templates_with_with_referencing_view_types()


temp = []
for vti_py in ViewTypePy.instances:
    vti_py_cde = vti_py.default_view_template_rvt_element_cde_status
    # temp.append((vti_py.name , vti_py.default_view_template_rvt_element, vti_py_cde))
    if vti_py_cde != False:
        vti_py_scale = vti_py.default_view_template_rvt_element_scale
        if vti_py_scale != False:
            vti_py_param_list = vti_py.default_view_template_rvt_element_bep_parameters_values
            if any(not element for element in vti_py_param_list):
                # Any False
                pass
            else:
                try:
                    vti_py_name = vti_py.name
                    # vti_py_name_current_des = vti_py_name.split("_")[-1].split("1*")[0]
                    vti_py_param_list[-1] = vti_py_param_list[-1].replace("X","0")
                    vti_py_name_current_des = vti_py.default_view_template_rvt_element_name.split("_")[2].split(" 1*")[0]
                    vti_py_param = "-".join(vti_py_param_list)
                    vti_py_new_name = vti_py_cde + "_" + vti_py_param + "_" + vti_py_name_current_des + " " + vti_py_scale
                    vti_py_new_name = clean_spaces(vti_py_new_name)
                    # vti_py_new_name = str(vti_py.rvt_element.Id)
                    ViewTypesUtils.set_new_name_to_view_type_instance(vti_py, vti_py_new_name)
                    temp.append((vti_py_name_current_des , vti_py_new_name))
                except:
                    pass


OUT = new_view_types_list, temp