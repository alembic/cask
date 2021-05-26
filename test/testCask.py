#-******************************************************************************
#
# Copyright (c) 2012-2018,
#  Sony Pictures Imageworks Inc. and
#  Industrial Light & Magic, a division of Lucasfilm Entertainment Company Ltd.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# *       Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# *       Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
# *       Neither the name of Sony Pictures Imageworks, nor
# Industrial Light & Magic, nor the names of their contributors may be used
# to endorse or promote products derived from this software without specific
# prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#-******************************************************************************

import os
import sys
import string
import unittest
import tempfile

import imath
import alembic
import cask
import meshData

kFacevaryingScope = alembic.AbcGeom.GeometryScope.kFacevaryingScope
kConstantScope = alembic.AbcGeom.GeometryScope.kConstantScope

# temporary directory for holding test archives
TEMPDIR = tempfile.mkdtemp()

"""
TODO
 - test creating prototype schema objects
 - test name collisions when creating new objects and properties
"""

def set_float(schema, target, shaderType, paramName, value):
    prop = alembic.Abc.OFloatProperty(schema.getShaderParameters(target, shaderType),
            paramName)
    prop.setValue(value)
    return prop

def lights_out():
    filename = os.path.join(TEMPDIR, "cask_test_lights.abc")
    if os.path.exists(filename) and cask.is_valid(filename):
        return filename

    os.system("rm -f %s" % filename)
    archive = alembic.Abc.OArchive(filename)
    lightA = alembic.AbcGeom.OLight(archive.getTop(), "lightA")
    lightB = alembic.AbcGeom.OLight(archive.getTop(), "lightB")

    samp = alembic.AbcGeom.CameraSample()
    lightB.getSchema().setCameraSample(samp)

    # camera data
    samp = alembic.AbcGeom.CameraSample(-0.35, 0.75, 0.1, 0.5)
    lightB.getSchema().getChildBoundsProperty().setValue(
        imath.Box3d(imath.V3d(0.0, 0.1, 0.2), imath.V3d(0.3, 0.4, 0.5 )))
    samp.setNearClippingPlane(0.0)
    samp.setFarClippingPlane(1000.0)
    samp.setHorizontalAperture(2.8)
    samp.setVerticalAperture(2.8)
    samp.setFocalLength(50)
    lightB.getSchema().setCameraSample(samp)

    # material data
    mat = alembic.AbcMaterial.addMaterial(lightB, "shader")
    mat.setShader("prman", "light", "materialB")

    exposure = set_float(mat, "prman", "light", "exposure", 1.0)
    spec = set_float(mat, "prman", "light", "specular", 0.1)

    for i in range(10):
        exposure.setValue(1.0)
        spec.setValue(0.1 + i/10.0)

    # user properties
    user = lightB.getSchema().getUserProperties()
    test = alembic.Abc.OFloatProperty(user, "test")
    test.setValue(10)

    return filename

def mesh_out(name="cask_test_mesh.abc", force=False):
    filename = os.path.join(TEMPDIR, name)
    if not force and (os.path.exists(filename) and cask.is_valid(filename)):
        return filename

    oarch = alembic.Abc.OArchive(filename)
    meshyObj = alembic.AbcGeom.OPolyMesh(oarch.getTop(), 'meshy')
    mesh = meshyObj.getSchema()

    uvsamp = alembic.AbcGeom.OV2fGeomParamSample(meshData.uvs, kFacevaryingScope)
    nsamp  = alembic.AbcGeom.ON3fGeomParamSample(meshData.normals, kFacevaryingScope)
    mesh_samp = alembic.AbcGeom.OPolyMeshSchemaSample(
            meshData.verts, meshData.indices, meshData.counts, uvsamp, nsamp)

    cbox = imath.Box3d()
    cbox.extendBy(imath.V3d(1.0, -1.0, 0.0))
    cbox.extendBy(imath.V3d(-1.0, 1.0, 3.0))

    for i in range(10):
        mesh.getChildBoundsProperty().setValue(cbox)
        mesh.set(mesh_samp)

    del oarch
    return filename

def cube_out(name="cask_test_cube.abc", force=False):
    filename = os.path.join(TEMPDIR, name)
    if not force and (os.path.exists(filename) and cask.is_valid(filename)):
        return filename

    tvec = alembic.AbcCoreAbstract.TimeVector()
    tvec[:] = [1, 2, 3]

    timePerCycle = 3.0
    numSamplesPerCycle = len(tvec)

    tst = alembic.AbcCoreAbstract.TimeSamplingType(numSamplesPerCycle, timePerCycle)
    ts = alembic.AbcCoreAbstract.TimeSampling(tst, tvec)

    top = alembic.Abc.OArchive(filename).getTop()
    tsidx = top.getArchive().addTimeSampling(ts)

    # create the top xform
    xform = alembic.AbcGeom.OXform(top, 'cube1', tsidx)
    xsamp = alembic.AbcGeom.XformSample()
    xform.getSchema().set(xsamp)

    # the mesh shape
    meshObj = alembic.AbcGeom.OPolyMesh(xform, 'cube1Shape')
    mesh = meshObj.getSchema()
    mesh_samp = alembic.AbcGeom.OPolyMeshSchemaSample(
        meshData.points, meshData.faceIndices, meshData.faceCounts
    )
    mesh_samp.setSelfBounds(meshData.selfBnds)
    mesh.set(mesh_samp)

    return filename

def deep_out():
    filename = os.path.join(TEMPDIR, "cask_test_deep.abc")
    if os.path.exists(filename) and cask.is_valid(filename):
        return filename

    obj = alembic.Abc.OArchive(filename).getTop()
    for i in range(10):
        obj = alembic.AbcGeom.OXform(obj, string.uppercase[i])
        p = obj.getProperties()
        for i in range(3):
            p = alembic.Abc.OCompoundProperty(p, string.lowercase[i])
        p = alembic.Abc.OStringProperty(p, "myprop")
        p.setValue("foo")

    return filename

class Test1_Write(unittest.TestCase):
    def test_write_basic(self):
        filename = os.path.join(TEMPDIR, "cask_write_basic.abc")

        # create empty archive
        a = cask.Archive()
        self.assertEqual(len(a.top.children), 0)

        # create xform object named foo and make it a child of top
        f = a.top.children["foo"] = cask.Xform()
        self.assertEqual(len(a.top.children), 1)
        self.assertEqual(a.top.children.values()[0].name, "foo")

        # create some simple properties
        b = f.properties["bar"] = cask.Property()
        a.top.children["foo"].properties["bar"].set_value("hello")
        f.properties["baz"] = cask.Property()
        a.top.children["foo"].properties["baz"].set_value(42.0)

        # check to make sure object() returns the right thing
        self.assertEqual(b.object(), f)

        # write to disk
        a.write_to_file(filename)
        self.assertTrue(os.path.isfile(filename))

    def test_extract_light(self):
        filename = os.path.join(TEMPDIR, "cask_extract_light.abc")

        # open light archive and create new empty archive
        a = cask.Archive(lights_out())
        b = cask.Archive()

        # find a light and reparent it under b
        results = cask.find(a.top, "lightB")
        self.assertEqual(len(results), 1)
        b.top.children["lightB"] = results[0]

        # write new archive to disk
        b.write_to_file(filename)
        self.assertTrue(os.path.isfile(filename))

    def test_copy_lights(self):
        filename = os.path.join(TEMPDIR, "cask_copy_lights.abc")

        # walks hierarchy and dupes each object and property as-is
        a = cask.Archive(lights_out())
        a.write_to_file(filename)
        self.assertTrue(os.path.isfile(filename))

    def test_copy_mesh(self):
        filename = os.path.join(TEMPDIR, "cask_copy_mesh.abc")

        # walks hierarchy and dupes each object and property as-is
        a = cask.Archive(mesh_out())
        a.write_to_file(filename)
        self.assertTrue(os.path.isfile(filename))

    def test_add_child(self):
        """Creates a simple cache with one mesh, then moves and copies it. 
        Resulting abc cache should look like this:

        ABC                                                                                                                                        
         |--x1
         |--x2
         |    `--meshy
         `--x3
             `--meshy
        """
        filename = os.path.join(TEMPDIR, "cask_add_child.abc")
        
        a = cask.Archive(mesh_out())
        meshy = a.top.children["meshy"]
        x1 = a.top.children["x1"] = cask.Xform()
        x2 = a.top.children["x2"] = cask.Xform()
        x3 = a.top.children["x3"] = cask.Xform()

        # test moving it and copying it
        x1.add_child(meshy)
        x2.add_child(meshy)
        x3.add_child(cask.copy(meshy))

        # export to a new filename
        a.write_to_file(filename)
        a.close()

        # test the new file
        a = cask.Archive(filename)
        self.assertEqual(set(a.top.children.keys()), set(["x1", "x2", "x3"]))
        
        x1 = a.top.children["x1"]
        x2 = a.top.children["x2"]
        x3 = a.top.children["x3"]
        
        # meshy should have been moved from x1->x2, and copied to x3
        self.assertEqual(len(x1.children), 0)
        self.assertEqual(len(x2.children), 1)
        self.assertEqual(len(x3.children), 1)

        m2 = x2.children["meshy"]
        m3 = x3.children["meshy"]

        # basic check to see if mesh points are the same
        self.assertEqual(m2.type(), "PolyMesh")
        self.assertEqual(m3.type(), "PolyMesh")
        self.assertEqual(m2.properties[".geom/P"].values,
                m3.properties[".geom/P"].values)
        a.close()

    def test_write_geom(self):
        filename = os.path.join(TEMPDIR, "cask_write_geom.abc")

        # create empty archive and put some objects in it
        a = cask.Archive()

        # create one of each geom class
        a.top.children["xform"] = cask.Xform()
        a.top.children["polymesh"] = cask.PolyMesh()
        a.top.children["subd"] = cask.SubD()
        a.top.children["faceset"] = cask.FaceSet()
        a.top.children["curve"] = cask.Curve()
        a.top.children["camera"] = cask.Camera()
        a.top.children["nupatch"] = cask.NuPatch()
        a.top.children["material"] = cask.Material()
        a.top.children["light"] = cask.Light()
        a.top.children["points"] = cask.Points()

        # export the archive
        a.write_to_file(filename)
        self.assertTrue(os.path.isfile(filename))

    def test_write_mesh(self):
        filename = os.path.join(TEMPDIR, "cask_write_mesh.abc")

        # create empty archive, xform and polymesh
        a = cask.Archive()
        x = cask.Xform()
        p = cask.PolyMesh()

        # hierarchy assignment
        a.top.children["foo"] = x
        x.children["meshy"] = p

        # set sample values using wrapped sample methods
        x.set_scale(imath.V3d(1, 2, 3))

        # create alembic polymesh sample and set it on our polymesh
        uvsamp = alembic.AbcGeom.OV2fGeomParamSample(meshData.uvs, kFacevaryingScope)
        nsamp = alembic.AbcGeom.ON3fGeomParamSample(meshData.normals, kFacevaryingScope)
        s = alembic.AbcGeom.OPolyMeshSchemaSample(meshData.verts, meshData.indices,
                meshData.counts, uvsamp, nsamp)
        p.set_sample(s)

        # write to disk
        a.write_to_file(filename)
        self.assertTrue(os.path.isfile(filename))

    def test_write_points(self):
        filename = os.path.join(TEMPDIR, "cask_write_points.abc")

        # create empty archive, xform and polymesh
        a = cask.Archive()
        x = cask.Xform()
        pts = cask.Points()

        # hierarchy assignment
        a.top.children["points"] = x
        x.children["pointsShape"] = pts

        pts_sample = alembic.AbcGeom.OPointsSchemaSample()
        pts_sample.setIds(meshData.pointsIndices)
        pts_sample.setPositions(meshData.points)

        pts.set_sample(pts_sample)

        # write to disk
        a.write_to_file(filename)
        self.assertTrue(os.path.isfile(filename))

    def test_new_property(self):
        filename = os.path.join(TEMPDIR, "cask_new_property.abc")

        # create a new property
        a = cask.Archive(mesh_out())
        t = a.top

        # create simple property
        f = t.properties["foo"] = cask.Property()
        self.assertEqual(f.name, "foo")
        self.assertEqual(f, t.properties["foo"])
        self.assertEqual(f.parent, t)
        self.assertEqual(f.object(), t)

        # create new object
        l = t.children["spot"] = cask.Light()
        self.assertEqual(a.top.children["spot"], l)
        self.assertEqual(l.name, "spot")
        self.assertEqual(t.children["spot"].name, "spot")
        self.assertEqual(l.parent, t)
        self.assertEqual(l.children, {})

        # change name in place
        t.children["spot"].name = "point"
        self.assertEqual(l.name, "point")

        a.write_to_file(filename)

    def test_selective_update(self):
        filename = os.path.join(TEMPDIR, "cask_selective_update.abc")

        # test setting bounds after reading in from an iarchive
        a = cask.Archive(lights_out())

        # update the name
        l = a.top.children["lightB"]
        l.name = "lightC"

        # update the x position
        p = l.properties["shader/prman.light.params/exposure"]
        p.set_value(0.5, index=5)
        self.assertAlmostEqual(p.values[5], 0.5)

        # write it back out
        a.write_to_file(filename)
        self.assertTrue(os.path.isfile(filename))

    def test_insert_node(self):
        filename = os.path.join(TEMPDIR, "cask_insert_node.abc")

        # test inerting a node into the hierarchy at the top
        a = cask.Archive(mesh_out())

        # insert a new xform between two nodes
        r = cask.Xform()
        m = a.top.children["meshy"]
        a.top.children["root"] = r
        r.children["meshy"] = m

        # write to disk
        a.write_to_file(filename)
        self.assertTrue(os.path.isfile(filename))

    def test_rename(self):
        filename = os.path.join(TEMPDIR, "cask_test_rename.abc")

        a = cask.Archive()
        t = a.top

        # create a new object and property
        t.children["foo"] = cask.Xform()
        t.properties["some"] = cask.Property()
        f = t.children.values()[0]
        p = t.properties.values()[0]
        self.assertEqual(f.name, "foo")
        self.assertEqual(p.name, "some")

        # rename them
        f.name = "bar"
        self.assertEqual(f.name, "bar")
        self.assertEqual(t.children.values()[0].name, "bar")
        p.name = "thing"
        self.assertEqual(p.name, "thing")
        self.assertEqual(t.properties.values()[0].name, "thing")

        # test for accessor updates
        self.assertEqual(t.children["bar"], f)
        self.assertRaises(KeyError, t.children.__getitem__, "foo")
        self.assertEqual(t.properties["thing"], p)
        self.assertRaises(KeyError, t.properties.__getitem__, "some")

        # write to a file
        a.write_to_file(filename)

    def test_reassign(self):
        filename = os.path.join(TEMPDIR, "cask_test_reassign.abc")

        a = cask.Archive()
        t = a.top
        t.children["xform"] = cask.Xform()
        t.properties["prop"] = cask.Property()
        self.assertEqual(t.children["xform"].type(), "Xform")
        self.assertEqual(t.properties["prop"].type(), "Property")

        # reassign object
        t.children["xform"] = cask.PolyMesh()
        self.assertEqual(t.children["xform"].type(), "PolyMesh")

        # rename object
        x = t.children["xform"]
        x.name = "meshy"
        self.assertRaises(KeyError, t.children.__getitem__, "xform")
        self.assertTrue("meshy" in t.children.keys())
        self.assertEqual(t.children["meshy"], x)

        # rename property
        p = t.properties["prop"]
        p.name = "new"
        self.assertRaises(KeyError, t.properties.__getitem__, "prop")
        self.assertEqual(t.properties.values()[0].name, "new")
        self.assertEqual(t.properties["new"], p)

        # another rename test
        x = cask.Xform()
        t.children["foo"] = x
        self.assertTrue("foo" in t.children.keys())
        self.assertEqual(x.path(), "/foo")
        x.name = "bar"
        self.assertEqual(x.path(), "/bar")
        self.assertFalse("foo" in t.children.keys())
        self.assertTrue("bar" in t.children.keys())
        self.assertEqual(x.archive(), a)

        # child of child rename/reassign test
        baz = x.children["baz"] = cask.Xform()
        self.assertEqual(baz.path(), "/bar/baz")
        baz.name = "zap"
        self.assertFalse("zap" in t.children.keys())
        self.assertEqual(baz.path(), "/bar/zap")
        self.assertTrue("zap" in x.children.keys())
        self.assertEqual(baz.type(), "Xform")

        # reassign child obj to PolyMesh
        x.children["zap"] = cask.PolyMesh()
        self.assertEqual(x.children["zap"].type(), "PolyMesh")

        # write to a file
        a.write_to_file(filename)

    def test_equivalency(self):
        # test empty archive equivalency
        a = cask.Archive()
        b = a
        self.assertEqual(a, b)
        self.assertEqual(a.top.parent, a)
        self.assertEqual(a.top.archive(), a)

        # reassign 'b' to a new empty archive
        b = cask.Archive()
        self.assertNotEqual(a, b)

    def test_frame_range(self):
        filename = os.path.join(TEMPDIR, "cask_frame_range.abc")

        # create a new archive and some objects
        a = cask.Archive()
        xf = a.top.children["renderCamXform"] = cask.Xform()

        # set the start frame to 1001
        a.set_start_frame(1001)

        self.assertEqual(a.start_frame(), 1001)
        self.assertEqual(a.start_time(), 1001 / float(a.fps))

        # add some sample data
        for i in range(24):
            samp = alembic.AbcGeom.XformSample()
            samp.setTranslation(imath.V3d(i, 2.0, 3.0))
            xf.set_sample(samp)

        # export it
        a.write_to_file(filename)

    def test_deep_dict(self):
        filename = os.path.join(TEMPDIR, "cask_deep_dict.abc")

        # read in a simple scene with several shapes
        a = cask.Archive(deep_out())
        t = a.top

        # deep dict access
        self.assertEqual(t.children["A"].name, "A")
        self.assertEqual(t.children["A/B/C/D"].name, "D")
        self.assertEqual(t.children["A"].properties["a"].name, "a")
        self.assertEqual(t.children["A/B/C/D"].properties["a/b/c"].name, "c")
        self.assertRaises(KeyError, t.children.__getitem__, "A/B/C/Z")

        # property accessors
        x = t.children.values()[0]
        self.assertEqual(x.name, "A")
        self.assertEqual(x.properties["a/b/c/myprop"].values[0], "foo")

        # test deep set item on leaf node
        p = t.children["A/B/C/D/meshy"] = cask.PolyMesh()
        self.assertEqual(p.name, "meshy")
        self.assertEqual(p.type(), "PolyMesh")
        self.assertEqual(p.parent, t.children["A/B/C/D"])
        self.assertTrue("meshy" in t.children["A/B/C/D"].children.keys())
        self.assertEqual(len(p.children.keys()), 0)

        # another test
        patch = cask.NuPatch()
        t.children["A/B/C/D/patch"] = patch
        self.assertEqual(patch.name, "patch")
        self.assertEqual(patch.parent, t.children["A/B/C/D"])
        self.assertTrue("patch" in t.children["A/B/C/D"].children.keys())
        self.assertFalse("patch" in t.children.keys())
        self.assertEqual(len(patch.children.keys()), 0)

        # rename test
        patch.name = "nurby"
        self.assertFalse("patch" in t.children["A/B/C/D"].children.keys())
        self.assertTrue("nurby" in t.children["A/B/C/D"].children.keys())
        self.assertEqual(patch.parent, t.children["A/B/C/D"])
        self.assertEqual(t.children["A/B/C/D/nurby"], patch)
        self.assertRaises(KeyError, t.children.__getitem__, "A/B/C/D/patch")

        # test deep dict reassignment
        t.children["A/B/C/D/meshy"] = cask.Xform()
        p2 = t.children["A/B/C/D/meshy"]
        self.assertEqual(p2.name, "meshy")
        self.assertEqual(p2.parent, t.children["A/B/C/D"])
        self.assertFalse(p2.name in t.children.keys())
        self.assertEqual(len(p2.children.values()), 0)
        self.assertEqual(t.children["A/B/C/D/meshy"].type(), "Xform")
        self.assertEqual(p2.type(), "Xform")

        # test deep set item when middle nodes do not exist
        try:
            x = t.children["A/foo/C/D/bar"] = cask.Xform()
            foo = x.properties[".xform/.userProperties/foo"] = cask.Property()
            foo.set_value(1.0)
        except KeyError:
            raise

        # assert that the created nodes are Xforms
        self.assertEqual(t.children["A/foo"].type(), "Xform")
        self.assertEqual(t.children["A/foo/C/D/bar"].type(), "Xform")
        self.assertEqual(foo.type(), "Property")
        self.assertEqual(foo.values[0], 1.0)

        # assert "a" still exists in "A"
        self.assertTrue("a" in t.children["A"].properties.keys())

        # write the archive
        a.write_to_file(filename)

        # re-open and create add'l properties
        a = cask.Archive(filename)
        x = a.top.children["A/foo/C/D/bar"]

        # create new user property
        bar = x.properties[".xform/.userProperties/bar"] = cask.Property()
        bar.set_value(2.0)
        self.assertTrue("bar" in x.properties[".xform/.userProperties"].properties)

        # assert that "foo" was not clobbered when we created "bar"
        self.assertTrue("foo" in x.properties[".xform/.userProperties"].properties)
        foo = x.properties[".xform/.userProperties/foo"]
        self.assertEqual(foo.values[0], 1.0)

    def test_light_shader(self):
        filename = os.path.join(TEMPDIR, "cask_light_shader.abc")

        a = cask.Archive()

        # create light and material
        light = a.top.children["spotlight"] = cask.Light()
        mat = light.properties[".materials"] = cask.Property()

        # set shader name
        names = mat.properties[".shaderNames"] = cask.Property()
        names.set_value(["prman.light", "spot_lgt"])

        # set shader values
        shader = mat.properties["prman.light.params"] = cask.Property()
        p1 = shader.properties["exposure"] = cask.Property()
        p1.set_value(1.0)
        p2 = shader.properties["specular"] = cask.Property()
        p2.set_value(0.1)
        p3 = shader.properties["color"] = cask.Property()
        p3.set_value(imath.Color3f(0.1, 0.2, 0.3))
        p3.metadata["interpretation"] = "rgb"

        # set light camera data
        samp = alembic.AbcGeom.CameraSample(-0.35, 0.75, 0.1, 0.5)
        light.set_sample(samp)
        samp.setNearClippingPlane(0.0)
        samp.setFarClippingPlane(1000.0)
        samp.setHorizontalAperture(2.8)
        samp.setVerticalAperture(2.8)
        samp.setFocalLength(50)
        light.set_sample(samp)

        # export
        a.write_to_file(filename)

    def test_pod_extent(self):
        filename = os.path.join(TEMPDIR, "cask_pod_extent.abc")

        extent = 5
        v = imath.UnsignedCharArray(extent)
        for i in range(0, extent):
            v[i] = i

        a = cask.Archive()

        # create test properties
        foo = a.top.children["foo"] = cask.Xform()
        bar = foo.properties["bar"] = cask.Property()
        baz = foo.properties["baz"] = cask.Property()
        qux = foo.properties["qux"] = cask.Property()
        quux = foo.properties["quux"] = cask.Property()
        garply = foo.properties["garply"] = cask.Property()
        quatf = foo.properties["quatf"] = cask.Property()
        quatf.metadata["interpretation"] = "quat"
        quatd = foo.properties["quatd"] = cask.Property()
        quatd.metadata["interpretation"] = "quat"
        waldo = foo.properties["waldo"] = cask.Property()
        fred = foo.properties["fred"] = cask.Property()
        color = foo.properties["color"] = cask.Property()
        color.metadata["interpretation"] = "rgb"

        # test setting explicit data type
        visible = foo.properties["visible"] = cask.Property()
        visible.set_value(cask.Int8(0), index=0)
        something = foo.properties["something"] = cask.Property()
        something.set_value(cask.Int32(1234), index=0)

        # set test values
        v = imath.UnsignedCharArray(5)
        for i in range(0, 5):
            v[i] = i
        bar.set_value(v)
        baz.set_value(["a", "b", "c"])
        qux.set_value(imath.Box3d())
        quux.set_value(imath.M33d())
        garply.set_value(imath.M44d())
        quatf.set_value(imath.Quatf())
        quatd.set_value(imath.Quatd())
        waldo.set_value(1)
        fred.set_value([1, 2, 3, 4])
        color.set_value(imath.Color3f(1, 2, 3))
       
        # export
        a.write_to_file(filename)
        a.close()

        # reimport the test file
        a = cask.Archive(filename)

        # recover the test properties
        foo = a.top.children["foo"]
        bar = foo.properties["bar"]
        baz = foo.properties["baz"]
        qux = foo.properties["qux"]
        quux = foo.properties["quux"]
        garply = foo.properties["garply"]
        quatf = foo.properties["quatf"]
        quatd = foo.properties["quatd"]
        waldo = foo.properties["waldo"]
        fred = foo.properties["fred"]
        color = foo.properties["color"]
        visible = foo.properties["visible"]
        something = foo.properties["something"]

        # assert pod, extent values
        self.assertEqual(bar.extent(), 1)
        self.assertEqual(bar.pod(), alembic.Util.POD.kUint8POD)
        self.assertEqual(bar.values[0], v)
        self.assertEqual(baz.extent(), 1)
        self.assertEqual(baz.pod(), alembic.Util.POD.kStringPOD)
        self.assertEqual(list(baz.values[0]), ["a", "b", "c"])
        self.assertEqual(qux.extent(), 6)
        self.assertEqual(qux.pod(), alembic.Util.POD.kFloat64POD)
        self.assertEqual(qux.values[0], imath.Box3d())
        self.assertEqual(quux.extent(), 9)
        self.assertEqual(quux.pod(), alembic.Util.POD.kFloat64POD)
        self.assertEqual(quux.values[0], imath.M33d())
        self.assertEqual(garply.extent(), 16)
        self.assertEqual(garply.pod(), alembic.Util.POD.kFloat64POD)
        self.assertEqual(garply.values[0], imath.M44d())
        self.assertEqual(quatf.extent(), 4)
        self.assertEqual(quatf.pod(), alembic.Util.POD.kFloat32POD)
        self.assertEqual(quatf.values[0], imath.Quatf())
        self.assertEqual(quatf.metadata["interpretation"], "quat")
        self.assertEqual(quatd.extent(), 4)
        self.assertEqual(quatd.pod(), alembic.Util.POD.kFloat64POD)
        self.assertEqual(quatd.values[0], imath.Quatd())
        self.assertEqual(quatd.metadata["interpretation"], "quat")
        self.assertEqual(waldo.extent(), 1)
        self.assertEqual(waldo.pod(), alembic.Util.POD.kInt32POD)
        self.assertEqual(waldo.values[0], 1)
        self.assertEqual(fred.extent(), 1)
        self.assertEqual(fred.pod(), alembic.Util.POD.kInt32POD)
        self.assertEqual(list(fred.values[0]), [1, 2, 3, 4])
        self.assertEqual(color.extent(), 3)
        self.assertEqual(color.pod(), alembic.Util.POD.kFloat32POD)
        self.assertEqual(color.metadata["interpretation"], "rgb")
        self.assertEqual(color.values[0], imath.Color3f(1, 2, 3))
        self.assertEqual(visible.values[0], 0)
        self.assertEqual(visible.pod(), alembic.Util.POD.kInt8POD)
        self.assertEqual(visible.extent(), 1)
        self.assertEqual(something.values[0], 1234)
        self.assertEqual(something.pod(), alembic.Util.POD.kInt32POD)
        self.assertEqual(something.extent(), 1)

    def test_child_bounds(self):
        filename_1 = os.path.join(TEMPDIR, "cask_child_bounds_1.abc")
        filename_2 = os.path.join(TEMPDIR, "cask_child_bounds_2.abc")
        filename_3 = os.path.join(TEMPDIR, "cask_child_bounds_3.abc")

        # create initial archive with initial value
        bounds = imath.Box3d(
            imath.V3d(1, 1, 1), imath.V3d(1, 1, 1)
        )
        a = cask.Archive()
        x = a.top.children["foo"] = cask.Xform()
        p = x.properties[".xform/.childBnds"] = cask.Property()
        p.set_value(bounds)
        self.assertEqual(p.values[0], bounds)
        a.write_to_file(filename_1)
        a.close()

        # verify export / value
        b = cask.Archive(filename_1)
        p = b.top.children["foo"].properties[".xform/.childBnds"]
        self.assertEqual(len(p.values), 1)
        self.assertEqual(p.values[0], bounds)
        self.assertEqual(p.metadata.get("interpretation"), "box")
        
        # set a new child bounds value and export
        bounds = imath.Box3d(
            imath.V3d(-5, -5, -5), imath.V3d(5, 5, 5)
        )
        p.values[0] = bounds
        self.assertEqual(p.values[0], bounds)
        b.write_to_file(filename_2)
        b.close()

        # verify the updated value in the export
        c = cask.Archive(filename_2)
        p = c.top.children["foo"].properties[".xform/.childBnds"]
        self.assertEqual(len(p.values), 1)
        self.assertEqual(p.values[0], bounds)
        self.assertEqual(p.metadata.get("interpretation"), "box")

        # reinitialize the property and export
        p = c.top.children["foo"].properties[".xform/.childBnds"] = cask.Property()
        p.set_value(bounds)
        c.write_to_file(filename_3)
        c.close()

        # re-verify the updated value in the export
        d = cask.Archive(filename_3)
        p = d.top.children["foo"].properties[".xform/.childBnds"]
        self.assertEqual(len(p.values), 1)
        self.assertEqual(p.values[0], bounds)
        self.assertEqual(p.metadata.get("interpretation"), "box")

class Test2_Read(unittest.TestCase):
    def test_verify_write_basic(self):
        filename = os.path.join(TEMPDIR, "cask_write_basic.abc")
        self.assertTrue(cask.is_valid(filename))

        a = cask.Archive(filename)
        self.assertEqual(len(a.top.children), 1)
        self.assertEqual(a.top.children.values()[0].name, "foo")
        self.assertEqual(type(a.top.children.values()[0]), cask.Xform)
        self.assertEqual(len(a.top.children.values()[0].properties), 3)

        self.assertEqual(a.top.children.values()[0].properties["bar"].get_value(), "hello")
        self.assertEqual(a.top.children.values()[0].properties["baz"].get_value(), 42.0)

    def test_read_lights(self):
        filepath = lights_out()
        a = cask.Archive(filepath)
        self.assertEqual(a.path(), filepath)
        self.assertEqual(a.name, os.path.basename(filepath))

        # test the top node
        t = a.top
        self.assertEqual(type(t), cask.Top)
        self.assertEqual(t.name, "ABC")
        self.assertEqual(t.parent, a)
        self.assertEqual(t.path(), "/")
        self.assertEqual(t.archive(), a)

        # child accessors
        l1 = t.children["lightA"]
        self.assertEqual(type(l1.parent), cask.Top)
        self.assertEqual(l1.name, "lightA")
        self.assertEqual(l1.archive(), a)
        self.assertEqual(type(l1), cask.Light)

        # get next child
        l2 = t.children["lightB"]
        self.assertEqual(type(l2), cask.Light)
        self.assertEqual(l2.name, "lightB")
        self.assertEqual(l2.archive(), a)
        self.assertEqual(type(l2.parent), cask.Top)

        # find lights (w/ deferred schemification)
        self.assertEqual(len(cask.find(a.top, "light.*")), 2)

        # schema accessor (schemifies object on demand)
        self.assertEqual(type(l2.iobject), alembic.Abc.IObject)
        self.assertEqual(len(l2.properties[".geom/.camera/.core"].properties), 0)
        self.assertEqual(len(l2.properties["shader/prman.light.params"].properties), 2)
        self.assertEqual(len(l2.properties["shader/prman.light.params/exposure"].values), 11)
        self.assertEqual(len(l2.properties["shader/prman.light.params/specular"].values), 11)
        self.assertAlmostEqual(l2.properties["shader/prman.light.params/exposure"].values[0], 1.0)
        self.assertAlmostEqual(l2.properties["shader/prman.light.params/specular"].values[0], 0.1)
        self.assertEqual(type(l2.schema), alembic.AbcGeom.ILightSchema)
        self.assertEqual(type(l2.iobject), alembic.AbcGeom.ILight)

    def test_read_mesh(self):
        filepath = mesh_out()
        self.assertTrue(cask.is_valid(filepath))
        a = cask.Archive(filepath)
        t = a.top

    def test_paths(self):
        filepath = lights_out()
        a = cask.Archive(filepath)
        t = a.top

        # get some objects to test
        lightA = t.children["lightA"]
        lightB = t.children["lightB"]

        # test paths on objects
        self.assertEqual(a.path(), filepath)
        self.assertEqual(t.path(), "/")
        self.assertEqual(lightA.path(), "/lightA")
        self.assertEqual(lightB.path(), "/lightB")
        self.assertEqual(t.children[lightA.path()], lightA)

        # test paths on properties
        self.assertEqual(lightB.properties[".geom/.camera/.core"].path(),
                            "/lightB/.geom/.camera/.core")

        # test paths on empty archive
        a = cask.Archive()
        t = a.top
        x = t.children["x"] = cask.Xform()
        y = x.children["y"] = cask.Xform()
        z = y.children["z"] = cask.Xform()
        p = z.properties["p"] = cask.Property()
        self.assertEqual(a.path(), None)
        self.assertEqual(t.path(), "/")
        self.assertEqual(x.path(), "/x")
        self.assertEqual(y.path(), "/x/y")
        self.assertEqual(z.path(), "/x/y/z")
        self.assertEqual(p.path(), "/x/y/z/p")

        # test reparenting
        p.parent = x
        self.assertEqual(p.path(), "/x/p")

    def test_verify_extract_light(self):
        filename = os.path.join(TEMPDIR, "cask_extract_light.abc")
        self.assertTrue(cask.is_valid(filename))

        # open the archive
        a = cask.Archive(filename)
        self.assertEqual(len(a.top.children), 1)

        # verify the hierarchy
        l = a.top.children["lightB"]
        self.assertEqual(type(l), cask.Light)
        self.assertEqual(len(l.properties.keys()), 2)
        self.assertEqual(len(l.properties[".geom/.userProperties"].properties), 1)
        self.assertTrue("specular" in l.properties["shader/prman.light.params"].properties.keys())
        self.assertTrue("exposure" in l.properties["shader/prman.light.params"].properties.keys())

    def test_verify_copy_lights(self):
        filename = os.path.join(TEMPDIR, "cask_copy_lights.abc")
        self.assertTrue(cask.is_valid(filename))

        # open archive
        a = cask.Archive(filename)
        self.assertEqual(len(a.top.children), 2)

        # examine a lights properties
        lightA = a.top.children["lightA"]
        lightB = a.top.children["lightB"]
        self.assertEqual(type(lightA), cask.Light)
        self.assertEqual(type(lightB), cask.Light)

        self.assertEqual(len(lightA.properties), 1)
        self.assertEqual(len(lightB.properties), 2)
        self.assertAlmostEqual(lightB.properties["shader/prman.light.params/exposure"].get_value(), 1.0)
        self.assertAlmostEqual(lightB.properties["shader/prman.light.params/specular"].get_value(), 0.1)

    def test_verify_copy_mesh(self):
        filename = os.path.join(TEMPDIR, "cask_copy_mesh.abc")
        self.assertTrue(cask.is_valid(filename))

        # open the archive
        a = cask.Archive(filename)
        p = a.top.children.values()[0]

        # verify timesamplings were copied
        self.assertEqual(len(a.timesamplings), 1)

        # verify the hierarchy
        self.assertEqual(p.name, "meshy")

        # check the global matrix of the polymesh object
        self.assertEqual(p.global_matrix(),
                imath.M44d((1,0,0,0), (0,1,0,0), (0,0,1,0), (0,0,0,1)))

        geom = p.properties[".geom"]
        self.assertEqual(len(geom.properties[".faceCounts"].values), 10)
        self.assertEqual(geom.properties[".faceCounts"].values[0][0], 4)
        self.assertEqual(geom.properties["P"].values[0][0], imath.V3f(-1, -1, -1))
        self.assertEqual(geom.properties["N"].values[0][0], imath.V3f(-1, 0, 0))

    def test_verify_write_geom(self):
        filename = os.path.join(TEMPDIR, "cask_write_geom.abc")
        self.assertTrue(os.path.isfile(filename))

        # open the test archive
        a = cask.Archive(filename)

        # verify the object names and geom classes are correct
        self.assertEqual(type(a.top.children["xform"]), cask.Xform)
        self.assertEqual(type(a.top.children["polymesh"]), cask.PolyMesh)
        self.assertEqual(type(a.top.children["subd"]), cask.SubD)
        self.assertEqual(type(a.top.children["faceset"]), cask.FaceSet)
        self.assertEqual(type(a.top.children["curve"]), cask.Curve)
        self.assertEqual(type(a.top.children["camera"]), cask.Camera)
        self.assertEqual(type(a.top.children["nupatch"]), cask.NuPatch)
        self.assertEqual(type(a.top.children["material"]), cask.Material)
        self.assertEqual(type(a.top.children["light"]), cask.Light)
        self.assertEqual(type(a.top.children["points"]), cask.Points)

    def test_verify_write_mesh(self):
        filename = os.path.join(TEMPDIR, "cask_write_mesh.abc")
        self.assertTrue(cask.is_valid(filename))

        # get the objects
        a = cask.Archive(filename)
        x = a.top.children.values()[0]
        p = x.children.values()[0]

        # verify the hierarchy
        self.assertEqual(x.name, "foo")
        self.assertEqual(type(x), cask.Xform)
        self.assertEqual(p.name, "meshy")
        self.assertEqual(type(p), cask.PolyMesh)

        # check one of the properties
        vals = x.properties.values()[0].properties[".vals"]
        self.assertEqual(vals.values[0], imath.V3d(1, 2, 3))

    def test_verify_write_points(self):
        filename = os.path.join(TEMPDIR, "cask_write_points.abc")
        self.assertTrue(cask.is_valid(filename))

        # get the objects
        a = cask.Archive(filename)
        x = a.top.children.values()[0]
        pts = x.children.values()[0]

        # verify the hierarchy
        self.assertEqual(x.name, "points")
        self.assertEqual(pts.name, "pointsShape")
        self.assertEqual(type(pts), cask.Points)

        # get sample
        self.assertEqual(len(pts.samples), 1)

        pts_sample = pts.samples[0]

        # get arrays
        pts_id_array = pts_sample.getIds()
        pts_pos_array = pts_sample.getPositions()

        self.assertIsInstance(pts_id_array, imath.IntArray)
        self.assertIsInstance(pts_pos_array, imath.V3fArray)

        self.assertEqual(pts_id_array, meshData.pointsIndices)
        self.assertEqual(pts_pos_array, meshData.points)

    def test_verify_selective_update(self):
        filename = os.path.join(TEMPDIR, "cask_selective_update.abc")
        self.assertTrue(cask.is_valid(filename))

        # verify our name change
        a = cask.Archive(filename)
        self.assertTrue("lightC" in a.top.children.keys())
        l = a.top.children["lightC"]

        # verify our translate update
        p = l.properties["shader/prman.light.params/exposure"]
        self.assertAlmostEqual(p.values[0], 1.0)
        self.assertAlmostEqual(p.values[5], 0.5)

    def test_verify_insert_node(self):
        filename = os.path.join(TEMPDIR, "cask_insert_node.abc")
        self.assertTrue(cask.is_valid(filename))

        # get some objects
        a = cask.Archive(filename)
        r = a.top.children.values()[0]
        m = r.children.values()[0]

        # verify re-parenting
        self.assertEqual(r.name, "root")
        self.assertEqual(type(r), cask.Xform)
        self.assertEqual(m.name, "meshy")
        self.assertEqual(type(m), cask.PolyMesh)
        self.assertEqual(len(m.properties[".geom"].properties), 7)

    def test_verify_frame_range(self):
        filename = os.path.join(TEMPDIR, "cask_frame_range.abc")
        self.assertTrue(cask.is_valid(filename))

        a = cask.Archive(filename)

        # verify the frame range
        self.assertEqual(a.start_time(), 1001 / float(a.fps))
        self.assertEqual(a.start_frame(), 1001)
        self.assertEqual(a.end_frame(), 1024)

    def test_verify_deep_dict(self):
        filename = os.path.join(TEMPDIR, "cask_deep_dict.abc")
        self.assertTrue(cask.is_valid(filename))

        # get some objects
        a = cask.Archive(filename)
        t = a.top
        d = t.children["A/B/C/D"]

        # verify writes
        self.assertTrue("meshy" in d.children.keys())
        self.assertTrue("nurby" in d.children.keys())
        self.assertEqual(type(d.children["meshy"]), cask.Xform)
        self.assertEqual(type(d.children["nurby"]), cask.NuPatch)

    def test_verify_copy_timesampling(self):
        test_cube_out = cube_out("cask_test_copy_timesamplings_1.abc")
        test_file_path = os.path.join(TEMPDIR, "cask_test_copy_timesamplings_2.abc")
        self.assertTrue(cask.is_valid(test_cube_out))

        a = cask.Archive(test_cube_out)

        # create new archive and copy ts objects
        b = cask.Archive()
        b.timesamplings.extend(a.timesamplings[:])

        self.assertEqual(len(a.timesamplings), len(b.timesamplings))
        b.write_to_file(test_file_path)
        b.close()

        # verify the ts objects were written to the archive
        c = cask.Archive(test_file_path)
        self.assertEqual(len(a.timesamplings), len(c.timesamplings))
        ts_a = a.timesamplings[-1]
        ts_c = c.timesamplings[-1]
        self.assertEqual(ts_a.getNumStoredTimes(), ts_c.getNumStoredTimes())
        for i, t in enumerate(ts_a.getStoredTimes()):
            self.assertEqual(t, ts_c.getStoredTimes()[i])

    def test_find(self):
        filename = os.path.join(TEMPDIR, "cask_write_mesh.abc")
        a = cask.Archive(filename)
        
        r = cask.find(a.top, name="meshy")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].name, "meshy")
        self.assertEqual(r[0].type(), "PolyMesh")

        r = cask.find(a.top, name=".*hy")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].name, "meshy")
        self.assertEqual(r[0].type(), "PolyMesh")

        r = cask.find(a.top, types=["PolyMesh"])
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].name, "meshy")
        self.assertEqual(r[0].type(), "PolyMesh")

        a.close()

        filename = os.path.join(TEMPDIR, "cask_deep_dict.abc")
        a = cask.Archive(filename)

        r = cask.find(a.top, types=["Xform"])
        self.assertEqual(len(r), 15)

        r = cask.find(a.top, types=["Light"])
        self.assertEqual(len(r), 0)

        r = cask.find(a.top, name="J")
        self.assertEqual(len(r), 1)

        r = cask.find(a.top, name="D")
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0].name, "D")
        self.assertEqual(r[0].type(), "Xform")

        r = cask.find(a.top, name="nurby")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].name, "nurby")
        self.assertEqual(r[0].type(), "NuPatch")

        r = cask.find(a.top, types=["NuPatch"])
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].name, "nurby")
        self.assertEqual(r[0].type(), "NuPatch")
        
        a.close()

class Test3_Issues(unittest.TestCase):
    def test_issue_318(self):
        """google code issue #318"""

        filename = "cask_test_issue_318.abc"

        # create a test file
        test_file_1 = mesh_out(filename)

        # access an object in the file, then close it
        a = cask.Archive(test_file_1)
        self.assertEqual(a.top.children.keys(), ['meshy'])
        a.close()

        # try to write to the same file path
        #  the error that's being tested for is this:
        #   hdf5-1.8.9/src/H5F.c line 1255 in H5F_open():
        #   unable to truncate a file which is already open
        test_file_2 = mesh_out(filename, force=True)

        self.assertEqual(test_file_1, test_file_2)

    def test_issue_345(self):
        """google code issue #345"""

        test_file_mesh = os.path.join(TEMPDIR, "cask_write_mesh.abc")
        test_file_geom = os.path.join(TEMPDIR, "cask_write_geom.abc")
        test_file_lights = os.path.join(TEMPDIR, "cask_test_lights.abc")
        test_file_cube = cube_out("cask_write_cube.abc")

        test_file_1 = os.path.join(TEMPDIR, "cask_test_issue_345_1.abc")
        test_file_2 = os.path.join(TEMPDIR, "cask_test_issue_345_2.abc")
        test_file_3 = os.path.join(TEMPDIR, "cask_test_issue_345_3.abc")
        test_file_4 = os.path.join(TEMPDIR, "cask_test_issue_345_4.abc")

        def compare_props(props1, props2):
            self.assertEqual(
                set((p1.name, p1.pod(), p1.extent()) for p1 in props1.values()),
                set((p2.name, p2.pod(), p2.extent()) for p2 in props2.values())
            )
            for p1 in props1.values():
                if p1.is_compound():
                    p2 = props2.get(p1.name)
                    self.assertTrue(p2.is_compound())
                    compare_props(p1.properties, p2.properties)

        # mesh test
        a = cask.Archive(test_file_mesh)
        a.write_to_file(test_file_1)
        a.close()
 
        a = cask.Archive(test_file_mesh)
        b = cask.Archive(test_file_1)

        for ageom in a.top.children.values():
            bgeom = b.top.children[ageom.name]
            compare_props(ageom.properties, bgeom.properties)

        # geom test
        a = cask.Archive(test_file_geom)
        a.write_to_file(test_file_2)
        a.close()

        a = cask.Archive(test_file_geom)
        b = cask.Archive(test_file_2)

        for ageom in a.top.children.values():
            bgeom = b.top.children[ageom.name]
            compare_props(ageom.properties, bgeom.properties)

        # cube test
        a = cask.Archive(test_file_cube)
        a.write_to_file(test_file_3)
        a.close()

        a = cask.Archive(test_file_cube)
        b = cask.Archive(test_file_3)

        for ageom in a.top.children.values():
            bgeom = b.top.children[ageom.name]
            compare_props(ageom.properties, bgeom.properties)

        # lights test
        a = cask.Archive(test_file_lights)
        a.write_to_file(test_file_4)
        a.close()

        a = cask.Archive(test_file_lights)
        b = cask.Archive(test_file_4)

        for ageom in a.top.children.values():
            bgeom = b.top.children[ageom.name]
            compare_props(ageom.properties, bgeom.properties)

    def test_issue_346(self):
        """google code issue #346"""

        filename_1 = "cask_test_issue_346_1.abc"
        filename_2 = "cask_test_issue_346_2.abc"

        # create a test file with 1 time sampling object
        test_file_1 = mesh_out(filename_1)
        test_file_2 = os.path.join(TEMPDIR, filename_2)

        a = cask.Archive(test_file_1)
        a.write_to_file(test_file_2)
        b = cask.Archive(test_file_2)

        # compare test1 and test2
        self.assertEqual(len(a.timesamplings), len(b.timesamplings))
        self.assertEqual(a.time_range(), b.time_range())
        tst_1 = a.timesamplings[0].getTimeSamplingType()
        tst_2 = b.timesamplings[0].getTimeSamplingType()
        self.assertEqual(str(tst_1), str(tst_2))

        filename_3 = "cask_test_issue_346_3.abc"
        filename_4 = "cask_test_issue_346_4.abc"

        # create another test with 2 time sampling objects
        test_file_3 = cube_out(filename_3)
        test_file_4 = os.path.join(TEMPDIR, filename_4)

        c = cask.Archive(test_file_3)
        c.write_to_file(test_file_4)
        d = cask.Archive(test_file_4)

        # compare test3 and test4
        self.assertEqual(len(c.timesamplings), len(d.timesamplings))
        self.assertEqual(c.time_range(), d.time_range())
        tst_3 = c.timesamplings[0].getTimeSamplingType()
        tst_4 = d.timesamplings[0].getTimeSamplingType()
        self.assertEqual(str(tst_3), str(tst_4))

    def test_issue_349(self):
        """google code issue #349"""

        test_file = os.path.join(TEMPDIR, "cask_test_issue_349.abc")

        # create a new archive and some objects
        a = cask.Archive()
        xf = a.top.children["renderCamXform"] = cask.Xform()
        cam = xf.children["renderCamShape"] = cask.Camera()

        # set camera smaple
        samp = alembic.AbcGeom.CameraSample(-0.35, 0.75, 0.1, 0.5)
        cam.set_sample(samp)

        # set xform samples
        for i in range(24):
            samp = alembic.AbcGeom.XformSample()
            samp.setTranslation(imath.V3d(i, 2.0, 3.0))
            xf.set_sample(samp)

        # export it
        a.write_to_file(test_file)
        a.close()

        # read the test archive back in and verify results
        a = cask.Archive(test_file)
        xform = a.top.children["renderCamXform"]
        cam = xform.children["renderCamShape"]
        self.assertEqual(len(a.timesamplings), 2)
        self.assertEqual(xform.time_sampling_id, 1)
        self.assertEqual(len(xform.samples), 24)
        self.assertEqual(len(cam.samples), 1)
        self.assertEqual(a.start_frame(), 0)
        self.assertEqual(a.end_frame(), 23)

    def test_issue_23(self):
        """github issue #23: preserve user properties"""

        test_file = os.path.join(TEMPDIR, "cask_test_issue_23.abc")
        test_file_2 = os.path.join(TEMPDIR, "cask_test_issue_23_2.abc")

        a = cask.Archive()
        x = a.top.children["x"] = cask.Xform()
        x.properties[".xform"] = cask.Property()

        # create the .userProperties compound prop
        up = x.properties[".xform"].properties[".userProperties"] = cask.Property()
        
        # create some user properties
        p1 = up.properties["foo"] = cask.Property()
        p1.set_value("bar")
        p2 = up.properties["bar"] = cask.Property()
        p2.set_value(1.0)

        # export it
        a.write_to_file(test_file)
        a.close()

        # read it back in and check for the user properties
        a = cask.Archive(test_file)
        x = a.top.children["x"]
        self.assertEqual(x.properties.keys(), [".xform"])
        self.assertEqual(x.properties[".xform"].properties.keys(), 
            [".userProperties"])
        up = x.properties[".xform/.userProperties"]

        # assert the values are the same
        self.assertEqual(len(up.properties), 2)
        self.assertEqual(up.properties["foo"].values[0], "bar")
        self.assertEqual(up.properties["bar"].values[0], 1.0)

        # use the alembic python api directly
        ph = a.top.children["x"].schema.getUserProperties().propertyheaders
        self.assertEqual(len(ph), 2)
        self.assertEqual(ph[0].getName(), "foo")
        self.assertEqual(ph[1].getName(), "bar")

        # recreate these properties and re-export
        # (test for AttributeError: 'OObject' object has no attribute 'getSchema')
        p1 = up.properties["foo"] = cask.Property()
        p2 = up.properties["bar"] = cask.Property()
        p1.set_value("baz")
        p2.set_value(2.0)
        a.write_to_file(test_file_2)

    def test_issue_26(self):
        """github issue #26: verify .ops and .vals pod and extent"""
        
        test_file_1 = os.path.join(TEMPDIR, "cask_test_issue_26.abc")

        # create some scalar properties with array values
        a = cask.Archive()
        a.top.children["foo"] = cask.Xform()
        p1 = a.top.children["foo"].properties["p1"] = cask.Property()
        p2 = a.top.children["foo"].properties["p2"] = cask.Property()
        p3 = a.top.children["foo"].properties["p3"] = cask.Property()
        p4 = a.top.children["foo"].properties["p4"] = cask.Property()

        ca = imath.UnsignedCharArray(6)
        for i in range(6):
            ca[i] = i
        p1.set_value(ca)

        da = imath.DoubleArray(12)
        for i in range(12):
            da[i] = i * 3.0
        p2.set_value(da)

        va = imath.V3fArray(3)
        for i in range(3):
            va[i] = imath.V3f(i, i*2.0, i*3.0)
        p3.set_value(va)

        p4.set_value([imath.V3f(1, 2, 3), imath.V3f(4, 5, 6), imath.V3f(7, 8, 9)])

        a.write_to_file(test_file_1)
        a.close()

        # open the exported file and assert properties are scalar
        a = cask.Archive(test_file_1)
        p1 = a.top.children["foo"].properties["p1"]
        p2 = a.top.children["foo"].properties["p2"]
        p3 = a.top.children["foo"].properties["p3"]
        p4 = a.top.children["foo"].properties["p4"]
        self.assertTrue(p1.iobject.isArray())
        self.assertTrue(p2.iobject.isArray())
        self.assertTrue(p3.iobject.isArray())
        self.assertTrue(p4.iobject.isArray())
        a.close()

    def test_issue_8(self):
        """creating arbGeomParams on geom objects
        https://github.com/alembic/cask/issues/8"""

        test_file_1 = os.path.join(TEMPDIR, "cask_test_issue_8.abc")

        a = cask.Archive()
        m = a.top.children["meshy"] = cask.PolyMesh()

        p1 = m.properties[".geom/.arbGeomParams/test"] = cask.Property()
        p1.set_value("somevalue")

        a.write_to_file(test_file_1)
        a.close()

        a1 = cask.Archive(test_file_1)
        m1 = a1.top.children["meshy"]
        self.assertTrue("test" in m1.properties[".geom/.arbGeomParams"].properties)

        self.assertEqual(m1.properties[".geom/.arbGeomParams/test"].values[0],
                "somevalue")

        a1.close()


if __name__ == '__main__':
    unittest.main()
