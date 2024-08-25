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
excel_path_string = IN[0]  # Ensure you have an input system in place
output_excel_path_string = IN[1]  # Ensure you have an input system in place

write_to_txt = IN[2]
write_to_rvt = IN[3]
write_to_excel = IN[4]

family_paths = IN[5]

error_log = []
error_log_1 = []
temp = []
temp_report = []


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
                row_data.append(cell_value)
            worksheet_data.append(row_data)
        workbook.Close(True)
        excel.Quit()
        return worksheet_data


class WriteXLS(object):
    __instance = None

    def __new__(cls, file_path=None):
        if cls.__instance is None:
            cls.__instance = super(WriteXLS, cls).__new__(cls)
        return cls.__instance

    def __init__(self, file_path):
        self.file_path = file_path

    def write_data(self, worksheet_name, data, start_row=2, start_col=1):
        excel = Excel.ApplicationClass()
        workbook = excel.Workbooks.Open(self.file_path)
        worksheet = workbook.Worksheets[worksheet_name]

        for row_idx, row_data in enumerate(data, start=start_row):
            for col_idx, value in enumerate(row_data, start=start_col):
                worksheet.Cells[row_idx, col_idx].Value2 = value

        workbook.Save()
        workbook.Close()
        excel.Quit()


class Singleton(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Singleton, cls).__new__(cls, *args, **kwargs)
        return cls._instance


class ListUtils(Singleton):

    @classmethod
    def to_list(cls, input):
        result = input if isinstance(input, list) else [input]
        return result

    @classmethod
    def flatten_list(cls, lst):
        flattened = []
        for item in lst:
            if isinstance(item, (list, tuple)):
                flattened.extend(ListUtils.flatten_list(item))
            else:
                flattened.append(item)
        return flattened

    @classmethod
    def sort_list_by_pattern(cls, pattern, elements):
        sorted_list = sorted(elements, key=lambda x: (pattern.index(x[0]) if x[0] in pattern else len(pattern)))
        return sorted_list

    @classmethod
    def sort_sublist_by_pattern(cls, pattern, sublists, subindex_value=0):
        matching_sublists = [sublist for sublist in sublists if sublist[subindex_value] in pattern]
        remaining_sublists = [sublist for sublist in sublists if sublist[subindex_value] not in pattern]
        sorted_sublists = sorted(matching_sublists, key=lambda x: pattern.index(x[subindex_value]) if x[
                                                                                                          subindex_value] in pattern else len(
            pattern))
        return sorted_sublists + remaining_sublists


class PyRevit(Singleton):
    class CombinedDefinitionPy():
        instances = []

        class IntDefinition:
            def __init__(self, internal_definition=None, binding=None, external_definition=None, name=None, guid=None,
                         description=None,
                         discipline=None, unit_type=None, unit_label=None, group=None):
                if internal_definition is not None:
                    self.element = internal_definition
                    self.name = name
                    self.guid = guid  # external_definition.GUID
                    self.description = description  # external_definition.Description
                    self.discipline = discipline  # external_definition
                    self.unit_type = unit_type  # external_definition
                    self.unit_label = unit_label  # external_definition
                    self.group = group  # external_definition.OwnerGroup.Name
                    self.internal_group = internal_definition.ParameterGroup  # external_definition.OwnerGroup.Name
                    self.varies_across_groups = internal_definition.VariesAcrossGroups
                    self.binding_type = binding  # InstanceBinding or TypeBinding
                    self.binding_categories_set = binding.Categories
                    self.visible = internal_definition.Visible
                else:
                    self.element = None
                    self.name = None
                    self.guid = None
                    self.description = None
                    self.discipline = None
                    self.unit_type = None
                    self.unit_label = None
                    self.group = None
                    self.internal_group = None
                    self.varies_across_groups = None
                    self.binding_type = None
                    self.binding_categories_set = None
                    self.visible = None

        class ExtDefinition:
            def __init__(self, external_definition=None, name=None, guid=None, description=None,
                         discipline=None, unit_type=None, unit_label=None, group=None):
                if external_definition is not None:
                    self.element = external_definition
                    self.name = name  # external_definition.Name
                    self.guid = guid  # external_definition.GUID
                    self.description = description  # external_definition.Description
                    self.discipline = discipline  # external_definition
                    self.unit_type = unit_type  # external_definition
                    self.unit_label = unit_label  # external_definition
                    self.group = group  # external_definition.OwnerGroup.Name
                else:
                    self.element = None
                    self.name = None
                    self.guid = None
                    self.description = None
                    self.discipline = None
                    self.unit_type = None
                    self.unit_label = None
                    self.group = None

        class XlsImpDefinition:
            def __init__(self, no_id=None, name=None, discipline=None, unit_label=None, description=None, group=None,
                         guid=None, internal_group=None, binding_type=None, varies_across_groups=None,
                         binding_categories_set=None):
                if name is not None:
                    self.no_id = no_id  # NO. -> str
                    self.name = name  # PARAMETER NAME -> str
                    self.discipline = discipline  # PARAMETER DISCIPLINE -> str
                    self.unit_label = unit_label  # TYPE OF PARAMETER -> str
                    self.unit_type = unit_label  # external_definition
                    self.description = description  # TOOLTIP DESCRIPTION  -> str
                    self.group = group  # PARAMETER GROUP -> str
                    self.guid = guid  # PARAMETER GUID -> str
                    self.internal_group = internal_group  # GROUP PARAMETER UNDER -> str
                    self.binding_type = binding_type  # 0 - TYPE / 1 - INSTANCE -> str
                    self.varies_across_groups = varies_across_groups  # 0 - VALUES PER GROUP TYPE / 1 - BY GROUP INSTANCE -> str
                    self.binding_categories_set = binding_categories_set  # CATEGORIES LIST -> str
                else:
                    self.no_id = None
                    self.name = None
                    self.discipline = None
                    self.unit_label = None
                    self.unit_type = None
                    self.description = None
                    self.group = None
                    self.guid = None
                    self.internal_group = None
                    self.binding_type = None
                    self.varies_across_groups = None
                    self.binding_categories_set = None

        def __init__(self, name=None, internal_definition=None, binding=None, external_definition=None,
                     xls_imp_definition=None):
            self.name = name
            self.external_definition = self.ExtDefinition(external_definition)
            self.internal_definition = self.IntDefinition(internal_definition)
            self.xls_imp_definition = self.XlsImpDefinition(xls_imp_definition)
            self.external_definition_exist = False
            self.internal_definition_exist = False
            self.xls_imp_definition_exist = False
            self.instances.append(self)

        def set_internal_definition(self, internal_definition):
            self.internal_definition = self.IntDefinition(*internal_definition)

        def set_external_definition(self, external_definition):
            self.external_definition = self.ExtDefinition(*external_definition)

        def set_xls_definition_values_lst(self, xls_imp_definition):
            self.xls_imp_definition = self.XlsImpDefinition(*xls_imp_definition)

    class CombinedDefinitionUtils():

        spec_type_id_to_txt_dict = {
            SpecTypeId.Reference.Material: {"type": "Material", "discipline": "Common"},
            SpecTypeId.Boolean.YesNo: {"type": "Boolean", "discipline": "Common"},
            SpecTypeId.Int.Integer: {"type": "Integer", "discipline": "Common"},
            SpecTypeId.String.MultilineText: {"type": "String", "discipline": "Common"},
            SpecTypeId.String.Text: {"type": "String", "discipline": "Common"},
            SpecTypeId.String.Url: {"type": "String", "discipline": "Common"},
            SpecTypeId.Angle: {"type": "Angle", "discipline": "Common"},
            SpecTypeId.Area: {"type": "Area", "discipline": "Common"},
            SpecTypeId.Currency: {"type": "Currency", "discipline": "Common"},
            SpecTypeId.DecimalSheetLength: {"type": "Decimal Sheet Length", "discipline": "Common"},
            SpecTypeId.Length: {"type": "Length", "discipline": "Common"},
            SpecTypeId.Number: {"type": "Number", "discipline": "Common"},
            SpecTypeId.RotationAngle: {"type": "Rotation Angle", "discipline": "Common"},
            SpecTypeId.SiteAngle: {"type": "Site Angle", "discipline": "Common"},
            SpecTypeId.Slope: {"type": "Slope", "discipline": "Common"},
            SpecTypeId.Speed: {"type": "Speed", "discipline": "Common"},
            SpecTypeId.Time: {"type": "Time", "discipline": "Common"},
            SpecTypeId.Volume: {"type": "Volume", "discipline": "Common"},
            SpecTypeId.ColorTemperature: {"type": "Color Temperature", "discipline": "Electrical"},
            SpecTypeId.ConduitSize: {"type": "Conduit Size", "discipline": "Electrical"},
            SpecTypeId.CostRateEnergy: {"type": "Cost Rate Energy", "discipline": "Electrical"},
            SpecTypeId.CostRatePower: {"type": "Cost Rate Power", "discipline": "Electrical"},
            SpecTypeId.Current: {"type": "Current", "discipline": "Electrical"},
            SpecTypeId.ElectricalFrequency: {"type": "Frequency", "discipline": "Electrical"},
            SpecTypeId.ElectricalPotential: {"type": "Electrical Potential", "discipline": "Electrical"},
            SpecTypeId.ElectricalPower: {"type": "Power", "discipline": "Electrical"},
            SpecTypeId.ElectricalPowerDensity: {"type": "Power Density", "discipline": "Electrical"},
            SpecTypeId.ElectricalResistivity: {"type": "Electrical Resistivity", "discipline": "Electrical"},
            SpecTypeId.ElectricalTemperature: {"type": "Temperature", "discipline": "Electrical"},
            SpecTypeId.ElectricalTemperatureDifference: {"type": "Temperature Difference", "discipline": "Electrical"},
            SpecTypeId.Illuminance: {"type": "Illuminance", "discipline": "Electrical"},
            SpecTypeId.Luminance: {"type": "Luminance", "discipline": "Electrical"},
            SpecTypeId.LuminousFlux: {"type": "Luminous Flux", "discipline": "Electrical"},
            SpecTypeId.LuminousIntensity: {"type": "Luminous Intensity", "discipline": "Electrical"},
            SpecTypeId.Wattage: {"type": "Wattage", "discipline": "Electrical"},
            SpecTypeId.WireDiameter: {"type": "Wire Diameter", "discipline": "Electrical"},
            SpecTypeId.AirFlow: {"type": "Air Flow", "discipline": "HVAC"},
            SpecTypeId.AirFlowDensity: {"type": "Air Flow Density", "discipline": "HVAC"},
            SpecTypeId.AirFlowDividedByCoolingLoad: {"type": "Air Flow divided by Cooling Load", "discipline": "HVAC"},
            SpecTypeId.AirFlowDividedByVolume: {"type": "Air Flow divided by Volume", "discipline": "HVAC"},
            SpecTypeId.AngularSpeed: {"type": "Angular Speed", "discipline": "HVAC"},
            SpecTypeId.CoolingLoad: {"type": "Cooling Load", "discipline": "HVAC"},
            SpecTypeId.CoolingLoadDividedByArea: {"type": "Cooling Load divided by Area", "discipline": "HVAC"},
            SpecTypeId.CoolingLoadDividedByVolume: {"type": "Cooling Load divided by Volume", "discipline": "HVAC"},
            SpecTypeId.Efficacy: {"type": "Efficacy", "discipline": "HVAC"},
            SpecTypeId.Factor: {"type": "Factor", "discipline": "HVAC"},
            SpecTypeId.Flow: {"type": "Flow", "discipline": "Piping"},
            SpecTypeId.FlowPerPower: {"type": "Flow per Power", "discipline": "HVAC"},
            SpecTypeId.HvacDensity: {"type": "Density", "discipline": "HVAC"},
            SpecTypeId.HvacEnergy: {"type": "Energy", "discipline": "Energy"},
            SpecTypeId.HvacFriction: {"type": "Friction", "discipline": "HVAC"},
            SpecTypeId.HvacMassPerTime: {"type": "Mass per Time", "discipline": "HVAC"},
            SpecTypeId.HvacPower: {"type": "Power", "discipline": "HVAC"},
            SpecTypeId.HvacPowerDensity: {"type": "Power Density", "discipline": "HVAC"},
            SpecTypeId.HvacPressure: {"type": "Pressure", "discipline": "HVAC"},
            SpecTypeId.HvacRoughness: {"type": "Roughness", "discipline": "HVAC"},
            SpecTypeId.HvacSlope: {"type": "Slope", "discipline": "HVAC"},
            SpecTypeId.HvacTemperature: {"type": "Temperature", "discipline": "HVAC"},
            SpecTypeId.HvacTemperatureDifference: {"type": "Temperature Difference", "discipline": "HVAC"},
            SpecTypeId.HvacVelocity: {"type": "Velocity", "discipline": "HVAC"},
            SpecTypeId.HvacViscosity: {"type": "Dynamic Viscosity", "discipline": "HVAC"},
            SpecTypeId.PipeDimension: {"type": "Pipe Dimension", "discipline": "Piping"},
            SpecTypeId.PipeInsulationThickness: {"type": "Pipe Insulation Thickness", "discipline": "Piping"},
            SpecTypeId.PipeMassPerUnitLength: {"type": "Mass per Unit Length", "discipline": "Piping"},
            SpecTypeId.PipeSize: {"type": "Pipe Size", "discipline": "Piping"},
            SpecTypeId.PipingDensity: {"type": "Density", "discipline": "Piping"},
            SpecTypeId.PipingFriction: {"type": "Friction", "discipline": "Piping"},
            SpecTypeId.PipingMass: {"type": "Mass", "discipline": "Piping"},
            SpecTypeId.PipingMassPerTime: {"type": "Mass per Time", "discipline": "Piping"},
            SpecTypeId.PipingPressure: {"type": "Pressure", "discipline": "Piping"},
            SpecTypeId.PipingRoughness: {"type": "Roughness", "discipline": "Piping"},
            SpecTypeId.PipingSlope: {"type": "Slope", "discipline": "Piping"},
            SpecTypeId.PipingTemperature: {"type": "Temperature", "discipline": "Piping"},
            SpecTypeId.PipingTemperatureDifference: {"type": "Temperature Difference", "discipline": "Piping"},
            SpecTypeId.PipingVelocity: {"type": "Velocity", "discipline": "Piping"},
            SpecTypeId.PipingViscosity: {"type": "Dynamic Viscosity", "discipline": "Piping"},
            SpecTypeId.PipingVolume: {"type": "Volume", "discipline": "Piping"},
            SpecTypeId.Stationing: {"type": "Stationing", "discipline": "Infrastructure"},
            SpecTypeId.StationingInterval: {"type": "Stationing Interval", "discipline": "Infrastructure"},
            SpecTypeId.AreaForce: {"type": "Area Force", "discipline": "Structural"},
            SpecTypeId.AreaForceScale: {"type": "Area Force Scale", "discipline": "Structural"},
            SpecTypeId.AreaSpringCoefficient: {"type": "Area Spring Coefficient", "discipline": "Structural"},
            SpecTypeId.BarDiameter: {"type": "Bar Diameter", "discipline": "Structural"},
            SpecTypeId.CableTraySize: {"type": "Cable Tray Size", "discipline": "Electrical"},
            SpecTypeId.CrackWidth: {"type": "Crack Width", "discipline": "Structural"},
            SpecTypeId.CrossSection: {"type": "Cross Section", "discipline": "HVAC"},
            SpecTypeId.DuctInsulationThickness: {"type": "Duct Insulation Thickness", "discipline": "HVAC"},
            SpecTypeId.DuctLiningThickness: {"type": "Duct Lining Thickness", "discipline": "HVAC"},
            SpecTypeId.DuctSize: {"type": "Duct Size", "discipline": "HVAC"},
            SpecTypeId.Displacement: {"type": "Displacement/Deflection", "discipline": "Structural"},
            SpecTypeId.Diffusivity: {"type": "Diffusivity", "discipline": "HVAC"},
            SpecTypeId.Energy: {"type": "Energy", "discipline": "Energy"},
            SpecTypeId.HeatCapacityPerArea: {"type": "Heat Capacity per Area", "discipline": "Energy"},
            SpecTypeId.HeatGain: {"type": "Heat Gain", "discipline": "HVAC"},
            SpecTypeId.HeatingLoad: {"type": "Heating Load", "discipline": "HVAC"},
            SpecTypeId.HeatingLoadDividedByArea: {"type": "Heating Load divided by Area", "discipline": "HVAC"},
            SpecTypeId.HeatingLoadDividedByVolume: {"type": "Heating Load divided by Volume", "discipline": "HVAC"},
            SpecTypeId.HeatTransferCoefficient: {"type": "Coefficient of Heat Transfer", "discipline": "Energy"},
            SpecTypeId.HvacEnergy: {"type": "Energy", "discipline": "Energy"},
            SpecTypeId.IsothermalMoistureCapacity: {"type": "Isothermal Moisture Capacity", "discipline": "Energy"},
            SpecTypeId.LinearForce: {"type": "Linear Force", "discipline": "Structural"},
            SpecTypeId.LinearForceScale: {"type": "Linear Force Scale", "discipline": "Structural"},
            SpecTypeId.LinearMoment: {"type": "Linear Moment", "discipline": "Structural"},
            SpecTypeId.LinearMomentScale: {"type": "Linear Moment Scale", "discipline": "Structural"},
            SpecTypeId.LineSpringCoefficient: {"type": "Line Spring Coefficient", "discipline": "Structural"},
            SpecTypeId.Mass: {"type": "Mass", "discipline": "Structural"},
            SpecTypeId.MassDensity: {"type": "Mass Density", "discipline": "Common"},
            SpecTypeId.MassPerUnitArea: {"type": "Mass per Unit Area", "discipline": "Structural"},
            SpecTypeId.MassPerUnitLength: {"type": "Mass per Unit Length", "discipline": "Structural"},
            SpecTypeId.Moment: {"type": "Moment", "discipline": "Structural"},
            SpecTypeId.MomentOfInertia: {"type": "Moment of Inertia", "discipline": "Structural"},
            SpecTypeId.MomentScale: {"type": "Moment Scale", "discipline": "Structural"},
            SpecTypeId.Number: {"type": "Number", "discipline": "Common"},
            SpecTypeId.Period: {"type": "Period", "discipline": "Structural"},
            SpecTypeId.Permeability: {"type": "Permeability", "discipline": "Energy"},
            SpecTypeId.PipeDimension: {"type": "Pipe Dimension", "discipline": "Piping"},
            SpecTypeId.PipeInsulationThickness: {"type": "Pipe Insulation Thickness", "discipline": "Piping"},
            SpecTypeId.PipeMassPerUnitLength: {"type": "Mass per Unit Length", "discipline": "Piping"},
            SpecTypeId.PipeSize: {"type": "Pipe Size", "discipline": "Piping"},
            SpecTypeId.PipingDensity: {"type": "Density", "discipline": "Piping"},
            SpecTypeId.PipingFriction: {"type": "Friction", "discipline": "Piping"},
            SpecTypeId.PipingMass: {"type": "Mass", "discipline": "Piping"},
            SpecTypeId.PipingMassPerTime: {"type": "Mass per Time", "discipline": "Piping"},
            SpecTypeId.PipingPressure: {"type": "Pressure", "discipline": "Piping"},
            SpecTypeId.PipingRoughness: {"type": "Roughness", "discipline": "Piping"},
            SpecTypeId.PipingSlope: {"type": "Slope", "discipline": "Piping"},
            SpecTypeId.PipingTemperature: {"type": "Temperature", "discipline": "Piping"},
            SpecTypeId.PipingTemperatureDifference: {"type": "Temperature Difference", "discipline": "Piping"},
            SpecTypeId.PipingVelocity: {"type": "Velocity", "discipline": "Piping"},
            SpecTypeId.PipingViscosity: {"type": "Dynamic Viscosity", "discipline": "Piping"},
            SpecTypeId.PipingVolume: {"type": "Volume", "discipline": "Piping"},
            SpecTypeId.PointSpringCoefficient: {"type": "Point Spring Coefficient", "discipline": "Structural"},
            SpecTypeId.PowerPerFlow: {"type": "Power per Flow", "discipline": "HVAC"},
            SpecTypeId.PowerPerLength: {"type": "Power per Length", "discipline": "Electrical"},
            SpecTypeId.Pulsation: {"type": "Pulsation", "discipline": "Structural"},
            SpecTypeId.ReinforcementArea: {"type": "Reinforcement Area", "discipline": "Structural"},
            SpecTypeId.ReinforcementAreaPerUnitLength: {"type": "Reinforcement Area per Unit Length",
                                                        "discipline": "Structural"},
            SpecTypeId.ReinforcementCover: {"type": "Reinforcement Cover", "discipline": "Structural"},
            SpecTypeId.ReinforcementLength: {"type": "Reinforcement Length", "discipline": "Structural"},
            SpecTypeId.ReinforcementSpacing: {"type": "Reinforcement Spacing", "discipline": "Structural"},
            SpecTypeId.ReinforcementVolume: {"type": "Reinforcement Volume", "discipline": "Structural"},
            SpecTypeId.Rotation: {"type": "Rotation", "discipline": "Structural"},
            SpecTypeId.RotationalLineSpringCoefficient: {"type": "Rotational Line Spring Coefficient",
                                                         "discipline": "Structural"},
            SpecTypeId.RotationalPointSpringCoefficient: {"type": "Rotational Point Spring Coefficient",
                                                          "discipline": "Structural"},
            SpecTypeId.SectionArea: {"type": "Section Area", "discipline": "Structural"},
            SpecTypeId.SectionDimension: {"type": "Section Dimension", "discipline": "Structural"},
            SpecTypeId.SectionModulus: {"type": "Section Modulus", "discipline": "Structural"},
            SpecTypeId.SectionProperty: {"type": "Section Property", "discipline": "Structural"},
            SpecTypeId.SpecificHeat: {"type": "Specific Heat", "discipline": "Energy"},
            SpecTypeId.SpecificHeatOfVaporization: {"type": "Specific Heat of Vaporization", "discipline": "Energy"},
            SpecTypeId.Stress: {"type": "Stress", "discipline": "Structural"},
            SpecTypeId.StructuralFrequency: {"type": "Frequency", "discipline": "Structural"},
            SpecTypeId.StructuralVelocity: {"type": "Velocity", "discipline": "Structural"},
            SpecTypeId.SurfaceAreaPerUnitLength: {"type": "Surface Area per Unit Length", "discipline": "Structural"},
            SpecTypeId.ThermalConductivity: {"type": "Thermal Conductivity", "discipline": "Energy"},
            SpecTypeId.ThermalExpansionCoefficient: {"type": "Thermal Expansion Coefficient",
                                                     "discipline": "Structural"},
            SpecTypeId.ThermalGradientCoefficientForMoistureCapacity: {
                "type": "Thermal Gradient Coefficient for Moisture Capacity", "discipline": "Energy"},
            SpecTypeId.ThermalMass: {"type": "Thermal Mass", "discipline": "Energy"},
            SpecTypeId.ThermalResistance: {"type": "Thermal Resistance", "discipline": "Energy"},
            SpecTypeId.UnitWeight: {"type": "Unit Weight", "discipline": "Structural"},
            SpecTypeId.WarpingConstant: {"type": "Warping Constant", "discipline": "Structural"}
        }

        revit_categories_names_to_rvt_cat_dict = {
            # "All": all_type_categories,
            "Air Terminals": BuiltInCategory.OST_DuctTerminal,
            "Analytical Beams": BuiltInCategory.OST_BeamAnalytical,
            "Analytical Braces": BuiltInCategory.OST_BraceAnalytical,
            "Analytical Columns": BuiltInCategory.OST_ColumnAnalytical,
            "Analytical Floors": BuiltInCategory.OST_FloorAnalytical,
            "Analytical Foundation Slabs": BuiltInCategory.OST_FoundationSlabAnalytical,
            "Analytical Isolated Foundations": BuiltInCategory.OST_IsolatedFoundationAnalytical,
            "Analytical Links": BuiltInCategory.OST_LinksAnalytical,
            "Analytical Nodes": BuiltInCategory.OST_AnalyticalNodes,
            "Analytical Pipe Connections": BuiltInCategory.OST_AnalyticalPipeConnections,
            "Analytical Spaces": BuiltInCategory.OST_AnalyticSpaces,
            "Analytical Surfaces": BuiltInCategory.OST_GbXMLFaces,
            "Analytical Wall Foundations": BuiltInCategory.OST_WallFoundationAnalytical,
            "Analytical Walls": BuiltInCategory.OST_WallAnalytical,
            "Areas": BuiltInCategory.OST_Areas,
            "Assemblies": BuiltInCategory.OST_Assemblies,
            "Cable Tray Fittings": BuiltInCategory.OST_CableTrayFitting,
            "Cable Tray Runs": BuiltInCategory.OST_CableTrayRun,
            "Cable Trays": BuiltInCategory.OST_CableTray,
            "Casework": BuiltInCategory.OST_Casework,
            "Ceilings": BuiltInCategory.OST_Ceilings,
            "Columns": BuiltInCategory.OST_Columns,
            "Communication Devices": BuiltInCategory.OST_CommunicationDevices,
            "Conduit Fittings": BuiltInCategory.OST_ConduitFitting,
            "Conduit Runs": BuiltInCategory.OST_ConduitRun,
            "Conduits": BuiltInCategory.OST_Conduit,
            "Curtain Panels": BuiltInCategory.OST_CurtainWallPanels,
            "Curtain Systems": BuiltInCategory.OST_CurtaSystem,
            "Curtain Wall Mullions": BuiltInCategory.OST_CurtainWallMullions,
            "Data Devices": BuiltInCategory.OST_DataDevices,
            "Detail Items": BuiltInCategory.OST_DetailComponents,
            "Doors": BuiltInCategory.OST_Doors,
            "Duct Accessories": BuiltInCategory.OST_DuctAccessory,
            "Duct Fittings": BuiltInCategory.OST_DuctFitting,
            "Duct Insulations": BuiltInCategory.OST_DuctInsulations,
            "Duct Linings": BuiltInCategory.OST_DuctLinings,
            "Duct Placeholders": BuiltInCategory.OST_PlaceHolderDucts,
            "Duct Systems": BuiltInCategory.OST_DuctSystem,
            "Ducts": BuiltInCategory.OST_DuctCurves,
            "Electrical Circuits": BuiltInCategory.OST_ElectricalCircuit,
            "Electrical Equipment": BuiltInCategory.OST_ElectricalEquipment,
            "Electrical Fixtures": BuiltInCategory.OST_ElectricalFixtures,
            "Entourage": BuiltInCategory.OST_Entourage,
            "Fire Alarm Devices": BuiltInCategory.OST_FireAlarmDevices,
            "Flex Ducts": BuiltInCategory.OST_FlexDuctCurves,
            "Flex Pipes": BuiltInCategory.OST_FlexPipeCurves,
            "Floors": BuiltInCategory.OST_Floors,
            "Furniture Systems": BuiltInCategory.OST_FurnitureSystems,
            "Furniture": BuiltInCategory.OST_Furniture,
            "Generic Models": BuiltInCategory.OST_GenericModel,
            "Grids": BuiltInCategory.OST_Grids,
            "HVAC Zones": BuiltInCategory.OST_HVAC_Zones,
            "Levels": BuiltInCategory.OST_Levels,
            "Lighting Devices": BuiltInCategory.OST_LightingDevices,
            "Lighting Fixtures": BuiltInCategory.OST_LightingFixtures,
            "Mass": BuiltInCategory.OST_Mass,
            "Materials": BuiltInCategory.OST_Materials,
            "Mechanical Equipment Sets": BuiltInCategory.OST_MechanicalEquipmentSet,
            "Mechanical Equipment": BuiltInCategory.OST_MechanicalEquipment,
            "MEP Fabrication Containment": BuiltInCategory.OST_FabricationContainment,
            "MEP Fabrication Ductwork": BuiltInCategory.OST_FabricationDuctwork,
            "MEP Fabrication Hangers": BuiltInCategory.OST_FabricationHangers,
            "MEP Fabrication Pipework": BuiltInCategory.OST_FabricationPipework,
            "Model Groups": BuiltInCategory.OST_IOSModelGroups,
            "Nurse Call Devices": BuiltInCategory.OST_NurseCallDevices,
            "Parking": BuiltInCategory.OST_Parking,
            "Parts": BuiltInCategory.OST_Parts,
            "Pipe Accessories": BuiltInCategory.OST_PipeAccessory,
            "Pipe Fittings": BuiltInCategory.OST_PipeFitting,
            "Pipe Insulations": BuiltInCategory.OST_PipeInsulations,
            "Pipe Placeholders": BuiltInCategory.OST_PlaceHolderPipes,
            "Pipes": BuiltInCategory.OST_PipeCurves,
            "Piping Systems": BuiltInCategory.OST_PipingSystem,
            "Planting": BuiltInCategory.OST_Planting,
            "Plumbing Fixtures": BuiltInCategory.OST_PlumbingFixtures,
            "Project Information": BuiltInCategory.OST_ProjectInformation,
            "Railings": BuiltInCategory.OST_StairsRailing,
            "Ramps": BuiltInCategory.OST_Ramps,
            "Rebar Shape": BuiltInCategory.OST_RebarShape,
            "Roads": BuiltInCategory.OST_Roads,
            "Roofs": BuiltInCategory.OST_Roofs,
            "Rooms": BuiltInCategory.OST_Rooms,
            "RVT Links": BuiltInCategory.OST_RvtLinks,
            "Schedules": BuiltInCategory.OST_Schedules,
            "Security Devices": BuiltInCategory.OST_SecurityDevices,
            "Shaft Openings": BuiltInCategory.OST_ShaftOpening,
            "Sheets": BuiltInCategory.OST_Sheets,
            "Site": BuiltInCategory.OST_Site,
            "Spaces": BuiltInCategory.OST_MEPSpaces,
            "Specialty Equipment": BuiltInCategory.OST_SpecialityEquipment,
            "Sprinklers": BuiltInCategory.OST_Sprinklers,
            "Stairs": BuiltInCategory.OST_Stairs,
            "Structural Area Reinforcement": BuiltInCategory.OST_AreaRein,
            "Structural Beam Systems": BuiltInCategory.OST_StructuralFramingSystem,
            "Structural Columns": BuiltInCategory.OST_StructuralColumns,
            "Structural Connections": BuiltInCategory.OST_StructConnections,
            "Structural Fabric Areas": BuiltInCategory.OST_FabricAreas,
            "Structural Fabric Reinforcement": BuiltInCategory.OST_FabricReinforcement,
            "Structural Foundations": BuiltInCategory.OST_StructuralFoundation,
            "Structural Framing": BuiltInCategory.OST_StructuralFraming,
            "Structural Path Reinforcement": BuiltInCategory.OST_PathRein,
            "Structural Rebar Couplers": BuiltInCategory.OST_Coupler,
            "Structural Rebar": BuiltInCategory.OST_Rebar,
            "Structural Stiffeners": BuiltInCategory.OST_StructuralStiffener,
            "Structural Trusses": BuiltInCategory.OST_StructuralTruss,
            "Switch System": BuiltInCategory.OST_SwitchSystem,
            "Telephone Devices": BuiltInCategory.OST_TelephoneDevices,
            "Topography": BuiltInCategory.OST_Topography,
            "Views": BuiltInCategory.OST_Views,
            "Walls": BuiltInCategory.OST_Walls,
            "Windows": BuiltInCategory.OST_Windows,
            "Wires": BuiltInCategory.OST_Wire
        }

        # BuiltInParameterGroup Enumeration
        revit_pg_names_to_rvt_pg_dict = {
            "Adaptive Component": BuiltInParameterGroup.PG_FLEXIBLE,
            "Advanced": BuiltInParameterGroup.PG_ENERGY_ANALYSIS_ADVANCED,
            # "Alternate Units": BuiltInParameterGroup.PG_ALTERNATE_UNITS,
            "Analysis Results": BuiltInParameterGroup.PG_ANALYSIS_RESULTS,
            "Analytical Alignment": BuiltInParameterGroup.PG_ANALYTICAL_ALIGNMENT,
            "Analytical Model": BuiltInParameterGroup.PG_ANALYTICAL_MODEL,
            "Analytical Properties": BuiltInParameterGroup.PG_ANALYTICAL_PROPERTIES,
            "Area": BuiltInParameterGroup.PG_AREA,
            "Bottom Chords": BuiltInParameterGroup.PG_TRUSS_FAMILY_BOTTOM_CHORD,
            "Building Data": BuiltInParameterGroup.PG_ENERGY_ANALYSIS_BUILDING_DATA,
            "Calculation Rules": BuiltInParameterGroup.PG_STAIRS_CALCULATOR_RULES,
            "Camera": BuiltInParameterGroup.PG_VIEW_CAMERA,
            "Conceptual Energy Data": BuiltInParameterGroup.PG_CONCEPTUAL_ENERGY_DATA,
            "Constraints": BuiltInParameterGroup.PG_CONSTRAINTS,
            "Construction": BuiltInParameterGroup.PG_CONSTRUCTION,
            # "Cross-Section Definition": BuiltInParameterGroup.PG_WALL_CROSS_SECTION_DEFINITION,
            "Data": BuiltInParameterGroup.PG_DATA,
            "Detailed Model": BuiltInParameterGroup.PG_ENERGY_ANALYSIS_DETAILED_MODEL,
            "Diagonal Webs": BuiltInParameterGroup.PG_TRUSS_FAMILY_DIAG_WEB,
            "Dimensions (linear units or % of thickness)": BuiltInParameterGroup.PG_SPLIT_PROFILE_DIMENSIONS,
            "Dimensions": BuiltInParameterGroup.PG_GEOMETRY,
            "Display": BuiltInParameterGroup.PG_DISPLAY,
            "Division Geometry": BuiltInParameterGroup.PG_DIVISION_GEOMETRY,
            "Electrical - Circuiting": BuiltInParameterGroup.PG_ELECTRICAL_CIRCUITING,
            "Electrical - Lighting": BuiltInParameterGroup.PG_ELECTRICAL_LIGHTING,
            "Electrical - Loads": BuiltInParameterGroup.PG_ELECTRICAL_LOADS,
            # "Electrical Analysis": BuiltInParameterGroup.PG_ELECTRICAL_ANALYSIS,
            # "Electrical Engineering": BuiltInParameterGroup.PG_ELECTRICAL_ENGINEERING,
            "Electrical": BuiltInParameterGroup.PG_ELECTRICAL,
            "End Connection": BuiltInParameterGroup.PG_STAIRS_OPEN_END_CONNECTION,
            "Energy Analysis": BuiltInParameterGroup.PG_ENERGY_ANALYSIS,
            "Energy Analytical Model": BuiltInParameterGroup.PG_ENERGY_ANALYSIS_CONCEPTUAL_MODEL,
            "Energy Model - Building Services": BuiltInParameterGroup.PG_CONCEPTUAL_ENERGY_DATA_BUILDING_SERVICES,
            "Essential": BuiltInParameterGroup.PG_ENERGY_ANALYSIS_DETAILED_AND_CONCEPTUAL_MODELS,
            "Extension (Beginning/Bottom)": BuiltInParameterGroup.PG_CONTINUOUSRAIL_BEGIN_BOTTOM_EXTENSION,
            "Extension (End/Top)": BuiltInParameterGroup.PG_CONTINUOUSRAIL_END_TOP_EXTENSION,
            "Extents": BuiltInParameterGroup.PG_VIEW_EXTENTS,
            "Fabrication Product Data": BuiltInParameterGroup.PG_FABRICATION_PRODUCT_DATA,
            "Fire Protection": BuiltInParameterGroup.PG_FIRE_PROTECTION,
            "Fittings": BuiltInParameterGroup.PG_FITTING,
            "Forces": BuiltInParameterGroup.PG_FORCES,
            "General": BuiltInParameterGroup.PG_GENERAL,
            "Geolocation": BuiltInParameterGroup.PG_GEO_LOCATION,
            "Geometric Position": BuiltInParameterGroup.PG_GEOMETRY_POSITIONING,
            "Graphics": BuiltInParameterGroup.PG_GRAPHICS,
            "Green Building Properties": BuiltInParameterGroup.PG_GREEN_BUILDING,
            "Grid 1 Mullions": BuiltInParameterGroup.PG_CURTAIN_MULLION_1,
            "Grid 1": BuiltInParameterGroup.PG_CURTAIN_GRID_1,
            "Grid 2 Mullions": BuiltInParameterGroup.PG_CURTAIN_MULLION_2,
            "Grid 2": BuiltInParameterGroup.PG_CURTAIN_GRID_2,
            "Grid": BuiltInParameterGroup.PG_CURTAIN_GRID,
            "Handrail 1": BuiltInParameterGroup.PG_RAILING_SYSTEM_FAMILY_HANDRAILS,
            "Handrail 2": BuiltInParameterGroup.PG_RAILING_SYSTEM_SECONDARY_FAMILY_HANDRAILS,
            "Horizontal Grid": BuiltInParameterGroup.PG_CURTAIN_GRID_HORIZ,
            "Horizontal Mullions": BuiltInParameterGroup.PG_CURTAIN_MULLION_HORIZ,
            "Identity Data": BuiltInParameterGroup.PG_IDENTITY_DATA,
            "IFC Parameters": BuiltInParameterGroup.PG_IFC,
            "Insulation": BuiltInParameterGroup.PG_INSULATION,
            "Layers": BuiltInParameterGroup.PG_REBAR_SYSTEM_LAYERS,
            "Length": BuiltInParameterGroup.PG_LENGTH,
            # "Life Safety": BuiltInParameterGroup.PG_LIFE_SAFETY,
            "Lining": BuiltInParameterGroup.PG_LINING,
            "Material Thermal Properties": BuiltInParameterGroup.PG_ENERGY_ANALYSIS_BLDG_CONS_MTL_THERMAL_PROPS,
            "Materials and Finishes": BuiltInParameterGroup.PG_MATERIALS,
            "Mechanical - Flow": BuiltInParameterGroup.PG_MECHANICAL_AIRFLOW,
            "Mechanical - Loads": BuiltInParameterGroup.PG_MECHANICAL_LOADS,
            "Mechanical": BuiltInParameterGroup.PG_MECHANICAL,
            "Model Properties": BuiltInParameterGroup.PG_ADSK_MODEL_PROPERTIES,
            "Moments": BuiltInParameterGroup.PG_MOMENTS,
            "Nodes": BuiltInParameterGroup.PG_NODES,
            "Overall Legend": BuiltInParameterGroup.PG_OVERALL_LEGEND,
            "Pattern Application": BuiltInParameterGroup.PG_PATTERN_APPLICATION,
            "Pattern Remainder": BuiltInParameterGroup.PG_RAILING_SYSTEM_SEGMENT_PATTERN_REMAINDER,
            "Pattern Repeat": BuiltInParameterGroup.PG_RAILING_SYSTEM_SEGMENT_PATTERN_REPEAT,
            "Pattern": BuiltInParameterGroup.PG_PATTERN,
            "Phasing": BuiltInParameterGroup.PG_PHASING,
            "Photometrics": BuiltInParameterGroup.PG_LIGHT_PHOTOMETRICS,
            "Plumbing": BuiltInParameterGroup.PG_PLUMBING,
            "Posts": BuiltInParameterGroup.PG_RAILING_SYSTEM_SEGMENT_POSTS,
            "Primary End": BuiltInParameterGroup.PG_PRIMARY_END,
            # "Primary Units": BuiltInParameterGroup.PG_PRIMARY_UNITS,
            "Profile 1": BuiltInParameterGroup.PG_PROFILE_1,
            "Profile 2": BuiltInParameterGroup.PG_PROFILE_2,
            "Profile": BuiltInParameterGroup.PG_PROFILE,
            "Rebar Set": BuiltInParameterGroup.PG_REBAR_ARRAY,
            "Reference": BuiltInParameterGroup.PG_REFERENCE,
            "Releases / Member Forces": BuiltInParameterGroup.PG_RELEASES_MEMBER_FORCES,
            "Rise / Drop": BuiltInParameterGroup.PG_SYSTEMTYPE_RISEDROP,
            "Risers": BuiltInParameterGroup.PG_STAIR_RISERS,
            "Room/Space Data": BuiltInParameterGroup.PG_ENERGY_ANALYSIS_ROOM_SPACE_DATA,
            "Rotation about": BuiltInParameterGroup.PG_ROTATION_ABOUT,
            # "Route Analysis": BuiltInParameterGroup.PG_ROUTE_ANALYSIS,
            "Secondary End": BuiltInParameterGroup.PG_SECONDARY_END,
            "Segment Pattern (default)": BuiltInParameterGroup.PG_RAILING_SYSTEM_FAMILY_SEGMENT_PATTERN,
            "Segments and Fittings": BuiltInParameterGroup.PG_SEGMENTS_FITTINGS,
            "Set": BuiltInParameterGroup.PG_COUPLER_ARRAY,
            "Slab Shape Edit": BuiltInParameterGroup.PG_SLAB_SHAPE_EDIT,
            "Stringers": BuiltInParameterGroup.PG_STAIR_STRINGERS,
            "Structural Analysis": BuiltInParameterGroup.PG_STRUCTURAL_ANALYSIS,
            "Structural Section Geometry": BuiltInParameterGroup.PG_STRUCTURAL_SECTION_GEOMETRY,
            "Structural": BuiltInParameterGroup.PG_STRUCTURAL,
            # "Terminations": BuiltInParameterGroup.PG_TERMINATION,
            "Text": BuiltInParameterGroup.PG_TEXT,
            "Threads/Risers": BuiltInParameterGroup.PG_STAIRS_TREADS_RISERS,
            "Title Text": BuiltInParameterGroup.PG_TITLE,
            "Top Chords": BuiltInParameterGroup.PG_TRUSS_FAMILY_TOP_CHORD,
            "Top Rail": BuiltInParameterGroup.PG_RAILING_SYSTEM_FAMILY_TOP_RAIL,
            "Translation in": BuiltInParameterGroup.PG_TRANSLATION_IN,
            "Treads": BuiltInParameterGroup.PG_STAIR_TREADS,
            "Underlay": BuiltInParameterGroup.PG_UNDERLAY,
            "Vertical Grid": BuiltInParameterGroup.PG_CURTAIN_GRID_VERT,
            "Vertical Mullions": BuiltInParameterGroup.PG_CURTAIN_MULLION_VERT,
            "Vertical Webs": BuiltInParameterGroup.PG_TRUSS_FAMILY_VERT_WEB,
            "Visibility": BuiltInParameterGroup.PG_VISIBILITY,
            "Other": BuiltInParameterGroup.PG_VISIBILITY,
            "Winders": BuiltInParameterGroup.PG_STAIRS_WINDERS
        }

        revit_pg_names_to_string_dict = {
            "PG_FLEXIBLE": "Adaptive Component",
            "PG_ENERGY_ANALYSIS_ADVANCED": "Advanced",
            "PG_ANALYSIS_RESULTS": "Analysis Results",
            "PG_ANALYTICAL_ALIGNMENT": "Analytical Alignment",
            "PG_ANALYTICAL_MODEL": "Analytical Model",
            "PG_ANALYTICAL_PROPERTIES": "Analytical Properties",
            "PG_AREA": "Area",
            "PG_TRUSS_FAMILY_BOTTOM_CHORD": "Bottom Chords",
            "PG_ENERGY_ANALYSIS_BUILDING_DATA": "Building Data",
            "PG_STAIRS_CALCULATOR_RULES": "Calculation Rules",
            "PG_VIEW_CAMERA": "Camera",
            "PG_CONCEPTUAL_ENERGY_DATA": "Conceptual Energy Data",
            "PG_CONSTRAINTS": "Constraints",
            "PG_CONSTRUCTION": "Construction",
            "PG_DATA": "Data",
            "PG_ENERGY_ANALYSIS_DETAILED_MODEL": "Detailed Model",
            "PG_TRUSS_FAMILY_DIAG_WEB": "Diagonal Webs",
            "PG_SPLIT_PROFILE_DIMENSIONS": "Dimensions (linear units or % of thickness)",
            "PG_GEOMETRY": "Dimensions",
            "PG_DISPLAY": "Display",
            "PG_DIVISION_GEOMETRY": "Division Geometry",
            "PG_ELECTRICAL_CIRCUITING": "Electrical - Circuiting",
            "PG_ELECTRICAL_LIGHTING": "Electrical - Lighting",
            "PG_ELECTRICAL_LOADS": "Electrical - Loads",
            "PG_ELECTRICAL": "Electrical",
            "PG_STAIRS_OPEN_END_CONNECTION": "End Connection",
            "PG_ENERGY_ANALYSIS": "Energy Analysis",
            "PG_ENERGY_ANALYSIS_CONCEPTUAL_MODEL": "Energy Analytical Model",
            "PG_CONCEPTUAL_ENERGY_DATA_BUILDING_SERVICES": "Energy Model - Building Services",
            "PG_ENERGY_ANALYSIS_DETAILED_AND_CONCEPTUAL_MODELS": "Essential",
            "PG_CONTINUOUSRAIL_BEGIN_BOTTOM_EXTENSION": "Extension (Beginning/Bottom)",
            "PG_CONTINUOUSRAIL_END_TOP_EXTENSION": "Extension (End/Top)",
            "PG_VIEW_EXTENTS": "Extents",
            "PG_FABRICATION_PRODUCT_DATA": "Fabrication Product Data",
            "PG_FIRE_PROTECTION": "Fire Protection",
            "PG_FITTING": "Fittings",
            "PG_FORCES": "Forces",
            "PG_GENERAL": "General",
            "PG_GEO_LOCATION": "Geolocation",
            "PG_GEOMETRY_POSITIONING": "Geometric Position",
            "PG_GRAPHICS": "Graphics",
            "PG_GREEN_BUILDING": "Green Building Properties",
            "PG_CURTAIN_MULLION_1": "Grid 1 Mullions",
            "PG_CURTAIN_GRID_1": "Grid 1",
            "PG_CURTAIN_MULLION_2": "Grid 2 Mullions",
            "PG_CURTAIN_GRID_2": "Grid 2",
            "PG_CURTAIN_GRID": "Grid",
            "PG_RAILING_SYSTEM_FAMILY_HANDRAILS": "Handrail 1",
            "PG_RAILING_SYSTEM_SECONDARY_FAMILY_HANDRAILS": "Handrail 2",
            "PG_CURTAIN_GRID_HORIZ": "Horizontal Grid",
            "PG_CURTAIN_MULLION_HORIZ": "Horizontal Mullions",
            "PG_IDENTITY_DATA": "Identity Data",
            "PG_IFC": "IFC Parameters",
            "PG_INSULATION": "Insulation",
            "PG_REBAR_SYSTEM_LAYERS": "Layers",
            "PG_LENGTH": "Length",
            "PG_LINING": "Lining",
            "PG_ENERGY_ANALYSIS_BLDG_CONS_MTL_THERMAL_PROPS": "Material Thermal Properties",
            "PG_MATERIALS": "Materials and Finishes",
            "PG_MECHANICAL_AIRFLOW": "Mechanical - Flow",
            "PG_MECHANICAL_LOADS": "Mechanical - Loads",
            "PG_MECHANICAL": "Mechanical",
            "PG_ADSK_MODEL_PROPERTIES": "Model Properties",
            "PG_MOMENTS": "Moments",
            "PG_NODES": "Nodes",
            "PG_OVERALL_LEGEND": "Overall Legend",
            "PG_PATTERN_APPLICATION": "Pattern Application",
            "PG_RAILING_SYSTEM_SEGMENT_PATTERN_REMAINDER": "Pattern Remainder",
            "PG_RAILING_SYSTEM_SEGMENT_PATTERN_REPEAT": "Pattern Repeat",
            "PG_PATTERN": "Pattern",
            "PG_PHASING": "Phasing",
            "PG_LIGHT_PHOTOMETRICS": "Photometrics",
            "PG_PLUMBING": "Plumbing",
            "PG_RAILING_SYSTEM_SEGMENT_POSTS": "Posts",
            "PG_PRIMARY_END": "Primary End",
            "PG_PROFILE_1": "Profile 1",
            "PG_PROFILE_2": "Profile 2",
            "PG_PROFILE": "Profile",
            "PG_REBAR_ARRAY": "Rebar Set",
            "PG_REFERENCE": "Reference",
            "PG_RELEASES_MEMBER_FORCES": "Releases / Member Forces",
            "PG_SYSTEMTYPE_RISEDROP": "Rise / Drop",
            "PG_STAIR_RISERS": "Risers",
            "PG_ENERGY_ANALYSIS_ROOM_SPACE_DATA": "Room/Space Data",
            "PG_ROTATION_ABOUT": "Rotation about",
            "PG_SECONDARY_END": "Secondary End",
            "PG_RAILING_SYSTEM_FAMILY_SEGMENT_PATTERN": "Segment Pattern (default)",
            "PG_SEGMENTS_FITTINGS": "Segments and Fittings",
            "PG_COUPLER_ARRAY": "Set",
            "PG_SLAB_SHAPE_EDIT": "Slab Shape Edit",
            "PG_STAIR_STRINGERS": "Stringers",
            "PG_STRUCTURAL_ANALYSIS": "Structural Analysis",
            "PG_STRUCTURAL_SECTION_GEOMETRY": "Structural Section Geometry",
            "PG_STRUCTURAL": "Structural",
            "PG_TEXT": "Text",
            "PG_STAIRS_TREADS_RISERS": "Threads/Risers",
            "PG_TITLE": "Title Text",
            "PG_TRUSS_FAMILY_TOP_CHORD": "Top Chords",
            "PG_RAILING_SYSTEM_FAMILY_TOP_RAIL": "Top Rail",
            "PG_TRANSLATION_IN": "Translation in",
            "PG_STAIR_TREADS": "Treads",
            "PG_UNDERLAY": "Underlay",
            "PG_CURTAIN_GRID_VERT": "Vertical Grid",
            "PG_CURTAIN_MULLION_VERT": "Vertical Mullions",
            "PG_TRUSS_FAMILY_VERT_WEB": "Vertical Webs",
            "PG_VISIBILITY": "Visibility",
            "PG_STAIRS_WINDERS": "Winders"
        }

        @staticmethod
        def invert_dict(input_dict):
            inverted_dict = {}
            for key, value in input_dict.items():
                inverted_dict[value] = key
            return inverted_dict

        @staticmethod
        def combined_definition_exist(new_name):
            test = False
            selected_instance = None
            for instance in PyRevit.CombinedDefinitionPy.instances:
                test = instance.name == new_name
                if test:
                    selected_instance = instance
                    break
            return test, selected_instance

        @classmethod
        def get_parameter_discipline_and_type_and_label(cls, parameter):
            parameter_discipline, parameter_unit_type, parameter_unit_label = None, None, None
            parameter_data_type = parameter.GetDataType()
            parameter_dict = cls.spec_type_id_to_txt_dict.get(parameter.GetDataType(), None)

            if parameter_dict is not None:
                parameter_discipline = parameter_dict.get("discipline", None)
                parameter_unit_type = parameter_dict.get("type", None)
                parameter_unit_label = LabelUtils.GetLabelForSpec(parameter_data_type)
            return parameter_discipline, parameter_unit_type, parameter_unit_label

        @classmethod
        def get_external_parameter_database(cls, parameter):

            # https://www.revitapidocs.com/2023/5015755d-ee80-9d74-68d9-55effc60ed0c.htm
            # CREATE NEW EXTERNAL DEFINITION PARAMETER
            # https://www.revitapidocs.com/2023/449e1cdb-ae48-6474-4da5-979c14b408f8.htm
            # https://thebuildingcoder.typepad.com/blog/2021/04/pdf-export-forgetypeid-and-multi-target-add-in.html

            parameter_name = parameter.Name
            parameter_guid = parameter.GUID
            parameter_description = parameter.Description
            parameter_group = parameter.OwnerGroup.Name
            parameter_discipline, parameter_type, parameter_label = cls.get_parameter_discipline_and_type_and_label(
                parameter)
            return [parameter_name, parameter_guid, parameter_description, parameter_discipline, parameter_type,
                    parameter_label, parameter_group]

        @classmethod
        def get_external_parameters_database_dict(cls):

            definition_file = app.OpenSharedParameterFile()
            groups = definition_file.Groups
            existing_shared_parameters_database = {}
            for group in groups:
                group_name = group.Name
                shared_parameters = group.Definitions
                for shared_parameter in shared_parameters:
                    parameter_database = cls.get_external_parameter_database(shared_parameter)
                    # name of parameter index =  parameter_database[0]
                    parameter_name = parameter_database[0]
                    # [shared_parameter] + [ame, guid, description, discipline, unit_type, unit_label, group]
                    existing_shared_parameters_database[parameter_name] = [shared_parameter] + parameter_database

                    # existing_shared_parameters_from_txt_lst.append(existing_shared_parameter)

            return existing_shared_parameters_database

        @classmethod
        def get_internal_parameters_database_dict(cls):
            # Take all existing Revit Project Parameters
            internal_and_external_definitions_pairs_lst = []
            iterator = doc.ParameterBindings.ForwardIterator()
            while iterator.MoveNext():
                # Get Internal Definition & Binding
                rvt_internal_definition = iterator.Key  # InternalDefinitions Class
                rvt_binding_class = iterator.Current  # TypeBinding or InstanceBinding Class
                # rvt_binding_class = InstanceBinding if isinstance(rvt_binding_class, InstanceBinding) else TypeBinding
                # Get External Definition and Crate tuple with Internal Definition
                definition_file = app.OpenSharedParameterFile()
                groups = definition_file.Groups
                existing_shared_parameters_from_txt_lst = []
                for group in groups:
                    group_name = group.Name
                    parameters = group.Definitions
                    for external_definition in parameters:
                        external_definition_name = external_definition.Name
                        try:
                            if external_definition_name == rvt_internal_definition.Name:
                                internal_and_external_definitions_pairs_lst.append(
                                    (rvt_internal_definition, rvt_binding_class, external_definition))
                        except:
                            error_log.append((external_definition_name, rvt_internal_definition))

            existing_internal_parameters_database = {}
            for pair in internal_and_external_definitions_pairs_lst:
                internal_pdefinition = pair[0]
                binding = pair[1]
                shared_parameter = pair[2]
                parameter_database = cls.get_external_parameter_database(shared_parameter)
                # name of parameter index =  parameter_database[0]
                parameter_name = parameter_database[0]
                # [shared_parameter] + [ame, guid, description, discipline, unit_type, unit_label, group]
                existing_internal_parameters_database[parameter_name] = [internal_pdefinition, binding,
                                                                         shared_parameter] + parameter_database

                # existing_shared_parameters_from_txt_lst.append(existing_shared_parameter)

            return existing_internal_parameters_database

        @classmethod
        def get_existing_internal_parameters_database_dict(cls):
            # Take all existing Revit Project Parameters
            internal_and_external_definitions_pairs_lst = []
            iterator = doc.ParameterBindings.ForwardIterator()
            existing_internal_parameters_database_ = {}
            while iterator.MoveNext():
                # Get Internal Definition & Binding
                rvt_internal_definition = iterator.Key  # InternalDefinitions Class
                rvt_binding_class = iterator.Current  # TypeBinding or InstanceBinding Class
                try:
                    parameter_name = rvt_internal_definition.Name
                    existing_internal_parameters_database_[parameter_name] = [rvt_internal_definition,
                                                                              rvt_binding_class]
                except:
                    error_log.append(rvt_internal_definition)
            return existing_internal_parameters_database_

        @classmethod
        def create_combined_definition_py_for_xls_imp_parameters(cls):
            xls_reader = ReadXLS(file_path=excel_path_string)
            worksheet_data = xls_reader.get_worksheet_data("SHARED PARAMETERS")[1:]
            for row in worksheet_data:
                bool_value, new_cd_py = cls.combined_definition_exist(row[1])
                if bool_value:
                    pass
                if bool_value is False:
                    new_cd_py = PyRevit.CombinedDefinitionPy(name=row[1])
                    new_cd_py.xls_imp_definition_exist = True
                new_cd_py.set_xls_definition_values_lst(row)

        @classmethod
        def create_combined_definition_py_for_external_parameters(cls):
            external_parameters_database_dict = cls.get_external_parameters_database_dict()
            for key, value in external_parameters_database_dict.items():
                bool_value, new_cd_py = cls.combined_definition_exist(key)
                if bool_value:
                    new_cd_py.external_definition_exist = True
                if bool_value is False:
                    new_cd_py = PyRevit.CombinedDefinitionPy(name=key)
                    new_cd_py.external_definition_exist = True
                new_cd_py.set_external_definition(value)

        @classmethod
        def create_combined_definition_py_for_internal_parameters(cls):
            internal_parameters_database_dict = cls.get_internal_parameters_database_dict()
            for key, value in internal_parameters_database_dict.items():
                bool_value, new_cd_py = cls.combined_definition_exist(key)
                if bool_value:
                    new_cd_py.internal_definition_exist = True
                if bool_value is False:
                    new_cd_py = PyRevit.CombinedDefinitionPy(name=key)
                    new_cd_py.internal_definition_exist = True
                new_cd_py.set_external_definition(value[2:])
                new_cd_py.set_internal_definition(value)

        @classmethod
        def create_combined_definition_py_complete(cls):
            cls.create_combined_definition_py_for_xls_imp_parameters()
            cls.create_combined_definition_py_for_external_parameters()
            cls.create_combined_definition_py_for_internal_parameters()

        @classmethod
        def create_xls_datum_to_forge_type_id_dict(cls):
            output_dict = {}
            for key, value in PyRevit.CombinedDefinitionUtils.spec_type_id_to_txt_dict.items():
                spec_type_id_label = LabelUtils.GetLabelForSpec(key)
                spec_type_id_discipline = value.get("discipline", None)
                spec_type_id_type = value.get("type", None)
                new_key = "@".join([spec_type_id_discipline, spec_type_id_label])
                output_dict[new_key] = key

            return output_dict

        @classmethod
        def create_new_external_definition(cls, py_instance):
            if py_instance.external_definition_exist is False:
                new_definition_name = py_instance.name
                new_definition_discipline = py_instance.xls_imp_definition.discipline
                new_definition_unit_type = py_instance.xls_imp_definition.unit_label
                new_definition_description = py_instance.xls_imp_definition.description
                new_definition_group = py_instance.xls_imp_definition.group
                #
                forge_type_id_key = "@".join([new_definition_discipline, new_definition_unit_type])
                #
                # forge_type_id = forge_type_id_key
                forge_type_id = cls.create_xls_datum_to_forge_type_id_dict().get(forge_type_id_key, False)
                if forge_type_id is False:
                    forge_type_id = SpecTypeId.String.MultilineText if new_definition_unit_type == "MultilineText" else forge_type_id
                if forge_type_id is not False:
                    # Open Shared Parameters Txt file
                    shared_param_file = app.OpenSharedParameterFile()
                    shared_parameter_groups = shared_param_file.Groups
                    existing_group = shared_parameter_groups.get_Item(new_definition_group)
                    #
                    if existing_group is None:
                        # Create
                        existing_group = shared_param_file.Groups.Create(new_definition_group)
                    #
                    new_definition = Autodesk.Revit.DB.ExternalDefinitionCreationOptions(new_definition_name,
                                                                                         forge_type_id)
                    try:
                        new_definition.Description = new_definition_description
                    except:
                        pass
                    # Create
                    new_external_definition = existing_group.Definitions.Create(new_definition)
                    py_instance.external_definition_element = new_external_definition
                return new_external_definition.Name + "parameter created in txt file."
            else:
                return py_instance.name + " already exist in txt file."

        @classmethod
        def create_new_external_definitions(cls):
            report_log = []
            for instance in PyRevit.CombinedDefinitionPy.instances:
                report_log.append(cls.create_new_external_definition(instance))
            return report_log

        @classmethod
        def create_lst_of_categories(cls, input):
            # Get all categories in the document
            # all_categories = doc.Settings.Categories
            categories_str_lst = input.lower().title().replace(", ", ",").replace("Rvt", "RVT").replace("Mep",
                                                                                                        "MEP").replace(
                "Hvac", "HVAC").split(",")
            output_categories_rvt_lst = []
            for str_cat in categories_str_lst:
                # 0-301 Number of All Revit Category
                rvt_category = cls.revit_categories_names_to_rvt_cat_dict.get(str_cat, None)
                if rvt_category is not None:
                    if str(rvt_category.GetType()) == "IronPython.Runtime.List":
                        pass
                    else:
                        rvt_category = uidoc.Document.Settings.Categories.get_Item(rvt_category)
                    output_categories_rvt_lst.append(rvt_category)
            return output_categories_rvt_lst

        @classmethod
        def get_internal_definitions_by_name(cls, name=None):
            selected_internal_parameter = None
            iterator = doc.ParameterBindings.ForwardIterator()
            while iterator.MoveNext():
                #
                internal_definition = iterator.Key
                try:
                    internal_definition_name = internal_definition.Name
                    binding = iterator.Current
                    #
                    if internal_definition_name == name:
                        selected_internal_parameter = internal_definition
                except:
                    error_log.append(internal_definition)
            return selected_internal_parameter

        @classmethod
        def create_new_internal_definition(cls, py_instance):

            def set_new_parameter_as_instance(_py_instance):

                # 0 - TYPE / 1 - INSTANCE -> str
                categories_set_names_all = ("Analytical Openings, Analytical Panels, Analytical Members, "
                                            "Analytical Links, Analytical Nodes, Structural Rebar Couplers, "
                                            "Modifiers, Welds, Holes, Shear Studs, Others, Bolts, Anchors, Plates, "
                                            "Profiles, Structural Connections, Fabric Wire, Structural Fabric Areas, "
                                            "Structural Fabric Reinforcement, Rebar Shape, Structural Path Reinforcement, "
                                            "Structural Area Reinforcement, Structural Rebar, Plumbing Equipment, "
                                            "Mechanical Control Devices, Insulation, Lining, MEP Fabrication Containment, "
                                            "MEP Fabrication Pipework, MEP Fabrication Hangers, Insulation, "
                                            "MEP Fabrication Ductwork, Analytical Surfaces, Analytical Spaces, "
                                            "Pipe Placeholders, Duct Placeholders, Cable Tray Runs, Conduit Runs, "
                                            "Conduits, Cable Trays, Conduit Fittings, Cable Tray Fittings, "
                                            "Duct Linings, Duct Insulations, Pipe Insulations, HVAC Zones, "
                                            "Switch System, Sprinklers, Lighting Devices, Fire Alarm Devices, "
                                            "Data Devices, Communication Devices, Security Devices, "
                                            "Nurse Call Devices, Telephone Devices, Pipe Accessories, Flex Pipes, "
                                            "Pipe Fittings, Pipes, Piping Systems, Wires, Electrical Circuits, "
                                            "Flex Ducts, Duct Accessories, Duct Systems, Air Terminals, Duct Fittings, "
                                            "Ducts, Structural Tendons, Expansion Joints, Vibration Isolators, "
                                            "Vibration Dampers, Vibration Management, Trusses, Diaphragms, "
                                            "Cross Bracing, Bridge Framing, Pier Walls, Pier Piles, Pier Columns, "
                                            "Pier Caps, Approach Slabs, Abutment Walls, Abutment Piles, "
                                            "Abutment Foundations, Bearings, Girders, Pier Foundations, "
                                            "Bridge Decks, Arches, Bridge Cables, Pier Towers, Piers, Abutments, "
                                            "Internal Area Loads, Internal Line Loads, Internal Point Loads, "
                                            "Area Loads, Line Loads, Point Loads, Spaces, Mass Opening, "
                                            "Mass Skylight, Mass Glazing, Mass Roof, Mass Exterior Wall, "
                                            "Mass Interior Wall, Mass Zone, Mass Floor, Mass, Areas, "
                                            "Project Information, Sheets, Detail Items, Roof Soffits, "
                                            "Slab Edges, Gutters, Fascias, Entourage, Planting, "
                                            "Structural Stiffeners, RVT Links, Specialty Equipment, Topography, "
                                            "Topography Links, Structural Trusses, Structural Columns, "
                                            "Structural Beam Systems, Structural Framing, Structural Foundations, "
                                            "Property Line Segments, Property Lines, Pads, Site, Roads, Parking, "
                                            "Plumbing Fixtures, Mechanical Equipment, Lighting Fixtures, "
                                            "Furniture Systems, Electrical Analytical Transformer, Electrical "
                                            "Fixtures, Signage, Audio Visual Devices, Vertical Circulation, "
                                            "Fire Protection, Medical Equipment, Food Service Equipment, "
                                            "Electrical Equipment, Temporary Structures, Hardscape, Electrical "
                                            "Analytical Power Source, Electrical Load Areas, Electrical Analytical "
                                            "Transfer Switch, Electrical Analytical Bus, Electrical Analytical Loads, "
                                            "Alignments, Zone Equipment, Water Loops, Air Systems, System-Zones, "
                                            "Casework, Shaft Openings, Mechanical Equipment Sets, "
                                            "Analytical Pipe Connections, Terminations, Supports, Handrails, "
                                            "Top Rails, Landings, Runs, <Path of Travel Lines>, Materials, "
                                            "Schedules, Curtain Systems, Views, Parts, Assemblies, Levels, "
                                            "Multi-segmented Grid, Grids, Wall Sweeps, Ramps, Curtain Wall Mullions,"
                                            " Curtain Panels, Rooms, Generic Models, Railings, Supports, "
                                            "Stairs, Columns, Model Groups, Furniture, Ceilings, Roofs, "
                                            "Floors, Doors, Windows, Walls")

                my_categories = app.Create.NewCategorySet()
                parameter_categories_string = _py_instance.xls_imp_definition.binding_categories_set
                if parameter_categories_string == "All":
                    parameter_categories_string = categories_set_names_all
                parameter_categories_lst = cls.create_lst_of_categories(parameter_categories_string)
                for my_category in parameter_categories_lst:
                    if my_category is not None:
                        if my_category.AllowsBoundParameters:
                            my_categories.Insert(my_category)
                # Create an instance of InstanceBinding
                instance_binding = app.Create.NewInstanceBinding(my_categories)
                # Get the BindingMap of current document.
                binding_map = uidoc.Document.ParameterBindings
                # Bind the definitions to the document
                new_parameter_group = cls.revit_pg_names_to_rvt_pg_dict.get(
                    _py_instance.xls_imp_definition.internal_group, None)
                temp.append(new_parameter_group)
                try:
                    instance_bind_ok = binding_map.Insert(py_instance.external_definition.element, instance_binding,
                                                          new_parameter_group)
                except:
                    pass

            def set_new_parameter_as_type(_py_instance):

                # 0 - TYPE / 1 - INSTANCE -> str
                categories_set_names_all = ("Analytical Links, Structural Rebar Couplers, Structural Connections, "
                                            "Fabric Wire, Structural Fabric Areas, Structural Fabric Reinforcement, "
                                            "Rebar Shape, Structural Path Reinforcement, Structural Area Reinforcement, "
                                            "Structural Rebar, Plumbing Equipment, Mechanical Control Devices, "
                                            "MEP Fabrication Containment, MEP Fabrication Pipework, "
                                            "MEP Fabrication Hangers, MEP Fabrication Ductwork, Pipe Placeholders, "
                                            "Duct Placeholders, Cable Tray Runs, Conduit Runs, Conduits, "
                                            "Cable Trays, Conduit Fittings, Cable Tray Fittings, Duct Linings, "
                                            "Duct Insulations, Pipe Insulations, Sprinklers, Lighting Devices, "
                                            "Fire Alarm Devices, Data Devices, Communication Devices, "
                                            "Security Devices, Nurse Call Devices, Telephone Devices, "
                                            "Pipe Accessories, Flex Pipes, Pipe Fittings, Pipes, "
                                            "Piping Systems, Wires, Flex Ducts, Duct Accessories, Duct Systems, "
                                            "Air Terminals, Duct Fittings, Ducts, Structural Tendons, "
                                            "Expansion Joints, Vibration Isolators, Vibration Dampers, "
                                            "Vibration Management, Trusses, Diaphragms, Cross Bracing, "
                                            "Bridge Framing, Pier Walls, Pier Piles, Pier Columns, Pier Caps, "
                                            "Approach Slabs, Abutment Walls, Abutment Piles, Abutment Foundations, "
                                            "Bearings, Girders, Pier Foundations, Bridge Decks, Arches, "
                                            "Bridge Cables, Pier Towers, Piers, Abutments, Mass, Detail Items, "
                                            "Roof Soffits, Slab Edges, Gutters, Fascias, Entourage, Planting, "
                                            "Structural Stiffeners, RVT Links, Specialty Equipment, Topography, "
                                            "Topography Links, Structural Trusses, Structural Columns, "
                                            "Structural Beam Systems, Structural Framing, Structural Foundations, "
                                            "Property Line Segments, Property Lines, Pads, Site, Roads, "
                                            "Parking, Plumbing Fixtures, Mechanical Equipment, Lighting Fixtures, "
                                            "Furniture Systems, Electrical Fixtures, Signage, "
                                            "Audio Visual Devices, Vertical Circulation, Fire Protection, "
                                            "Medical Equipment, Food Service Equipment, Electrical Equipment, "
                                            "Temporary Structures, Hardscape, Alignments, Casework, "
                                            "Mechanical Equipment Sets, Analytical Pipe Connections, "
                                            "Terminations, Supports, Handrails, Top Rails, Landings, Runs, "
                                            "Curtain Systems, Assemblies, Levels, Multi-segmented Grid, "
                                            "Grids, Wall Sweeps, Ramps, Curtain Wall Mullions, Curtain Panels, "
                                            "Generic Models, Railings, Supports, Stairs, Columns, Model Groups, "
                                            "Furniture, Ceilings, Roofs, Floors, Doors, Windows, Walls")

                my_categories = app.Create.NewCategorySet()
                parameter_categories_string = _py_instance.xls_imp_definition.binding_categories_set
                if parameter_categories_string == "All":
                    parameter_categories_string = categories_set_names_all
                parameter_categories_lst = cls.create_lst_of_categories(parameter_categories_string)
                for my_category in parameter_categories_lst:
                    if my_category is not None:
                        if my_category.AllowsBoundParameters:
                            my_categories.Insert(my_category)
                # Create an instance of InstanceBinding
                type_binding = app.Create.NewTypeBinding(my_categories)
                # Get the BindingMap of current document.
                binding_map = uidoc.Document.ParameterBindings
                # Bind the definitions to the document
                new_parameter_group = cls.revit_pg_names_to_rvt_pg_dict.get(
                    _py_instance.xls_imp_definition.internal_group, None)
                temp.append(new_parameter_group)
                #
                try:
                    instance_bind_ok = binding_map.Insert(py_instance.external_definition.element, type_binding,
                                                          new_parameter_group)
                except:
                    pass

            if py_instance.internal_definition_exist is False and py_instance.xls_imp_definition_exist is True:
                # 0 - TYPE / 1 - INSTANCE -> str
                if str(py_instance.xls_imp_definition.binding_type) == "0":
                    TransactionManager.Instance.EnsureInTransaction(doc)
                    set_new_parameter_as_type(py_instance)
                    TransactionManager.Instance.TransactionTaskDone()

                # 0 - TYPE / 1 - INSTANCE -> str
                if str(py_instance.xls_imp_definition.binding_type) == "1":

                    TransactionManager.Instance.EnsureInTransaction(doc)
                    set_new_parameter_as_instance(py_instance)
                    TransactionManager.Instance.TransactionTaskDone()

                    internal_definition = cls.get_internal_definitions_by_name(py_instance.name)

                    TransactionManager.Instance.EnsureInTransaction(doc)
                    try:
                        internal_definition.SetAllowVaryBetweenGroups(doc, True)
                    except:
                        temp.append("FAIL")
                    TransactionManager.Instance.TransactionTaskDone()

        @staticmethod
        def sort_instances(instances):
            # Define a custom sorting function
            def custom_sort_key(instance):
                # If the instance has an xls_imp_definition.no_id, use it as the sorting key
                if instance.xls_imp_definition.no_id:
                    # Convert the no_id to an integer if possible, otherwise, return as is
                    try:
                        return int(instance.xls_imp_definition.no_id)
                    except:
                        return instance.xls_imp_definition.no_id
                else:
                    # If no_id is None or empty, return a tuple with a large value
                    # to ensure it's placed at the end of the sorted list
                    return (float('inf'), instance.name)

            # Sort the instances using the custom sorting function
            sorted_instances = sorted(instances, key=custom_sort_key)

            return sorted_instances

        @classmethod
        def create_new_internal_definitions(cls):
            report_log = []
            sorted_list = cls.sort_instances(PyRevit.CombinedDefinitionPy.instances)
            for instance in sorted_list:
                report_log.append(
                    (instance.xls_imp_definition.no_id, instance.name, cls.create_new_internal_definition(instance)))
            return report_log

        @classmethod
        def create_combined_definition_py_database_to_xls_export(cls):
            output_dataset = []

            pg_dict = cls.revit_pg_names_to_string_dict
            internal_dict = cls.get_existing_internal_parameters_database_dict()

            sorted_list = cls.sort_instances(PyRevit.CombinedDefinitionPy.instances)
            for instance in sorted_list:
                if instance.internal_definition is not None:
                    #
                    instance.internal_definition.binding_type = internal_dict.get(instance.name, None)
                    #
                    if instance.internal_definition.internal_group is not None:
                        internal_group = pg_dict.get(str(instance.internal_definition.internal_group),
                                                     "None")  # definition.OwnerGroup.Name
                    else:
                        internal_group = "None"
                    #
                    if instance.internal_definition.binding_type is not None:
                        # error_log_1.append((instance.name, instance.internal_definition.binding_type[1], b__l))
                        instance.xls_imp_definition.binding_type = "1" if isinstance(
                            instance.internal_definition.binding_type[1], Autodesk.Revit.DB.InstanceBinding) else "0"
                    else:
                        instance.xls_imp_definition.binding_type = "None"
                    #

                    #
                    if instance.internal_definition.varies_across_groups is False:
                        instance.xls_imp_definition.varies_across_groups = "0"
                    if instance.internal_definition.varies_across_groups is True:
                        instance.xls_imp_definition.varies_across_groups = "1"
                    #
                    cat_list = instance.internal_definition.binding_categories_set
                    if cat_list is not None:
                        cat_names_list = [cat.Name for cat in cat_list]
                        instance.xls_imp_definition.binding_categories_set = ", ".join(cat_names_list)
                    else:
                        instance.xls_imp_definition.binding_categories_set = "None"
                    #
                    no_id = instance.xls_imp_definition.no_id if instance.xls_imp_definition.no_id is not None else ""
                    #
                    categories_list_string = []
                    #
                    row = [
                        no_id,
                        instance.name,
                        instance.external_definition.discipline,  # external_definition
                        instance.external_definition.unit_label,  # external_definition
                        instance.external_definition.description,  # external_definition.Description
                        instance.external_definition.group,  # external_definition.OwnerGroup.Name
                        str(instance.external_definition.guid),  # external_definition.GUID
                        internal_group,  # external_definition.OwnerGroup.Name
                        instance.xls_imp_definition.binding_type,  # InstanceBinding or TypeBinding
                        instance.xls_imp_definition.varies_across_groups,
                        instance.xls_imp_definition.binding_categories_set
                    ]
                    row = ["None" if cell is None else cell for cell in row]
                    output_dataset.append(row)

            return output_dataset

        @classmethod
        def export_data_to_excel(cls):
            xls_export_data = cls.create_combined_definition_py_database_to_xls_export()
            # Write data to excel
            writer = WriteXLS(file_path=output_excel_path_string)
            # Write data to the specified worksheet starting at row 2, column 1
            writer.write_data(worksheet_name="SHARED PARAMETERS", data=xls_export_data, start_row=2, start_col=1)

        @classmethod
        def create_db_parameters_to_switch(cls):
            xls_reader = ReadXLS(file_path=excel_path_string)
            worksheet_data = xls_reader.get_worksheet_data("SWITCH FAMILIES SHP")[1:]
            switch_dict = {}
            for row in worksheet_data:
                current_name = row[2]
                param_dict = {
                    "NO": row[0],
                    "CURRENT_NAME": current_name,
                    "NEW_NAME": row[1],
                    "NEW_PG_GROUP": row[3],
                    "NEW_TYPE_OR_INSTANCE": row[4],
                }
                switch_dict[current_name] = param_dict

            return switch_dict


def open_family_documents():
    global family_paths

    # Current doc/app/ui
    paths = ListUtils.to_list(family_paths)
    documents, outcomes = [], []
    for path in paths:
        try:
            document = app.OpenDocumentFile(path)
            documents.append(document)
            outcomes.append(True)
        except:
            documents.append(None)
            outcomes.append(False)
    # return [documents, outcomes]
    return documents


def get_parameter_properties(params_list):
    param_properties = []
    for param in params_list:
        prop_list = [
            param.Definition.Name,
            param.Definition.Description if hasattr(param.Definition, 'Description') else None,
            param.Element.Id if hasattr(param, 'Element') else None,
            param.GUID if hasattr(param, 'GUID') else None,
            param.Id.IntegerValue,
            param.IsReadOnly,
            param.IsShared,
            param.StorageType.ToString(),
            param.UserModifiable
        ]
        param_properties.append(prop_list)
    return param_properties

# Create complete list of definitions as PyRevit.CombinedDefinition
PyRevit.CombinedDefinitionUtils.create_combined_definition_py_complete()

#########################

families_doc_lst = open_family_documents()
#
#
switch_db_dict = PyRevit.CombinedDefinitionUtils.create_db_parameters_to_switch()
#
outcomes = []
# Collect values
for rvt_family in families_doc_lst:
    if rvt_family.IsFamilyDocument:
        # IList < FamilyParameter > GetParameters()
        family_parameters_list = list(rvt_family.FamilyManager.GetParameters())
        new_pattern_list = []
        outcome = []
        for param_def in family_parameters_list:
            param_def_name = param_def.Definition.Name
            switch_dict = switch_db_dict.get(param_def_name, False)
            if switch_dict != False:
                current_family_parameter = param_def
                new_parameter_name = switch_dict.get("NEW_NAME")
                new_parameter_exist, combined_definition = PyRevit.CombinedDefinitionUtils.combined_definition_exist(new_parameter_name)
                temp_report.append((new_parameter_name, new_parameter_exist, combined_definition))
                if new_parameter_exist:
                    d = combined_definition.external_definition.element
                    b = PyRevit.CombinedDefinitionUtils.revit_pg_names_to_rvt_pg_dict.get(switch_dict.get("NEW_PG_GROUP"))
                    i = True if str(switch_dict.get("NEW_TYPE_OR_INSTANCE")) == "1" else False
                    # outcomes.append((d, b, i))
                    try:
                        TransactionManager.Instance.EnsureInTransaction(rvt_family)
                        new = rvt_family.FamilyManager.ReplaceParameter(current_family_parameter, d, b, i)
                        TransactionManager.Instance.ForceCloseTransaction()
                        outcome.append(new)
                        new_pattern_list.append(new_parameter_name)
                    except:
                        outcome.append("Parameter not changed, new parameter unit type is different than current.")
                        new_pattern_list.append(param_def_name)

                else:
                    outcome.append("New Parameter not found in Shared Parameters rxt file.")
                    new_pattern_list.append(param_def_name)
            else:
                outcome.append("Parameter to change not found.")
                new_pattern_list.append(param_def_name)
        # IList < FamilyParameter > GetParameters()
        family_parameters_list = list(rvt_family.FamilyManager.GetParameters())
        combined_family_parameters_list = []
        for param_def in family_parameters_list:
            param_def_name = param_def.Definition.Name
            combined_family_parameters_list.append((param_def, param_def_name))

        combined_family_parameters_list = ListUtils.sort_sublist_by_pattern(new_pattern_list,
                                                                            combined_family_parameters_list, 1)
        #
        family_parameters_list = list(zip(*combined_family_parameters_list))[0]
        outcomes.append(get_parameter_properties(family_parameters_list))
        # Create a List[FamilyParameter] object
        parameters_i_list = List[FamilyParameter]()
        # Add the FamilyParameter objects from the IronPython list to the List[FamilyParameter] object
        for param in family_parameters_list:
            parameters_i_list.Add(param)
        TransactionManager.Instance.EnsureInTransaction(rvt_family)
        # Use the ReorderParameters method with the parameter_list
        rvt_family.FamilyManager.ReorderParameters(parameters_i_list)
        TransactionManager.Instance.ForceCloseTransaction()
    else:
        outcome = "Document is not a family document."
    outcomes.append(outcome)


families_doc_lst = [families_doc_lst, outcomes, temp_report, PyRevit.CombinedDefinitionPy.instances]

OUT = families_doc_lst
