/*
 * This file was automatically generated by EvoSuite
 * Sat Dec 28 10:29:22 GMT 2019
 */

package org.apache.commons.math4.special;

import org.junit.Test;
import static org.junit.Assert.*;
import static org.evosuite.runtime.EvoAssertions.*;
import org.apache.commons.math4.special.Gamma;
import org.evosuite.runtime.EvoRunner;
import org.evosuite.runtime.EvoRunnerParameters;
import org.junit.runner.RunWith;

@RunWith(EvoRunner.class) @EvoRunnerParameters(mockJVMNonDeterminism = true, useVFS = true, useVNET = true, resetStaticState = true, separateClassLoader = true, useJEE = true) 
public class Gamma_ESTest extends Gamma_ESTest_scaffolding {

  @Test(timeout = 4000)
  public void test00()  throws Throwable  {
      double double0 = Gamma.gamma(2.0);
      assertEquals(1.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test01()  throws Throwable  {
      double double0 = Gamma.gamma(0.0);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test02()  throws Throwable  {
      double double0 = Gamma.logGamma1p((-0.5));
      assertEquals(0.5723649429247001, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test03()  throws Throwable  {
      double double0 = Gamma.gamma(1.5);
      assertEquals(0.886226925452758, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test04()  throws Throwable  {
      double double0 = Gamma.invGamma1pm1((-0.5));
      assertEquals((-0.4358104164522437), double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test05()  throws Throwable  {
      double double0 = Gamma.trigamma((-14.63924921113668));
      assertEquals(11.962360147949699, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test06()  throws Throwable  {
      double double0 = Gamma.digamma((-797.5));
      assertEquals(6.682108660105181, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test07()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ(64.6349, 2.5066282746310007);
      assertEquals(1.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test08()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ(0.0, 7.984485303520287E21);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test09()  throws Throwable  {
      // Undeclared exception!
      try { 
        Gamma.regularizedGammaP(2.5, 1.5728330277104463E-12, 1.5728330277104463E-12, (-723));
        fail("Expecting exception: RuntimeException");
      
      } catch(RuntimeException e) {
         //
         // illegal state: maximal count (-723) exceeded
         //
         verifyException("org.apache.commons.math4.special.Gamma", e);
      }
  }

  @Test(timeout = 4000)
  public void test10()  throws Throwable  {
      double double0 = Gamma.regularizedGammaP(6.8716741130671986E-9, 7.146161576402001);
      assertEquals(0.999999999999327, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test11()  throws Throwable  {
      double double0 = Gamma.logGamma(7.704139560392505);
      assertEquals(7.934717687839098, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test12()  throws Throwable  {
      double double0 = Gamma.logGamma(0.0);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test13()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ(3.257488853378793E-70, 3409.1, 3.257488853378793E-70, 1354);
      assertEquals(0.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test14()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ(1.200354814529419, 882.066797);
      assertEquals(0.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test15()  throws Throwable  {
      double double0 = Gamma.logGamma1p(0.0);
      assertEquals(-0.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test16()  throws Throwable  {
      double double0 = Gamma.logGamma(1.276776446174077);
      assertEquals((-0.10393719404860506), double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test17()  throws Throwable  {
      double double0 = Gamma.logGamma1p(6.8716741130671986E-9);
      assertEquals((-3.966437903323919E-9), double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test18()  throws Throwable  {
      double double0 = Gamma.invGamma1pm1(0.6990466710183736);
      assertEquals(0.10076583543726556, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test19()  throws Throwable  {
      double double0 = Gamma.invGamma1pm1(0.0);
      assertEquals(0.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test20()  throws Throwable  {
      double double0 = Gamma.lanczos(3.09768273342776E-42);
      assertEquals(32.94631867978169, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test21()  throws Throwable  {
      double double0 = Gamma.trigamma(882.066797);
      assertEquals(0.0011343438706800841, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test22()  throws Throwable  {
      double double0 = Gamma.digamma(1269.724738);
      assertEquals(7.146161576402001, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test23()  throws Throwable  {
      // Undeclared exception!
      try { 
        Gamma.regularizedGammaQ(1732.4888255, 2567.4, 2830.914873403111, (-2535));
        fail("Expecting exception: RuntimeException");
      
      } catch(RuntimeException e) {
         //
         // illegal state: Continued fraction convergents failed to converge (in less than -2,535 iterations) for value 2,567.4
         //
         verifyException("org.apache.commons.math4.util.ContinuedFraction", e);
      }
  }

  @Test(timeout = 4000)
  public void test24()  throws Throwable  {
      // Undeclared exception!
      try { 
        Gamma.regularizedGammaQ(1961.88115229966, 1.0, (-158.982838876149), 7);
        fail("Expecting exception: RuntimeException");
      
      } catch(RuntimeException e) {
         //
         // illegal state: maximal count (7) exceeded
         //
         verifyException("org.apache.commons.math4.special.Gamma", e);
      }
  }

  @Test(timeout = 4000)
  public void test25()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ(Double.NaN, Double.NaN, Double.NaN, (-201));
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test26()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ((-2973.9788068964467), Double.NaN, (double) 0, (-723));
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test27()  throws Throwable  {
      double double0 = Gamma.regularizedGammaP(5.883385169571802E-83, 0.5, 0.0, 690);
      assertEquals(0.9999999999999893, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test28()  throws Throwable  {
      // Undeclared exception!
      try { 
        Gamma.regularizedGammaP(1.1887460088806523E235, 1.1887460088806523E235, 0.0, 826);
        fail("Expecting exception: RuntimeException");
      
      } catch(RuntimeException e) {
         //
         // illegal state: Continued fraction convergents diverged to +/- infinity for value 11,887,460,088,806,523,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000
         //
         verifyException("org.apache.commons.math4.util.ContinuedFraction", e);
      }
  }

  @Test(timeout = 4000)
  public void test29()  throws Throwable  {
      double double0 = Gamma.regularizedGammaP(0.0, 581.1, 2.5066282746310007, 1217);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test30()  throws Throwable  {
      double double0 = Gamma.regularizedGammaP(0.0, Double.NaN, Double.NaN, 336);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test31()  throws Throwable  {
      double double0 = Gamma.regularizedGammaP(3240.471474205515, (-3.2282195629939283E41), 1.4366366863250732, 858);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test32()  throws Throwable  {
      double double0 = Gamma.logGamma(715.22807417);
      assertEquals(3983.313776592188, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test33()  throws Throwable  {
      double double0 = Gamma.logGamma(2.1743961811521265E-4);
      assertEquals(8.433463893167964, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test34()  throws Throwable  {
      double double0 = Gamma.gamma((-556.2507));
      assertEquals(-0.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test35()  throws Throwable  {
      double double0 = Gamma.gamma(17.775167657135782);
      assertEquals(1.87158627695075E14, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test36()  throws Throwable  {
      double double0 = Gamma.gamma(1.0157048955659895);
      assertEquals(0.9911753764030692, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test37()  throws Throwable  {
      double double0 = Gamma.gamma((-0.04219773455554433));
      assertEquals((-24.318599161589667), double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test38()  throws Throwable  {
      double double0 = Gamma.gamma(7.984485303520287E21);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test39()  throws Throwable  {
      double double0 = Gamma.gamma((-35.0));
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test40()  throws Throwable  {
      try { 
        Gamma.logGamma1p(1204.0101);
        fail("Expecting exception: RuntimeException");
      
      } catch(RuntimeException e) {
         //
         // 1,204.01 is larger than the maximum (1.5)
         //
         verifyException("org.apache.commons.math4.special.Gamma", e);
      }
  }

  @Test(timeout = 4000)
  public void test41()  throws Throwable  {
      try { 
        Gamma.logGamma1p((-1.0));
        fail("Expecting exception: RuntimeException");
      
      } catch(RuntimeException e) {
         //
         // -1 is smaller than the minimum (-0.5)
         //
         verifyException("org.apache.commons.math4.special.Gamma", e);
      }
  }

  @Test(timeout = 4000)
  public void test42()  throws Throwable  {
      double double0 = Gamma.invGamma1pm1(1.4366366863250732);
      assertEquals((-0.21425508494674791), double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test43()  throws Throwable  {
      // Undeclared exception!
      try { 
        Gamma.invGamma1pm1(2.441415786743164);
        fail("Expecting exception: RuntimeException");
      
      } catch(RuntimeException e) {
         //
         // 2.441 is larger than the maximum (1.5)
         //
         verifyException("org.apache.commons.math4.special.Gamma", e);
      }
  }

  @Test(timeout = 4000)
  public void test44()  throws Throwable  {
      // Undeclared exception!
      try { 
        Gamma.invGamma1pm1((-1507.0942446161898));
        fail("Expecting exception: RuntimeException");
      
      } catch(RuntimeException e) {
         //
         // -1,507.094 is smaller than the minimum (-0.5)
         //
         verifyException("org.apache.commons.math4.special.Gamma", e);
      }
  }

  @Test(timeout = 4000)
  public void test45()  throws Throwable  {
      double double0 = Gamma.trigamma(2.167272474431968E-8);
      assertEquals(2.1289868036714918E15, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test46()  throws Throwable  {
      double double0 = Gamma.trigamma(0.0);
      assertEquals(Double.POSITIVE_INFINITY, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test47()  throws Throwable  {
      double double0 = Gamma.trigamma(Double.NEGATIVE_INFINITY);
      assertEquals(Double.NEGATIVE_INFINITY, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test48()  throws Throwable  {
      double double0 = Gamma.trigamma(Double.NaN);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test49()  throws Throwable  {
      double double0 = Gamma.digamma(3.09768273342776E-42);
      assertEquals((-3.2282195629939283E41), double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test50()  throws Throwable  {
      double double0 = Gamma.digamma(0.0);
      assertEquals(Double.NEGATIVE_INFINITY, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test51()  throws Throwable  {
      double double0 = Gamma.digamma(Double.NaN);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test52()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ(3.09768273342776E-42, 0.0, (-1871.3655864061225), 858);
      assertEquals(1.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test53()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ(0.39164922110384404, (-452.19), 0.5215104818344116, 2292);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test54()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ((-1126.0), 0.0, 241.6535, 2021);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test55()  throws Throwable  {
      double double0 = Gamma.regularizedGammaP(1.8755581378936768, 0.0, 1.0152035576959588, (-3992));
      assertEquals(0.0, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test56()  throws Throwable  {
      double double0 = Gamma.regularizedGammaP((-1682.5), 1.0152035576959588);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test57()  throws Throwable  {
      double double0 = Gamma.regularizedGammaP(Double.NaN, (double) 3526, (double) 3526, 0);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test58()  throws Throwable  {
      double double0 = Gamma.logGamma(0.9999999999999971);
      assertEquals(1.6661791155048086E-15, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test59()  throws Throwable  {
      double double0 = Gamma.logGamma((-6.4304548177935305E-6));
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test60()  throws Throwable  {
      double double0 = Gamma.logGamma(Double.NaN);
      assertEquals(Double.NaN, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test61()  throws Throwable  {
      double double0 = Gamma.regularizedGammaQ(6.8716741130671986E-9, 6.8716741130671986E-9);
      assertEquals(1.251925648704244E-7, double0, 0.01);
  }

  @Test(timeout = 4000)
  public void test62()  throws Throwable  {
      double double0 = Gamma.regularizedGammaP(4051.392932455604, 1204.0101);
      assertEquals(0.0, double0, 0.01);
  }
}