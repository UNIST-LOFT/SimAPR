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
public class ModifyIfStmtMethodName extends AlterMethodInvocation {
	
	/*
	 * UPD IfStatement
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
		ITree suspExpTree = children.get(0);
		if (Checker.isMethodInvocation(suspExpTree.getType())) {
			ModifyMethodInvocation mmi = new ModifyMethodInvocation(suspExpTree, ModifyType.MethodName);
			mmi.returnTypeStr = "boolean";
			mmi.setSuspiciousCodeStr(this.getSuspiciousCodeStr());
			mmi.setSuspiciousCodeTree(this.getSuspiciousCodeTree());
			mmi.setSourceCodePath(this.sourceCodePath);
			mmi.setSuspJavaFileCode(this.getSuspJavaFileCode());
			mmi.setLiterals(literals);
			mmi.generatePatches();
			this.getPatches().addAll(mmi.getPatches());
		}
	}
	

}
