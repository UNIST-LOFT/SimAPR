/*
 * This file was automatically generated by EvoSuite
 * Tue Dec 10 20:06:13 GMT 2019
 */

package com.alibaba.dubbo.rpc.cluster.router.condition;

import org.junit.Test;
import static org.junit.Assert.*;
import static org.evosuite.runtime.EvoAssertions.*;
import com.alibaba.dubbo.common.URL;
import com.alibaba.dubbo.rpc.Invocation;
import com.alibaba.dubbo.rpc.Invoker;
import com.alibaba.dubbo.rpc.RpcInvocation;
import com.alibaba.dubbo.rpc.cluster.Router;
import com.alibaba.dubbo.rpc.cluster.router.MockInvokersSelector;
import com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter;
import com.alibaba.dubbo.rpc.protocol.InvokerWrapper;
import java.util.LinkedList;
import java.util.List;
import org.evosuite.runtime.EvoRunner;
import org.evosuite.runtime.EvoRunnerParameters;
import org.junit.runner.RunWith;

@RunWith(EvoRunner.class) @EvoRunnerParameters(mockJVMNonDeterminism = true, useVFS = true, useVNET = true, resetStaticState = true, separateClassLoader = true, useJEE = true) 
public class ConditionRouter_ESTest extends ConditionRouter_ESTest_scaffolding {

  @Test(timeout = 4000)
  public void test00()  throws Throwable  {
      URL uRL0 = new URL("com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter$1", (String) null, (String) null, "*`|%LJ$ ", 0, "com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter$1");
      URL uRL1 = uRL0.addParameter("com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter$1", (byte) (-7));
      URL uRL2 = uRL1.addParameterIfAbsent("rule", "com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter$1");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL2);
      RpcInvocation rpcInvocation0 = new RpcInvocation();
      LinkedList<Invoker<ConditionRouter>> linkedList0 = new LinkedList<Invoker<ConditionRouter>>();
      InvokerWrapper<ConditionRouter> invokerWrapper0 = new InvokerWrapper<ConditionRouter>((Invoker<ConditionRouter>) null, uRL2);
      linkedList0.offerFirst(invokerWrapper0);
      List<Invoker<ConditionRouter>> list0 = conditionRouter0.route((List<Invoker<ConditionRouter>>) linkedList0, uRL1, (Invocation) rpcInvocation0);
      assertFalse(list0.isEmpty());
  }

  @Test(timeout = 4000)
  public void test01()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, "*`|%LJ$ ", 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "D vAb^ =O");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      RpcInvocation rpcInvocation0 = new RpcInvocation();
      LinkedList<Invoker<ConditionRouter>> linkedList0 = new LinkedList<Invoker<ConditionRouter>>();
      linkedList0.add((Invoker<ConditionRouter>) null);
      List<Invoker<ConditionRouter>> list0 = conditionRouter0.route((List<Invoker<ConditionRouter>>) linkedList0, uRL0, (Invocation) rpcInvocation0);
      assertEquals(1, list0.size());
  }

  @Test(timeout = 4000)
  public void test02()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, "*`|%LJ$ ", 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "D vAb^ =O");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      RpcInvocation rpcInvocation0 = new RpcInvocation();
      boolean boolean0 = conditionRouter0.matchWhen(uRL1, rpcInvocation0);
      assertTrue(boolean0);
  }

  @Test(timeout = 4000)
  public void test03()  throws Throwable  {
      URL uRL0 = new URL("9#9J=?c/l$&a&~P", "9#9J=?c/l$&a&~P", "9#9J=?c/l$&a&~P", "*`|%LJ$ ", (-20), "9#9J=?c/l$&a&~P");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "rule");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      URL uRL2 = conditionRouter0.getUrl();
      assertNotSame(uRL0, uRL2);
  }

  @Test(timeout = 4000)
  public void test04()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, "*`|%LJ$ ", 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "D vAb^ =O");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      URL uRL2 = uRL1.setUsername("hSW");
      ConditionRouter conditionRouter1 = new ConditionRouter(uRL2);
      int int0 = conditionRouter0.compareTo((Router) conditionRouter1);
      assertEquals((-62), int0);
  }

  @Test(timeout = 4000)
  public void test05()  throws Throwable  {
      ConditionRouter conditionRouter0 = null;
      try {
        conditionRouter0 = new ConditionRouter((URL) null);
        fail("Expecting exception: NullPointerException");
      
      } catch(NullPointerException e) {
         //
         // no message in exception (getMessage() returned null)
         //
         verifyException("com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter", e);
      }
  }

  @Test(timeout = 4000)
  public void test06()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, "*`|%LJ$ ", 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "6<a%d*$n3");
      ConditionRouter conditionRouter0 = null;
      try {
        conditionRouter0 = new ConditionRouter(uRL1);
        fail("Expecting exception: IllegalArgumentException");
      
      } catch(IllegalArgumentException e) {
         //
         // URLDecoder: Illegal hex characters in escape (%) pattern - For input string: \"d*\"
         //
         verifyException("java.net.URLDecoder", e);
      }
  }

  @Test(timeout = 4000)
  public void test07()  throws Throwable  {
      URL uRL0 = new URL("=", (String) null, (String) null, "*`|%LJ$ ", 0, "=");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "=");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      RpcInvocation rpcInvocation0 = new RpcInvocation();
      LinkedList<Invoker<ConditionRouter>> linkedList0 = new LinkedList<Invoker<ConditionRouter>>();
      InvokerWrapper<ConditionRouter> invokerWrapper0 = new InvokerWrapper<ConditionRouter>((Invoker<ConditionRouter>) null, uRL0);
      linkedList0.offerFirst(invokerWrapper0);
      List<Invoker<ConditionRouter>> list0 = conditionRouter0.route((List<Invoker<ConditionRouter>>) linkedList0, uRL1, (Invocation) rpcInvocation0);
      assertEquals(1, list0.size());
  }

  @Test(timeout = 4000)
  public void test08()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, (String) null, 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "D vAb^ =O");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      int int0 = conditionRouter0.compareTo((Router) conditionRouter0);
      assertEquals(0, int0);
  }

  @Test(timeout = 4000)
  public void test09()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, "*`|%LJ$ ", 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "D vAb^ =O");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      MockInvokersSelector mockInvokersSelector0 = new MockInvokersSelector();
      int int0 = conditionRouter0.compareTo((Router) mockInvokersSelector0);
      assertEquals(1, int0);
  }

  @Test(timeout = 4000)
  public void test10()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, "*`|%LJ$ ", 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "D vAb^ =O");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      int int0 = conditionRouter0.compareTo((Router) null);
      assertEquals(1, int0);
  }

  @Test(timeout = 4000)
  public void test11()  throws Throwable  {
      URL uRL0 = new URL("com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter$1", (String) null, (String) null, "*`|%LJ$ ", 0, "com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter$1");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter$1");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      RpcInvocation rpcInvocation0 = new RpcInvocation();
      LinkedList<Invoker<ConditionRouter>> linkedList0 = new LinkedList<Invoker<ConditionRouter>>();
      InvokerWrapper<ConditionRouter> invokerWrapper0 = new InvokerWrapper<ConditionRouter>((Invoker<ConditionRouter>) null, uRL1);
      linkedList0.offerFirst(invokerWrapper0);
      List<Invoker<ConditionRouter>> list0 = conditionRouter0.route((List<Invoker<ConditionRouter>>) linkedList0, uRL0, (Invocation) rpcInvocation0);
      assertEquals(1, linkedList0.size());
      assertFalse(list0.isEmpty());
  }

  @Test(timeout = 4000)
  public void test12()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, "*`|%LJ$ ", 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "D vAb^ =O");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      RpcInvocation rpcInvocation0 = new RpcInvocation();
      LinkedList<Invoker<ConditionRouter>> linkedList0 = new LinkedList<Invoker<ConditionRouter>>();
      InvokerWrapper<ConditionRouter> invokerWrapper0 = new InvokerWrapper<ConditionRouter>((Invoker<ConditionRouter>) null, uRL0);
      linkedList0.offerFirst(invokerWrapper0);
      List<Invoker<ConditionRouter>> list0 = conditionRouter0.route((List<Invoker<ConditionRouter>>) linkedList0, uRL1, (Invocation) rpcInvocation0);
      assertEquals(1, list0.size());
  }

  @Test(timeout = 4000)
  public void test13()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, "*`|%LJ$ ", 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "D vAb^ =O");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      RpcInvocation rpcInvocation0 = new RpcInvocation();
      LinkedList<Invoker<ConditionRouter>> linkedList0 = new LinkedList<Invoker<ConditionRouter>>();
      List<Invoker<ConditionRouter>> list0 = conditionRouter0.route((List<Invoker<ConditionRouter>>) linkedList0, uRL0, (Invocation) rpcInvocation0);
      assertTrue(list0.isEmpty());
  }

  @Test(timeout = 4000)
  public void test14()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", (String) null, (String) null, (String) null, 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "D vAb^ =O");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      RpcInvocation rpcInvocation0 = new RpcInvocation();
      List<Invoker<Invoker<MockInvokersSelector>>> list0 = conditionRouter0.route((List<Invoker<Invoker<MockInvokersSelector>>>) null, uRL0, (Invocation) rpcInvocation0);
      assertNull(list0);
  }

  @Test(timeout = 4000)
  public void test15()  throws Throwable  {
      URL uRL0 = new URL("D vAb^ =O", "D vAb^ =O", "D vAb^ =O", "D vAb^ =O", 0, "D vAb^ =O");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", ", attachments=");
      ConditionRouter conditionRouter0 = null;
      try {
        conditionRouter0 = new ConditionRouter(uRL1);
        fail("Expecting exception: IllegalStateException");
      
      } catch(IllegalStateException e) {
         //
         // Illegal route rule \", attachments=\", The error char ',' at index 0 before \"attachments\".
         //
         verifyException("com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter", e);
      }
  }

  @Test(timeout = 4000)
  public void test16()  throws Throwable  {
      URL uRL0 = new URL("_3O;&i<!|fwS", (String) null, (String) null, "_3O;&i<!|fwS", 0, "_3O;&i<!|fwS");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "_3O;&i<!|fwS");
      ConditionRouter conditionRouter0 = null;
      try {
        conditionRouter0 = new ConditionRouter(uRL1);
        fail("Expecting exception: IllegalStateException");
      
      } catch(IllegalStateException e) {
         //
         // Illegal route rule \"_3O;&i<!|fwS\", The error char '!' at index 7 before \"|fwS\".
         //
         verifyException("com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter", e);
      }
  }

  @Test(timeout = 4000)
  public void test17()  throws Throwable  {
      URL uRL0 = new URL("=>", "=>", "=>", "=>", 0, "=>");
      URL uRL1 = uRL0.addParameterIfAbsent("rule", "=>");
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
  }

  @Test(timeout = 4000)
  public void test18()  throws Throwable  {
      String[] stringArray0 = new String[4];
      URL uRL0 = new URL(" before \"", "", "", "ejc", 2, "ejc", stringArray0);
      ConditionRouter conditionRouter0 = null;
      try {
        conditionRouter0 = new ConditionRouter(uRL0);
        fail("Expecting exception: IllegalArgumentException");
      
      } catch(IllegalArgumentException e) {
         //
         // Illegal route rule!
         //
         verifyException("com.alibaba.dubbo.rpc.cluster.router.condition.ConditionRouter", e);
      }
  }

  @Test(timeout = 4000)
  public void test19()  throws Throwable  {
      URL uRL0 = new URL("*`|%LJ$ ", ", attachment4s=", 4622, "-1LRSr9");
      URL uRL1 = uRL0.addParameter("rule", false);
      ConditionRouter conditionRouter0 = new ConditionRouter(uRL1);
      URL uRL2 = conditionRouter0.getUrl();
      assertSame(uRL2, uRL1);
  }
}