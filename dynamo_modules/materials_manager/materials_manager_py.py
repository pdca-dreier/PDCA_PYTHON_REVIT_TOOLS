import clr
import sys
import os
from collections import defaultdict

# Add CLR references for Revit and Geometry
clr.AddReference('ProtoGeometry')
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("RevitNodes")
clr.AddReference("RevitServices")
clr.AddReference("Microsoft.Office.Interop.Excel")

# Import DesignScript libraries for geometry operations
from Autodesk.DesignScript.Geometry import *

# Import Revit DB and UI elements
import Autodesk.Revit.DB as DB
import Autodesk.Revit.UI as UI

# Import Revit services
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

# Import Revit and Excel extensions
import Revit

clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)
import Microsoft.Office.Interop.Excel as Excel

# Add standard Python library path for IronPython
sys.path.append('C:/Program Files (x86)/IronPython 2.7/Lib')

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

import math

import decimal

from System import Object
from Microsoft.Office.Interop import Excel

doc = DocumentManager.Instance.CurrentDBDocument
uiapp = DocumentManager.Instance.CurrentUIApplication
app = uiapp.Application
uidoc = uiapp.ActiveUIDocument

excel_path_string = IN[0]
import_data = UnwrapElement(IN[1])
export_data = UnwrapElement(IN[2])

temp = []
failed_set_parameters_list = []


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
    def collect_all_ako_materials(include_in_list_if_name_contains=""):
        collector = FilteredElementCollector(doc).OfClass(Material).ToElements()
        materials = [mat for mat in collector if include_in_list_if_name_contains in mat.Name]
        return materials

    @classmethod
    def ako_materials_names_dict(cls):
        ako_materials = cls.collect_all_ako_materials()
        ako_materials_names = [mat.Name for mat in ako_materials]
        ako_materials_ids = [mat.Id for mat in ako_materials]
        output_dict = cls.create_dictionary(ako_materials_names, ako_materials_ids)
        return output_dict

    @classmethod
    def ako_materials_ids_dict(cls):
        ako_materials = cls.collect_all_ako_materials()
        ako_materials_names = [mat.Name for mat in ako_materials]
        ako_materials_ids = [mat.Id for mat in ako_materials]
        output_dict = cls.create_dictionary(ako_materials_ids, ako_materials)
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
        materials_dictionary = PyMaterialsUtils.ako_materials_ids_dict()
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


input_xlsx_dataset = []
# ## Load dataset to Revit ## #
if import_data:
    # Example usage:
    excel_path_string = IN[0]  # Ensure you have an input system in place
    xls_reader = ReadXLS(file_path=excel_path_string)
    worksheet_names = xls_reader.get_worksheet_names()
    worksheet_data = xls_reader.get_worksheet_data("DYN")
    input_xlsx_dataset = worksheet_data[1:]
    #
    PyMaterialsUtils.set_materials_parameters_from_xlsx(input_xlsx_dataset)

# ## Export dataset to XLSX ## #
xls_dataset_list = PyMaterialsUtils.materials_headers() + input_xlsx_dataset
if export_data:
    PyMaterial.instances = []
    ako_materials_list = PyMaterialsUtils.collect_all_ako_materials()

    for material in ako_materials_list:
        PyMaterial(material.Id)

    xls_dataset_list = PyMaterialsUtils.get_materials_dataset_to_xlsx()
    xls_dataset_list = xls_dataset_list[:]

    # Example usage for writing data
    xls_writer = WriteXLS(file_path=excel_path_string)
    data_to_write = xls_dataset_list
    xls_writer.write_to_excel(data_to_write, worksheet_name="DYN")

all_materials = PyMaterialsUtils.collect_all_ako_materials()

output = []

for material in all_materials:
    material_class = ParameterUtils.get_sh_parameter_value_by_name(material, "Class")
    material_mark = ParameterUtils.get_sh_parameter_value_by_name(material, "Mark")
    keynote = ParameterUtils.get_sh_parameter_value_by_name(material, "Keynote")
    output.append((material_mark, keynote, material_class))

OUT = input_xlsx_dataset, output
