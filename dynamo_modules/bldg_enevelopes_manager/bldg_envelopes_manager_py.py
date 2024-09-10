import clr
import sys
import math
import os

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

from collections import defaultdict

clr.AddReference("Microsoft.Office.Interop.Excel")
import Microsoft.Office.Interop.Excel as Excel

# AUTHOR:
# ©PAWEŁ DREIER

doc = DocumentManager.Instance.CurrentDBDocument
uiapp = DocumentManager.Instance.CurrentUIApplication
app = uiapp.Application
uidoc = uiapp.ActiveUIDocument

failed_lst = []


#######OK NOW YOU CAN CODE########
class Singleton(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls._instance


# Class for reading Excel files
class ReadXLS(object):
    __instance = None

    def __new__(cls, file_path=None):
        if cls.__instance is None:
            cls.__instance = super(ReadXLS, cls).__new__(cls)
        return cls.__instance

    def __init__(self, file_path):
        self.file_path = file_path
        self.worksheets_list = self.get_worksheet_names()

    def get_worksheet_names(self):
        excel = Excel.ApplicationClass()
        workbook = excel.Workbooks.Open(self.file_path)
        worksheet_names = [worksheet.Name for worksheet in workbook.Worksheets]
        workbook.Close(True)
        excel.Quit()
        return worksheet_names

    def get_worksheet_data(self, worksheet_name="SHARED PARAMETERS"):
        excel = Excel.ApplicationClass()
        workbook = excel.Workbooks.Open(self.file_path)
        worksheet = workbook.Worksheets[worksheet_name]
        worksheet_data = []
        for row in range(1, worksheet.UsedRange.Rows.Count + 1):
            row_data = []
            for col in range(1, worksheet.UsedRange.Columns.Count + 1):
                cell_value = worksheet.Cells[row, col].Value2
                cell_value = "" if cell_value is None else cell_value
                row_data.append(cell_value)
            worksheet_data.append(row_data)
        workbook.Close(True)
        excel.Quit()
        return worksheet_data


# Class for writing data to Excel file
class WriteXLS(object):
    def __init__(self, file_path):
        self.file_path = file_path

    def write_to_excel(self, data, worksheet_name="Output"):
        excel = Excel.ApplicationClass()
        workbook = excel.Workbooks.Open(self.file_path)
        try:
            workbook_name = os.path.splitext(os.path.basename(self.file_path))[0]
            worksheet = workbook.Worksheets[worksheet_name]
        except KeyError:
            workbook.Close()
            excel.Quit()
            return
        for i, row in enumerate(data, 1):
            for j, value in enumerate(row, 1):
                worksheet.Cells[i, j].Value = value
        workbook.Save()
        workbook.Close()
        excel.Quit()


class ListUtils:
    @classmethod
    def sort_list_by_index(cls, lst, n):
        sorted_lst = sorted(lst, key=lambda x: x[n])
        return sorted_lst

    @classmethod
    def extract_elements_from_sub_lists(cls, list_of_sublists, index_to_extract):
        extracted_elements = [sublist[index_to_extract] for sublist in list_of_sublists]
        return extracted_elements

    @classmethod
    def group_by_index(cls, list_of_sublists, index_to_group_by):
        grouped_data = {}
        for sublist in list_of_sublists:
            key = sublist[index_to_group_by]
            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(sublist)

        # Convert the grouped data dictionary to a list
        grouped_list = sorted(list(grouped_data.values()))
        return grouped_list


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
    def get_parameter_by_parameter_list(cls, element, parameter_list, empty_value="", check_project_info=False):
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


class DuplicatesUtils:

    @staticmethod
    def _add_prefix_to_duplicates_views():
        full_code_count = {}  # Dictionary to keep track of full_code count
        duplicates_dict_from_dict = {}

        # Count the occurrences of each full_code
        for instance in PyRevit.RevitViewOrSheetElement.views_instances:
            full_code = instance.nc_code
            full_code_count[full_code] = full_code_count.get(full_code, 0) + 1

        #
        duplicates_list_from_dict = [key for key, value in full_code_count.items() if value > 1]
        for i, key in enumerate(duplicates_list_from_dict, 1):
            duplicates_dict_from_dict[key] = i
        #
        # Modify full_code based on duplicates
        for instance in PyRevit.RevitViewOrSheetElement.views_instances:
            element = instance.nc_code
            element_short_name = instance.nc_view_short_name
            count = full_code_count[element]
            if count >= 1:
                duplicate_m_number = duplicates_dict_from_dict.get(element, "REMOVE")
                duplicate_number = count
                element_output = "DUPLIKAT_KODU_" + str(duplicate_m_number).zfill(3) + "." + str(
                    duplicate_number).zfill(3) + "_" + element
                element_output_short = "DUPLIKAT_KODU_" + str(duplicate_m_number).zfill(3) + "." + str(duplicate_number).zfill(3) + "_" + element_short_name
                full_code_count[element] -= 1
                if "REMOVE" in element_output:
                    instance.nc_code = element
                else:
                    instance.nc_code = element_output
                    instance.nc_view_short_name = element_output_short
            else:
                instance.nc_code = element

        # error_log.append((instance.nc_code, instance.nc_view_short_name, instance.element))
        # for instance in PyRevit.RevitViewOrSheetElement.views_instances:
        #     error_log.append(instance.nc_code)

    @staticmethod
    def _add_prefix_to_duplicates_sheets():
        full_code_count = {}  # Dictionary to keep track of full_code count
        duplicates_dict_from_dict = {}

        # Count the occurrences of each view_or_sheet.nc_code
        for instance in PyRevit.RevitViewOrSheetElement.sheets_instances:
            full_code = instance.nc_code
            full_code_count[full_code] = full_code_count.get(full_code, 0) + 1
        #
        duplicates_list_from_dict = [key for key, value in full_code_count.items() if value > 1]
        for i, key in enumerate(duplicates_list_from_dict, 1):
            duplicates_dict_from_dict[key] = i
        #
        # Modify full_code based on duplicates
        for instance in PyRevit.RevitViewOrSheetElement.sheets_instances:
            element = instance.nc_code
            count = full_code_count[element]
            if count >= 1:
                duplicate_m_number = duplicates_dict_from_dict.get(element, "REMOVE")
                duplicate_number = count
                element_output = "DUPLIKAT_KODU_" + str(duplicate_m_number).zfill(3) + "." + str(
                    duplicate_number).zfill(3) + "_" + element
                full_code_count[element] -= 1
                if "REMOVE" in element_output:
                    instance.nc_code = element
                else:
                    instance.nc_code = element_output
            else:
                instance.nc_code = element

        # error_log.append("SHEETS")
        # for instance in PyRevit.RevitViewOrSheetElement.sheets_instances:
        #     error_log.append(instance.nc_code)


class PyMaterial:
    instances = []

    def __init__(self, element_id):
        self.element_id = element_id
        self.element = doc.GetElement(element_id)
        self.name = self.element.Name
        self.description = self.element.LookupParameter("Description").AsString() if self.element.LookupParameter(
            "Description") else None
        self.class_ = self.element.LookupParameter("Class").AsString() if self.element.LookupParameter(
            "Class") else None
        self.keywords = self.element.LookupParameter("Keywords").AsString() if self.element.LookupParameter(
            "Keywords") else None
        self.model = self.element.LookupParameter("Model").AsString() if self.element.LookupParameter("Model") else None
        self.manufacturer = self.element.LookupParameter("Manufacturer").AsString() if self.element.LookupParameter(
            "Manufacturer") else None
        self.comments = self.element.LookupParameter("Comments").AsString() if self.element.LookupParameter(
            "Comments") else None
        self.keynote = ParameterUtils.get_sh_parameter_value_by_name(self.element, "Keynote")
        self.mark = self.element.LookupParameter("Mark").AsString() if self.element.LookupParameter("Mark") else None
        # Surface patterns and colors
        self.surface_foreground_pattern_id = self.get_name_by_id(self.element.SurfaceForegroundPatternId)
        self.surface_foreground_pattern_color = PyMaterialsUtils.revit_color_to_hex(
            self.element.SurfaceForegroundPatternColor)
        self.surface_background_pattern_id = self.get_name_by_id(self.element.SurfaceBackgroundPatternId)
        self.surface_background_pattern_color = PyMaterialsUtils.revit_color_to_hex(
            self.element.SurfaceBackgroundPatternColor)
        # Cut patterns and colors
        self.cut_foreground_pattern_id = self.get_name_by_id(self.element.CutForegroundPatternId)
        self.cut_foreground_pattern_color = PyMaterialsUtils.revit_color_to_hex(self.element.CutForegroundPatternColor)
        self.cut_background_pattern_id = self.get_name_by_id(self.element.CutBackgroundPatternId)
        self.cut_background_pattern_color = PyMaterialsUtils.revit_color_to_hex(self.element.CutBackgroundPatternColor)
        try:
            self.asset = doc.GetElement(self.element.AppearanceAssetId).Name
        except:
            self.asset = doc.GetElement(self.element.AppearanceAssetId)
        #
        self.instances.append(self)

    @staticmethod
    def get_name_by_id(id):
        name = None
        try:
            name = doc.GetElement(id).Name
        except:
            name = doc.GetElement(id)
        return name

    def get_attributes(self):
        # Define a list to store attribute values
        attribute_values = [
            str(self.element_id),
            str(self.name),
            str(self.description),
            str(self.class_),
            str(self.keywords),
            str(self.model),
            str(self.manufacturer),
            str(self.comments),
            str(self.keynote),
            str(self.mark),
            str(self.surface_foreground_pattern_id),
            str(self.surface_foreground_pattern_color),
            str(self.surface_background_pattern_id),
            str(self.surface_background_pattern_color),
            str(self.cut_foreground_pattern_id),
            str(self.cut_foreground_pattern_color),
            str(self.cut_background_pattern_id),
            str(self.cut_background_pattern_color),
            str(self.asset)
        ]
        return attribute_values

    def set_name(self, new_name):
        self.name = new_name
        self.element.Name = new_name

    def set_description(self, new_description):
        self.description = new_description
        self.element.LookupParameter("Description").Set(new_description)

    def set_class(self, new_class):
        try:
            self.class_ = new_class
            self.element.LookupParameter("Class").Set(new_class)
        except:
            pass

    def set_keywords(self, new_keywords):
        try:
            self.keywords = new_keywords
            self.element.LookupParameter("Keywords").Set(new_keywords)
        except:
            pass

    def set_model(self, new_model):
        self.model = new_model
        self.element.LookupParameter("Model").Set(new_model)

    def set_manufacturer(self, new_manufacturer):
        self.manufacturer = new_manufacturer
        self.element.LookupParameter("Manufacturer").Set(new_manufacturer)

    def set_comments(self, new_comments):
        self.comments = new_comments
        self.element.LookupParameter("Comments").Set(new_comments)

    def set_keynote(self, new_keynote):
        self.keynote = new_keynote
        ParameterUtils.set_parameter_by_name(self.element, "Keynote", new_keynote)

    def set_mark(self, new_mark):
        self.mark = new_mark
        self.element.LookupParameter("Mark").Set(new_mark)


class PyMaterialsUtils():

    @staticmethod
    def create_dictionary(keys_list, values_list):
        # Check if the length of keys_list and values_list are the same
        if len(keys_list) != len(values_list):
            raise ValueError("Length of keys_list and values_list must be the same")

        # Create an empty dictionary
        result_dict = {}

        # Iterate through the keys_list and values_list to populate the dictionary
        for key, value in zip(keys_list, values_list):
            result_dict[key] = value

        return result_dict

    @staticmethod
    def collect_all_materials(include_in_list_if_name_contains=""):
        collector = FilteredElementCollector(doc).OfClass(Material).ToElements()
        materials = [mat for mat in collector if include_in_list_if_name_contains in mat.Name]
        return materials

    @classmethod
    def materials_names_dict(cls):
        materials = cls.collect_all_materials()
        materials_names = [mat.Name for mat in materials]
        materials_ids = [mat.Id for mat in materials]
        output_dict = cls.create_dictionary(materials_names, materials_ids)
        return output_dict

    @classmethod
    def materials_ids_dict(cls):
        materials = cls.collect_all_materials()
        materials_names = [mat.Name for mat in materials]
        materials_ids = [mat.Id for mat in materials]
        output_dict = cls.create_dictionary(materials_ids, materials)
        return output_dict

    @staticmethod
    def collect_all_material_assets():
        collector = FilteredElementCollector(doc).OfClass(Material).ToElements()
        material_assets = [mat.AppearanceAssetId for mat in collector if mat.AppearanceAssetId is not None]
        output = []
        for mat_asset in material_assets:
            try:
                mat_asset = doc.GetElement(mat_asset)
                mat_name = mat_asset.Name
                output.append(mat_asset)
            except:
                pass

        return output

    @classmethod
    def all_materials_assets_dict(cls):
        materials_assets = cls.collect_all_material_assets()
        materials_assets_names = [mat.Name for mat in materials_assets]
        materials_assets_ids = [mat.Id for mat in materials_assets]
        output_dict = cls.create_dictionary(materials_assets_names, materials_assets_ids)
        return output_dict

    @staticmethod
    def collect_all_model_patterns():
        collector = FilteredElementCollector(doc).OfClass(FillPatternElement).ToElements()
        model_patterns = [pattern for pattern in collector if isinstance(pattern.GetFillPattern(), FillPattern)]
        output = []
        for pattern in model_patterns:
            try:
                pattern_name = pattern
                output.append(pattern_name)
            except:
                pass

        return output

    @classmethod
    def all_model_patterns_names_dict(cls):
        all_model_patterns = cls.collect_all_model_patterns()
        all_model_patterns_names = [mat.Name for mat in all_model_patterns]
        all_model_patterns_ids = [mat.Id for mat in all_model_patterns]
        output_dict = cls.create_dictionary(all_model_patterns_names, all_model_patterns_ids)
        return output_dict

    @staticmethod
    def collect_all_detail_patterns():
        collector = FilteredElementCollector(doc).OfClass(FillPatternElement).ToElements()
        detail_patterns = [pattern for pattern in collector if not isinstance(pattern.GetFillPattern(), FillPattern)]
        output = []
        for pattern in detail_patterns:
            try:
                pattern_name = pattern.Name
                output.append(pattern_name)
            except:
                pass

        return output

    @staticmethod
    def revit_color_to_hex(revit_color):
        # Extract RGB values from the Revit color parameter
        red = int(revit_color.Red)
        green = int(revit_color.Green)
        blue = int(revit_color.Blue)

        # Convert RGB values to hexadecimal format
        hex_color = "#{:02X}{:02X}{:02X}".format(red, green, blue)

        return hex_color

    @staticmethod
    def hex_to_revit_color(hex_color):

        # Remove '#' if present
        hex_color = hex_color.lstrip('#')

        # Convert hexadecimal color code to RGB values
        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)

        # Create a Revit color parameter
        revit_color = Color(red, green, blue)

        return revit_color

    @staticmethod
    def materials_headers():
        headers = [[
            "ELEMENT ID",
            "NAME",
            "DESCRIPTION",
            "CLASSIFICATION",
            "KEYWORDS",
            "MODEL",
            "MANUF.",
            "COMMENTS",
            "KEYNOTE",
            "MARK",
            "SURFACE PATTERN FG",
            "SURFACE PATTERN FG COLOR",
            "SURFACE PATTERN BG",
            "SURFACE PATTERN BG COLOR",
            "CUT PATTERN FG",
            "CUT PATTERN FG COLOR",
            "CUT PATTERN BG",
            "CUT PATTERN BG COLOR",
            "ASSET"
        ]]
        return headers

    @classmethod
    def get_materials_dataset_to_xlsx(cls):

        data_list = cls.materials_headers()

        for py_material in PyMaterial.instances:
            attributes = py_material.get_attributes()
            data_list.append(attributes)

        return data_list

    @classmethod
    def create_new_material(cls, name):
        # Start a transaction
        TransactionManager.Instance.EnsureInTransaction(doc)

        # Create a new material
        new_material = doc.GetElement(Autodesk.Revit.DB.Material.Create(doc, name))

        # # Set material properties
        # appearance_asset_id = new_material.AppearanceAssetId
        # appearance_asset = doc.GetElement(appearance_asset_id)
        #
        # if appearance_asset:
        #     asset_prop = appearance_asset.FindByName(AssetPropertyType.Material)
        #     if asset_prop:
        #         asset_prop.SetMaterialColor(color)
        #
        # Commit the transaction
        TransactionManager.Instance.TransactionTaskDone()

        return new_material

    @classmethod
    def set_materials_parameters_from_xlsx(cls, xlsx_dataset):

        failed_lst = []
        materials_dictionary = PyMaterialsUtils.materials_ids_dict()
        patterns_dictionary = PyMaterialsUtils.all_model_patterns_names_dict()
        assets_dictionary = PyMaterialsUtils.all_materials_assets_dict()
        # xlsx_dataset = xlsx_dataset[:5]
        xlsx_dataset = xlsx_dataset
        for row in xlsx_dataset:
            TransactionManager.Instance.EnsureInTransaction(doc)
            for i, cell in enumerate(row):
                # Check if cell header matches and add comments accordingly
                if i == 0:
                    # Comment for "ELEMENT ID"
                    try:
                        element = materials_dictionary.get(ElementId(int(cell)), False)
                    except:
                        element = False
                    if element is not False:
                        py_material = PyMaterial(element.Id)
                        temp.append(element)
                    if element is False:
                        # Create new material
                        new_name = row[1]
                        py_material = PyMaterial(cls.create_new_material(new_name).Id)
                elif i == 1:
                    # Comment for "NAME"
                    py_material.set_name(cell)
                elif i == 2:
                    # Comment for "DESCRIPTION"
                    py_material.set_description(cell)
                elif i == 3:
                    # Comment for "CLASSIFICATION"
                    py_material.set_class(cell)
                elif i == 4:
                    # Comment for "KEYWORDS"
                    py_material.set_keywords(cell)
                elif i == 5:
                    # Comment for "MODEL"
                    py_material.set_model(cell)
                elif i == 6:
                    # Comment for "MANUF."
                    py_material.set_manufacturer(cell)
                elif i == 7:
                    # Comment for "COMMENTS"
                    py_material.set_comments(cell)
                elif i == 8:
                    # Comment for "KEYNOTE"
                    py_material.set_keynote(cell)
                elif i == 9:
                    # Comment for "MARK"
                    py_material.set_mark(cell)
                elif i == 10:
                    # Comment for "SURFACE PATTERN FG"
                    pattern_id = patterns_dictionary.get(cell, False)
                    if pattern_id is not False:
                        py_material.element.SurfaceForegroundPatternId = pattern_id
                elif i == 11:
                    # Comment for "SURFACE PATTERN FG COLOR"
                    new_color = PyMaterialsUtils.hex_to_revit_color(cell)
                    py_material.element.SurfaceForegroundPatternColor = new_color
                elif i == 12:
                    # Comment for "SURFACE PATTERN BG"
                    pattern_id = patterns_dictionary.get(cell, False)
                    if pattern_id is not False:
                        py_material.element.SurfaceBackgroundPatternId = pattern_id
                elif i == 13:
                    # Comment for "SURFACE PATTERN BG COLOR"
                    new_color = PyMaterialsUtils.hex_to_revit_color(cell)
                    py_material.element.SurfaceBackgroundPatternColor = new_color
                elif i == 14:
                    # Comment for "CUT PATTERN FG"
                    pattern_id = patterns_dictionary.get(cell, False)
                    if pattern_id is not False:
                        py_material.element.CutForegroundPatternId = pattern_id
                elif i == 15:
                    # Comment for "CUT PATTERN FG COLOR"
                    new_color = PyMaterialsUtils.hex_to_revit_color(cell)
                    py_material.element.CutForegroundPatternColor = new_color
                elif i == 16:
                    # Comment for "CUT PATTERN BG"
                    pattern_id = patterns_dictionary.get(cell, False)
                    if pattern_id is not False:
                        py_material.element.CutBackgroundPatternId = pattern_id
                elif i == 17:
                    # Comment for "CUT PATTERN BG COLOR"
                    new_color = PyMaterialsUtils.hex_to_revit_color(cell)
                    py_material.element.CutBackgroundPatternColor = new_color
                elif i == 18:
                    # Comment for "ASSET"
                    new_asset_id = assets_dictionary.get(cell, False)
                    if new_asset_id is not False:
                        py_material.element.AppearanceAssetId = new_asset_id
            TransactionManager.Instance.TransactionTaskDone()
        return failed_lst


class BuildingEnvelope():
    def __init__(self, rvt_element=None, rvt_element_id=None, type_name="", compound_layers=None,
                 width=0.0, function="", horizontal=False, vertical=False, category="",
                 coarse_pattern=None, coarse_fill_color=None, keynote="", model="",
                 manufacturer="", type_comments="", description="", assembly_code="",
                 type_mark="", be_code="", be_code_all_compound_layers="", be_code_auto=True):
        # Revit Element and ID
        self.rvt_element = rvt_element  # The Revit Element object
        self.rvt_element_id = rvt_element_id  # The ElementId in Revit

        # General Information
        self.type_name = type_name  # The type name of the building envelope
        self.compound_layers = compound_layers if compound_layers else []  # List of CompoundLayer objects
        self.width = width  # The total width of the building envelope
        self.function = function  # Function of the element (e.g., Exterior, Interior)

        # Orientation
        self.horizontal = horizontal  # Boolean indicating horizontal orientation
        self.vertical = vertical  # Boolean indicating vertical orientation

        # Revit Category
        self.category = category  # Category of the element (e.g., Walls, Floors, Roofs)

        # Coarse Representation
        self.coarse_pattern = coarse_pattern  # Coarse fill pattern for the element
        self.coarse_fill_color = coarse_fill_color  # Coarse fill color

        # Documentation Properties
        self.keynote = keynote  # Keynote associated with the element
        self.model = model  # Model associated with the element
        self.manufacturer = manufacturer  # Manufacturer of the element
        self.type_comments = type_comments  # Comments related to the element type
        self.description = description  # Description of the element
        self.assembly_code = assembly_code  # Assembly code
        self.type_mark = type_mark  # Type mark for the element

        # Building Envelope Code
        self.be_code = be_code  # Specific code for the building envelope
        self.be_code_all_compound_layers = be_code_all_compound_layers  # Code combining all layers
        self.be_code_auto = be_code_auto  # Boolean to automatically generate `be_code`

    def calculate_width(self):
        # Calculate the total width from compound layers if applicable
        self.width = sum(layer.thickness for layer in self.compound_layers)

    def generate_be_code(self):
        # Generate building envelope code if auto-generation is enabled
        if self.be_code_auto:
            self.be_code = f"{self.category}_{self.function}_{self.width:.2f}"


class CompoundLayer():
    def __init__(self, order_index=0, function="", material="", thickness=0.0, wraps=False,
                 structural_material=False, variable=False, is_core=False):
        self.order_index = order_index  # Index of the layer in the compound structure
        self.function = function  # Function of the layer (e.g., Structure, Finish)
        self.material = material  # Material name or ID
        self.thickness = thickness  # Thickness of the layer
        self.wraps = wraps  # Boolean indicating if the layer wraps
        self.structural_material = structural_material  # Boolean for structural material
        self.variable = variable  # Boolean indicating if the thickness is variable
        self.is_core = is_core  # Boolean indicating if the layer is part of the core