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
public class ModifyVarDecStmtMethodName extends AlterMethodInvocation {
	
	/*
	 * UPD VariableDeclarationStatement
	 * ---UPD VariableDeclarationFragment
	 * ------UPD MethodInvocation
	 * ---------UPD SimpleName(method name)
	 *
	 * 1. method1() -> method1
	 * 2. exp.method2() -> method2
	 */
	
	
	@Override
	public void generatePatches() {
		ITree suspCodeAst = this.getSuspiciousCodeTree();
		
		List<ITree> children = suspCodeAst.getChildren();
		List<ITree> fragments = null;
		String returnType = null;
		for (int index = 0, size = children.size(); index < size; index ++) {
			ITree child = children.get(index);
			if (Checker.isModifier(child.getType())) continue;
			returnType = this.readType(child.getLabel());
			fragments = children.subList(index + 1, size);
			break;
		}
		
		if (returnType == null || fragments == null || fragments.isEmpty()) return;
		
		for (ITree fragment : fragments) {
			children = fragment.getChildren();
			if (children.size() == 2) {
				ITree suspExpTree = children.get(1);
				
				if (Checker.isMethodInvocation(suspExpTree.getType())) {
					ModifyMethodInvocation mmi = new ModifyMethodInvocation(suspExpTree, ModifyType.MethodName);
					mmi.returnTypeStr = returnType;
					mmi.setSuspiciousCodeStr(this.getSuspiciousCodeStr());
					mmi.setSuspiciousCodeTree(this.getSuspiciousCodeTree());
					mmi.setSourceCodePath(this.sourceCodePath);
					mmi.setSuspJavaFileCode(this.getSuspJavaFileCode());
					mmi.generatePatches();
					this.getPatches().addAll(mmi.getPatches());
				}
			}
		}
	}
	
}
