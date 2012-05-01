#-------------------------------------------------------------------------------
# NeL 3D Blender Importer - Version 0.3.4 -
# Copyright (C) 2012 Holger Dammertz
#
#-------------------------------------------------------------------------------
#
# ***** begin GPL LICENSE BLOCK *****
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENCE BLOCK *****
#
#-------------------------------------------------------------------------------
#
# This is a work in progress importer for NeL 3D files (*.shape,
# *.skel, ...).  The goal is to batch-import unpacked files from NeL
# 3D (Ryzom) into a usable blender format.
#
# The code here is based directly on the NeL source-code as contained
# in the dev.ryzom.com hg repository. Most of the relevant files are
# in 'code/nel/src/3d' where the serial(...) method of each class
# defines the binary data format that is loaded here.
# 
#-------------------------------------------------------------------------------
#  TODO: 
#   - alot
#-------------------------------------------------------------------------------
#  Notes: 
#   - gStreamIDMap this variable holds the cached nodes during
#     loading; it is reset for every load_NEL_file call
#-------------------------------------------------------------------------------
#  Changelog:
#   0.3.4: changes to be compatible with blender 2.63
#   0.3.3: creating vertex groups in MRM converted files
#   0.3.2: reading of CMeshMRMSkinnedGeom (but no conversion yet)
#   0.3.1: reading of .anim files (but no conversion yet)
#   0.2.1: basic loading of skeleton and creation of blender armature
#   0.1.1: basic mesh loading (with materials) and creation of blender mesh 
#          object
#-------------------------------------------------------------------------------

bl_info= {
    "name": "Import NeL 3D Objects",
    "author": "NeoSpark314",
    "version": (0, 3, 4),
    "blender": (2, 6, 3),
    "location": "File > Import > NeL 3D (.shape)",
    "description": "Import NeL 3D assets",
    "warning": "",
    "category": "Import-Export"}

gFileRootPath = "./"


import bpy
import os
import struct
import mathutils
import operator
from bpy_extras.io_utils import unpack_list, unpack_face_list
from bpy_extras.image_utils import load_image



def error(message):
    raise Exception(message);

   

def r_uint64(f):
    return struct.unpack('<Q', f.read(8))[0];

def r_uint32(f):
    return struct.unpack('<I', f.read(4))[0];

def r_uint16(f):
    return struct.unpack('<H', f.read(2))[0];

def r_uint8(f):
    return struct.unpack('<B', f.read(1))[0];

def r_int64(f):
    return struct.unpack('<q', f.read(8))[0];

def r_int32(f):
    return struct.unpack('<i', f.read(4))[0];

def r_int16(f):
    return struct.unpack('<h', f.read(2))[0];

def r_int8(f):
    return struct.unpack('<b', f.read(1))[0];

def r_double(f):
    return struct.unpack('<d', f.read(8))[0];

def r_float(f):
    return struct.unpack('<f', f.read(4))[0];

def r_bool(f):
    return r_uint8(f) != 0;

def r_version(f):
    ver = r_uint8(f);
    if (ver == 0xFF):
        return r_uint32(f);
    else:
        return ver;

def r_lstring(f): # reading a length-encoded string
    len = r_uint32(f);
    val = f.read(len)
    try:
        val = val.decode();
    except:
        print("WARNING: could not decode string: " + str(val));
        val = str(val);
        #error("break");
    return val;

def r_Vec2f(f): 
    return (r_float(f), r_float(f));

def r_Vec3f(f): 
    return (r_float(f), r_float(f), r_float(f));

def r_Vec4f(f): 
    return (r_float(f), r_float(f), r_float(f), r_float(f));

def r_RGBA(f):
    return (r_uint8(f), r_uint8(f), r_uint8(f), r_uint8(f));

# reads a versioned type of a (i.e. versioned(r_RGBA, f)) used for CTrackDefaultBlendable
def versioned(a, f):
    r_version(f);
    return a(f);


enum_TCameraCollisionGenerate = ("AutoCameraCol", "NoCameraCol", "ForceCameraCol", );

enum_TShader = ("Normal", "Bump", "UserColor", "LightMap", "Specular", "Caustics", "PerPixelLighting", "PerPixelLightingNoSpec", "Cloud", "Water",);
enum_TBlend = ("one", "zero", "srcalpha", "invsrcalpha", "srccolor", "invsrccolor", "blendConstantColor", "blendConstantInvColor", "blendConstantAlpha", "blendConstantInvAlpha",);
enum_ZFunc = ("always", "never", "equal", "notequal", "less", "lessequal", "greater", "greaterequal",);

enum_TUploadFormat = ("Auto", "RGBA8888", "RGBA4444", "RGBA5551", "RGB888", "RGB565", "DXTC1", "DXTC1Alpha", "DXTC3", "DXTC5", "Luminance", "Alpha", "AlphaLuminance", "DsDt", );

enum_TMinFilter = ("NearestMipMapOff", "NearestMipMapNearest", "NearestMipMapLinear", "LinearMipMapOff", "LinearMipMapNearest", "LinearMipMapLinear", );
enum_TMagFilter = ("Nearest", "Linear", );
enum_TWrapMode = ("Repeat", "Clamp", );

enum_CPointLight_TType = ("PointLight", "SpotLight", "AmbientLight");

IDRV_MAT_MAXTEXTURES = 4;

IDRV_MAT_TEX_ADDR = 0x00000400;
IDRV_MAT_USER_TEX_0_MAT = 0x00100000;

NL3D_MESH_MRM_SKINNED_MAX_MATRIX = 4;

NL3D_MESH_SKINNING_MAX_MATRIX = 4;

NL3D_MESH_MRM_SKINNED_WEIGHT_FACTOR = 255.0;
NL3D_MESH_MRM_SKINNED_UV_FACTOR	= 8192.0;
NL3D_MESH_MRM_SKINNED_NORMAL_FACTOR = 32767.0;
NL3D_MESH_MRM_SKINNED_DEFAULT_POS_SCALE = 8.0/32767.0;

NL3D_OO32767 = 1.0/32767;


# we use the 32bit float max here:
FLT_MAX = 3.402823466e+38;

def r_enum(enum, f):
    return enum[r_int32(f)];


def parse_CTrackDefaultVector(f):
    return versioned(r_Vec3f, f);

def parse_CTrackDefaultQuat(f):
    return versioned(r_Vec4f, f);


def parse_ITexture(f):
    data = {};
    ver = r_version(f);
    data['_UploadFormat'] = r_enum(enum_TUploadFormat, f);
    data['_WrapS'] = r_enum(enum_TWrapMode, f);
    data['_WrapT'] = r_enum(enum_TWrapMode, f);
    data['_MinFilter'] = r_enum(enum_TMinFilter, f);
    data['_Magfilter'] = r_enum(enum_TMagFilter, f);
    data['_LoadGraysacleAsAlpha'] = r_bool(f) if (ver >= 1) else False;

    return data;
    


def parse_CTextureFile(f):
    ver = r_version(f);
    data = parse_ITexture(f);
    data['_FileName'] = r_lstring(f);
    data['_AllowDegradation'] = r_bool(f) if (ver >= 1) else True;

    data['NelType'] = 'CTextureFile';
    return data;

def parse_TexEnv(f, ver):
    data = {};
    #!!TODO: currently only skipping the packed data here; see nel/include/nel/3d/material.h line 586
    if (ver > 0):
        f.read(14);
    else:
        f.read(10);
    data['ConstantColor'] = r_RGBA(f);
    return data;

def parse_CTextureCube(f):
    ver = r_version(f);
    data = parse_ITexture(f);
    data['_Textures'] = [parse_PolyPtr(f) for i in range(6)];
    if (ver == 1): r_bool(f);
        
    data['NelType'] = 'CTextureCube';
    return data;


# State Bits
MAT_TRANS = 1;
MAT_ROT = 2;
MAT_SCALEUNI = 4;
MAT_SCALEANY = 8;
MAT_PROJ = 16;

def parse_CMatrix(f):
    data = {};
    ver = r_version(f);
    mat = mathutils.Matrix.Identity(4);
    data['StateBit'] = r_uint32(f);
    data['Scale33'] = r_float(f);

    if (data['StateBit'] & (MAT_ROT|MAT_SCALEUNI|MAT_SCALEANY) !=0): #hasRot()
        mat[0][0] = r_float(f);
        mat[0][1] = r_float(f);
        mat[0][2] = r_float(f);
        mat[1][0] = r_float(f);
        mat[1][1] = r_float(f);
        mat[1][2] = r_float(f);
        mat[2][0] = r_float(f);
        mat[2][1] = r_float(f);
        mat[2][2] = r_float(f);
    if (data['StateBit'] & MAT_TRANS != 0): #hasTrans()
        mat[0][3] = r_float(f);
        mat[1][3] = r_float(f);
        mat[2][3] = r_float(f);
    if (data['StateBit'] & MAT_PROJ != 0):
        mat[3][0] = r_float(f);
        mat[3][1] = r_float(f);
        mat[3][2] = r_float(f);
        mat[3][3] = r_float(f);
        
    data['M'] = mat;

    data['NelType'] = 'CMatrix';
    return data;

    
    
# implements the serial2 from CLightMap
def parse_CLightMap_2(f):
    data = {};
    ver = r_version(f);
    data['Factor'] = r_RGBA(f);
    data['LMCDiffuse'] = r_RGBA(f);
    data['LMCAmbient'] = r_RGBA(f) if (ver >= 1) else (0,0,0,0);
    data['Texture'] = parse_PolyPtr(f);

    data['NelType'] = 'CLightMap';
    return data;

def parse_CLightMap(f):
    data = {};
    data['Factor'] = r_RGBA(f);
    data['Texture'] = parse_PolyPtr(f);

    data['NelType'] = 'CLightMap';
    return data;
    

def parse_CMaterial(f):
    cMat = {}
    ver = r_version(f);
    cMat['_ShaderType'] = enum_TShader[r_int32(f)];
    cMat['_Flags'] = r_uint32(f);
    cMat['_SrcBlend'] = enum_TBlend[r_int32(f)];
    cMat['_DstBlend'] = enum_TBlend[r_int32(f)];
    cMat['_ZFunction'] = enum_ZFunc[r_int32(f)];
    cMat['_ZBias'] = r_float(f);
    cMat['_Color'] = r_RGBA(f);
    cMat['_Emissive'] = r_RGBA(f);
    cMat['_Ambient'] = r_RGBA(f);
    cMat['_Diffuse'] = r_RGBA(f);
    cMat['_Specular'] = r_RGBA(f);
    cMat['_Shininess'] = r_float(f) if (ver >= 2) else 0.0;
    cMat['_AlphaTestThreshold'] = r_float(f) if (ver >= 5) else 0.0;
    cMat['_TexCoordGenMode'] = r_uint16(f) if (ver >= 8) else 0;

    cMat['_Textures'] = [];
    cMat['_TexEnvs'] = [];

    # next we need to read the textures
    for i in range(0, IDRV_MAT_MAXTEXTURES):
        tex = parse_PolyPtr(f);
        cMat['_Textures'].append(tex);
        if (ver >= 1):
            cMat['_TexEnvs'].append(parse_TexEnv(f, 1 if (ver >= 9) else 0));
        else:
            cMat['_TexEnvs'].append(None); # !!TODO: check if we need a default here

    if (ver >= 3):
        if (ver >= 7):
            n = r_uint32(f);
            #print('num LightMaps = %d' % n);
            cMat['_LightMaps'] = [];
            for i in range(0, n):
                cMat['_LightMaps'].append(parse_CLightMap_2(f));
            cMat['_LightMapsMulx2'] = r_bool(f);
        else:
            cMat['_LightMaps'] = parse_cont(f, parse_CLightMap);


    cMat['_TexAddrMode'] = [];
    if (ver >= 4):
        if (cMat['_Flags'] & IDRV_MAT_TEX_ADDR != 0):
            for i in range(0, IDRV_MAT_MAXTEXTURES):
                cMat['_TexAddrMode'].append(r_uint8(f));
    
    cMat['_TexUserMat'] = [];
    if (ver >= 6):
        for i in range(0, IDRV_MAT_MAXTEXTURES):
            # implements CMaterial::isUserTexMatEnabled(uint stage):
            if (cMat['_Flags'] & (IDRV_MAT_USER_TEX_0_MAT << i) != 0):
                cMat['_TexUserMat'].append(parse_CMatrix(f));
            else:
                cMat['_TexUserMat'].append(None);

    #print("Finished reading CMaterial");
        
    cMat['NelType'] = 'CMaterial';
    return cMat;



def parse_CLightMapInfoList(f):
    data = {};
    ver = r_version(f);
    data['LightGroup'] = r_uint32(f);
    data['AnimatedLight'] = r_lstring(f);

    data['StageList'] = [];
    numCMatStage = r_uint32(f);
    for i in range(0, numCMatStage):
        matStage = {};
        r_version(f);
        matStage['MatId'] = r_uint8(f);
        matStage['StageId'] = r_uint8(f);
        data['StageList'].append(matStage);

    data['NelType'] = 'CLightMapInfoList';
    return data;


def parse_CLodCharacterTexture(f):
    data = {};
    r_version(f);
    data['_Width'] = r_uint32(f);
    data['_Height'] = r_uint32(f);
    num = r_uint32(f);
    data['Texture'] = [];
    for i in range (0, num):
        data['Texture'].append( (r_uint8(f), r_uint8(f), r_uint8(f), r_uint8(f)) ); # T U V Q

    data['NelType'] = 'CLodCharacterTexture';
    return data;


def parse_CAnimatedTexture(f):
    data = {}
    data['Texture'] = parse_PolyPtr(f);
    data['NelType'] = 'CAnimatedTexture';
    return data;

def parse_CMaterialBase(f):
    data = {};
    ver = r_version(f);
    data['Name'] = r_lstring(f);

    data['DefaultAmbient'] = versioned(r_RGBA, f);
    data['DefaultDiffuse'] = versioned(r_RGBA, f);
    data['DefaultSpecular'] = versioned(r_RGBA, f);
    data['DefaultShininess'] = versioned(r_float, f);
    data['DefaultEmissive'] = versioned(r_RGBA, f);
    data['DefaultOpacity'] = versioned(r_float, f);
    data['DefaultTexture'] = versioned(r_int32, f);
    data['_AnimatedTextures'] = parse_map(f, r_uint32, parse_CAnimatedTexture, 'TAnimatedTextureMap');

    if (ver > 0):
        data['DefaultTexAnimTracks'] = [parse_CTexAnimTracks(f) for i in range(IDRV_MAT_MAXTEXTURES)];
    else:
        print("WARNING: parse_CMaterialBase: setting default values of DefaultTexAnimTracks not yet supported!");

    data['NelType'] = 'CMaterialBase';
    return data;

def parse_CMeshBase(f):
    data = {};
    ver = r_version(f);

    # Vector of _AnimatedMorph not yet supported
    if (ver >= 2):
        if (r_int32(f) != 0):
            error("Reading _AnimatedMorph not yet supported");
    if (ver < 1):
        error("Mesh with ver < 1 is too old");

    data['_DefaultPos'] = versioned(r_Vec3f, f);
    data['_DefaultPivot'] = versioned(r_Vec3f, f);
    data['_DefaultRotEuler'] = versioned(r_Vec3f, f);
    data['_DefaultRotQuat'] = versioned(r_Vec4f, f);
    data['_DefaultScale'] = versioned(r_Vec3f, f);
    data['_Materials'] = parse_cont(f, parse_CMaterial);
    data['_AnimatedMaterials'] = parse_map(f, r_uint32, parse_CMaterialBase, 'TAnimatedMaterialMap');

    if (ver >= 8):
        data['_LightInfos'] = parse_cont(f, parse_CLightMapInfoList);
    else:
        data['_LightInfos'] = []
        numLightInfosOld = r_int32(f);
        if (numLightInfosOld > 0):
            error("parse_CMeshBase loading of _LightInfosOld not yet supported");

    data['_IsLightable'] = r_bool(f) if (ver >= 3) else False; # Note: in the orig. code vor ver < 3 this is computed by looking for light-maps in the materials
    
    data['_UseLightingLocalAttenuation'] = r_bool(f) if (ver >= 4) else False;
    data['_AutoAnim'] = r_bool(f) if (ver >= 5) else False;
    data['_DistMax'] = r_float(f) if (ver >= 6) else 0.0;
    if (ver >= 7):
        data['_LodCharacterTexture'] = parse_ptr(f, parse_CLodCharacterTexture);
    
    if (ver >= 9):
        data['_CollisionMeshGeneration'] = r_enum(enum_TCameraCollisionGenerate, f);
    else:
        data['_CollisionMeshGeneration'] = enum_TCameraCollisionGenerate[0];

    data['NelType'] = 'CMeshBase';
    return data;


def parse_CMeshMorpher(f):
    data = {};
    r_version(f);

    data['BlendShapes'] = [];
    numBlendShapes = r_uint32(f);
    if (numBlendShapes > 0):
        error("Reading of BlendShapes in parse_CMeshMorpher not yet implemented!");
    
    data['NelType'] = 'CMeshMorpher';
    return data;


  


enum_CVertexBuffer_TValue = ("Position", "Normal", "TexCoord0", "TexCoord1", "TexCoord2", "TexCoord3", "TexCoord4", "TexCoord5", "TexCoord6", "TexCoord7", "PrimaryColor", "SecondaryColor", "Weight", "PaletteSkin", "Fog", "Empty",);
enum_CVertexBuffer_TPreferredMemory = ("RAMPreferred", "AGPPreferred", "StaticPreferred", "RAMVolatile", "AGPVolatile",);

# Float2 == 4; Float3 == 7; 12 == UChar4; Float4 == 10; Float1 = 1 (See vertex_buffer.cpp line 69)
DefaultValueType = (7, 7, 4, 4, 4, 4, 4, 4, 4, 4, 12, 12, 10, 12, 1, 1);


def parse_VertexData(sizeType, f):
    if sizeType == 0: return (r_double(f),);
    elif sizeType == 1: return (r_float(f),);
    elif sizeType == 2: return (r_int16(f),);
    elif sizeType == 3: return (r_double(f),r_double(f),);
    elif sizeType == 4: return (r_float(f),r_float(f),);
    elif sizeType == 5: return (r_int16(f),r_int16(f),);
    elif sizeType == 6: return (r_double(f),r_double(f),r_double(f),);
    elif sizeType == 7: return (r_float(f),r_float(f),r_float(f),);
    elif sizeType == 8: return (r_int16(f),r_int16(f),r_int16(f),);
    elif sizeType == 9: return (r_double(f),r_double(f),r_double(f),r_double(f),);
    elif sizeType == 10: return (r_float(f),r_float(f),r_float(f),r_float(f),);
    elif sizeType == 11: return (r_int16(f),r_int16(f),r_int16(f),r_int16(f),);
    elif sizeType == 12: return (r_int8(f),r_int8(f),r_int8(f),r_int8(f),);
    else: error("parse_VertexData with invalid SizeType");

# CVertexBuffer::serialHeader(...) '3d/vertex_buffer.cpp'
def read_CVertexBuffer_Header(f, data):
    flags = 0;
    hver = r_version(f);
    if (hver < 1):
        oldFlags = r_uint32(f);
        print("!!TODO: remapping of old flags in CVertexBuffer header ver < 1 not yet implemented! oldFlags = " + str(oldFlags));
        flags = 12295; # !!TODO: hardcoded value for GNU
        data['_Type'] = [DefaultValueType[i] for i in range(len(enum_CVertexBuffer_TValue))];
    else:
        flags = r_uint16(f);
        data['_Type'] = [r_uint8(f) for i in range(len(enum_CVertexBuffer_TValue))];

    data['_NbVerts'] = r_uint32(f);
    data['_Flags'] = flags; # Note: in the orig. code this is set again using addValueEx (with some error checking)
    data['_VertexColorFormat'] = r_uint8(f) if (hver >= 2) else 0; # 0 == TRGBA; 1 == TBGRA

    if (hver >= 3):
        data['_PreferredMemory'] = r_enum(enum_CVertexBuffer_TPreferredMemory, f);
        data['_Name'] = r_lstring(f);
    else:
        data['_PreferredMemory'] = enum_CVertexBuffer_TPreferredMemory[0];
        data['_Name'] = "";


# CVertexBuffer::serialSubset(...) '3d/vertex_buffer.cpp'
def read_CVertexBuffer_Subset(f, vertexStart, vertexEnd, data):
    flags = data['_Flags'];
    data['_VertexData'] = {};
    sver = r_version(f);

    for id in range(vertexStart, vertexEnd):
        for value in range(0, len(enum_CVertexBuffer_TValue)):
            if ((flags & (1 << value)) != 0):
                valueIdx = enum_CVertexBuffer_TValue[value];
                if valueIdx not in data['_VertexData']: 
                    data['_VertexData'][valueIdx] = [];
                data['_VertexData'][valueIdx].append(parse_VertexData(data['_Type'][value], f))

    #print(data['_VertexData'].keys());
    #print(data['_VertexData']['Position']);

    if (sver >= 2):
        data['_UVRouting'] = (r_uint8(f),r_uint8(f),r_uint8(f),r_uint8(f),r_uint8(f),r_uint8(f),r_uint8(f),r_uint8(f));
    else:
        data['_UVRouting'] = (0,1,2,3,4,5,6,7);
    

def parse_CVertexBuffer(f):
    data = {};
    bver = r_version(f);
    if (bver < 2):
        error("Parsing old CVertexBuffer (< 2) not yet implemented!");
    #else
    
    # serialHeader()
    read_CVertexBuffer_Header(f, data);

    # serialSubset(): this reads in all the vertex data as specified by flags
    read_CVertexBuffer_Subset(f, 0, data['_NbVerts'], data);

    data['NelType'] = 'CVertexBuffer';
    return data;
        

def parse_CIndexBuffer(f):
    data = {};

    ver = r_version(f);

    if ver < 1:
        # skip:
        r_uint32(f); r_uint32(f);
        parse_cont(f, r_uint32);
        # read triangles
        data['_NbIndexes'] = r_uint32(f)*3;
        data['_Capacity'] = r_uint32(f)*3;
        data['_NonResidentIndexes'] = parse_cont(f, r_uint32);
        # skip:
        r_uint32(f); r_uint32(f);
        parse_cont(f, r_uint32);
    else: # ver >= 1
        data['_NbIndexes'] = r_uint32(f);
        data['_Capacity'] = r_uint32(f);
        data['_NonResidentIndexes'] = parse_cont(f, r_uint32);
        data['_PreferredMemory'] = r_enum(enum_CVertexBuffer_TPreferredMemory, f);
        if ver == 1: 
            for i in range(len(enum_CVertexBuffer_TPreferredMemory)): r_bool(f);

    data['NelType'] = 'CIndexBuffer';
    return data;


def parse_CMeshVPWindTree(f):
    data = {};
    r_version(f);
    for i in range(3):
        data['Frequency_'+str(i)] = r_float(f);
        data['FrequencyWindFactor_'+str(i)] = r_float(f);
        data['PowerXY_'+str(i)] = r_float(f);
        data['PowerZ_'+str(i)] = r_float(f);
        data['Bias_'+str(i)] = r_float(f);
    data['SpecularLighting'] = r_bool(f);

    data['NelType'] = 'CMeshVPWindTree';
    return data;

#!!TODO: check which CRdrPass this was (there are several defined as subclasses!!
def parse_CRdrPass(f):
    data = {};
    r_version(f);
    data['MaterialId'] = r_uint32(f);
    data['PBlock'] = parse_CIndexBuffer(f);

    data['NelType'] = 'CRdrPass';
    return data;


def parse_CMatrixBlock(f):
    data = {};
    r_version(f);
    data['MatrixId'] = [r_uint32(f) for i in range(16)];
    data['NumMatrix'] = r_uint32(f);
    data['RdrPass'] = parse_cont(f, parse_CRdrPass);

    data['NelType'] = 'CMatrixBlock';
    return data;


def parse_CAABBox(f):
    data = {};
    r_version(f);
    data['Center'] = r_Vec3f(f);
    data['HalfSize'] = r_Vec3f(f);

    data['NelType'] = 'CAABBox';
    return data;

# CMRMWedgeGeom::serial(...) (nel/3d/mrm_mesh.h)
def parse_CMRMWedgeGeom(f):
    data = {};

    data['Start'] = r_uint32(f);
    data['End'] = r_uint32(f);
    
    data['NelType'] = 'CMRMWedgeGeom';
    return data;


#CMeshMRMSkinnedGeom::CPackedVertexBuffer::CPackedVertex::serial
def parse_CMeshMRMSkinnedGeom_CPackedVertexBuffer_CPackedVertex(f):
    data = {};
    r_version(f);

    data['X'] = r_int16(f);
    data['Y'] = r_int16(f);
    data['Z'] = r_int16(f);
    data['Nx'] = r_int16(f);
    data['Ny'] = r_int16(f);
    data['Nz'] = r_int16(f);
    data['U'] = r_int16(f);
    data['V'] = r_int16(f);
    #Matrices and Weights are stored interleaved
    data['Matrices_Weights'] = [(r_uint8(f), r_uint8(f)) for i in range(NL3D_MESH_MRM_SKINNED_MAX_MATRIX)];

    data['NelType'] = 'CMeshMRMSkinnedGeom::CPackedVertexBuffer::CPackedVertex';
    return data;

#CMeshMRMSkinnedGeom::CPackedVertexBuffer::serial(...)
def parse_CMeshMRMSkinnedGeom_CPackedVertexBuffer(f):
    data = {};
    r_version(f);

    data['_PackedBuffer'] = parse_cont(f, parse_CMeshMRMSkinnedGeom_CPackedVertexBuffer_CPackedVertex);
    data['_DecompactScale'] = r_float(f);
    
    data['NelType'] = 'CMeshMRMSkinnedGeom::CPackedVertexBuffer';
    return data;


#CMeshMRMSkinnedGeom::CRdrPass::serial(...) (mesh_mrm_skinned.h)
def parse_CMeshMRMSkinnedGeom_CRdrPass(f):
    data = {};
    r_version(f);

    data['MaterialId'] = r_uint32(f);
    data['PBlock'] = parse_cont(f, r_uint16);

    data['NelType'] = 'CMeshMRMSkinnedGeom::CRdrPass';
    return data;

#CMeshMRMSkinnedGeom::CLod::serial(...) (mesh_mrm_skinned.h)
def parse_CMeshMRMSkinnedGeom_CLod(f):
    data = {};
    r_version(f);

    data['NWedges'] = r_uint32(f);
    data['RdrPass'] = parse_cont(f, parse_CMeshMRMSkinnedGeom_CRdrPass);
    data['Geomorphs'] = parse_cont(f, parse_CMRMWedgeGeom);
    data['MatrixInfluences'] = parse_cont(f, r_uint32);
    data['InfluencedVertices'] = [parse_cont(f, r_uint32) for i in range(NL3D_MESH_SKINNING_MAX_MATRIX)];

    data['NelType'] = 'CMeshMRMSkinnedGeom::CLod';
    return data;

#CShadowVertex::serial(...)  (shadow_skin.h)
def parse_CShadowVertex(f):
    data = {};
    r_version(f);

    data['Vertex'] = r_Vec3f(f);
    data['MatrixId'] = r_uint32(f);

    data['NelType'] = 'CShadowVertex';
    return data;


#CMeshMRMSkinnedGeom::serial
def parse_CMeshMRMSkinnedGeom(f):
    data = {};
    r_version(f);

    data['_BonesName'] = parse_cont(f, r_lstring);

    data['_BBox'] = parse_CAABBox(f);
    data['_LevelDetail.MaxFaceUsed'] = r_uint32(f);
    data['_LevelDetail.MinFaceUsed'] = r_uint32(f);
    data['_LevelDetail.DistanceFinest'] = r_float(f);
    data['_LevelDetail.DistanceMiddle'] = r_float(f);
    data['_LevelDetail.DistanceCoarsest'] = r_float(f);
    data['_LevelDetail.OODistanceDelta'] = r_float(f);
    data['_LevelDetail.DistancePow'] = r_float(f);

    data['_VBufferFinal'] = parse_CMeshMRMSkinnedGeom_CPackedVertexBuffer(f);
    data['_ShadowSkin.Vertices'] = parse_cont(f, parse_CShadowVertex);
    data['_ShadowSkin.Triangles'] = parse_cont(f, r_uint32);

    data['_Lods'] = parse_cont(f, parse_CMeshMRMSkinnedGeom_CLod);

    data['NelType'] = 'CMeshMRMSSkinnedGeom';
    return data;
    

# CMeshMRMGeom::CLodInfo::serial(...) from 'nel/3d/mesh_mrm.h'
def parse_CMeshMRMGeom_CLodInfo(f):
    data = {};
    r_version(f);
    data['StartAddWedge'] = r_uint32(f);
    data['EndAddWedges'] = r_uint32(f);

    data['NelType'] = 'CMeshMRMGeom::CLodInfo';
    return data;

# CMeshMRMGeom::CVertexBlock
def parse_CMeshMRMGeom_CVertexBlock(f):
    # (VertexStart, NVertices)
    return (r_uint32(f), r_uint32(f));
    

def parse_CMeshMRMGeom_CRdrPass(f):
    data = {};
    r_version(f);

    data['MaterialId'] = r_uint32(f);
    data['PBlock'] = parse_CIndexBuffer(f);

    data['NelType'] = 'CMeshMRMGeom::CRdrPass';
    return data;


# CMeshMRMGeom::CLod::serial(NLMISC::IStream &f) from '3d/mesh_mrm.cpp'
def parse_CMeshMRMGeom_CLod(f):
    data = {}
    ver = r_version(f);
    
    data['NWedges'] = r_uint32(f);
    data['RdrPass'] = parse_cont(f, parse_CMeshMRMGeom_CRdrPass);
    data['Geomorphs'] = parse_cont(f, parse_CMRMWedgeGeom);
    data['MatrixInfluences'] = parse_cont(f, r_uint32);
    data['InfluencedVertices'] = [parse_cont(f, r_uint32) for i in range(NL3D_MESH_SKINNING_MAX_MATRIX)];

    print(data['NWedges']);
    
    if (ver >= 1):
        data['SkinVertexBlocks'] = parse_cont(f, parse_CMeshMRMGeom_CVertexBlock);
    else:
        print("WARNING: building SkinVertexBlocks in parse_CMeshMRMGeom_CLod not yet implemented!");

    data['NelType'] = 'CMeshMRMGeom::CLod';
    return data;


# CMeshMRMGeom::serialLodVertexData(NLMISC::IStream &f, uint startWedge, uint endWedge) from '3d/mesh_mrm.cpp'
def read_CMeshMRMGeom_serialLodVertexData(f, startWedge, endWedge, data):
    ver = r_version(f);

    read_CVertexBuffer_Subset(f, startWedge, endWedge, data['_VBufferFinal']);

    if data['_Skinned'] and ver < 1:
        error('Skinned CMeshMRMGeom not yet implemented');
    

# CMeshMRMGeom::load(...) '3d/mesh_mrm.cpp'
def parse_CMeshMRMGeom(f):
    data = {};

    #CMeshMRMGeom::loadHeader(...)
    hver = r_version(f);
    data['_BonesName'] = parse_cont(f, r_lstring) if (hver >= 3) else [];
    data['_MeshVertexProgram'] = parse_PolyPtr(f) if (hver >= 2) else None;
    data['_MeshMorpher'] = parse_CMeshMorpher(f) if (hver >= 1) else None;
    
    data['_Skinned'] = r_bool(f);
    data['_BBox'] = parse_CAABBox(f);
    data['_LevelDetail.MaxFaceUsed'] = r_uint32(f);
    data['_LevelDetail.MinFaceUsed'] = r_uint32(f);
    data['_LevelDetail.DistanceFinest'] = r_float(f);
    data['_LevelDetail.DistanceMiddle'] = r_float(f);
    data['_LevelDetail.DistanceCoarsest'] = r_float(f);
    data['_LevelDetail.OODistanceDelta'] = r_float(f);
    data['_LevelDetail.DistancePow'] = r_float(f);

    data['_LodInfos'] = parse_cont(f, parse_CMeshMRMGeom_CLodInfo);

    nWedges = r_uint32(f);

    data['_VBufferFinal'] = {'NelType':"CVertexBuffer"};
    read_CVertexBuffer_Header(f, data['_VBufferFinal']);

    data['_SkinWeights'] = parse_cont(f, parse_CMesh_CSkinWeight) if (hver >= 4) else [];

    if (hver >= 5):
        data['_ShadowSkin.Vertices'] = parse_cont(f, parse_CShadowVertex);
        data['_ShadowSkin.Triangles'] = parse_cont(f, r_uint32);

    # this computes some absolute offset ?? directly taken from the code; not sure yet what this does
    startPos = f.tell();
    for lodInfo in data['_LodInfos']:
        lodInfo['LodOffset'] = startPos + r_int32(f);

    # finished CMeshMRMGeom::loadHeader(...)

    # next we read all the Lod:
    data['_Lods'] = [];

    for lodInfo in data['_LodInfos']:
        data['_Lods'].append(parse_CMeshMRMGeom_CLod(f));
        read_CMeshMRMGeom_serialLodVertexData(f, lodInfo['StartAddWedge'], lodInfo['EndAddWedges'], data);

    data['NelType'] = 'CMeshMRMGeom';
    return data;

def parse_CMeshGeom(f):
    data = {}
    ver = r_version(f);
    #print(" CMeshGeom ver = %d" % ver);

    data['_BonesName'] = []
    if (ver >= 4):
        numBoneNames = r_uint32(f);
        for i in range(0, numBoneNames):
            data['_BonesName'].append(r_lstring(f));
            print("   read a BoneName: " + str(data['_BonesName'][-1]));

    data['_MeshVertexProgram'] = parse_PolyPtr(f) if (ver >= 3) else None;
    data['_MeshMorpher'] = parse_CMeshMorpher(f) if (ver >= 1) else None;
    data['_VBuffer'] = parse_CVertexBuffer(f);
    data['_MatrixBlocks'] = parse_cont(f, parse_CMatrixBlock);
    data['_BBox'] = parse_CAABBox(f);
    data['_Skinned'] = r_bool(f);
    data['NelType'] = 'CMeshGeom';
    return data;


# CMesh::CSkinWeight::serial(...)
def parse_CMesh_CSkinWeight(f):
    data = {};

    data['MatrixId_Weights'] = [(r_uint32(f), r_float(f)) for i in range(NL3D_MESH_SKINNING_MAX_MATRIX)];

    data['NelType'] = 'CMesh::CSkinWeight';
    return data;


def parse_CMesh(f):
    ver = r_version(f);
    data = parse_CMeshBase(f);
    data['_MeshGeom'] = parse_CMeshGeom(f);

    data['NelType'] = 'CMesh';
    return data;


def parse_CMeshMRMSkinned(f):
    r_version(f);
    data = parse_CMeshBase(f);

    data['_MeshMRMGeom'] = parse_CMeshMRMSkinnedGeom(f);
    data['NelType'] = 'CMeshMRMSkinned';
    return data;
    

# CMeshMRM::serial '3d/mesh_mrm.cpp'
def parse_CMeshMRM(f):
    ver = r_version(f);
    data = parse_CMeshBase(f);
    data['_MeshMRMGeom'] = parse_CMeshMRMGeom(f);

    data['NelType'] = 'CMeshMRM';
    return data;




def parse_CTextureMultiFile(f):
    r_version(f);
    data = parse_ITexture(f);
    data['_FileNames'] = parse_cont(f, r_lstring);
    data['_CurrSelectedTexture'] = r_uint32(f);
    
    data['NelType'] = 'CTextureMultiFile';
    return data;
    

def parse_CMeshSlot(f):
    data = {};
    r_version(f);

    data['MeshGeom'] = parse_PolyPtr(f);
    data['A'] = r_float(f);
    data['B'] = r_float(f);
    data['DistMax'] = r_float(f);
    data['EndPolygonCount'] = r_float(f);
    data['BlendLength'] = r_float(f);
    data['Flags'] = r_uint8(f);

    data['NelType'] = 'CMeshSlot';
    return data;

def parse_CMeshMultiLod(f):
    r_version(f);
    data = parse_CMeshBase(f);
    data['_StaticLod'] = r_bool(f);
    data['_MeshVector'] = parse_cont(f, parse_CMeshSlot);
    
    data['NelType'] = 'CMeshMultiLod';
    return data;



def parse_CBoneBase(f):
    data = {};
    ver = r_version(f);

    data['Name'] = r_lstring(f);

    data['InvBindPos'] = parse_CMatrix(f);
    data['FatherId'] = r_int32(f);
    data['UnheritScale'] = r_bool(f);
    data['LodDisableDistance'] = r_float(f) if ver >= 1 else 0.0;
    data['DefaultPos'] = versioned(r_Vec3f, f);
    data['DefaultRotEuler'] = versioned(r_Vec3f, f);
    data['DefaultRotQuat'] = versioned(r_Vec4f, f);
    data['DefaultScale'] = versioned(r_Vec3f, f);
    data['DefaultPivot'] = versioned(r_Vec3f, f);
    data['SkinScale'] = r_Vec3f(f) if ver >= 2 else (1.0, 1.0, 1.0);

    print("Loaded : "+ data['Name'] + "  DefaultRotQuat = " + str(data['DefaultRotQuat']) );
    
    data['NelType'] = 'CBoneBase';
    return data;


def parse_CSkeletonShapeCLod(f):
    data = {};
    r_version(f);
    data['Distance'] = r_float(f);
    data['ActiveBones'] = parse_cont(f, r_uint8);

    data['NelType'] = 'CSkeletonShapeCLod';
    return data;
   

def parse_CSkeletonShape(f):
    data = {};
    ver = r_version(f);

    data['_Bones'] = parse_cont(f, parse_CBoneBase);
    data['_BoneMap'] = parse_map(f, r_lstring, r_uint32, 'std::map<std::string, uint32>');
    #print(data['_BoneMap']);

    if (ver >= 1):
        data['_Lods'] = parse_cont(f, parse_CSkeletonShapeCLod);
    else:
        print("WARNING: parse_CSkeletonShape for old version (< 1) not yet fully implemented!");
        data['_Lods'] = [{}];
        data['_Lods'][0]['Distance'] = 0;
        #data['_Lods'][0]['ActiveBones'] = ?? !!TODO

    data['NelType'] = 'CSkeletonShape';
    return data;


# implements 'template<class T> class CKey ::serial(...)' from nel/3d/key.h
def parse_CKey(f, Type_ParseFunc):
    r_version(f);
    return Type_ParseFunc(f);

# implements 'template<class T> class CKeyTCB : public CKey<T> ::serial(...)' from nel/3d/key.h
def parse_CKeyTCB(f, Type_ParseFunc):
    r_version(f);
    data = {};
    data['Value'] = Type_ParseFunc(f);
    data['Tension'] = r_float(f);
    data['Continuity'] = r_float(f);
    data['Bias'] = r_float(f);
    data['EaseTo'] = r_float(f);
    data['EaseFrom'] = r_float(f);
    return data;

# implements 'template<class CKeyT> class ITrackKeyFramer::serial' from nel/3d/track_keyframer.h
def parse_ITrackKeyFramer(f, nelCTrackKeyFramer_TypeName, nelKey_TypeName, fCKey_ParseFunc, fKeyType_ParseFunc):
    #print("Called parse_ITrackKeyFramer");
    data = {};

    r_version(f);

    # parse the map of CKey values (specified by Type_ParseFunc for internal data)
    data['NelCKeyType'] = nelKey_TypeName; # this is stored to later identify the values stored in the key map
    data['_MapKey'] = {};
    numElements = r_uint32(f);
    for i in range(numElements):
        key = r_float(f);
        mat = fCKey_ParseFunc(f, fKeyType_ParseFunc);
        data['_MapKey'][key] = mat;

    #print(data['NelCKeyType']);
    #print(data['_MapKey']);

    data['_RangeLock'] = r_bool(f);
    data['_RangeBegin'] = r_float(f);
    data['_RangeEnd'] = r_float(f);
    data['_LoopMode'] = r_bool(f);

    data['NelType'] = nelCTrackKeyFramer_TypeName;
    return data;


# CTrackSampledCommon::CTimeBlock 'nel/3d/track_sampled_common.h'
def parse_CTrackSampledCommon_CTimeBlock(f):
    data = {};
    r_version(f);
    data['TimeOffset'] = r_uint16(f);
    data['KeyOffset'] = r_uint32(f);
    data['Times'] = parse_cont(f, r_uint8);

    data['NelType'] = 'CTrackSampledCommon::CTimeBlock';
    return data;
  
# CQuatPack from 'nel/3d/track_sampled_quat.h'
# Note: we unpack them here already
def parse_CQuatPack(f):
    # x y z w
    x = r_int16(f);
    y = r_int16(f);
    z = r_int16(f);
    w = r_int16(f);
    return unpack_CQuatPack((x, y, z, w));

def unpack_CQuatPack(quatpack):
    bquat = mathutils.Quaternion();
    bquat.x = quatpack[0] * NL3D_OO32767;
    bquat.y = quatpack[1] * NL3D_OO32767;
    bquat.z = quatpack[2] * NL3D_OO32767;
    bquat.w = quatpack[3] * NL3D_OO32767;

    bquat.normalize();
    return bquat;



def _CTrackSampledCommon_serialCommon(f, data):
    # Note: for compatibility with CTrackSampledQuat.serial the r_version is skipped here and expected to be done by the caller
    data['_LoopMode'] = r_bool(f);
    data['_BeginTime'] = r_float(f);
    data['_EndTime'] = r_float(f);
    data['_TotalRange'] = r_float(f);
    data['_OOTotalRange'] = r_float(f);
    data['_DeltaTime'] = r_float(f);
    data['_OODeltaTime'] = r_float(f);
    data['_TimeBlocks'] = parse_cont(f, parse_CTrackSampledCommon_CTimeBlock);

    
# CTrackSampledQuat from 'nel/3d/track_sampled_quat.h'
def parse_CTrackSampledQuat(f):
    data = {};
    ver = r_version(f);
    
    if (ver >= 1): # the code then calls CTrackSampledCommon::serialCommon where the only difference is another serialVersion
        r_version(f);

    _CTrackSampledCommon_serialCommon(f, data);

    # CQuatPack is a class {sint16 x,y,z,w;}
    data['_Keys'] = parse_cont(f, parse_CQuatPack);
        
    data['NelType'] = 'CTrackSampledQuat';
    return data;
    

# CTrackSampledQuat from 'nel/3d/track_sampled_vector.h'
def parse_CTrackSampledVector(f):
    data = {};
    ver = r_version(f);

    r_version(f); # another r_version for the version stored in the 'serialCommon' part of this data
    _CTrackSampledCommon_serialCommon(f, data);

    data['_Keys'] = parse_cont(f, r_Vec3f); #this is an array of CVector

    data['NelType'] = 'CTrackSampledVector';
    return data;

# CSurfaceLightGrid::CCellCorner  'nel/3d/surface_light_grid.h'
def parse_CSurfaceLightGrid_CCellCorner(f):
    data = {};
    ver = r_version(f);
    
    data['LocalAmbientId'] = r_uint8(f) if (ver >= 1) else 0xFF;
    data['SunContribution'] = r_uint8(f);
    data['Light'] = (r_uint8(f), r_uint8(f));

    data['NelType'] = 'CSurfaceLightGrid::CCellCorner';
    return data;

# CSurfaceLightGrid::serial(...) from 'nel/3d/surface_light_grid.cpp'
def parse_CSurfaceLightGrid(f):
    data = {};
    r_version(f);

    data['Origin'] = r_Vec2f(f);
    data['Width'] = r_uint32(f);
    data['Height'] = r_uint32(f);
    data['Cells'] = parse_cont(f, parse_CSurfaceLightGrid_CCellCorner);

    data['NelType'] = 'CSurfaceLightGrid';
    return data;

# CIGSurfaceLight::CRetrieverLightGrid from 'nel/3d/ig_surface_light.h'
def parse_CIGSurfaceLight_CRetrieverLightGrid(f):
    data = {};
    r_version(f);
    
    data['Grids'] = parse_cont(f, parse_CSurfaceLightGrid);

    data['NelType'] = 'CRetrieverLightGrid';
    return data;

# CIGSurfaceLight::serial(...) from 'nel/3d/ig_surface_light.cpp'
def parse_CIGSurfaceLight(f):
    data = {};
    ver = r_version(f);

    data['_CellSize'] = r_float(f);
    data['_OOCellSize'] = r_float(f);

    if (ver < 1):
        data['_RetrieverGridMap'] = parse_map(f, r_lstring, parse_CIGSurfaceLight_CRetrieverLightGrid, 'TRetrieverGridMap'); 
    else:
        data['_RetrieverGridMap'] = parse_map(f, r_uint32, parse_CIGSurfaceLight_CRetrieverLightGrid, 'TRetrieverGridMap'); 

    data['NelType'] = 'CIGSurfaceLight';
    return data;

# CPointLightNamedArray::CPointLightGroup(...) from 'nel/3d/point_light_named_array.h'
def parse_CPointLightNamedArray_CPointLightGroup(f):
    data = {};
    r_version(f);
    data['AnimationLight'] = r_lstring(f);
    data['LightGroup'] = r_uint32(f);
    data['StartId'] = r_uint32(f);
    data['EndId'] = r_uint32(f);

    data['NelType'] = 'CPointLightNamedArray::CPointLightGroup';
    return data;
    


# reads the data from CPointLight into the given data dict (from 'src/3d/point_light.cpp')
def read_CPointLight(f, data):
    ver = r_version(f);

    data['_AddAmbientWithSun'] = r_bool(f) if ver >= 2 else False;
    data['_Type'] = r_enum(enum_CPointLight_TType, f) if ver >= 1 else enum_CPointLight_TType[0];
    data['_SpotDirection'] = r_Vec3f(f) if ver >= 1 else (0,1,0);
    data['_SpotAngleBegin'] = r_float(f) if ver >= 1 else math.pi/4;
    data['_SpotAngleEnd'] = r_float(f) if ver >= 1 else math.pi/2;

    data['_Position'] = r_Vec3f(f);
    data['_Ambient'] = r_RGBA(f);
    data['_Diffuse'] = r_RGBA(f);
    data['_Specular'] = r_RGBA(f);
    data['_AttenuationBegin'] = r_float(f);
    data['_AttenuationEnd'] = r_float(f);


# CPointLightNamed::serial(...) from 'src/3d/point_light_named.cpp'
def parse_CPointLightNamed(f):
    data = {};
    ver = r_version(f);

    read_CPointLight(f, data);

    data['AnimatedLight'] = r_lstring(f);
    data['_DefaultAmbient'] = r_RGBA(f);
    data['_DefaultDiffuse'] = r_RGBA(f);
    data['_DefaultSpecular'] = r_RGBA(f);

    if (ver >= 1):
        data['LightGroup'] = r_uint32(f);

    data['NelType'] = 'CPointLightNamed';
    return data;
    

# CPointLightNamedArray::serial(...) from 'nel/3d/point_light_named_array.h'
def parse_CPointLightNamedArray(f):
    data = {};
    ver = r_version(f);

    data['_PointLights'] = parse_cont(f, parse_CPointLightNamed);

    if ver == 0:
        error("Parsing old CPointLightNamedArray map not yet implemented");
    else:
        data['_PointLightGroupMap'] = parse_cont(f, parse_CPointLightNamedArray_CPointLightGroup);

    data['NelType'] = 'CPointLightNamedArray';
    return data;

# CPortal::serial(...) from 'src/3d/portal.cpp'
def parse_CPortal(f):
    data = {};
    version = r_version(f);

    data['_LocalPoly'] = parse_cont(f, r_Vec3f);
    data['_Name'] = r_lstring(f);

    if (version >= 1):
        data['_OcclusionModelId_str'] = r_lstring(f);
        data['_OpenOcclusionModelId_str'] = r_lstring(f);

    data['NelType'] = 'CPortal';
    return data;

    
# CCluster::serial(...) from 'nel/3d/cluster.cpp'
def parse_CCluster(f):
    data = {};

    version = r_version(f);

    data['Name'] = r_lstring(f) if (version >= 1) else "";
    data['_LocalVolume'] = parse_cont(f, r_Vec4f); # CPlane type (plane.h) (as four floats)
    data['_LocalBBox'] = parse_CAABBox(f);
    data['FatherVisible'] = r_bool(f);
    data['VisibleFromFather'] = r_bool(f);

    if (version >= 2):
        data['_SoundGroupId_str'] = r_lstring(f);
        data['_EnvironmentFxId_str'] = r_lstring(f);

    if (version >= 3):
        data['AudibleFromFather'] = r_bool(f);
        data['FatherAudible'] = r_bool(f);

    data['NelType'] = 'CCluster';
    return data;


# CInstanceGroup::CInstance 'nel/3d/scene_group.h'
def parse_CInstanceGroup_CInstance(f):
    data = {};
    version = r_version(f);

    data['Visible'] = r_bool(f) if version >= 7 else True;
    data['DontCastShadowForExterior'] = r_bool(f) if version >= 6 else False;
    data['DontCastShadowForInterior'] = r_bool(f) if version >= 5 else False;
    data['LocalAmbientId'] = r_uint8(f) if version >= 4 else 0xFF;
    if (version >= 3):
        data['AvoidStaticLightPreCompute'] = r_bool(f);
        data['DontCastShadow'] = r_bool(f);
        data['StaticLightEnabled'] = r_bool(f);
        data['SunContribution'] = r_uint8(f);
        data['Light'] = (r_uint8(f), r_uint8(f));
    if (version >= 2):
        data['InstanceName'] = r_lstring(f);
        data['DontAddToScene'] = r_bool(f);
    if (version >= 1):
        data['Clusters'] = parse_cont(f, r_int32);

    data['Name'] = r_lstring(f);
    data['Pos'] = r_Vec3f(f);
    data['Rot'] = r_Vec4f(f);
    data['Scale'] = r_Vec3f(f);
    data['nParent'] = r_int32(f);

    data['NelType'] = 'CInstanceGroup::CInstance';
    return data;


# CInstanceGroup::serial(...) from 'nel/3d/scene_group.cpp'
def parse_CInstanceGroup(f):
    data = {};
    ver = r_version(f);
    
    data['_RealTimeSunContribution'] = r_bool(f) if ver >= 5 else True;
    data['_IGSurfaceLight'] = parse_CIGSurfaceLight(f) if ver >= 4 else [];
    data['_PointLightArray'] = parse_CPointLightNamedArray(f) if ver >= 3 else [];
    data['_GlobalPos'] = r_Vec3f(f) if ver >= 2 else (0,0,0);

    if (ver >= 1):
        data['_ClusterInfos'] = parse_cont(f, parse_CCluster);
        data['_Portals'] = parse_cont(f, parse_CPortal);

        for i in range(len(data['_ClusterInfos'])):
            nNbPortals = r_uint32(f);
            for j in range(nNbPortals):
                nPortalNb = r_int32(f);
                #!!TODO: actually set the data here (if it is needed); currently ignored


    data['_InstancesInfos'] = parse_cont(f, parse_CInstanceGroup_CInstance);

    data['NelType'] = 'CInstanceGroup';
    return data;


def parse_map(f, key_func, parse_func, typeName):
    data = {};
    numElements = r_uint32(f);

    for i in range(numElements):
        key = key_func(f);
        mat = parse_func(f);
        data[key] = mat;

    data['NelType'] = typeName;
    return data;


def parse_cont(f, parse_func):
    data = [];
    num = r_uint32(f);
    for i in range(0, num):
        data.append(parse_func(f));
    return data;


gStreamIDMap = {}; # stores the loaded 'id's of PolyPtr for one stream !!TODO: encapsulate it into a stream


def parse_ptr(f, parse_func):
    node = r_uint64(f);
    #print("Node in parse_ptr: " + str(node));
    if (node == 0):
        return None;
    if (node in gStreamIDMap):
        return gStreamIDMap[node];

    return parse_func(f);
    

def parse_PolyPtr(f):
    node = r_uint64(f);
    #print('node = %d' % node);
    if (node == 0):
        return None;

    if (node in gStreamIDMap):
        print("FoundSth: " + gStreamIDMap[node]["NelType"]);
        return gStreamIDMap[node];

    className = r_lstring(f);

    if className == 'CMesh':
        gStreamIDMap[node] = parse_CMesh(f);
    elif className == 'CMeshMultiLod':
        gStreamIDMap[node] = parse_CMeshMultiLod(f);
    elif className == 'CMeshMRM':
        gStreamIDMap[node] = parse_CMeshMRM(f);
    elif className == 'CMeshMRMSkinned':
        gStreamIDMap[node] = parse_CMeshMRMSkinned(f);
    elif className == 'CTextureFile':
        gStreamIDMap[node] = parse_CTextureFile(f);
    elif className == 'CTextureMultiFile':
        gStreamIDMap[node] = parse_CTextureMultiFile(f);
    elif className == 'CMeshGeom':
        gStreamIDMap[node] = parse_CMeshGeom(f);
    elif className == 'CMeshVPWindTree':
        gStreamIDMap[node] = parse_CMeshVPWindTree(f);
    elif className == 'CTextureCube':
        gStreamIDMap[node] = parse_CTextureCube(f);
    elif className == 'CSkeletonShape':
        gStreamIDMap[node] = parse_CSkeletonShape(f);

    elif className == 'CTrackSampledQuat':
        gStreamIDMap[node] = parse_CTrackSampledQuat(f);
    elif className == 'CTrackSampledVector':
        gStreamIDMap[node] = parse_CTrackSampledVector(f);

    # Animation Track Classes: see 'nel/3d/track_keyframer.h'
    elif className == 'CTrackKeyFramerLinearQuat':
        gStreamIDMap[node] = parse_ITrackKeyFramer(f, 'CTrackKeyFramerLinearQuat', 'CKeyQuat', parse_CKey, r_Vec4f); # reads quaternions as Vec4f
    elif className == 'CTrackKeyFramerLinearVector':
        gStreamIDMap[node] = parse_ITrackKeyFramer(f, 'CTrackKeyFramerLinearVector', 'CKeyVector', parse_CKey, r_Vec3f);
    elif className == 'CTrackKeyFramerTCBQuat':
        gStreamIDMap[node] = parse_ITrackKeyFramer(f, 'CTrackKeyFramerTCBQuat', 'CKeyTCBQuat', parse_CKeyTCB, r_Vec4f);

    elif className == 'CTrackDefaultVector':
        gStreamIDMap[node] = parse_CTrackDefaultVector(f);
    elif className == 'CTrackDefaultQuat':
        gStreamIDMap[node] = parse_CTrackDefaultQuat(f);

    else:
        error("Unsuported PolyPtr node = " + str(node) + " className = " + str(className));
        return None;

    return gStreamIDMap[node];

# reading in a file where magic == b'NEL_ANIM' and returning a 'CAnimation' data object
def parse_CAnimation(f):
    data = {};

    version = r_version(f);
    data['_Name'] = r_lstring(f);
    data['_IdByName'] = parse_map(f, r_lstring, r_uint32, 'TMapStringUInt'); # this is empty if AnimHeaderCompression is enabled; the required mapping will come from an animation set
    data['_TrackVector'] = parse_cont(f, parse_PolyPtr);

    data['_MinEndTime'] = r_float(f) if version >= 1 else -FLT_MAX;

    if (version >= 2):
        data['_SSSShapes'] = parse_cont(f, r_lstring);

    data['NelType'] = "CAnimation";
    return data;
    


gImageSearchPaths = ['.', '../ryzom_assets_rev2/orig_textures_flat', '../testdata', 'construction', 'newbieland_maps', 'lacustre_maps', 'fauna_maps', 'desert_maps', 'jungle_maps', 'snowballs/maps', 'outgame', 'objects']
    
def findImage(filename, importRootPath):
    filename = filename.lower();
    for path in gImageSearchPaths:
        path = importRootPath + '/' + path + '/';
        fname = filename;
        if not os.path.exists(path+fname):
            fname = filename.replace('.tga', '.dds').replace('.TGA', '.dds');
        if not os.path.exists(path+fname):
            fname = filename.replace('.tga', '.png').replace('.TGA', '.png');
        if not os.path.exists(path+fname):
            continue;

        img = load_image(path+fname);
        if (img): return img;
        else:
            print("ERROR loading image from " + path+fname);
            return None;

    print("WARNING: could not find image texture " + filename);
    return None;


def helper_createAndAddTexture_returnImage(bmat, texFileName, suffixName, importRootPath):
    img = findImage(texFileName, importRootPath);
    if img == None: return None;
    btex = bpy.data.textures.new(texFileName+"_mat_"+suffixName, type='IMAGE')
    btex.image = img;

    img.use_premultiply = True;

    print("Loaded texture: " + texFileName);

    mtex = bmat.texture_slots.add();
    mtex.texture = btex;
    mtex.texture_coords = 'UV'
    mtex.alpha_factor = 1.0;
    mtex.use_map_alpha = True;

    return img;
    


def load_NEL_file(fullFilePath):
    gStreamIDMap.clear(); # clear the node ID cache

    if not os.path.exists(fullFilePath):
        error("Could not load file %r" % fullFilePath);
    name = os.path.basename(fullFilePath);
    f = open(fullFilePath, 'rb');
    
    # read the first 3 'magic' 32 bits
    magic0 = f.read(4);
    magic1 = f.read(4);
    magic2 = f.read(4);
    f.seek(0); # rewind file (since we have to check how long the magic is below

    if magic0 == b'SHAP':
        f.read(4); # skip magic
        meshdata = parse_PolyPtr(f);
        meshdata['NelName'] = name;
        return meshdata;
    elif magic0 == b'NEL_' and magic1 == 'ANIM' and magic2 == b'_SET':
        f.read(12); # skip magic
        error("!!TODO: ANIM_SET not yet implemented");
    elif magic0 == b'NEL_' and magic1 == b'ANIM':
        f.read(8); # skip magic
        animdata = parse_CAnimation(f);
        animdata['NelName'] = name;
        return animdata;
    elif magic0 == b'GRPT':
        f.read(4); # skip magic
        igroup = parse_CInstanceGroup(f);
        igroup['NelName'] = name;
        return igroup;
    else:
        error("Unsupported NEL file format magic = " + str(magic) + "; only 'SHAP' and 'NEL_ANIM' file are currently supported.");
        

    return None;



# this function expects an already generated bmesh and adds the geometry
def convert_CMeshGeom_to_BlenderMesh(bmesh, temp_Geom):
    temp_VData = temp_Geom['_VBuffer']['_VertexData'];
    bmesh.vertices.add(temp_Geom['_VBuffer']['_NbVerts']);
    bmesh.vertices.foreach_set("co", unpack_list(temp_VData['Position']));
    if 'Normal' in temp_VData: bmesh.vertices.foreach_set("normal", unpack_list(temp_VData['Normal']));

    #!!TOOPT: this conversion copies the index data again (which might be slow when batch-importing a huge amount of models)
    temp_AllFace_Idxs = []
    temp_AllFace_MatIds = []
    for matrixBlock in temp_Geom['_MatrixBlocks']:
        for rdrPass in matrixBlock['RdrPass']:
            matId = rdrPass['MaterialId'];
            numIndices = rdrPass['PBlock']['_NbIndexes'];
            for iIdx in range(0, numIndices, 3):
                faceIdxs = (rdrPass['PBlock']['_NonResidentIndexes'][iIdx],rdrPass['PBlock']['_NonResidentIndexes'][iIdx+1],rdrPass['PBlock']['_NonResidentIndexes'][iIdx+2]);
                temp_AllFace_Idxs.append(faceIdxs);
                temp_AllFace_MatIds.append(matId);

    bmesh.tessfaces.add(len(temp_AllFace_Idxs));
    bmesh.tessfaces.foreach_set("vertices_raw", unpack_face_list(temp_AllFace_Idxs));
    bmesh.tessfaces.foreach_set("material_index", temp_AllFace_MatIds);

    if (temp_Geom['_Skinned']):
        print("WARNING: !!TODO: add vertex groups in convert_CMeshGeom_to_BlenderMesh");

    #look for uv's and add them as named uv-sets to the bmesh
    for i in range (8):
        setKey = 'TexCoord'+str(i);
        if setKey in temp_VData:
            bUVLayer = bmesh.tessface_uv_textures.new(setKey);
            vertexUVs = temp_VData[setKey];
            for i, faceIdxs in enumerate(temp_AllFace_Idxs):
                b_texFace = bUVLayer.data[i];
                b_texFace.uv1 = vertexUVs[faceIdxs[0]];
                b_texFace.uv2 = vertexUVs[faceIdxs[1]];
                b_texFace.uv3 = vertexUVs[faceIdxs[2]];

                b_texFace.uv1[1] = 1.0 - b_texFace.uv1[1]
                b_texFace.uv2[1] = 1.0 - b_texFace.uv2[1]
                b_texFace.uv3[1] = 1.0 - b_texFace.uv3[1]

                if (len(bmesh.materials[temp_AllFace_MatIds[i]].texture_slots) > 0):
                    if (bmesh.materials[temp_AllFace_MatIds[i]].texture_slots[0] != None):
                        b_texFace.image = bmesh.materials[temp_AllFace_MatIds[i]].texture_slots[0].texture.image;

    # enddef --convert_CMeshGeom_to_BlenderMesh(bmesh, temp_Geom)--


def convert_CMeshMRMGeom_to_BlenderMesh(bobj, bmesh, nelGeom):
    error("!!TODO: not yet implemented: convert_CMeshMRMGeom_to_BlenderMesh");

    # enddef --def convert_CMeshMRMGeom_to_BlenderMesh(bobj, bmesh, nelGeom)--


# unpacks a CMeshMRMSkinnedGeom::CPackedVertexBuffer into [[Position], [Normal], [UV])
def unpack_CPackedVertexBuffer(packedVB):
    scale = packedVB['_DecompactScale'];
    normalScale = 1.0 / NL3D_MESH_MRM_SKINNED_NORMAL_FACTOR;
    uvScale = 1.0 / NL3D_MESH_MRM_SKINNED_UV_FACTOR;
    weightScale = 1.0 / NL3D_MESH_MRM_SKINNED_WEIGHT_FACTOR;

    packedVertices = packedVB['_PackedBuffer'];
    unpackedVB = {};
    unpackedVB['Postion'] = [ (v['X'] * scale, v['Y'] * scale, v['Z'] * scale) for v in packedVertices];
    unpackedVB['Normal'] = [ (v['Nx'] * normalScale, v['Ny'] *  normalScale, v['Nz'] *  normalScale)  for v in packedVertices];
    unpackedVB['UVs'] = [ (v['U'] * uvScale, v['V'] * uvScale) for v in packedVertices];

    unpackedVB['Matrix'] = [(v['Matrices_Weights'][0][0],
                            v['Matrices_Weights'][1][0],
                            v['Matrices_Weights'][2][0],
                            v['Matrices_Weights'][3][0]) for v in packedVertices];
    unpackedVB['Weight'] = [(v['Matrices_Weights'][0][1] * weightScale,
                            v['Matrices_Weights'][1][1] * weightScale,
                            v['Matrices_Weights'][2][1] * weightScale,
                            v['Matrices_Weights'][3][1] * weightScale) for v in packedVertices];

    return unpackedVB;



def debug_PrintMRMGeomInfo(mrmGeom):
    print(" NumLODs = %d" % len(mrmGeom['_Lods']));

    for i, lod in enumerate(mrmGeom['_Lods']):
        print("  LOD %d " % i);
        print("   Num RdrPass = %d" % len(lod['RdrPass']));
        for rdrPass in lod['RdrPass']:
            print("    NumTris = %d" % (len(rdrPass['PBlock'])/3));
            print("    MaterialID = %d" % rdrPass['MaterialId']);

    lod = mrmGeom['_Lods'][-1];
    
    for rdrPass in lod['RdrPass']:
        #numTris = numTris + len(rdrPass['PBlock'])/3;
        matId = rdrPass['MaterialId'];
        for fIdx in range(0, len(rdrPass['PBlock']), 3):
            faceIdxs = (rdrPass['PBlock'][fIdx+0], rdrPass['PBlock'][fIdx+1], rdrPass['PBlock'][fIdx+2]);
            #print(faceIdxs);
    

# the bobj is used to create the vertex groups
def convert_CMeshMRMSkinnedGeom_to_BlenderMesh(bobj, bmesh, mrmGeom):
    packedVB = mrmGeom['_VBufferFinal'];

    #for lod in mrmGeom['_Lods']: !!TODO: need a plan on how to handle Lod meshes
    lod = mrmGeom['_Lods'][-1];

    geoms = lod['Geomorphs'];

    #applyGeomorph for selected lod using the 'Start' index for the maximum LoD level
    # this data must be preserved if LoD support should be added to the loader
    for i, morph in enumerate(geoms):
        startIdx = morph['Start'];
        endIdx = morph['End'];
        packedVB['_PackedBuffer'][i] = packedVB['_PackedBuffer'][startIdx]; # ????


    unpackedVB = unpack_CPackedVertexBuffer(packedVB);

    temp_AllFace_Idxs = []
    temp_AllFace_MatIds = []

    hack_VertexMap = {}; # maps the nel vertex index to the blender vertex index in temp_AllVertices
    temp_AllVertices = []; # used to store only the vertices that are actually used (?? is this needed ??)
    temp_AllNormals = [];
    temp_AllUVs = [];
    
    for rdrPass in lod['RdrPass']:
        #numTris = numTris + len(rdrPass['PBlock'])/3;
        matId = rdrPass['MaterialId'];
        for fIdx in range(0, len(rdrPass['PBlock']), 3):
            faceIdxs = (rdrPass['PBlock'][fIdx+0], rdrPass['PBlock'][fIdx+1], rdrPass['PBlock'][fIdx+2]);

            idx = [0,0,0];
            for i in range(3):
                if faceIdxs[i] in hack_VertexMap:
                    idx[i] = hack_VertexMap[faceIdxs[i]];
                else:
                    idx[i] = len(temp_AllVertices);
                    hack_VertexMap[faceIdxs[i]] = idx[i];
                    temp_AllVertices.append(unpackedVB['Postion'][faceIdxs[i]]);
                    temp_AllNormals.append(unpackedVB['Normal'][faceIdxs[i]]);
                    temp_AllUVs.append(unpackedVB['UVs'][faceIdxs[i]]);

                    if (temp_AllVertices[-1] == (0, 0, 0)):
                        print("%d <== %d" % (idx[i], faceIdxs[i]));
            
            temp_AllFace_Idxs.append((idx[0], idx[1], idx[2]));
            temp_AllFace_MatIds.append(matId);


    bmesh.vertices.add(len(temp_AllVertices));
    bmesh.vertices.foreach_set("co", unpack_list(temp_AllVertices));
    bmesh.vertices.foreach_set("normal", unpack_list(temp_AllNormals));

    bmesh.tessfaces.add(len(temp_AllFace_Idxs));
    bmesh.tessfaces.foreach_set("vertices_raw", unpack_face_list(temp_AllFace_Idxs));
    bmesh.tessfaces.foreach_set("material_index", temp_AllFace_MatIds);

    bUVLayer = bmesh.tessface_uv_textures.new("uv0");
    for i, faceIdxs in enumerate(temp_AllFace_Idxs):
        b_texFace = bUVLayer.data[i];
        b_texFace.uv1 = temp_AllUVs[faceIdxs[0]];
        b_texFace.uv2 = temp_AllUVs[faceIdxs[1]];
        b_texFace.uv3 = temp_AllUVs[faceIdxs[2]];

        b_texFace.uv1[1] = 1.0 - b_texFace.uv1[1]
        b_texFace.uv2[1] = 1.0 - b_texFace.uv2[1]
        b_texFace.uv3[1] = 1.0 - b_texFace.uv3[1]

        # This is more or less a hack to assign the first loaded image in a material to each face
        # so it is visible in blender
        if (len(bmesh.materials[temp_AllFace_MatIds[i]].texture_slots) > 0):
            b_texFace.image = bmesh.materials[temp_AllFace_MatIds[i]].texture_slots[0].texture.image;



    vgroups = [];
    # now we create the vertex groups named with the '_BonesName' array from the nel mrmGeom:
    for boneName in mrmGeom['_BonesName']:
        print(boneName);
        vgroups.append(bobj.vertex_groups.new(boneName));

    
    for nelIdx, bIdx in hack_VertexMap.items():
        nelVertexMatrix = unpackedVB['Matrix'][nelIdx];
        nelVertexWeight = unpackedVB['Weight'][nelIdx];
        for i, w in enumerate(nelVertexWeight):
            if (w != 0):
                vgroupIdx = nelVertexMatrix[i];
                vgroups[vgroupIdx].add([bIdx], w, 'ADD');
                

    return;
    error("Not yet implemented");
    
    



def convert_NelMesh_to_BlenderObject(meshdata, importRootPath):
    name = meshdata['NelName'];
    bmesh = bpy.data.meshes.new(name);

    # convert the materials !!TODO: lots of parameters are not yet added/implemented
    for i, mat in enumerate(meshdata['_Materials']):
        # all keys in mat: ['_Specular', '_ShaderType', '_DstBlend', '_AlphaTestThreshold', '_Textures', '_ZFunction', '_TexAddrMode', '_LightMapsMulx2', '_TexCoordGenMode, '_TexEnvs', '_Shininess', '_ZBias', '_Color', '_TexUserMat', '_Ambient', '_Flags', '_Emissive', '_SrcBlend', '_LightMaps', '_Diffuse'])

        bmat = bpy.data.materials.new(name+"_mat"+str(i));
        
        #!!TODO: what is '_Color' what is '_Diffuse' ??
        #!!Note: alpha and specular_alpha are currently ignored here
        bmat.diffuse_color = [x / 255.0 for x in mat['_Color'][:3]];
        bmat.specular_color = [x / 255.0 for x in mat['_Specular'][:3]];
        bmat.specular_hardness = mat['_Shininess']; #!!TODO: this needs a propper conversion; bmat.specular_hardness is in int[0..511] the mat['_Shininess'] is a float

        for tex in mat['_Textures']:
            if tex != None and '_FileName' in tex:
                texFileName = tex['_FileName'];
                helper_createAndAddTexture_returnImage(bmat, texFileName, str(i), importRootPath);
            elif tex != None and '_FileNames' in tex:
                for texNum, texFileName in enumerate(tex['_FileNames']):
                    helper_createAndAddTexture_returnImage(bmat, texFileName, str(i)+"_"+str(texNum), importRootPath);
            elif tex != None:
                print("WARNING !!TODO: Texture without '_Filename': NelType = " + tex['NelType']);
                #print(tex);
                

        #print(mat['_SrcBlend']);
        #print(mat['_DstBlend']);
        #print(mat['_AlphaTestThreshold']);
        #print("");

        if (mat['_SrcBlend'] == 'one'):        
            # Settings for nicer preview; !!TODO: this should depend on the texture??
            bmat.game_settings.alpha_blend = "ALPHA";
            bmat.game_settings.use_backface_culling = False;

            # Settings to render alphaclipping
            bmat.alpha = 0.0;
            bmat.use_transparency = True;
            bmat.use_transparent_shadows = True;

        bmesh.materials.append(bmat);


    # create the blender object
    bobj = bpy.data.objects.new(name, bmesh);

    # convert the vertex data and faces and store them in the bmesh 

    if '_MeshGeom' in meshdata:
        temp_Geom = meshdata['_MeshGeom'];
        convert_CMeshGeom_to_BlenderMesh(bmesh, temp_Geom);
    elif '_MeshVector' in meshdata:
        temp_Geom = meshdata['_MeshVector'][0]['MeshGeom']; # first? lod
        convert_CMeshGeom_to_BlenderMesh(bmesh, temp_Geom);
    elif meshdata['NelType'] == 'CMeshMRMSkinned':
        convert_CMeshMRMSkinnedGeom_to_BlenderMesh(bobj, bmesh, meshdata['_MeshMRMGeom']);
    elif meshdata['NelType'] == 'CMeshMRM':
        convert_CMeshMRMGeom_to_BlenderMesh(bobj, bmesh, meshdata['_MeshMRMGeom']);
    else:
        error("No Geometry found in loaded shape file " + name + " Type is " + meshdata['NelType']);
    

    # add the blender object to the current blender scene
    bscene =  bpy.context.scene;
    bscene.objects.link(bobj);
    bscene.update();

    #bscene.objects.active = bobj;
    #bpy.ops.object.shade_smooth();

    return bobj;
  
    #--enddef convert_NelMesh_to_BlenderObject(meshdata)--


def convert_NelSkeleton_to_BlenderArmature(skeleton):
    if skeleton['NelType'] != 'CSkeletonShape':
        error("convert_NelSkeleton_to_BlenderArmature: Invalid NelType given: " + str(skeleton['NelType']));

    name = skeleton['NelName'];

    barmature = bpy.data.armatures.new(name);
    bobj = bpy.data.objects.new(name, barmature);

    bscene =  bpy.context.scene;
    bscene.objects.link(bobj);
    bscene.objects.active = bobj;
    bpy.ops.object.mode_set(mode='EDIT');
   
    bbonelist = [barmature.edit_bones.new(nbone['Name']) for nbone in skeleton['_Bones']];

    for bbone, nbone in zip(bbonelist, skeleton['_Bones']):
        if (nbone['UnheritScale']): #!!TODO: this error only affects animation loading; so it should be moved there
            print("WARNING: Bone UnheritScale not yet implemented! (in bone '"+bbone.name+"')");

        bbone.parent = bbonelist[nbone['FatherId']] if nbone['FatherId'] >= 0 else None;

        #!!TODO: need to understand how to handle inv bind position and the Default* stored in the skeleton
        # animation data seems to be absolute to the Default* matrix

        worldTM = nbone['InvBindPos']['M'].inverted();
        #worldTM = helper_Nel_get_LocalSkeletonMatrix_Recursive(nbone, skeleton);
        #worldTM = mathutils.Matrix.Identity(4);

        print (bbone.head);
        print (bbone.tail);

        v0 = mathutils.Vector((0,0,0,1));
        v1 = mathutils.Vector((0,0,0.25,1));

        bbone.head = (worldTM * v0).to_3d();
        bbone.tail = (worldTM * v1).to_3d(); # ??

    for bbone in bbonelist:
        if (bbone.parent != None):
            bbone.parent.tail = bbone.head; # ??
            #bbone.use_connect = True;
            
    bpy.ops.object.mode_set(mode='OBJECT');

    bscene.update();

    return bobj
    
    #--enddef convert_NelSkeleton_to_BlenderArmature(skeleton)--


def getDefRot_Recursive(boneName, nelSkeleton):
    nelBone = nelSkeleton['_Bones'][nelSkeleton['_BoneMap'][boneName]];

    bMat = mathutils.Quaternion((-nelBone['DefaultRotQuat'][3], 
                                 nelBone['DefaultRotQuat'][0],
                                 nelBone['DefaultRotQuat'][1],
                                 nelBone['DefaultRotQuat'][2])).to_matrix();

    return bMat;
    if (nelBone['FatherId'] == -1):
        return bMat;

    parentMat = getDefRot_Recursive(nelSkeleton['_Bones'][nelBone['FatherId']]['Name'], nelSkeleton);

    return parentMat * bMat;


def getBindTrafo_Recursive(boneName, nelSkeleton):
    nelBone = nelSkeleton['_Bones'][nelSkeleton['_BoneMap'][boneName]];
    
    #print(nelBone['InvBindPos']['M']);
    bMat = nelBone['InvBindPos']['M'];


    if (nelBone['FatherId'] == -1):
        print(boneName);
        print(bMat);
        return bMat;

    parentMat = getBindTrafo_Recursive(nelSkeleton['_Bones'][nelBone['FatherId']]['Name'], nelSkeleton);

    print(boneName);
    print(bMat);
    print("");

    return bMat * parentMat;

                                   
# this is to experiment and understand how to transform the nel anim curves to a coord system used in blender
# my current unterstanding is: it has to convert the given key quat (x, y, z, w) to
#                              a local rotation by applying the inverse default ??
def temp_helper_KeyQuatToBlenderFCurveQuat(nelBone, nelSkeleton, x, y, z, w):
    keyQuat = mathutils.Quaternion((w, x, y, z));

    invLocalMat = helper_Nel_CBone_GetMatix(nelBone).to_3x3().inverted();

    # hmm; how to get the animation relative to the BindPosition
    #bp = nelBone['InvBindPos']['M'].to_3x3();
    #lp = helper_Nel_get_LocalSkeletonMatrix_Recursive(nelBone, nelSkeleton).to_3x3();
    #keyQuat = (lp * bp * invLocalMat * keyQuat.to_matrix()).to_quaternion();

    #keyQuat = (invLocalMat * kekeyQuat = (bp * lp * invLocalMat * keyQuat.to_matrix()).to_quaternion();yQuat.to_matrix()).to_quaternion();

    return keyQuat;



def helper_convertNelTrackToBlenderRotationFCurves(baction, bbone, nelTrackData, nelBone, nelSkeleton):
    groupName = bbone.name;
    rotDataPath = 'pose.bones["%s"].rotation_quaternion'%bbone.name;

    #if isinstance(nelTrackData, dict):
    #    return;
    #print("    " + str(type(nelTrackData)));
    #print(bbone.name+":");

    qw = baction.fcurves.new(rotDataPath, 0, (groupName));
    qx = baction.fcurves.new(rotDataPath, 1, (groupName));
    qy = baction.fcurves.new(rotDataPath, 2, (groupName));
    qz = baction.fcurves.new(rotDataPath, 3, (groupName));

    #--------------------------------------------------------------------------------
    if isinstance(nelTrackData, tuple): # a plain tuple (?? constant?? !!TODO: check what this actually means to nel)
        frame = 0;
        keyQuat = temp_helper_KeyQuatToBlenderFCurveQuat(nelBone, nelSkeleton, nelTrackData[0], nelTrackData[1], nelTrackData[2], nelTrackData[3]);

        qx.keyframe_points.insert(frame, keyQuat.x);
        qy.keyframe_points.insert(frame, keyQuat.y);
        qz.keyframe_points.insert(frame, keyQuat.z);
        qw.keyframe_points.insert(frame, keyQuat.w);
        #print("  quat: %f %f %f %f" % (x, y, z, w));
    #--------------------------------------------------------------------------------
    elif isinstance(nelTrackData, dict):
        frame = 0;
        if nelTrackData['NelType'] == 'CTrackSampledQuat':
            #nelTrackData['_LoopMode']
            startTime = nelTrackData['_BeginTime'];
            endTime = nelTrackData['_EndTime'];
            keyFrames = nelTrackData['_Keys'];

            for idx, key in enumerate(keyFrames):
                frame = 60 * (startTime + (idx*(endTime-startTime))/len(keyFrames));
                
                keyQuat = temp_helper_KeyQuatToBlenderFCurveQuat(nelBone, nelSkeleton, key[1], key[2], key[3], key[0]);
                        
                qx.keyframe_points.insert(frame, keyQuat.x);
                qy.keyframe_points.insert(frame, keyQuat.y);
                qz.keyframe_points.insert(frame, keyQuat.z);
                qw.keyframe_points.insert(frame, keyQuat.w);
        elif nelTrackData['NelType'] == 'CTrackKeyFramerTCBQuat':
            startTime = nelTrackData['_RangeBegin'];
            endTime = nelTrackData['_RangeEnd'];
            keyFrames = nelTrackData['_MapKey'];
            # !!TODO: not yet implemented... 
            error("CTrackKeyFramerTCBQuat not yet implemented for FCurve conversion");
            for idx, key in enumerate(sorted(keyFrames.keys())):
                frame = 60 * (startTime + key);
                nquat = keyFrames[key]['Value'];
                print(str(key) + ": " + str(nquat));
            print("");
        else:
            error("Unsupported rotation track dict of type = " + nelTrackData['NelType']);
    #--------------------------------------------------------------------------------
    else:
        error("Got an unsupported nelTrackData in helper_convertNelTrackToBlenderRotationFCurves");

def helper_convertNelTrackToBlenderPositionFCurves(baction, bbone, nelTrackData):
    return;
    groupName = bbone.name;
    posDataPath = 'pose.bones["%s"].location'%bbone.name
    px = baction.fcurves.new(posDataPath, 0, (groupName));
    py = baction.fcurves.new(posDataPath, 1, (groupName));
    pz = baction.fcurves.new(posDataPath, 2, (groupName));

    if isinstance(nelTrackData, tuple): # a plain tuple (?? constant?? !!TODO: check what this actually means to nel)
        frame = 0;
        #print(nelTrackData);
        x = nelTrackData[0];
        y = nelTrackData[1];
        z = nelTrackData[2];
        px.keyframe_points.insert(frame, x);
        py.keyframe_points.insert(frame, y);
        pz.keyframe_points.insert(frame, z);
        print("  vec : %f %f %f" % (x, y, z));
    elif isinstance(nelTrackData, dict):
        frame = 0;
        if nelTrackData['NelType'] == 'CTrackSampledVector':
            #nelTrackData['_LoopMode']
            startTime = nelTrackData['_BeginTime'];
            endTime = nelTrackData['_EndTime'];
            keyFrames = nelTrackData['_Keys'];

            for idx, key in enumerate(keyFrames):
                frame = 60 * (startTime + (idx*(endTime-startTime))/len(keyFrames));
                x = key[0];
                y = key[1];
                z = key[2];
                if (idx == 0):
                    print("  vec : %f %f %f" % (x, y, z));
        
                px.keyframe_points.insert(frame, x);
                py.keyframe_points.insert(frame, y);
                pz.keyframe_points.insert(frame, z);


        else:
            error("Unsupported position track dict of type = " + nelTrackData['NelType']);
    else:
        error("Got an unsupported nelTrackData in helper_convertNelTrackToBlenderPositionFCurves");

    
    


def helper_ConvertBoneTrackMap_To_FCurvesInAction(boneTrackMap, baction, nelSkeleton):
    for bbone in boneTrackMap.keys():
        nelBone = nelSkeleton['_Bones'][nelSkeleton['_BoneMap'][bbone.name]];

        #print(bbone.name);
        for track in boneTrackMap[bbone]:
            trackName = track[0];
            trackData = track[1];

            print(trackName + ":"); # the track name;

            if trackName.endswith('rotquat'):
                helper_convertNelTrackToBlenderRotationFCurves(baction, bbone, trackData, nelBone, nelSkeleton);
            elif trackName.endswith('pos'):
                helper_convertNelTrackToBlenderPositionFCurves(baction, bbone, trackData);



def convert_NelAnimation_to_BlenderAction(animdata, nelSkeleton, bobj):
    # some very early experiments:
    if (animdata['NelType'] != "CAnimation"):
        error("convert_NelAnimation_to_BlenderAction got unsupported type: " + animdata['NelType']);

    actionName = animdata['NelName'];
    print("NelName = " + actionName);


    #for name, i in animdata['_IdByName'].items():
        #print(str(i) + ":  " + name);
    #print(animdata['_TrackVector'][2]['NelCKeyType']);

    #for name, trackID in animdata['_IdByName'].items():
    #    print(animdata['_TrackVector'][trackID]['NelType']);
    #error('blub');

    bscene = bpy.context.scene;
    bscene.objects.active = bobj;

    barmature = bobj.data;

    baction = bpy.data.actions.new(actionName);


    boneTrackMap = {};

    # we now go through all tracks, try to find the associated bone (by name) in the bobj
    # and store it in the 'boneTrackMap' to later convert it
    for trackName, trackID in animdata['_IdByName'].items():
        if trackName == 'NelType': continue; # skip our own typename we added to the map

        if (trackName.find('.') != -1):
            [boneName, type] = trackName.split('.', 2);
            #print(str(i) + ":  " + boneName);
            if boneName not in bobj.pose.bones:
                print("Warning: bone with name '"+boneName+"' not found in given blender object " + str(bobj.name));
            else:
                bone = bobj.pose.bones[boneName];

                if bone not in boneTrackMap:
                    boneTrackMap[bone] = [];

                track = animdata['_TrackVector'][trackID];

                #print(track);

                #if not isinstance(track, dict):
                #    print("WARNING: track with name '" + name + "' is not a dict");
                #    # this might be a static position !!TODO: needs more research; currently ignored
                #    continue;

                boneTrackMap[bone].append((trackName, track));

                #if track['NelCKeyType'] == 'CKeyQuat':
                #    boneTrackMap[bone][0] = track;
                #elif track['NelCKeyType'] == 'CKeyVector':
                #    boneTrackMap[bone][1] = track;
                #else:
                #    error("Unsupported track type '"+track['NelCKeyType']+"' in animation conversion for bone '"+bone.name+"'");

        else:
            #!!TODO: probably no valid bone or it is for the root?? (not yet sure...)
            print("Warning: probably invalid bone: _IdByName is : '" + trackName + "' for trackID " + str(trackID) + " or it is the global model transform... !!TODO: check");

    # now boneTrackMap contains all the data and next we convert it into actual fcurves
    # 
    helper_ConvertBoneTrackMap_To_FCurvesInAction(boneTrackMap, baction, nelSkeleton);


    if bobj.animation_data == None:
        bobj.animation_data_create();
    bobj.animation_data.action = baction; 

    #--enddef convert_NelAnimation_to_BlenderAction(animdata)--

    
def connectBlenderSkeleton_To_BlenderMeshObject(bSkeletonObj, bMeshObj):
    armatureMod = bMeshObj.modifiers.new(type='ARMATURE',name='Armature');
    armatureMod.use_bone_envelopes = False;
    armatureMod.use_vertex_groups = True;
    armatureMod.object = bSkeletonObj;


# _LocalMatrix that is computed from the DefaultPos/Quat/Pivot/  (Scale is currently missing)
def helper_Nel_CBone_GetMatix(nelBone):
    nelDefRotQuat = nelBone['DefaultRotQuat'];
    x = nelDefRotQuat[0];
    y = nelDefRotQuat[1];
    z = nelDefRotQuat[2];
    w = nelDefRotQuat[3];
    bquat = mathutils.Quaternion((w, x, y, z));

    # getMatrix(); as stored in _LocalMatrix
    nelPos = mathutils.Vector(nelBone['DefaultPos']);
    nelPivot = mathutils.Vector(nelBone['DefaultPivot']);
    nelScale = mathutils.Vector(nelBone['DefaultScale']);
    _LocalMatrix = mathutils.Matrix.Translation(nelPos + nelPivot);
    _LocalMatrix = _LocalMatrix * mathutils.Quaternion((w, x, y, z)).to_matrix().to_4x4();
    #_LocalMatrix = _LocalMatrix * mathutils.Matrix.Scale(nelScale);
    _LocalMatrix = _LocalMatrix * mathutils.Matrix.Translation(-nelPivot);

    return _LocalMatrix;


def helper_Nel_get_LocalSkeletonMatrix_Recursive(nelBone, nelSkeleton):
    _LocalMatrix = helper_Nel_CBone_GetMatix(nelBone);
    if (nelBone['FatherId'] == -1):
        return _LocalMatrix;

    parentNelBone = nelSkeleton['_Bones'][nelBone['FatherId']];
    parentMatrix = helper_Nel_get_LocalSkeletonMatrix_Recursive(parentNelBone, nelSkeleton);
    return parentMatrix * _LocalMatrix;

    
# Note; !!TODO: all 'scale' is completely ignore currently
def debug_ApplyDefaultPosRot_AsPose(nelSkeleton, bSkeletonObj):

    #barmature = bSkeletonObj.data;
    #bpy.context.scene.objects.active = bSkeletonObj;
    #bpy.ops.object.mode_set(mode='POSE');

    for nelBone in nelSkeleton['_Bones']:
        if nelBone['Name'] not in bSkeletonObj.pose.bones:
            print("'" + nelBone['Name'] + "' not found");
            continue;
            
        bbone = bSkeletonObj.pose.bones[nelBone['Name']];
        print(bbone.name + ": ");

        _LocalMatrix = helper_Nel_CBone_GetMatix(nelBone); # !!checked!!ok
        _BoneBase_InvBindPos = nelBone['InvBindPos']['M']; # !!checked!!ok
        _LocalSkeletonMatrix = helper_Nel_get_LocalSkeletonMatrix_Recursive(nelBone, nelSkeleton); # !!checked!!ok
        _BoneSkinMatrix = _LocalSkeletonMatrix * _BoneBase_InvBindPos; # !!checked!!ok

        #print(_LocalMatrix.transposed());
        #print(_BoneBase_InvBindPos.transposed());
        #print(_LocalSkeletonMatrix.transposed());
        #print(_BoneSkinMatrix.transposed());

        #bbone.matrix = # ?? Final 4x4 matrix after constraints and drivers are applied (object space)
        #bbone.matrix_basis = # ?? Alternative access to location/scale/rotation relative to the parent and own rest bone
        #bbone.matrix_channel = # ?? 4x4 matrix, before constraints

    #bpy.ops.object.mode_set(mode='OBJECT');

    return;



def helper_Nel_CBone_GetLocalRotationOnlyMatix(nelBone):
    nelDefRotQuat = nelBone['DefaultRotQuat'];
    x = nelDefRotQuat[0];
    y = nelDefRotQuat[1];
    z = nelDefRotQuat[2];
    w = nelDefRotQuat[3];

    _LocalRotMatrix =  mathutils.Quaternion((w, x, y, z)).to_matrix().to_4x4();

    return _LocalRotMatrix;


def getParentInvBindPos(nelBone, nelSkeleton):
    if (nelBone['FatherId'] == -1):
        return mathutils.Matrix.Identity(4);
    else:
        return nelSkeleton['_Bones'][nelBone['FatherId']]['InvBindPos']['M'];
    

def debug_CreateDefaultBoneTracks(nelSkeleton, bSkeletonObj):
    
    for nelBone in nelSkeleton['_Bones']:
        if nelBone['Name'] not in bSkeletonObj.pose.bones:
            print("'" + nelBone['Name'] + "' not found");
            continue;
            
        bbone = bSkeletonObj.pose.bones[nelBone['Name']];

        _LocalMatrix = helper_Nel_CBone_GetMatix(nelBone); # !!checked!!ok
        _BoneBase_InvBindPos = nelBone['InvBindPos']['M']; # !!checked!!ok
        _LocalSkeletonMatrix = helper_Nel_get_LocalSkeletonMatrix_Recursive(nelBone, nelSkeleton); # !!checked!!ok
        _BoneSkinMatrix = _LocalSkeletonMatrix * _BoneBase_InvBindPos; # !!checked!!ok

        print("===============================================");
        print(bbone.name);

        parentInvBP = getParentInvBindPos(nelBone, nelSkeleton);

        localBP = _BoneBase_InvBindPos.inverted() * parentInvBP; # ????

        #print(localBP.to_3x3());

        #print(_LocalMatrix.to_3x3());

        #if bbone.name == 'Bip01':
        #print(localBP);
        #bbone.matrix_basis = localBP.to_3x3().to_4x4();

        print(_BoneBase_InvBindPos * bbone.matrix );
        #print(_BoneBase_InvBindPos.inverted());

        #bbone.matrix_basis = localBP.inverted().to_3x3().to_4x4();

        #print(_BoneBase_InvBindPos.inverted().to_3x3());
        #print(_LocalSkeletonMatrix);
        #print(_LocalMatrix.to_3x3());
        #print(_BoneBase_InvBindPos.to_3x3());
        
        #print(bbone.matrix);
        #print(_BoneBase_InvBindPos.inverted().to_3x3().to_4x4());
        #print(_BoneBase_InvBindPos);
        #print(_BoneBase_InvBindPos.inverted().to_3x3());
        #print(_LocalMatrix.to_3x3());
        #_LocalSkeletonMatrix = helper_Nel_get_LocalSkeletonMatrix_Recursive(nelBone, nelSkeleton); # !!checked!!ok

        
        print("===============================================");

        #bbone.matrix_basis = _LocalMatrix.to_3x3().inverted().to_4x4();

        #bbone.matrix = _LocalSkeletonMatrix;


    return;



# !!TODO: a very very early test
def convert_NelInstanceGroup_to_Blender(nelIG, rootPath):
    print("WARNING: convert_NelInstanceGroup_to_Blender is just an early test");
    
    globalCenter = mathutils.Vector((0,0,0));
    allBObjs = [];

    for nelInstance in nelIG['_InstancesInfos']:
        fname = rootPath + nelInstance['Name'] + ".shape";
        if os.path.exists(fname):
            print('Trying to load ' + fname);
            nelMesh = load_NEL_file(fname);
            # !!TODO: find an easy way of instancing meshes (probably need to split the convert_NelMesh_to_BlenderObject method
            try:
                bMeshObj = convert_NelMesh_to_BlenderObject(nelMesh, rootPath);
            except:
                print("Excpetion thrown while loading file: ");
                continue;

            allBObjs.append(bMeshObj);

            position = mathutils.Vector(nelInstance['Pos']);
            scale = mathutils.Vector(nelInstance['Scale']);
            rotation = mathutils.Quaternion((-nelInstance['Rot'][3], nelInstance['Rot'][0], nelInstance['Rot'][1], nelInstance['Rot'][2]));

            scaleMat = mathutils.Matrix.Identity(4);
            scaleMat[0][0] = scale[0];
            scaleMat[1][1] = scale[1];
            scaleMat[2][2] = scale[2];

            bMeshObj.matrix_basis = rotation.to_matrix().to_4x4() * scaleMat * mathutils.Matrix.Translation(position);

            globalCenter = globalCenter + position;

    globalCenter = globalCenter / len(allBObjs);

    # test: re-center all loaded objects around average
    for bMeshObj in allBObjs:
        bMeshObj.matrix_basis = bMeshObj.matrix_basis * mathutils.Matrix.Translation(-globalCenter);

    print(globalCenter);


from bpy.props import StringProperty, BoolProperty

class IMPORT_OT_NeL(bpy.types.Operator):
    '''Import NeL 3D Operator.'''
    bl_idname= "import_scene.nel3d_shape"
    bl_label= "Import NeL 3D"
    bl_description= "Import a NeL 3D shape file"
    bl_options= {'REGISTER', 'UNDO'}

    filepath= StringProperty(name="File Path", description="Filepath used for importing the NeL 3D file", maxlen=1024, default="")

    def execute(self, context):
        fileRootPath = os.path.dirname(self.filepath);
        print(gFileRootPath);
        print();
        nelMesh = load_NEL_file(self.filepath);
        bMeshObj = convert_NelMesh_to_BlenderObject(nelMesh, fileRootPath);
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


def menu_func(self, context):
    self.layout.operator(IMPORT_OT_NeL.bl_idname, text="NeL 3D (.shape)")


def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func)


# comment these two lines when using the script from the script editor
if __name__ == "__main__":
    register()

#===============================================================================

#gFileRootPath = "d:/programming/data/ryzom/flat_unpacked_data/"
gFileRootPath = "e:/ryzom/data/flat/"
#gSkeletonFileName = "tr_mo_clapclap.skel"
#gShapeFileName = "FO_S2_big_tree.shape"
#gShapeFileName = "ge_mission_capsule.shape"
#gShapeFileName = "GE_Mission_oeuf_kitin.shape";

#nelSkeleton = load_NEL_file(gFileRootPath+gSkeletonFileName);
#bSkeletonObj = convert_NelSkeleton_to_BlenderArmature(nelSkeleton);
#debug_CreateDefaultBoneTracks(nelSkeleton, bSkeletonObj);

#nelMesh = load_NEL_file(gFileRootPath+gShapeFileName);
#bMeshObj = convert_NelMesh_to_BlenderObject(nelMesh, gFileRootPath);



           

