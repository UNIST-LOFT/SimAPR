package edu.uni.lu.serval.fixminer.fixtemplate;

import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.FixTemplate;
import edu.lu.uni.serval.utils.Checker;

/**
 * Change operator in the conditional infix-expression of if statement.
 * 
 * @author kui.liu
 *
 */
public class IfOperator extends FixTemplate {

	public void generatePatches() {
		ITree suspCodeTree = this.getSuspiciousCodeTree();
		ITree suspExpTree = suspCodeTree.getChild(0);
		if (Checker.isComplexExpression(suspExpTree.getType())) {
			if (Checker.isInfixExpression(suspExpTree.getType())) {
				fixOperatore(suspExpTree);
			}
			fixSubInfixExpressions(suspExpTree);
		}
	}

	private void fixSubInfixExpressions(ITree suspExpTree) {
		List<ITree> children = suspExpTree.getChildren();
		
		for (ITree child : children) {
			if (Checker.isComplexExpression(child.getType())) {
				if (Checker.isInfixExpression(child.getType())) {
					fixOperatore(child);
					// TODO: how to fix them together?
				}
				fixSubInfixExpressions(child);
			}
		}
	}

	private void fixOperatore(ITree suspExpTree) {
		ITree operator = suspExpTree.getChild(1);
		int startPos = operator.getPos();
		int endPos = suspExpTree.getChild(2).getPos();
		String codePart1 = this.getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
		String codePart2 = this.getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
		
		String op = operator.getLabel();
		if ("&&".equals(op)) {
			String fixedCodeStr1 = codePart1 + " || " + codePart2;
			this.generatePatch(fixedCodeStr1);
		} else if ("||".equals(op)) {
			String fixedCodeStr1 = codePart1 + " && " + codePart2;
			this.generatePatch(fixedCodeStr1);
		} else if ("==".equals(op)) {
			String fixedCodeStr1 = codePart1 + " != " + codePart2;
			this.generatePatch(fixedCodeStr1);
		} else if ("!=".equals(op)) {
			String fixedCodeStr1 = codePart1 + " == " + codePart2;
			this.generatePatch(fixedCodeStr1);
		} else if (">".equals(op)) {
			String fixedCodeStr1 = codePart1 + " >= " + codePart2;
			this.generatePatch(fixedCodeStr1);
			fixedCodeStr1 = codePart1 + " <= " + codePart2;
			this.generatePatch(fixedCodeStr1);
			fixedCodeStr1 = codePart1 + " < " + codePart2;
			this.generatePatch(fixedCodeStr1);
		} else if (">=".equals(op)) {
			String fixedCodeStr1 = codePart1 + " > " + codePart2;
			this.generatePatch(fixedCodeStr1);
			fixedCodeStr1 = codePart1 + " < " + codePart2;
			this.generatePatch(fixedCodeStr1);
			fixedCodeStr1 = codePart1 + " <= " + codePart2;
			this.generatePatch(fixedCodeStr1);
		} else if ("<".equals(op)) {
			String fixedCodeStr1 = codePart1 + " <= " + codePart2;
			this.generatePatch(fixedCodeStr1);
			fixedCodeStr1 = codePart1 + " >= " + codePart2;
			this.generatePatch(fixedCodeStr1);
			fixedCodeStr1 = codePart1 + " > " + codePart2;
			this.generatePatch(fixedCodeStr1);
		} else if ("<=".equals(op)) {
			String fixedCodeStr1 = codePart1 + " < " + codePart2;
			this.generatePatch(fixedCodeStr1);
			fixedCodeStr1 = codePart1 + " > " + codePart2;
			this.generatePatch(fixedCodeStr1);
			fixedCodeStr1 = codePart1 + " >= " + codePart2;
			this.generatePatch(fixedCodeStr1);
		}
	}

}
