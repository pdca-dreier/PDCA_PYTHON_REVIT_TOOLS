
import clr
import sys
import math
from System.Collections.Generic import List
import Autodesk.Revit.DB as DB
import Autodesk.Revit.UI as UI
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from collections import defaultdict

clr.AddReference('ProtoGeometry')
clr.AddReference("RevitNodes")
clr.AddReference("RevitServices")
clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.DesignScript.Geometry import *

class BldgEnvelopesManager:
    def __init__(self, doc):
        self.doc = doc
        self.vertical_types = []
        self.horizontal_types = []
        self.collect_building_envelopes()

    def to_cm(self, value):
        return DB.UnitUtils.ConvertFromInternalUnits(value, DB.UnitTypeId.Centimeters)

    def collect_building_envelopes(self):
        self.vertical_types = self.vertical_building_envelopes_types()
        self.horizontal_types = self.horizontal_building_envelopes_types()

    def vertical_building_envelopes_types(self):
        return DB.FilteredElementCollector(self.doc).OfCategory(
            DB.BuiltInCategory.OST_Walls).WhereElementIsElementType().ToElements()

    def horizontal_building_envelopes_types(self):
        categories_ids = List[DB.BuiltInCategory]()
        categories_ids.Add(DB.BuiltInCategory.OST_Floors)
        categories_ids.Add(DB.BuiltInCategory.OST_Roofs)
        categories_ids.Add(DB.BuiltInCategory.OST_Ceilings)
        filter_horizontal_categories = DB.ElementMulticategoryFilter(categories_ids)
        return DB.FilteredElementCollector(self.doc).WherePasses(
            filter_horizontal_categories).WhereElementIsElementType().ToElements()

    def get_compound_structure_layers(self, item):
        layers = []
        layermat = []
        layerfunc = []
        layerwidth = []
        layercore = []
        layerwraps = []
        
        compound_structure = item.GetCompoundStructure()
        if compound_structure:
            for i in range(compound_structure.LayerCount):
                layer = compound_structure.GetLayer(i)
                layers.append(layer)
                layermat.append(self.doc.GetElement(layer.MaterialId).Name)
                layerfunc.append(layer.Function)
                layerwidth.append(self.to_cm(layer.Width))
                if layer.Function == DB.MaterialFunctionAssignment.Structure:
                    layercore.append(layer)
                if layer.Function in (DB.MaterialFunctionAssignment.Finish1, DB.MaterialFunctionAssignment.Finish2):
                    layerwraps.append(layer)
        return {
            'layers': layers,
            'materials': layermat,
            'functions': layerfunc,
            'widths': layerwidth,
            'core': layercore,
            'wraps': layerwraps
        }

    def analyze_envelopes(self):
        vertical_analysis = [self.get_compound_structure_layers(item) for item in self.vertical_types]
        horizontal_analysis = [self.get_compound_structure_layers(item) for item in self.horizontal_types]
        return {'vertical': vertical_analysis, 'horizontal': horizontal_analysis}

    def update_envelope_parameters(self, updates):
        TransactionManager.Instance.EnsureInTransaction(self.doc)
        for elem_id, params in updates.items():
            element = self.doc.GetElement(DB.ElementId(elem_id))
            if element:
                self.set_parameters(element, params)
        TransactionManager.Instance.TransactionTaskDone()

    def set_parameters(self, element, params):
        for param_name, value in params.items():
            param = element.LookupParameter(param_name)
            if param:
                if param.StorageType == DB.StorageType.Double:
                    param.Set(value)
                elif param.StorageType == DB.StorageType.Integer:
                    param.Set(int(value))
                elif param.StorageType == DB.StorageType.String:
                    param.Set(str(value))
                elif param.StorageType == DB.StorageType.ElementId:
                    param.Set(DB.ElementId(value))

# Entry point for running the script
def main():
    doc = DocumentManager.Instance.CurrentDBDocument
    manager = BldgEnvelopesManager(doc)

    # Perform analysis on building envelopes
    analysis_results = manager.analyze_envelopes()
    print("Analysis Results:", analysis_results)

    # Example of updating envelope parameters
    updates = {
        # Example envelope ID and parameter updates
        12345: {"ParameterName": 50.0},
        67890: {"ParameterName": 75.0}
    }
    manager.update_envelope_parameters(updates)

if __name__ == "__main__":
    main()
