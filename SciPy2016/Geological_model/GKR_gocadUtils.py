#%%
from SimPEG import np, Mesh
import SimPEG as simpeg
import time as tm
import vtk, vtk.util.numpy_support as npsup
import re, sys, os

def read_GOCAD_ts(tsfile):
    """Read GOCAD triangulated surface (*.ts) file
    INPUT:
    tsfile: Triangulated surface

    OUTPUT:
    vrts : Array of vertices in XYZ coordinates [n x 3]
    trgl : Array of index for triangles [m x 3]. The order of the vertices
            is important and describes the normal
            n = cross( (P2 - P1 ) , (P3 - P1) )


    Created on Jan 13th, 2016

    Author: @fourndo
    """


    fid = open(tsfile,'r')
    line = fid.readline()

    # Skip all the lines until the vertices
    while re.match('TFACE',line)==None:
        line = fid.readline()

    line = fid.readline()
    vrtx = []

    # Run down all the vertices and save in array
    while re.match('VRTX',line):
        l_input  = re.split('[\s*]',line)
        temp = np.array(l_input[2:5])
        vrtx.append(temp.astype(np.float))

        # Read next line
        line = fid.readline()

    vrtx = np.asarray(vrtx)

    # Skip lines to the triangles
    while re.match('TRGL',line)==None:
        line = fid.readline()

    # Run down the list of triangles
    trgl = []

    # Run down all the vertices and save in array
    while re.match('TRGL',line):
        l_input  = re.split('[\s*]',line)
        temp = np.array(l_input[1:4])
        trgl.append(temp.astype(np.int))

        # Read next line
        line = fid.readline()

    trgl = np.asarray(trgl)

    return vrtx, trgl

def gocad2vtp(gcFile):
    """"
    Function to read gocad polystructure file and makes VTK Polydata object (vtp).

    Input:
        gcFile: gocadFile with polysturcture

    """
    print "Reading GOCAD ts file..."
    vrtx, trgl = read_GOCAD_ts(gcFile)
    # Adjust the index
    trgl = trgl - 1

    # Make vtk pts
    ptsvtk = vtk.vtkPoints()
    ptsvtk.SetData(npsup.numpy_to_vtk(vrtx,deep=1))

    # Make the polygon connection
    polys = vtk.vtkCellArray()
    for face in trgl:
        poly = vtk.vtkPolygon()
        poly.GetPointIds().SetNumberOfIds(len(face))
        for nrv, vert in enumerate(face):
            poly.GetPointIds().SetId(nrv,vert)
        polys.InsertNextCell(poly)

    # Make the polydata, structure of connections and vrtx
    polyData = vtk.vtkPolyData()
    polyData.SetPoints(ptsvtk)
    polyData.SetPolys(polys)

    return polyData

def gocad2simpegMeshIndex(gcFile,mesh,extractBoundaryCells=True,extractInside=True):
    """"
    Function to read gocad polystructure file and output indexes of mesh with in the structure.

    """

    # Make the polydata
    polyData = gocad2vtp(gcFile)

    # Make implicit func
    ImpDistFunc = vtk.vtkImplicitPolyDataDistance()
    ImpDistFunc.SetInput(polyData)

    # Convert the mesh
    vtkMesh = vtk.vtkRectilinearGrid()
    vtkMesh.SetDimensions(mesh.nNx,mesh.nNy,mesh.nNz)
    vtkMesh.SetXCoordinates(npsup.numpy_to_vtk(mesh.vectorNx,deep=1))
    vtkMesh.SetYCoordinates(npsup.numpy_to_vtk(mesh.vectorNy,deep=1))
    vtkMesh.SetZCoordinates(npsup.numpy_to_vtk(mesh.vectorNz,deep=1))
    # Add indexes cell data to the object
    vtkInd = npsup.numpy_to_vtk(np.arange(mesh.nC),deep=1)
    vtkInd.SetName('Index')
    vtkMesh.GetCellData().AddArray(vtkInd)

    # Define the extractGeometry
    extractImpDistRectGridFilt = vtk.vtkExtractGeometry() # Object constructor
    extractImpDistRectGridFilt.SetImplicitFunction(ImpDistFunc) #
    extractImpDistRectGridFilt.SetInputData(vtkMesh)

    # Set extraction type
    if extractBoundaryCells is True:
        extractImpDistRectGridFilt.ExtractBoundaryCellsOn()
    else:
        extractImpDistRectGridFilt.ExtractBoundaryCellsOff()

    if extractInside is True:
        extractImpDistRectGridFilt.ExtractInsideOn()
    else:
        extractImpDistRectGridFilt.ExtractInsideOff()

    print "Extracting indices from grid..."
    # Executing the pipe
    extractImpDistRectGridFilt.Update()

    # Get index inside
    insideGrid = extractImpDistRectGridFilt.GetOutput()
    insideGrid = npsup.vtk_to_numpy(insideGrid.GetCellData().GetArray('Index'))


    # Return the indexes inside
    return insideGrid



def makeVTPFiles():

    # Read in topo surface
    geosurf = ['CDED_Lake_Coarse.ts','Till.ts','XVK.ts','PK1.ts','PK1_extended.ts','PK2.ts','PK3.ts','HK1.ts','VK.ts']

    # The make the polydata
    polyDict = {}
    for fileName in geosurf:
        tin = tm.time()
        name = fileName.split('.')[0]
        print "Computing indices with VTK: " + fileName
        polyDict[name] = gocad2vtp(fileName)
        print "VTK operation completed in " + str(tm.time() - tin) + " sec"
    # Write the files
    sys.path.append('/home/gudni/gitCodes/python/telluricpy')
    import telluricpy

    for k,vtpObj in polyDict.iteritems():
        telluricpy.vtkTools.io.writeVTPFile(k+'.vtp',vtpObj)

def makeModelFile():
    """
    Loads in a triangulated surface from Gocad (*.ts) and use VTK to transfer onto
    a 3D mesh.

    New scripts to be added to basecode
    """
    #%%

    work_dir = ''

    mshfile = 'MEsh_TEst.msh'

    # Load mesh file
    mesh = Mesh.TensorMesh.readUBC(work_dir+mshfile)

    # Load in observation file
    #[B,M,dobs] = PF.BaseMag.readUBCmagObs(obsfile)

    # Read in topo surface
    topsurf = work_dir+'CDED_Lake_Coarse.ts'
    geosurf =  [[work_dir+'Till.ts',True,True],
                [work_dir+'XVK.ts',True,True],
                [work_dir+'PK1.ts',True,True],
                [work_dir+'PK2.ts',True,True],
                [work_dir+'PK3.ts',True,True],
                [work_dir+'HK1.ts',True,True],
                [work_dir+'VK.ts',True,True]
    ]

    # Background density
    bkgr = 1e-4
    airc = 1e-8

    # Units
    vals = np.asarray([1e-2,3e-2,5e-2,2e-2,2e-2,1e-3,5e-3])

    #%% Script starts here
    # # Create a grid of observations and offset the z from topo

    model= np.ones(mesh.nC) * bkgr
    # Load GOCAD surf
    #[vrtx, trgl] = PF.BaseMag.read_GOCAD_ts(tsfile)
    # Find active cells from surface

    for ii in range(len(geosurf)):
        tin = tm.time()
        print "Computing indices with VTK: " + geosurf[ii][0]
        indx = gocad2simpegMeshIndex(geosurf[ii][0],mesh)
        print "VTK operation completed in " + str(tm.time() - tin) + " sec"

        model[indx] = vals[ii]

    indx = gocad2simpegMeshIndex(topsurf,mesh)
    actv = np.zeros(mesh.nC)
    actv[indx] = 1

    model[actv==0] = airc

    Mesh.TensorMesh.writeModelUBC(mesh,'VTKout.dat',model)
