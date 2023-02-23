package edu.uni.lu.serval.fixminer.fixtemplate;

import java.util.ArrayList;
import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.FixTemplate;
import edu.lu.uni.serval.utils.Checker;

/**
 * Insert null-check for variables.
 * 
 * @author kui.liu
 *
 */
public class IfNullChecker extends FixTemplate {

	@Override
	public void generatePatches() {
		ITree suspCodeTree = this.getSuspiciousCodeTree();
		int type = suspCodeTree.getType();
		
		if (Checker.isReturnStatement(type) && !isBooleanReturnType(suspCodeTree)) return;
		
		ITree suspExpTree = suspCodeTree.getChild(0);
		if (Checker.isMethodInvocation(suspExpTree.getType())) {
			List<ITree> variables = identifyVariables(suspExpTree);
			int startPos = suspExpTree.getPos();
			String codePart1 = this.getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
			String codePart2 = this.getSubSuspiciouCodeStr(startPos, suspCodeEndPos);
			for (ITree var : variables) {
				String label = var.getLabel();
				if (label.startsWith("Name:")) label = label.substring(5);
				String fixedCodeStr1 = codePart1 + label + " != null && " + codePart2;
				this.generatePatch(fixedCodeStr1);
				fixedCodeStr1 = codePart1 + label + " != null || " + codePart2;
				this.generatePatch(fixedCodeStr1);
			}
		}
	}

	private boolean isBooleanReturnType(ITree suspCodeTree) {
		ITree parentTree = suspCodeTree.getParent();
		while (true) {
			if (Checker.isMethodDeclaration(parentTree.getType()))
				break;
			if (Checker.isTypeDeclaration(parentTree.getType())) {
				parentTree = null;
				break;
			}
			parentTree = parentTree.getParent();
		}
		
		if (parentTree == null) return false;
		
		String label = parentTree.getLabel();
		int indexOfMethodName = label.indexOf("MethodName:");
		
		// Read return type.
		String returnType = label.substring(label.indexOf("@@") + 2, indexOfMethodName - 2);
		int index = returnType.indexOf("@@tp:");
		if (index > 0) returnType = returnType.substring(0, index - 2);
		
		returnType = readType(returnType);

		return returnType.equalsIgnoreCase("boolean");
	}

	private List<ITree> identifyVariables(ITree codeAst) {
		List<ITree> variables = new ArrayList<>();
		List<ITree> children = codeAst.getChildren();
		for (ITree child : children) {
			int type = child.getType();
			if (Checker.isComplexExpression(type)) 
				variables.addAll(identifyVariables(child));
			else if (Checker.isSimpleName(type)) {
				String label = child.getLabel();
				if (label.startsWith("MethodName:")) continue;
				variables.add(child);
			} else if (Checker.isStatement(type) || Checker.isMethodDeclaration(type))
				break;
		}
		return variables;
	}

}
