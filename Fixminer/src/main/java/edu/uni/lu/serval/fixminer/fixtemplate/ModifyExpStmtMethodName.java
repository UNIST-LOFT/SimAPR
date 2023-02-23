package edu.uni.lu.serval.fixminer.fixtemplate;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.AlterMethodInvocation;
import edu.lu.uni.serval.utils.Checker;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyMethodInvocation.ModifyType;

/**
 * 
 * @author kui.liu
 *
 */
public class ModifyExpStmtMethodName extends AlterMethodInvocation {
	
	/*
	 * UPD ExpressionStatement
	 * ---UPD MethodInvocation
	 * ------UPD SimpleName(method name)
	 *
	 * 1. method1() -> method1
	 * 2. exp.method2() -> method2
	 */
	
	@Override
	public void generatePatches() {
		ITree suspCodeAst = this.getSuspiciousCodeTree();
		
		ITree suspExpTree = suspCodeAst.getChildren().get(0);
		if (Checker.isMethodInvocation(suspExpTree.getType())) {
			ModifyMethodInvocation mmi = new ModifyMethodInvocation(suspExpTree, ModifyType.MethodName);
			mmi.setSuspiciousCodeStr(this.getSuspiciousCodeStr());
			mmi.setSuspiciousCodeTree(this.getSuspiciousCodeTree());
			mmi.setSourceCodePath(this.sourceCodePath);
			mmi.setSuspJavaFileCode(this.getSuspJavaFileCode());
			mmi.generatePatches();
			this.getPatches().addAll(mmi.getPatches());
		}
	}
	
}
