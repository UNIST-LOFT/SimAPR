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
public class ModifyMethodQualifiedArgument extends AlterMethodInvocation {
	
	/*
	 * MethodInvocation Variable Parameter: INS, DEL, UPD
	 * UPD ExpressionStatement/ReturnStatement/IfStatement
	 * ---UPD MethodInvocation
	 * ------UPD SimpleName
	 * ---------UPD QualifiedName
	 */
	
	@Override
	public void generatePatches() {
		ITree suspCodeAst = this.getSuspiciousCodeTree();
		int suspCodeAstType = suspCodeAst.getType();
		String returnTypeStr = null;
		if (Checker.isReturnStatement(suspCodeAstType)) returnTypeStr = "=ReturnType=";
		else if (Checker.isExpressionStatement(suspCodeAstType)) returnTypeStr = "=Void=";
		else if (Checker.isIfStatement(suspCodeAstType)) returnTypeStr = "boolean";
		
		if (returnTypeStr == null) return;
		
		List<ITree> children = suspCodeAst.getChildren();
		if (children.isEmpty()) return;
		ITree suspExpAst = children.get(0);
		if (!Checker.isMethodInvocation(suspExpAst.getType())) return;
		
		ModifyMethodInvocation mmi = new ModifyMethodInvocation(suspExpAst, ModifyType.SubVarArgument);
		mmi.returnTypeStr = returnTypeStr;
		mmi.setSuspiciousCodeStr(this.getSuspiciousCodeStr());
		mmi.setSuspiciousCodeTree(this.getSuspiciousCodeTree());
		mmi.setSourceCodePath(this.sourceCodePath);
		mmi.setSuspJavaFileCode(this.getSuspJavaFileCode());
		mmi.setLiterals(literals);
		mmi.generatePatches();
		this.getPatches().addAll(mmi.getPatches());
	}
	
}
