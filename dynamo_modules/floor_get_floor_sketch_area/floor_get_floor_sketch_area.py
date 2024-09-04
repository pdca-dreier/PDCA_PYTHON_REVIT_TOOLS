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

floors_list = UnwrapElement(IN[0])
#######OK NOW YOU CAN CODE########


# Define the function to get and print the sketch profile curves from a floor
def print_floor_sketch_profile(floor):
    """
    This function takes a Revit floor element and prints its sketch profile curves.

    :param floor: The Revit floor element
    """
    doc = DocumentManager.Instance.CurrentDBDocument

    # Get the Sketch element from the floor's SketchId
    sketch_id = floor.SketchId
    sketch = doc.GetElement(sketch_id)  # Retrieve the sketch element
    output = []
    if sketch:
        # Iterate over the curve arrays in the sketch profile
        for curve_array in sketch.Profile:
            sub_output = []
            # Iterate through each curve in the curve array
            for curve in curve_array:
                sub_output.append(curve.ToProtoType())  # Print each curve's string representation
            output.append(sub_output)  # Print a blank line after each curve array
    return output


output = []
for floor in floors_list:
    curve_loop_list =  print_floor_sketch_profile(floor)
    output.append(curve_loop_list)

OUT = output