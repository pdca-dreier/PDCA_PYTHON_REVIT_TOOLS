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
from abc import ABC, abstractmethod

#######OK NOW YOU CAN CODE########

# Shared Revit document context
uiapp = DocumentManager.Instance.CurrentUIApplication
app = uiapp.Application
uidoc = uiapp.ActiveUIDocument
doc = DocumentManager.Instance.CurrentDBDocument

# --- FLEXIBLE DIMENSION DATA CLASS ---
class FamilyDimensions:
    def __init__(self, *, width=None, height=None, rough_width=None, rough_height=None):
        self.width = width
        self.height = height
        self.rough_width = rough_width
        self.rough_height = rough_height

    def has_rough_dims(self):
        return self.rough_width is not None and self.rough_height is not None

    def has_final_dims(self):
        return self.width is not None and self.height is not None

    def __repr__(self):
        return f"FamilyDimensions(width={self.width}, height={self.height}, rough_width={self.rough_width}, rough_height={self.rough_height})"

# --- UNIT UTILITIES ---
class UnitUtils:
    @staticmethod
    def convert_internal_to_cm(value):
        return UnitUtils._convert_from_internal(value, UnitTypeId.Centimeters)

    @staticmethod
    def convert_cm_to_internal(value_cm):
        return UnitUtils._convert_to_internal(value_cm, UnitTypeId.Centimeters)

    @staticmethod
    def _convert_from_internal(value, unit_type):
        return UnitUtils._safe_convert(value, lambda v: UnitUtils.ConvertFromInternalUnits(v, unit_type))

    @staticmethod
    def _convert_to_internal(value, unit_type):
        return UnitUtils._safe_convert(value, lambda v: UnitUtils.ConvertToInternalUnits(v, unit_type))

    @staticmethod
    def _safe_convert(value, converter):
        try:
            return converter(value)
        except:
            return None

# --- LIST UTILITIES ---
class ListUtils:
    @staticmethod
    def flatten_nested_list(nested):
        return [item for sublist in nested for item in sublist]

    @staticmethod
    def sort_tuples_by_multiple_indices(tuples, indices):
        return sorted(tuples, key=lambda x: tuple(x[i] for i in indices))

# --- PARAMETER UTILITIES ---
class ParameterUtils:
    @staticmethod
    def get_parameter_value_by_name(element, name):
        try:
            param = element.LookupParameter(name)
            if not param or not param.HasValue:
                return None
            if param.StorageType == StorageType.String:
                return param.AsString()
            elif param.StorageType == StorageType.Integer:
                return param.AsInteger()
            elif param.StorageType == StorageType.Double:
                return param.AsDouble()
            elif param.StorageType == StorageType.ElementId:
                return param.AsElementId()
        except:
            return None

    @staticmethod
    def set_parameter_value_by_name(element, name, value):
        param = element.LookupParameter(name)
        if param and not param.IsReadOnly:
            try:
                return param.Set(value)
            except:
                return False
        return False

# --- ABSTRACT ELEMENT WRAPPER ---
class RevitElement(ABC):
    def __init__(self, element):
        self.element = element

    def get_id(self):
        return self.element.Id.IntegerValue

    def get_param(self, name):
        return ParameterUtils.get_parameter_value_by_name(self.element, name)

    @abstractmethod
    def describe(self):
        pass

# --- DOOR ELEMENT WRAPPER ---
class Door(RevitElement):
    def __init__(self, element):
        super(Door, self).__init__(element)
        self.dimensions = DoorUtils.get_dimensions_cm(element)
        self.rough_width = self.dimensions.rough_width
        self.rough_height = self.dimensions.rough_height
        self.width = self.dimensions.width
        self.height = self.dimensions.height
        self.type_comments = FamilyUtils.get_type_comments(element)
        self.type_mark = FamilyUtils.get_type_mark(element)

    def describe(self):
        return f"Door: {self.type_mark}, {self.width}x{self.height} cm"


# --- WINDOW ELEMENT WRAPPER ---
class Window(RevitElement):
    def __init__(self, element):
        super(Window, self).__init__(element)
        self.dimensions = WindowUtils.get_dimensions_cm(element)
        self.rough_width = self.dimensions.rough_width
        self.rough_height = self.dimensions.rough_height
        self.width = self.dimensions.width
        self.height = self.dimensions.height
        self.type_comments = FamilyUtils.get_type_comments(element)
        self.type_mark = FamilyUtils.get_type_mark(element)

    def describe(self):
        return f"Window: {self.type_mark}, {self.rough_width}x{self.rough_height} cm"


# --- FAMILY UTILITIES ---
class FamilyUtils:
    @staticmethod
    def get_type_comments(element):
        param = element.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_COMMENTS)
        if param and param.HasValue:
            return param.AsString()
        return ""

    @staticmethod
    def get_family_type(instance):
        return doc.GetElement(instance.GetTypeId())

    @staticmethod
    def get_family_name(instance):
        return FamilyUtils.get_family_type(instance).Family.Name

    @staticmethod
    def get_length_cm(instance, param_name):
        val = FamilyUtils.get_family_type(instance).LookupParameter(param_name).AsDouble()
        return UnitUtils.convert_internal_to_cm(val)

    @staticmethod
    def get_text_param(instance, param_name):
        return FamilyUtils.get_family_type(instance).LookupParameter(param_name).AsString()

    @staticmethod
    def get_type_mark(element):
        return element.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_MARK).AsString()

# --- DOOR UTILITIES ---
class DoorUtils(FamilyUtils):
    @staticmethod
    def get_door_types():
        return FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsElementType().ToElements()

    @staticmethod
    def get_dimensions_cm(element):
        height = UnitUtils.convert_internal_to_cm(element.get_Parameter(BuiltInParameter.DOOR_HEIGHT).AsDouble())
        width = UnitUtils.convert_internal_to_cm(element.get_Parameter(BuiltInParameter.DOOR_WIDTH).AsDouble())
        rough_height = UnitUtils.convert_internal_to_cm(element.get_Parameter(BuiltInParameter.FAMILY_ROUGH_HEIGHT_PARAM).AsDouble())
        rough_width = UnitUtils.convert_internal_to_cm(element.get_Parameter(BuiltInParameter.FAMILY_ROUGH_WIDTH_PARAM).AsDouble())
        return FamilyDimensions(width=width, height=height, rough_width=rough_width, rough_height=rough_height)

    @staticmethod
    def get_tm_id_code(element):
        dims = DoorUtils.get_dimensions_cm(element)
        type_comment = element.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_COMMENTS).AsString()
        return f"{type_comment}-{int(dims.height)}X{int(dims.width)}"

# --- WINDOW UTILITIES ---
class WindowUtils(FamilyUtils):
    @staticmethod
    def get_window_types():
        return FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsElementType().ToElements()

    @staticmethod
    def get_dimensions_cm(element):
        rough_height = UnitUtils.convert_internal_to_cm(element.get_Parameter(BuiltInParameter.FAMILY_ROUGH_HEIGHT_PARAM).AsDouble())
        rough_width = UnitUtils.convert_internal_to_cm(element.get_Parameter(BuiltInParameter.FAMILY_ROUGH_WIDTH_PARAM).AsDouble())
        height = UnitUtils.convert_internal_to_cm(element.get_Parameter(BuiltInParameter.WINDOW_HEIGHT).AsDouble()) if element.LookupParameter("Height") else None
        width = UnitUtils.convert_internal_to_cm(element.get_Parameter(BuiltInParameter.WINDOW_WIDTH).AsDouble()) if element.LookupParameter("Width") else None
        return FamilyDimensions(width=width, height=height, rough_width=rough_width, rough_height=rough_height)

    @staticmethod
    def get_tm_id_code(element):
        dims = WindowUtils.get_dimensions_cm(element)
        type_comment = FamilyUtils.get_type_comments(element)
        return f"{type_comment}-{int(dims.rough_height)}X{int(dims.rough_width)}"

# --- ELEMENT FILTERING ---
class ElementFilterUtils:
    @staticmethod
    def get_elements_from_filter(element_filter):
        return element_filter.WhereElementIsNotElementType().ToElements()

    @staticmethod
    def filter_instances_by_family_name_contains(instances, substring):
        return [i for i in instances if substring in FamilyUtils.get_family_name(i)]