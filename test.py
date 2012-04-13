# Test importer for import_nel3d.py

from import_nel3d import *

#===============================================================================
# The global file names here are used for testing during development
# Adjust them and uncomment the function calls at the end to load files
#===============================================================================


#gFileRootPath = "d:/programming/data/ryzom/unpacked_data/"
gFileRootPath = "d:/programming/data/ryzom/flat_unpacked_data/"
#gFileRootPath = "e:/ryzom/data/flat/"

#gShapeFileName = "Ge_Mission_Outpost_townhall.shape"

#gShapeFileName = "Ge_Mission_Hut.shape" # (n) CMeshMRMGeom_to_BlenderMesh
#gShapeFileName = "GE_Mission_Altar_Karavan.shape" # (n) CMeshMRMGeom

#gShapeFileName = "Ge_Mission_Stand.shape"
#gShapeFileName = "GE_Mission_Prison.shape"

#gShapeFileName = "indoors_shapes/TR_Hall_reunion.shape" # textures?

#gShapeFileName = "objects/CA_HOF_Acc_Gauntlet.shape" # (y); skinned
#gShapeFileName = "objects/Ge_Mission_Outpost_Drill_karavan.shape" # (y) 
#gShapeFileName = "objects/ge_mission_temple_of_maduk.shape" # # (y)
#gShapeFileName = "jungle_shapes/FO_S1_giant_tree.shape" #


gSkeletonFileName = "tr_mo_clapclap.skel"


#===============================================================================
# calling the importer functions...
#===============================================================================

nelSkeleton = load_NEL_file(gFileRootPath+gSkeletonFileName);
bSkeletonObj = convert_NelSkeleton_to_BlenderArmature(nelSkeleton);

#debug_ApplyDefaultPosRot_AsPose(nelSkeleton, bSkeletonObj);

#nelMesh = load_NEL_file(gFileRootPath+gShapeFileName);
#bMeshObj = convert_NelMesh_to_BlenderObject(nelMesh, gFileRootPath);
#connectBlenderSkeleton_To_BlenderMeshObject(bSkeletonObj, bMeshObj);

#animation = load_NEL_file(gFileRootPath + gAnimFileName);
#convert_NelAnimation_to_BlenderAction(animation, nelSkeleton, bSkeletonObj);

#print(getBindTrafo_Recursive("Bip01 Tail", nelSkeleton));
#print(rotation_quaterniongetBindTrafo_Recursive("Bip01 Tail", nelSkeleton).inverted());

#nelIG = load_NEL_file(gFileRootPath + gIGFileName);
#convert_NelInstanceGroup_to_Blender(nelIG, gFileRootPath);

