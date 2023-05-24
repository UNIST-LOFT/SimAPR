/*
 * This file was automatically generated by EvoSuite
 * Wed Dec 25 20:46:21 GMT 2019
 */

package org.apache.accumulo.core.iterators.user;

import org.junit.Test;
import static org.junit.Assert.*;
import static org.evosuite.shaded.org.mockito.Mockito.*;
import static org.evosuite.runtime.EvoAssertions.*;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.PatternSyntaxException;
import org.apache.accumulo.core.client.IteratorSetting;
import org.apache.accumulo.core.data.Key;
import org.apache.accumulo.core.data.Value;
import org.apache.accumulo.core.iterators.ColumnFamilyCounter;
import org.apache.accumulo.core.iterators.DevNull;
import org.apache.accumulo.core.iterators.FirstEntryInRowIterator;
import org.apache.accumulo.core.iterators.IteratorEnvironment;
import org.apache.accumulo.core.iterators.OptionDescriber;
import org.apache.accumulo.core.iterators.SortedKeyValueIterator;
import org.apache.accumulo.core.iterators.user.RegExFilter;
import org.evosuite.runtime.EvoRunner;
import org.evosuite.runtime.EvoRunnerParameters;
import org.evosuite.runtime.ViolatedAssumptionAnswer;
import org.junit.runner.RunWith;

@RunWith(EvoRunner.class) @EvoRunnerParameters(mockJVMNonDeterminism = true, useVFS = true, useVNET = true, resetStaticState = true, separateClassLoader = true, useJEE = true) 
public class RegExFilter_ESTest extends RegExFilter_ESTest_scaffolding {

  @Test(timeout = 4000)
  public void test00()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      OptionDescriber.IteratorOptions optionDescriber_IteratorOptions0 = regExFilter0.describeOptions();
      Key key0 = new Key("UTF-8");
      FirstEntryInRowIterator firstEntryInRowIterator0 = new FirstEntryInRowIterator();
      IteratorEnvironment iteratorEnvironment0 = mock(IteratorEnvironment.class, new ViolatedAssumptionAnswer());
      regExFilter0.init(firstEntryInRowIterator0, optionDescriber_IteratorOptions0.namedOptions, iteratorEnvironment0);
      // Undeclared exception!
      try { 
        regExFilter0.accept(key0, (Value) null);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.accumulo.core.iterators.user.RegExFilter", e);
      }
  }

  @Test(timeout = 4000)
  public void test01()  throws Throwable  {
      IteratorSetting iteratorSetting0 = new IteratorSetting(3451, " ~*_EnT=U^8i\"50", "5$H%a:>TEIRL:$ql_");
      Map<String, String> map0 = iteratorSetting0.getProperties();
      RegExFilter.setRegexs(iteratorSetting0, "Invalid size: ", "sQ", "Og*NlIM{Mx'Mz", "hTVJ:jr", true);
      RegExFilter regExFilter0 = new RegExFilter();
      // Undeclared exception!
      try { 
        regExFilter0.validateOptions(map0);
        fail("Expecting exception: PatternSyntaxException");
      
      } catch(PatternSyntaxException e) {
         //
         // Illegal repetition near index 6
         // Og*NlIM{Mx'Mz
         //       ^
         //
         verifyException("java.util.regex.Pattern", e);
      }
  }

  @Test(timeout = 4000)
  public void test02()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      // Undeclared exception!
      try { 
        regExFilter0.validateOptions((Map<String, String>) null);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.accumulo.core.iterators.Filter", e);
      }
  }

  @Test(timeout = 4000)
  public void test03()  throws Throwable  {
      // Undeclared exception!
      try { 
        RegExFilter.setEncoding((IteratorSetting) null, "org.apache.accumulo.core.iterators.user.RegExFilter");
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.accumulo.core.iterators.user.RegExFilter", e);
      }
  }

  @Test(timeout = 4000)
  public void test04()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      ColumnFamilyCounter columnFamilyCounter0 = new ColumnFamilyCounter();
      TreeMap<String, String> treeMap0 = new TreeMap<String, String>();
      treeMap0.put("colfRegex", "(*Zf4k2.ULO");
      IteratorEnvironment iteratorEnvironment0 = mock(IteratorEnvironment.class, new ViolatedAssumptionAnswer());
      // Undeclared exception!
      try { 
        regExFilter0.init(columnFamilyCounter0, treeMap0, iteratorEnvironment0);
        fail("Expecting exception: PatternSyntaxException");
      
      } catch(PatternSyntaxException e) {
         //
         // Dangling meta character '*' near index 1
         // (*Zf4k2.ULO
         //  ^
         //
         verifyException("java.util.regex.Pattern", e);
      }
  }

  @Test(timeout = 4000)
  public void test05()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      IteratorEnvironment iteratorEnvironment0 = mock(IteratorEnvironment.class, new ViolatedAssumptionAnswer());
      // Undeclared exception!
      try { 
        regExFilter0.init(regExFilter0, (Map<String, String>) null, iteratorEnvironment0);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.accumulo.core.iterators.Filter", e);
      }
  }

  @Test(timeout = 4000)
  public void test06()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      OptionDescriber.IteratorOptions optionDescriber_IteratorOptions0 = regExFilter0.describeOptions();
      IteratorEnvironment iteratorEnvironment0 = mock(IteratorEnvironment.class, new ViolatedAssumptionAnswer());
      DevNull devNull0 = new DevNull();
      IteratorEnvironment iteratorEnvironment1 = mock(IteratorEnvironment.class, new ViolatedAssumptionAnswer());
      regExFilter0.init(devNull0, optionDescriber_IteratorOptions0.namedOptions, iteratorEnvironment1);
      // Undeclared exception!
      try { 
        regExFilter0.deepCopy(iteratorEnvironment0);
        fail("Expecting exception: UnsupportedOperationException");
      
      } catch(UnsupportedOperationException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.accumulo.core.iterators.DevNull", e);
      }
  }

  @Test(timeout = 4000)
  public void test07()  throws Throwable  {
      Class<org.apache.accumulo.core.iterators.WholeRowIterator> class0 = org.apache.accumulo.core.iterators.WholeRowIterator.class;
      IteratorSetting iteratorSetting0 = new IteratorSetting(27, class0);
      RegExFilter.setEncoding(iteratorSetting0, "");
      assertFalse(iteratorSetting0.hasProperties());
  }

  @Test(timeout = 4000)
  public void test08()  throws Throwable  {
      Class<org.apache.accumulo.core.iterators.WholeRowIterator> class0 = org.apache.accumulo.core.iterators.WholeRowIterator.class;
      IteratorSetting iteratorSetting0 = new IteratorSetting(27, class0);
      RegExFilter.setRegexs(iteratorSetting0, "$G77qi>10WpKh", "", "$G77qi>10WpKh", "", false);
      assertTrue(iteratorSetting0.hasProperties());
  }

  @Test(timeout = 4000)
  public void test09()  throws Throwable  {
      IteratorSetting iteratorSetting0 = new IteratorSetting(3451, " ~*_EnT=U^8i\"50", "5$H%a:>TEIRL:$ql_");
      RegExFilter.setRegexs(iteratorSetting0, "Invalid size: ", (String) null, "Invalid size: ", "9*%um=^suP_JQ", true);
      assertEquals(" ~*_EnT=U^8i\"50", iteratorSetting0.getName());
  }

  @Test(timeout = 4000)
  public void test10()  throws Throwable  {
      // Undeclared exception!
      try { 
        RegExFilter.setRegexs((IteratorSetting) null, (String) null, (String) null, (String) null, (String) null, true);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("org.apache.accumulo.core.iterators.user.RegExFilter", e);
      }
  }

  @Test(timeout = 4000)
  public void test11()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      OptionDescriber.IteratorOptions optionDescriber_IteratorOptions0 = regExFilter0.describeOptions();
      boolean boolean0 = regExFilter0.validateOptions(optionDescriber_IteratorOptions0.namedOptions);
      assertFalse(boolean0);
      assertEquals("The RegExFilter/Iterator allows you to filter for key/value pairs based on regular expressions", optionDescriber_IteratorOptions0.getDescription());
      assertEquals("regex", optionDescriber_IteratorOptions0.getName());
  }

  @Test(timeout = 4000)
  public void test12()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      TreeMap<String, String> treeMap0 = new TreeMap<String, String>();
      boolean boolean0 = regExFilter0.validateOptions(treeMap0);
      assertTrue(boolean0);
  }

  @Test(timeout = 4000)
  public void test13()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      ColumnFamilyCounter columnFamilyCounter0 = new ColumnFamilyCounter();
      TreeMap<String, String> treeMap0 = new TreeMap<String, String>();
      treeMap0.put("colfRegex", "fcUmOrGi^n<k");
      IteratorEnvironment iteratorEnvironment0 = mock(IteratorEnvironment.class, new ViolatedAssumptionAnswer());
      regExFilter0.init(columnFamilyCounter0, treeMap0, iteratorEnvironment0);
      byte[] byteArray0 = new byte[5];
      Key key0 = new Key(byteArray0, byteArray0, byteArray0, byteArray0, (byte)21);
      boolean boolean0 = regExFilter0.accept(key0, (Value) null);
      assertFalse(boolean0);
  }

  @Test(timeout = 4000)
  public void test14()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      ColumnFamilyCounter columnFamilyCounter0 = new ColumnFamilyCounter();
      TreeMap<String, String> treeMap0 = new TreeMap<String, String>();
      treeMap0.put("rowRegex", "orFields");
      IteratorEnvironment iteratorEnvironment0 = mock(IteratorEnvironment.class, new ViolatedAssumptionAnswer());
      regExFilter0.init(columnFamilyCounter0, treeMap0, iteratorEnvironment0);
      byte[] byteArray0 = new byte[5];
      Key key0 = new Key(byteArray0, byteArray0, byteArray0, byteArray0, (byte)21);
      boolean boolean0 = regExFilter0.accept(key0, (Value) null);
      assertFalse(boolean0);
  }

  @Test(timeout = 4000)
  public void test15()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      ColumnFamilyCounter columnFamilyCounter0 = new ColumnFamilyCounter();
      TreeMap<String, String> treeMap0 = new TreeMap<String, String>();
      treeMap0.put("colqRegex", "encoding");
      IteratorEnvironment iteratorEnvironment0 = mock(IteratorEnvironment.class, new ViolatedAssumptionAnswer());
      regExFilter0.init(columnFamilyCounter0, treeMap0, iteratorEnvironment0);
      byte[] byteArray0 = new byte[5];
      Key key0 = new Key(byteArray0, byteArray0, byteArray0, byteArray0, (byte)21);
      boolean boolean0 = regExFilter0.accept(key0, (Value) null);
      assertFalse(boolean0);
  }

  @Test(timeout = 4000)
  public void test16()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      ColumnFamilyCounter columnFamilyCounter0 = new ColumnFamilyCounter();
      TreeMap<String, String> treeMap0 = new TreeMap<String, String>();
      treeMap0.put("colqRegex", "encoding");
      IteratorEnvironment iteratorEnvironment0 = mock(IteratorEnvironment.class, new ViolatedAssumptionAnswer());
      regExFilter0.init(columnFamilyCounter0, treeMap0, iteratorEnvironment0);
      SortedKeyValueIterator<Key, Value> sortedKeyValueIterator0 = regExFilter0.deepCopy((IteratorEnvironment) null);
      assertNotSame(regExFilter0, sortedKeyValueIterator0);
  }

  @Test(timeout = 4000)
  public void test17()  throws Throwable  {
      RegExFilter regExFilter0 = new RegExFilter();
      // Undeclared exception!
      try { 
        regExFilter0.deepCopy((IteratorEnvironment) null);
        fail("Expecting exception: IllegalStateException");
      
      } catch(IllegalStateException e) {
         //
         // getting null source
         //
         verifyException("org.apache.accumulo.core.iterators.WrappingIterator", e);
      }
  }
}