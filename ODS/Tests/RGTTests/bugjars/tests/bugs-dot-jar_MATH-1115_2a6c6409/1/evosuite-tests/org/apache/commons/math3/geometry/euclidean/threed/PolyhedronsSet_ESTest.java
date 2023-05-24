/*
 * This file was automatically generated by EvoSuite
 * Fri Dec 27 19:24:40 GMT 2019
 */

package org.apache.commons.math3.geometry.euclidean.threed;

import org.junit.Test;
import static org.junit.Assert.*;
import static org.evosuite.shaded.org.mockito.Mockito.*;
import static org.evosuite.runtime.EvoAssertions.*;
import java.util.Collection;
import java.util.LinkedList;
import org.apache.commons.math3.geometry.euclidean.threed.Euclidean3D;
import org.apache.commons.math3.geometry.euclidean.threed.Line;
import org.apache.commons.math3.geometry.euclidean.threed.Plane;
import org.apache.commons.math3.geometry.euclidean.threed.PolyhedronsSet;
import org.apache.commons.math3.geometry.euclidean.threed.Rotation;
import org.apache.commons.math3.geometry.euclidean.threed.RotationOrder;
import org.apache.commons.math3.geometry.euclidean.threed.SubPlane;
import org.apache.commons.math3.geometry.euclidean.threed.Vector3D;
import org.apache.commons.math3.geometry.euclidean.twod.Euclidean2D;
import org.apache.commons.math3.geometry.euclidean.twod.PolygonsSet;
import org.apache.commons.math3.geometry.euclidean.twod.Vector2D;
import org.apache.commons.math3.geometry.partitioning.AbstractSubHyperplane;
import org.apache.commons.math3.geometry.partitioning.BSPTree;
import org.apache.commons.math3.geometry.partitioning.Hyperplane;
import org.apache.commons.math3.geometry.partitioning.SubHyperplane;
import org.apache.commons.math3.geometry.partitioning.Transform;
import org.evosuite.runtime.EvoRunner;
import org.evosuite.runtime.EvoRunnerParameters;
import org.evosuite.runtime.ViolatedAssumptionAnswer;
import org.junit.runner.RunWith;

@RunWith(EvoRunner.class) @EvoRunnerParameters(mockJVMNonDeterminism = true, useVFS = true, useVNET = true, resetStaticState = true, separateClassLoader = true, useJEE = true) 
public class PolyhedronsSet_ESTest extends PolyhedronsSet_ESTest_scaffolding {

  @Test(timeout = 4000)
  public void test00()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet((-679.3572), 0.0, 0.0, 1.0, (-679.3572), 1.5360384725315293);
      assertFalse(polyhedronsSet0.isEmpty());
  }

  @Test(timeout = 4000)
  public void test01()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet((-1.0), (-1.0), (-1313.4743), 0.0, 0.0, (-1313.4743), (-1313.4743));
      assertTrue(polyhedronsSet0.isEmpty());
  }

  @Test(timeout = 4000)
  public void test02()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet((-2832.67), (-2832.67), 0.0, (-2832.67), 0.0, 0.0, (-2832.67));
      assertFalse(polyhedronsSet0.isFull());
  }

  @Test(timeout = 4000)
  public void test03()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(0.0, 1634.67898, 1634.67898, 0.0, 0.0, (-97.7));
      Vector3D vector3D0 = Vector3D.MINUS_K;
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.translate(vector3D0);
      assertFalse(polyhedronsSet1.isFull());
  }

  @Test(timeout = 4000)
  public void test04()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(0.0);
      Vector3D vector3D0 = Vector3D.NaN;
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.translate(vector3D0);
      assertNotSame(polyhedronsSet1, polyhedronsSet0);
  }

  @Test(timeout = 4000)
  public void test05()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet((-0.0018001876583522368), (-0.0018001876583522368), (-0.0018001876583522368), 1.0, (-0.0018001876583522368), 1.0, (-679.3572));
      Vector3D vector3D0 = Vector3D.PLUS_J;
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.translate(vector3D0);
      assertFalse(polyhedronsSet1.isEmpty());
  }

  @Test(timeout = 4000)
  public void test06()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet((-3127.26448664213), (-3127.26448664213), 4.0, (-3127.26448664213), 4.0, 4.0);
      BSPTree<Euclidean3D> bSPTree0 = polyhedronsSet0.getTree(true);
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.buildNew(bSPTree0);
      assertFalse(polyhedronsSet1.isFull());
  }

  @Test(timeout = 4000)
  public void test07()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(2399.495358798, 2399.495358798, 91.300840964717, 1.0E-10, 91.300840964717, 0.0);
      PolyhedronsSet polyhedronsSet1 = new PolyhedronsSet();
      BSPTree<Euclidean3D> bSPTree0 = polyhedronsSet1.getTree(false);
      PolyhedronsSet polyhedronsSet2 = polyhedronsSet0.buildNew(bSPTree0);
      assertNotSame(polyhedronsSet1, polyhedronsSet2);
  }

  @Test(timeout = 4000)
  public void test08()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(Double.POSITIVE_INFINITY, 0.0, Double.POSITIVE_INFINITY, 0.0, Double.POSITIVE_INFINITY, 0.0, 0.0);
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.buildNew((BSPTree<Euclidean3D>) null);
      assertNotSame(polyhedronsSet1, polyhedronsSet0);
  }

  @Test(timeout = 4000)
  public void test09()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(Double.POSITIVE_INFINITY, Double.POSITIVE_INFINITY, 5790.665, 0.0, 5790.665, 1943.8143, (-4134.54582323));
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.buildNew((BSPTree<Euclidean3D>) null);
      assertNotSame(polyhedronsSet0, polyhedronsSet1);
  }

  @Test(timeout = 4000)
  public void test10()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet((BSPTree<Euclidean3D>) null);
      // Undeclared exception!
      try { 
        polyhedronsSet0.translate((Vector3D) null);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.commons.math3.geometry.partitioning.AbstractRegion", e);
      }
  }

  @Test(timeout = 4000)
  public void test11()  throws Throwable  {
      Vector3D vector3D0 = new Vector3D(2343.447151774883, (-1899.8854200219));
      Plane plane0 = new Plane(vector3D0, (-1899.8854200219));
      PolygonsSet polygonsSet0 = new PolygonsSet(2343.447151774883);
      SubPlane subPlane0 = new SubPlane(plane0, polygonsSet0);
      BSPTree<Euclidean3D> bSPTree0 = new BSPTree<Euclidean3D>();
      BSPTree<Euclidean3D> bSPTree1 = new BSPTree<Euclidean3D>(subPlane0, bSPTree0, bSPTree0, plane0);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(bSPTree1);
      // Undeclared exception!
      try { 
        polyhedronsSet0.translate(vector3D0);
        fail("Expecting exception: ClassCastException");
      
      } catch(ClassCastException e) {
         //
         // org.apache.commons.math3.geometry.euclidean.threed.Plane cannot be cast to org.apache.commons.math3.geometry.partitioning.BoundaryAttribute
         //
         verifyException("org.apache.commons.math3.geometry.partitioning.AbstractRegion", e);
      }
  }

  @Test(timeout = 4000)
  public void test12()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      Vector3D vector3D0 = new Vector3D(1.5707963267948966, 0.0, 1.5707963267948966);
      Plane plane0 = new Plane(vector3D0, 1.5707963267948966);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane0);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0, 1020.3350588274237);
      Rotation rotation0 = new Rotation(vector3D0, vector3D0);
      // Undeclared exception!
      try { 
        polyhedronsSet0.rotate((Vector3D) null, rotation0);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
      }
  }

  @Test(timeout = 4000)
  public void test13()  throws Throwable  {
      Vector3D vector3D0 = Vector3D.MINUS_J;
      Plane plane0 = new Plane(vector3D0, vector3D0, 4.0);
      PolyhedronsSet polyhedronsSet0 = plane0.wholeSpace();
      Vector2D[] vector2DArray0 = new Vector2D[0];
      PolygonsSet polygonsSet0 = new PolygonsSet(4.0, vector2DArray0);
      SubPlane subPlane0 = new SubPlane(plane0, polygonsSet0);
      BSPTree<Euclidean3D> bSPTree0 = new BSPTree<Euclidean3D>();
      BSPTree<Euclidean3D> bSPTree1 = new BSPTree<Euclidean3D>(subPlane0, bSPTree0, bSPTree0, vector3D0);
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.buildNew(bSPTree1);
      RotationOrder rotationOrder0 = RotationOrder.ZYX;
      Rotation rotation0 = new Rotation(rotationOrder0, 4.0, 4.0, 4.0);
      // Undeclared exception!
      try { 
        polyhedronsSet1.rotate(vector3D0, rotation0);
        fail("Expecting exception: ClassCastException");
      
      } catch(ClassCastException e) {
         //
         // org.apache.commons.math3.geometry.euclidean.threed.Vector3D cannot be cast to org.apache.commons.math3.geometry.partitioning.BoundaryAttribute
         //
         verifyException("org.apache.commons.math3.geometry.partitioning.AbstractRegion", e);
      }
  }

  @Test(timeout = 4000)
  public void test14()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(0.0, 0.0, 0.0, 1.0, 0.0, 1.0, (-679.3572));
      Vector3D vector3D0 = new Vector3D(0.0, Double.POSITIVE_INFINITY, Double.POSITIVE_INFINITY);
      Rotation rotation0 = new Rotation(4150.56, 0.0, 4150.56, 1.0, true);
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.rotate(vector3D0, rotation0);
      Line line0 = new Line(vector3D0, vector3D0, 147.2237522509);
      // Undeclared exception!
      try { 
        polyhedronsSet1.firstIntersection(vector3D0, line0);
        fail("Expecting exception: IllegalStateException");
      
      } catch(IllegalStateException e) {
         //
         // illegal state: internal error, please fill a bug report at https://issues.apache.org/jira/browse/MATH
         //
         verifyException("org.apache.commons.math3.geometry.partitioning.AbstractRegion$BoundaryBuilder", e);
      }
  }

  @Test(timeout = 4000)
  public void test15()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      Vector3D vector3D0 = Vector3D.MINUS_J;
      Plane plane0 = new Plane(vector3D0, vector3D0, 880.2809682084987);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane0);
      Vector3D vector3D1 = new Vector3D(0.0, 0.0, 1.5707963267948966);
      Vector3D vector3D2 = Vector3D.NaN;
      Plane plane1 = new Plane(vector3D2, vector3D1, 1.5707963267948966);
      Transform<Euclidean3D, Euclidean2D> transform0 = (Transform<Euclidean3D, Euclidean2D>) mock(Transform.class, new ViolatedAssumptionAnswer());
      doReturn(plane1).when(transform0).apply(nullable(org.apache.commons.math3.geometry.partitioning.Hyperplane.class));
      AbstractSubHyperplane<Euclidean3D, Euclidean2D> abstractSubHyperplane0 = subPlane0.applyTransform(transform0);
      linkedList0.add((SubHyperplane<Euclidean3D>) abstractSubHyperplane0);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0, 1020.3350588274237);
      // Undeclared exception!
      try { 
        polyhedronsSet0.computeGeometricalProperties();
        fail("Expecting exception: IllegalStateException");
      
      } catch(IllegalStateException e) {
         //
         // illegal state: internal error, please fill a bug report at https://issues.apache.org/jira/browse/MATH
         //
         verifyException("org.apache.commons.math3.geometry.euclidean.twod.PolygonsSet", e);
      }
  }

  @Test(timeout = 4000)
  public void test16()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0);
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.buildNew((BSPTree<Euclidean3D>) null);
      // Undeclared exception!
      try { 
        polyhedronsSet1.computeGeometricalProperties();
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
      }
  }

  @Test(timeout = 4000)
  public void test17()  throws Throwable  {
      Object object0 = new Object();
      BSPTree<Euclidean3D> bSPTree0 = new BSPTree<Euclidean3D>(object0);
      Vector3D vector3D0 = Vector3D.PLUS_J;
      Plane plane0 = new Plane(vector3D0, 258.89107512038);
      PolygonsSet polygonsSet0 = new PolygonsSet(15.4607269897962, 258.89107512038, 15.4607269897962, (-2885.3558165), 3.5657055376960205);
      SubPlane subPlane0 = new SubPlane(plane0, polygonsSet0);
      BSPTree<Euclidean3D> bSPTree1 = bSPTree0.split(subPlane0);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(bSPTree1);
      // Undeclared exception!
      try { 
        polyhedronsSet0.computeGeometricalProperties();
        fail("Expecting exception: ClassCastException");
      
      } catch(ClassCastException e) {
         //
         // java.lang.Object cannot be cast to java.lang.Boolean
         //
         verifyException("org.apache.commons.math3.geometry.partitioning.AbstractRegion$BoundaryBuilder", e);
      }
  }

  @Test(timeout = 4000)
  public void test18()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      Vector3D vector3D0 = new Vector3D(0.0, 0.0, 1.5707963267948966);
      Plane plane0 = new Plane(vector3D0, 1.5707963267948966);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      Transform<Euclidean3D, Euclidean2D> transform0 = (Transform<Euclidean3D, Euclidean2D>) mock(Transform.class, new ViolatedAssumptionAnswer());
      doReturn((Hyperplane) null).when(transform0).apply(nullable(org.apache.commons.math3.geometry.partitioning.Hyperplane.class));
      AbstractSubHyperplane<Euclidean3D, Euclidean2D> abstractSubHyperplane0 = subPlane0.applyTransform(transform0);
      linkedList0.add((SubHyperplane<Euclidean3D>) abstractSubHyperplane0);
      PolyhedronsSet polyhedronsSet0 = null;
      try {
        polyhedronsSet0 = new PolyhedronsSet(linkedList0, 1020.3350588274237);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.commons.math3.geometry.partitioning.AbstractRegion", e);
      }
  }

  @Test(timeout = 4000)
  public void test19()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = null;
      try {
        polyhedronsSet0 = new PolyhedronsSet((Collection<SubHyperplane<Euclidean3D>>) null);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.commons.math3.geometry.partitioning.AbstractRegion", e);
      }
  }

  @Test(timeout = 4000)
  public void test20()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = null;
      try {
        polyhedronsSet0 = new PolyhedronsSet((-967.63282), (-967.63282), (-967.63282), (-967.63282), 3.0, 1.0E-20, (-967.63282));
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
      }
  }

  @Test(timeout = 4000)
  public void test21()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      Vector3D vector3D0 = Vector3D.MINUS_J;
      Vector3D vector3D1 = Vector3D.crossProduct(vector3D0, vector3D0);
      Plane plane0 = new Plane(vector3D1, vector3D0, 880.2809682084987);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane0);
      Vector3D vector3D2 = new Vector3D(0.0, 0.0, 1.5707963267948966);
      Vector3D vector3D3 = Vector3D.NaN;
      Plane plane1 = new Plane(vector3D3, vector3D2, 1.5707963267948966);
      SubPlane subPlane1 = plane1.wholeHyperplane();
      AbstractSubHyperplane<Euclidean3D, Euclidean2D> abstractSubHyperplane0 = subPlane1.copySelf();
      linkedList0.add((SubHyperplane<Euclidean3D>) abstractSubHyperplane0);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0, 1020.3350588274237);
      Line line0 = plane1.intersection(plane1);
      // Undeclared exception!
      try { 
        polyhedronsSet0.firstIntersection(vector3D2, line0);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.commons.math3.geometry.euclidean.threed.Plane", e);
      }
  }

  @Test(timeout = 4000)
  public void test22()  throws Throwable  {
      BSPTree<Euclidean3D> bSPTree0 = new BSPTree<Euclidean3D>();
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(bSPTree0, 3.0);
      assertEquals(3.0, polyhedronsSet0.getTolerance(), 0.01);
  }

  @Test(timeout = 4000)
  public void test23()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(0.0);
      RotationOrder rotationOrder0 = RotationOrder.YZY;
      Vector3D vector3D0 = rotationOrder0.getA3();
      Rotation rotation0 = new Rotation(rotationOrder0, 0.0, 0.0, 0.0);
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.rotate(vector3D0, rotation0);
      assertEquals(0.0, polyhedronsSet1.getTolerance(), 0.01);
  }

  @Test(timeout = 4000)
  public void test24()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      Vector3D vector3D0 = Vector3D.MINUS_J;
      Plane plane0 = new Plane(vector3D0, vector3D0, 880.2809682084987);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane0);
      Vector3D vector3D1 = new Vector3D(0.0, 0.0, 1.5707963267948966);
      Vector3D vector3D2 = Vector3D.NaN;
      Plane plane1 = new Plane(vector3D2, vector3D1, 1.5707963267948966);
      SubPlane subPlane1 = plane1.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane1);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0, 1020.3350588274237);
      Line line0 = plane1.intersection(plane0);
      polyhedronsSet0.firstIntersection(vector3D1, line0);
      Rotation rotation0 = new Rotation(vector3D1, vector3D1);
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.rotate(vector3D0, rotation0);
      assertNotSame(polyhedronsSet0, polyhedronsSet1);
  }

  @Test(timeout = 4000)
  public void test25()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      Vector3D vector3D0 = Vector3D.MINUS_J;
      Vector3D vector3D1 = Vector3D.crossProduct(vector3D0, vector3D0);
      Plane plane0 = new Plane(vector3D1, vector3D0, 1.5707963267948966);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane0);
      Vector3D vector3D2 = new Vector3D(0.07763901580874948, 0.0, 1.5707963267948966);
      Plane plane1 = new Plane(vector3D0, vector3D2, 1.5707963267948966);
      Transform<Euclidean3D, Euclidean2D> transform0 = (Transform<Euclidean3D, Euclidean2D>) mock(Transform.class, new ViolatedAssumptionAnswer());
      doReturn(plane1).when(transform0).apply(nullable(org.apache.commons.math3.geometry.partitioning.Hyperplane.class));
      AbstractSubHyperplane<Euclidean3D, Euclidean2D> abstractSubHyperplane0 = subPlane0.applyTransform(transform0);
      linkedList0.add((SubHyperplane<Euclidean3D>) abstractSubHyperplane0);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0, 1020.3350588274237);
      Line line0 = plane1.intersection(plane0);
      SubHyperplane<Euclidean3D> subHyperplane0 = polyhedronsSet0.firstIntersection(vector3D2, line0);
      assertNull(subHyperplane0);
  }

  @Test(timeout = 4000)
  public void test26()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      double[] doubleArray0 = new double[3];
      doubleArray0[2] = 647.54314121526;
      Vector3D vector3D0 = new Vector3D(doubleArray0);
      Plane plane0 = new Plane(vector3D0, vector3D0, 0.0);
      Vector3D vector3D1 = new Vector3D(5108.83764990328, 647.54314121526, 0.0);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane0);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0);
      Line line0 = plane0.intersection(plane0);
      // Undeclared exception!
      try { 
        polyhedronsSet0.firstIntersection(vector3D1, line0);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.commons.math3.geometry.euclidean.threed.Plane", e);
      }
  }

  @Test(timeout = 4000)
  public void test27()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      Vector3D vector3D0 = Vector3D.MINUS_J;
      Plane plane0 = new Plane(vector3D0, vector3D0, 1.5707963267948966);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane0);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0, 1020.3350588274237);
      Line line0 = plane0.intersection(plane0);
      SubHyperplane<Euclidean3D> subHyperplane0 = polyhedronsSet0.firstIntersection(vector3D0, line0);
      assertFalse(linkedList0.contains(subHyperplane0));
  }

  @Test(timeout = 4000)
  public void test28()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      Vector3D vector3D0 = Vector3D.POSITIVE_INFINITY;
      Plane plane0 = new Plane(vector3D0, 1.5707963267949);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane0);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0, 1020.3350588274237);
      Line line0 = plane0.intersection(plane0);
      SubHyperplane<Euclidean3D> subHyperplane0 = polyhedronsSet0.firstIntersection(vector3D0, line0);
      assertFalse(linkedList0.contains(subHyperplane0));
  }

  @Test(timeout = 4000)
  public void test29()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(1.0E-10, 2508.735645368426, 1.0E-10, 2508.735645368426, 1.0E-10, 1640.85, 1.0E-10);
      // Undeclared exception!
      polyhedronsSet0.computeGeometricalProperties();
  }

  @Test(timeout = 4000)
  public void test30()  throws Throwable  {
      LinkedList<SubHyperplane<Euclidean3D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean3D>>();
      Vector3D vector3D0 = Vector3D.MINUS_J;
      Plane plane0 = new Plane(vector3D0, vector3D0, 1.5707963267948966);
      SubPlane subPlane0 = plane0.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane0);
      Vector3D vector3D1 = new Vector3D(0.07763901580874948, 0.0, 1.5707963267948966);
      Plane plane1 = new Plane(vector3D0, vector3D1, 1.5707963267948966);
      SubPlane subPlane1 = plane1.wholeHyperplane();
      linkedList0.add((SubHyperplane<Euclidean3D>) subPlane1);
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(linkedList0, 1020.3350588274237);
      polyhedronsSet0.computeGeometricalProperties();
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.translate(vector3D1);
      assertNotSame(polyhedronsSet1, polyhedronsSet0);
  }

  @Test(timeout = 4000)
  public void test31()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet((-2885.3558165), (-1160.685521225842), (-1898.5004), (-1160.685521225842), (-1898.5004), (-2885.3558165));
      Rotation rotation0 = new Rotation((-3.4028234663852886E38), (-2885.3558165), 0.0, 54.54924150353084, true);
      PolyhedronsSet polyhedronsSet1 = polyhedronsSet0.rotate((Vector3D) null, rotation0);
      assertNotSame(polyhedronsSet0, polyhedronsSet1);
  }

  @Test(timeout = 4000)
  public void test32()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet();
      BSPTree<Euclidean3D> bSPTree0 = polyhedronsSet0.getTree(false);
      Vector3D vector3D0 = new Vector3D(574.03006069439, 1557.3482016879, 1557.3482016879);
      Plane plane0 = new Plane(vector3D0, vector3D0, 574.03006069439);
      LinkedList<SubHyperplane<Euclidean2D>> linkedList0 = new LinkedList<SubHyperplane<Euclidean2D>>();
      PolygonsSet polygonsSet0 = new PolygonsSet(linkedList0, 1557.3482016879);
      SubPlane subPlane0 = new SubPlane(plane0, polygonsSet0);
      BSPTree<Euclidean3D> bSPTree1 = bSPTree0.split(subPlane0);
      PolyhedronsSet polyhedronsSet1 = new PolyhedronsSet(bSPTree1, 574.03006069439);
      double double0 = polyhedronsSet1.getSize();
      assertEquals(0.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test33()  throws Throwable  {
      PolyhedronsSet polyhedronsSet0 = new PolyhedronsSet(0.0, 0.0, 0.0, 1.0, 0.0, 1.0, (-679.3572));
      Vector3D vector3D0 = Vector3D.MINUS_J;
      Vector3D vector3D1 = vector3D0.negate();
      Line line0 = new Line(vector3D1, vector3D0, (-679.3572));
      SubHyperplane<Euclidean3D> subHyperplane0 = polyhedronsSet0.firstIntersection(vector3D1, line0);
      assertNotNull(subHyperplane0);
      assertFalse(polyhedronsSet0.isEmpty());
  }
}