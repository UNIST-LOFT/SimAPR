package edu.uni.lu.serval.fixminer.fixtemplate;

import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.AlterMethodInvocation;
import edu.lu.uni.serval.utils.Checker;
import edu.uni.lu.serval.fixminer.fixtemplate.ModifyMethodInvocation.ModifyType;

/**
 * 
 * @author kui.liu
 *
 */
public class ModifyReturnStmtMethodName extends AlterMethodInvocation {
	
	/*
	 * UPD ReturnStatement
	 * ---UPD MethodInvocation
	 * ------UPD SimpleName(method name)/INS SimpleName(e.g., Utils)
	 *
	 * 1. method1() -> method1
	 * 2. exp.method2(...) -> method2
	 */
	
	
	@Override
	public void generatePatches() {
		ITree suspCodeAst = this.getSuspiciousCodeTree();
		
		List<ITree> children = suspCodeAst.getChildren();
		if (children.size() != 1) return;
		ITree suspExpTree = children.get(0);
		if (Checker.isMethodInvocation(suspExpTree.getType())) {
			ModifyMethodInvocation mmi = new ModifyMethodInvocation(suspExpTree, ModifyType.MethodName);
			mmi.returnTypeStr = "=ReturnType=";
			mmi.setSuspiciousCodeStr(this.getSuspiciousCodeStr());
			mmi.setSuspiciousCodeTree(this.getSuspiciousCodeTree());
			mmi.setSourceCodePath(this.sourceCodePath);
			mmi.setSuspJavaFileCode(this.getSuspJavaFileCode());
			mmi.generatePatches();
			this.getPatches().addAll(mmi.getPatches());
		}
	}
	

}
