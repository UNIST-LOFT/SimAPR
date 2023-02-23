package edu.uni.lu.serval.fixminer.fixtemplate;

import java.util.ArrayList;
import java.util.List;

import edu.lu.uni.serval.jdt.tree.ITree;
import edu.lu.uni.serval.templates.FixTemplate;
import edu.lu.uni.serval.utils.Checker;

/**
 * Modify the value of Boolean variable.
 * @author kui.liu
 *
 */
public class ModifyBooleanValue extends FixTemplate {

	@Override
	public void generatePatches() {
		List<ITree> suspBooleanLiteral = identifyAllBooleanLiteral(this.getSuspiciousCodeTree());
		for (ITree booleanLiteral : suspBooleanLiteral) {
			int startPos = booleanLiteral.getPos();
			int endPos = startPos + booleanLiteral.getLength();
			String codePart1 = getSubSuspiciouCodeStr(suspCodeStartPos, startPos);
			String codePart2 = getSubSuspiciouCodeStr(endPos, suspCodeEndPos);
			boolean boolVal = Boolean.valueOf(booleanLiteral.getLabel());
			// update (reverse) the boolean value.
			if (boolVal) {
				codePart2 = "false" + codePart2;
			} else {
				codePart2 = "true" + codePart2;
			}
			generatePatch(codePart1 + codePart2);
		}
	}
	
	private List<ITree> identifyAllBooleanLiteral(ITree codeAst) {
		List<ITree> suspBooleanLiteral = new ArrayList<>();
		List<ITree> children = codeAst.getChildren();
		for (ITree child : children) {
			int type = child.getType();
			if (Checker.isComplexExpression(type)) 
				suspBooleanLiteral.addAll(identifyAllBooleanLiteral(child));
			else if (Checker.isBooleanLiteral(type))
				suspBooleanLiteral.add(child);
			else if (Checker.isStatement(type) || Checker.isMethodDeclaration(type))
				break;
		}
		return suspBooleanLiteral;
	}
	
}
